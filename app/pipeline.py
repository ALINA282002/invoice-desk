"""The invoice-to-decision pipeline.

Design principle: AI (or OCR + parser) *reads* the invoice; deterministic, auditable rules *decide*.
Every stage records the checks it ran, so a reviewer can see exactly why a decision was made.
All stages always run (no short-circuit) so a reviewer gets the full picture in one pass.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import queue
import re
import threading
import time
import traceback
import uuid
from datetime import date, datetime, timedelta
from typing import Any

from rapidfuzz import fuzz

from . import db
from .extraction import (claude_available, claude_extract, claude_summarise, grounding_report, name_similarity, read_document,
                         rule_extract)

log = logging.getLogger("pipeline")

STAGE_MIN_MS = int(os.environ.get("STAGE_MIN_MS", "350"))  # pacing so people can follow the live view

STAGES = [
    ("intake", "Receive", "Register the file and fingerprint it"),
    ("read", "Read document", "PDF text layer, or OCR for scanned pages"),
    ("extract", "Extract fields", "Vendor, numbers, dates, PO, lines, remit-to"),
    ("validate", "Validate", "Required fields, addressee, arithmetic, tax, dates"),
    ("vendor", "Verify vendor", "Vendor master, status, bank details, sender domain"),
    ("po_match", "Match purchase order", "Find PO, match lines, tolerance, PO balance"),
    ("duplicate", "Duplicate check", "Same file, same/re-numbered number, same charge"),
    ("decide", "Decide", "Apply approval policy, explain, route"),
]

REASON_TITLES = {
    "MISSING_REQUIRED_FIELDS": "Required fields missing", "UNREADABLE": "Document unreadable",
    "LOW_OCR_CONFIDENCE": "Poor scan quality", "LOW_EXTRACTION_CONFIDENCE": "Extraction not verifiable",
    "BILL_TO_MISMATCH": "Addressed to another company",
    "LINE_ARITHMETIC": "Line maths don't add up", "SUBTOTAL_MISMATCH": "Lines don't match subtotal",
    "TOTAL_MISMATCH": "Totals don't reconcile", "TAX_RATE": "Tax rate implausible", "FUTURE_DATED": "Future-dated",
    "STALE_INVOICE": "Invoice too old", "VENDOR_UNKNOWN": "Vendor not in vendor master",
    "VENDOR_FUZZY_MATCH": "Vendor identity uncertain", "VENDOR_BLOCKED": "Vendor is blocked",
    "VENDOR_NOT_ACTIVE": "Vendor not approved for payment", "BANK_DETAILS_CHANGED": "Bank details changed",
    "EMAIL_DOMAIN_MISMATCH": "Sender domain mismatch", "TAX_ID_MISMATCH": "Tax ID mismatch",
    "DUPLICATE_EXACT_FILE": "Same file already received", "DUPLICATE_INVOICE": "Duplicate invoice number",
    "DUPLICATE_RENUMBERED": "Re-numbered duplicate", "POSSIBLE_DUPLICATE": "Possible duplicate charge",
    "PO_NOT_FOUND": "PO not found", "PO_UNDETERMINED": "PO could not be determined", "PO_INFERRED": "PO inferred",
    "PO_VENDOR_MISMATCH": "PO belongs to another vendor", "PO_CLOSED": "PO is closed",
    "CURRENCY_MISMATCH": "Currency differs from PO", "LINE_NOT_ON_PO": "Charges not on PO",
    "PRICE_VARIANCE": "Price over tolerance", "PO_OVERBILLED": "PO over-billed",
    "ABOVE_AUTO_APPROVE_LIMIT": "Above approval limit", "STAGE_ERROR": "Processing error",
}

OUTCOME_RANK = {"APPROVED": 0, "NEEDS_REVIEW": 1, "ON_HOLD": 2, "REJECTED": 3}


def TODAY() -> date:
    return date.fromisoformat(os.environ.get("AP_TODAY", date.today().isoformat()))


def money(v: float | None, cur: str = "USD") -> str:
    if v is None:
        return "—"
    sym = {"USD": "$", "EUR": "€", "GBP": "£"}.get(cur or "USD", "")
    return f"{sym}{v:,.2f}" if sym else f"{v:,.2f} {cur}"


def human_list(xs: list[str]) -> str:
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def norm_inv(s: str | None) -> str:
    return re.sub(r"[^A-Z0-9]", "", (s or "").upper())


def base_inv(s: str | None) -> str:
    """Strip re-issue suffixes vendors add to resubmissions: -R, -A, -COPY, -REV2, (2) ..."""
    s = (s or "").upper().strip()
    s = re.sub(r"(?:[\s\-_/]+(?:R|A|B|C|COPY|DUP|DUPLICATE|REV\d*|REISSUED?|V\d+|\d)|\(\d+\))$", "", s)
    return norm_inv(s)


def po_digits(s: str | None) -> str:
    return re.sub(r"\D", "", s or "")


def vendor_norm(s: str) -> str:
    s = s.lower()
    s = re.sub(r"\b(inc|llc|ltd|co|corp|corporation|company|limited|plc|gmbh)\b\.?", "", s)
    return re.sub(r"[^a-z0-9 ]", "", s).strip()


def email_domain(e: str | None) -> str | None:
    return e.split("@", 1)[1].lower() if e and "@" in e else None


# =====================================================================================
class LiveRun:
    def __init__(self, run_id: str, filename: str, source: str):
        self.id, self.filename, self.source = run_id, filename, source
        self.events: list[dict[str, Any]] = []
        self.cond = threading.Condition()
        self.done = False
        self.stages: dict[str, dict[str, Any]] = {}
        for i, (key, title, desc) in enumerate(STAGES):
            self.stages[key] = {"key": key, "index": i + 1, "title": title, "description": desc,
                                "status": "pending", "summary": "", "checks": [], "data": {}}
        self.reasons: list[dict[str, Any]] = []
        self.notes: list[str] = []
        self.ctx: dict[str, Any] = {}

    def emit(self, ev: dict[str, Any]) -> None:
        with self.cond:
            ev["seq"] = len(self.events)
            self.events.append(json.loads(json.dumps(ev, default=str)))
            self.cond.notify_all()

    def reason(self, code: str, outcome: str, message: str, stage: str) -> None:
        if any(r["code"] == code and r["message"] == message for r in self.reasons):
            return
        self.reasons.append({"code": code, "title": REASON_TITLES.get(code, code), "outcome": outcome,
                             "message": message, "stage": stage})


class Stage:
    def __init__(self, run: LiveRun, key: str):
        self.run, self.key = run, key
        self.s = run.stages[key]

    def check(self, label: str, status: str, detail: str = "") -> None:
        self.s["checks"].append({"label": label, "status": status, "detail": detail})

    def __enter__(self):
        self.t0 = time.perf_counter()
        self.s["status"] = "running"
        self.s["started_at"] = db.now_iso()
        self.run.emit({"type": "stage", "stage": self.s})
        return self

    def __exit__(self, et, ev, tb):
        compute = (time.perf_counter() - self.t0) * 1000
        if et is not None:
            self.s["status"] = "failed"
            self.check("Stage error", "fail", f"{et.__name__}: {ev}")
            self.s["summary"] = self.s["summary"] or "Stage raised an error"
            self.run.reason("STAGE_ERROR", "NEEDS_REVIEW", f"{self.s['title']} failed: {ev}", self.key)
            log.error("stage %s failed\n%s", self.key, "".join(traceback.format_exception(et, ev, tb)))
        elif self.s["status"] == "running":
            sts = {c["status"] for c in self.s["checks"]}
            self.s["status"] = "failed" if "fail" in sts else ("warning" if "warn" in sts else "passed")
        if compute < STAGE_MIN_MS:
            time.sleep((STAGE_MIN_MS - compute) / 1000)
        self.s["compute_ms"] = round(compute)
        self.s["ended_at"] = db.now_iso()
        self.run.emit({"type": "stage", "stage": self.s})
        return True  # pipeline continues; the error is recorded as a review reason


# =====================================================================================
# Processing queue: strictly first-in-first-out, one invoice at a time, so duplicate and
# PO-balance checks always see every earlier invoice.
LIVE: dict[str, LiveRun] = {}
_jobs: "queue.Queue[tuple[LiveRun, bytes]]" = queue.Queue()


def _worker() -> None:
    while True:
        lr, data = _jobs.get()
        try:
            execute(lr, data)
        except Exception as e:  # last-resort guard: never leave a run hanging
            log.exception("run failed")
            with db.tx() as c:
                c.execute("UPDATE runs SET state='error', error=?, finished_at=? WHERE id=?",
                          (str(e), db.now_iso(), lr.id))
            lr.emit({"type": "run_error", "error": str(e)})
        finally:
            with lr.cond:
                lr.done = True
                lr.cond.notify_all()
            _jobs.task_done()


threading.Thread(target=_worker, daemon=True, name="invoice-worker").start()


def start_run(pdf_bytes: bytes, filename: str, source: str) -> str:
    run_id = datetime.now().strftime("INV%y%m%d-%H%M%S-") + uuid.uuid4().hex[:4].upper()
    db.FILES.mkdir(parents=True, exist_ok=True)
    (db.FILES / f"{run_id}.pdf").write_bytes(pdf_bytes)
    with db.tx() as c:
        c.execute("INSERT INTO runs (id, created_at, source, filename, state) VALUES (?,?,?,?,?)",
                  (run_id, db.now_iso(), source, filename, "queued"))
    lr = LiveRun(run_id, filename, source)
    LIVE[run_id] = lr
    lr.emit({"type": "run_queued", "run_id": run_id, "filename": filename, "source": source,
             "stages": list(lr.stages.values())})
    _jobs.put((lr, pdf_bytes))
    return run_id


def busy() -> bool:
    return any(not lr.done for lr in LIVE.values())


# =====================================================================================
def execute(lr: LiveRun, pdf_bytes: bytes) -> None:
    t_start = time.perf_counter()
    with db.tx() as c:
        c.execute("UPDATE runs SET state='running' WHERE id=?", (lr.id,))
    ctx = lr.ctx
    ctx["policy"] = db.get_policy()
    ctx["company"] = db.get_company()
    lr.emit({"type": "run_started", "run_id": lr.id})

    stage_intake(lr, pdf_bytes)
    stage_read(lr, pdf_bytes)
    stage_extract(lr, pdf_bytes)
    stage_validate(lr)
    stage_vendor(lr)
    stage_po_match(lr)
    stage_duplicate(lr)
    result = stage_decide(lr)

    duration = round((time.perf_counter() - t_start) * 1000)
    f = ctx.get("fields", {})
    vendor = ctx.get("vendor") or {}
    with db.tx() as c:
        c.execute("""UPDATE runs SET state='done', finished_at=?, file_hash=?, decision=?, final_status=?,
                     vendor_id=?, vendor_name=?, invoice_number=?, invoice_date=?, due_date=?, po_number=?, total=?,
                     currency=?, duration_ms=?, extractor=?, read_method=?, pages=?, headline=?, reason_codes=?,
                     queue=?, line_sig=?, trace=?, result=? WHERE id=?""", (
            db.now_iso(), ctx.get("sha256"), result["decision"], result["final_status"], vendor.get("vendor_id"),
            vendor.get("name") or f.get("vendor_name"), f.get("invoice_number"), f.get("invoice_date"),
            result.get("payment_due"), (ctx.get("po") or {}).get("po_number") or f.get("po_number"), f.get("total"),
            f.get("currency"), duration, ctx.get("extractor"), ctx.get("read_method"),
            (ctx.get("doc") or {}).get("page_count"), result["headline"],
            ",".join(sorted({r["code"] for r in result["reasons"]})), result.get("queue"), ctx.get("line_sig"),
            json.dumps(list(lr.stages.values()), default=str), json.dumps(result, default=str), lr.id))
    db.audit(lr.id, "System", f"Decision: {result['decision'].replace('_', ' ').title()}", result["headline"])
    lr.emit({"type": "run_completed", "run_id": lr.id, "result": result, "duration_ms": duration})


# ------------------------------------------------------------------------------- 1 intake
def stage_intake(lr: LiveRun, pdf_bytes: bytes) -> None:
    with Stage(lr, "intake") as st:
        sha = hashlib.sha256(pdf_bytes).hexdigest()
        lr.ctx["sha256"] = sha
        is_pdf = pdf_bytes[:5] == b"%PDF-"
        st.check("File is a PDF", "pass" if is_pdf else "fail", f"{len(pdf_bytes) / 1024:.1f} KB")
        if not is_pdf:
            raise ValueError("File is not a PDF")
        st.check("Fingerprint (SHA-256)", "info", sha[:16] + "…")
        st.check("Channel", "info", {"upload": "Uploaded by user", "inbox": "AP mailbox (watched folder)"}.get(
            lr.source, lr.source))
        st.s["data"] = {"filename": lr.filename, "bytes": len(pdf_bytes), "sha256": sha, "source": lr.source}
        st.s["summary"] = f"{lr.filename}"


# ------------------------------------------------------------------------------- 2 read
def stage_read(lr: LiveRun, pdf_bytes: bytes) -> None:
    with Stage(lr, "read") as st:
        doc = read_document(pdf_bytes)
        lr.ctx["doc"] = doc
        lr.ctx["read_method"] = doc["method"]
        for p in doc["pages"]:
            if p["method"] == "text_layer":
                st.check(f"Page {p['page']}: machine-readable text", "pass", f"{len(p['text'])} characters")
            else:
                st.check(f"Page {p['page']}: scanned image, no text layer", "info", "OCR performed on-device")
                if p["text"].strip():
                    low = p.get("low_share", 0.0)
                    ok = p["confidence"] >= 0.85 and low <= 0.05
                    st.check(f"Page {p['page']}: OCR quality", "pass" if ok else "warn",
                             f"{p['confidence'] * 100:.1f}% average confidence · {low * 100:.0f}% of text read uncertainly")
                    if not ok:
                        lr.reason("LOW_OCR_CONFIDENCE", "NEEDS_REVIEW",
                                  f"Scan quality is poor: {low * 100:.0f}% of the text on page {p['page']} was read with "
                                  "low confidence, so numbers may be misread. Confirm the extracted values against the "
                                  "image before paying.", "read")
        if len(doc["text"].strip()) < 20:
            st.check("Readable content", "fail", "No readable text on any page")
            lr.reason("UNREADABLE", "REJECTED", "The document has no readable content (blank or illegible scan). "
                      "Ask the vendor to resend a legible copy.", "read")
        st.s["data"] = {"method": doc["method"], "pages": doc["page_count"], "chars": len(doc["text"]),
                        "ocr_confidence": doc["ocr_confidence"], "text": doc["text"][:8000]}
        st.s["summary"] = ("Scanned — OCR" if doc["method"] == "ocr" else "Text layer") + \
            f" · {doc['page_count']} page{'s' if doc['page_count'] != 1 else ''}"


# ------------------------------------------------------------------------------- 3 extract
KEY_FIELDS = [("vendor_name", "Vendor"), ("invoice_number", "Invoice number"), ("invoice_date", "Invoice date"),
              ("po_number", "PO reference"), ("total", "Total"), ("line_items", "Line items")]


def _vendor_name_list() -> list[tuple[str, str]]:
    out = []
    for v in db.vendors():
        out.append((v["vendor_id"], v["name"]))
        out += [(v["vendor_id"], a) for a in (v["aliases"] or "").split("|") if a]
    return out


def stage_extract(lr: LiveRun, pdf_bytes: bytes) -> None:
    with Stage(lr, "extract") as st:
        text = lr.ctx["doc"]["text"]
        fields, extractor = None, "rules"
        if claude_available() and text.strip():
            try:
                fields = claude_extract(pdf_bytes)
                extractor = "claude"
                st.check("Extraction engine", "info", "Claude — structured JSON output")
            except Exception as e:
                st.check("Claude unavailable — used rule-based parser", "warn", str(e)[:160])
        if fields is None:
            fields = rule_extract(text, _vendor_name_list())
            st.check("Extraction engine", "info", "Rule-based parser (on-device)")
        fields.setdefault("line_items", [])
        fields.setdefault("bank", {})
        fields.setdefault("notes", [])
        fields["currency"] = (fields.get("currency") or lr.ctx["company"].get("currency") or "USD").upper()
        lr.ctx["fields"] = fields
        lr.ctx["extractor"] = extractor

        found = 0
        for k, label in KEY_FIELDS:
            v = fields.get(k)
            ok = bool(v) if k == "line_items" else v not in (None, "")
            found += ok
            disp = f"{len(v)} line(s)" if k == "line_items" else (
                money(v, fields["currency"]) if k == "total" and v is not None else v)
            st.check(label, "pass" if ok else ("info" if k == "po_number" else "warn"),
                     str(disp) if ok else "not found on document")
        grounding = grounding_report(fields, text)
        ungrounded = [k for k, ok in grounding.items() if not ok]
        if grounding:
            st.check("Values traceable to document text", "warn" if ungrounded else "pass",
                     ("Not found verbatim: " + ", ".join(ungrounded)) if ungrounded else f"{len(grounding)} key values verified")
        confidence = round(found / len(KEY_FIELDS) * (0.7 if ungrounded else 1.0), 2)
        lr.ctx["extraction_confidence"] = confidence
        if ungrounded and confidence < lr.ctx["policy"]["min_extraction_confidence"]:
            lr.reason("LOW_EXTRACTION_CONFIDENCE", "NEEDS_REVIEW",
                      "Some extracted values could not be traced back to the document text.", "extract")
        for n in (fields.get("notes") or [])[:4]:
            st.check("Note on invoice", "info", n)
        st.s["data"] = {"extractor": extractor, "fields": fields, "grounding": grounding, "confidence": confidence}
        st.s["summary"] = f"{found} of {len(KEY_FIELDS)} key fields · {len(fields['line_items'])} line items"


# ------------------------------------------------------------------------------- 4 validate
def stage_validate(lr: LiveRun) -> None:
    with Stage(lr, "validate") as st:
        f, pol, co = lr.ctx["fields"], lr.ctx["policy"], lr.ctx["company"]
        cur = f["currency"]
        missing = [label for k, label in [("vendor_name", "Vendor name"), ("invoice_number", "Invoice number"),
                                          ("invoice_date", "Invoice date"), ("total", "Total amount")]
                   if f.get(k) in (None, "")]
        if missing:
            st.check("Required fields present", "fail", "Missing: " + ", ".join(missing))
            lr.reason("MISSING_REQUIRED_FIELDS", "REJECTED",
                      f"The invoice is missing the {human_list([m.lower() for m in missing])}. Without an invoice number "
                      "there is no duplicate control; without a date there is no payment-term start.", "validate")
            lr.ctx["missing"] = missing
        else:
            st.check("Required fields present", "pass", "Vendor, invoice number, date, total")

        # Addressee: invoice must be billed to our legal entity
        legal = (co.get("legal_name") or "").strip()
        text = lr.ctx["doc"]["text"]
        if legal and text.strip():
            core = vendor_norm(legal)
            sc = fuzz.partial_ratio(core, vendor_norm(text)) if core else 100
            if sc >= 90:
                st.check("Billed to our company", "pass", legal)
            else:
                st.check("Billed to our company", "fail", f"'{legal}' does not appear as the bill-to party")
                lr.reason("BILL_TO_MISMATCH", "REJECTED",
                          f"This invoice is not addressed to {legal.rstrip('.')}. It was probably sent to us by mistake — "
                          "return it to the vendor.", "validate")
        elif not legal:
            st.check("Billed to our company", "info", "Skipped — company legal name not set in Settings")

        items = f.get("line_items") or []
        bad_lines = [li for li in items if None not in (li.get("quantity"), li.get("unit_price"), li.get("amount"))
                     and abs(li["quantity"] * li["unit_price"] - li["amount"]) > 0.02]
        if items:
            st.check("Line maths (qty × price = amount)", "warn" if bad_lines else "pass",
                     f"{len(bad_lines)} line(s) don't multiply out" if bad_lines else f"All {len(items)} lines correct")
            if bad_lines:
                lr.reason("LINE_ARITHMETIC", "NEEDS_REVIEW", "Some line amounts don't equal quantity × unit price.",
                          "validate")
        lines_sum = round(sum((li.get("amount") or 0) for li in items), 2)
        subtotal = f.get("subtotal")
        if subtotal is None and items:
            subtotal = lines_sum
            st.check("Subtotal", "info", f"Not printed — derived from lines: {money(subtotal, cur)}")
        elif subtotal is not None and items:
            ok = abs(lines_sum - subtotal) <= 0.02
            st.check("Lines add up to subtotal", "pass" if ok else "warn",
                     f"{money(lines_sum, cur)} vs {money(subtotal, cur)}")
            if not ok:
                lr.reason("SUBTOTAL_MISMATCH", "NEEDS_REVIEW",
                          f"Line items add to {money(lines_sum, cur)} but the subtotal says {money(subtotal, cur)}.",
                          "validate")
        lr.ctx["net"] = subtotal if subtotal is not None else f.get("total")

        tax = f.get("tax_amount") or 0.0
        ship = f.get("shipping_amount") or 0.0
        total = f.get("total")
        if total is not None and subtotal is not None:
            calc = round(subtotal + tax + ship, 2)
            ok = abs(calc - total) <= 0.02
            st.check("Subtotal + tax = total", "pass" if ok else "fail",
                     f"{money(subtotal, cur)} + {money(tax, cur)}" + (f" + {money(ship, cur)}" if ship else "") +
                     f" = {money(calc, cur)}" + ("" if ok else f", but invoice total is {money(total, cur)}"))
            if not ok:
                if abs(subtotal - total) <= 0.02 and tax:
                    st.check("Tax treatment", "info", "Tax appears to be included in prices (tax-inclusive)")
                else:
                    lr.reason("TOTAL_MISMATCH", "NEEDS_REVIEW",
                              f"Subtotal + tax = {money(calc, cur)}, but the invoice total is {money(total, cur)} "
                              f"(difference {money(round(total - calc, 2), cur)}). Ask the vendor for a corrected invoice.",
                              "validate")
        if subtotal and tax:
            rate = tax / subtotal * 100
            ok = rate <= pol["max_tax_rate_pct"]
            stated = f.get("tax_rate_pct")
            st.check("Tax rate plausible", "pass" if ok else "warn",
                     f"Effective {rate:.2f}%" + (f" (printed {stated:g}%)" if stated else "") +
                     ("" if ok else f" — above the {pol['max_tax_rate_pct']:g}% ceiling"))
            if not ok:
                lr.reason("TAX_RATE", "NEEDS_REVIEW",
                          f"Tax of {money(tax, cur)} is {rate:.1f}% of the net amount, above the "
                          f"{pol['max_tax_rate_pct']:g}% ceiling. Confirm the vendor applied the right tax.", "validate")
            if stated and abs(stated - rate) > 0.05:
                st.check("Printed tax rate matches amount", "warn", f"{stated}% printed vs {rate:.2f}% computed")
                lr.reason("TAX_RATE", "NEEDS_REVIEW", "The printed tax rate does not match the tax amount.", "validate")
        elif subtotal:
            st.check("Tax", "info", "No tax charged")

        d = f.get("invoice_date")
        if d:
            try:
                dd = date.fromisoformat(d)
                today = TODAY()
                if dd > today + timedelta(days=1):
                    st.check("Invoice date", "warn", f"{d} is in the future")
                    lr.reason("FUTURE_DATED", "NEEDS_REVIEW",
                              f"The invoice is dated {d}, in the future. It may be a pre-bill or a typo.", "validate")
                elif (today - dd).days > pol["max_invoice_age_days"]:
                    st.check("Invoice date", "warn", f"{d} is {(today - dd).days} days old")
                    lr.reason("STALE_INVOICE", "NEEDS_REVIEW",
                              f"The invoice is dated {d}, {(today - dd).days} days ago — older than the "
                              f"{pol['max_invoice_age_days']:g}-day limit. Check it wasn't already paid another way and "
                              "that its accounting period is still open.", "validate")
                else:
                    st.check("Invoice date", "pass", f"{d}")
                if f.get("due_date") and f["due_date"] < d:
                    st.check("Due date after invoice date", "warn", f"due {f['due_date']}")
            except ValueError:
                st.check("Invoice date", "warn", f"Unparseable date '{d}'")
        st.s["data"] = {"net": lr.ctx["net"], "tax": tax, "total": total, "lines_sum": lines_sum}
        bad = [c for c in st.s["checks"] if c["status"] in ("warn", "fail")]
        st.s["summary"] = "All checks passed" if not bad else f"{len(bad)} issue{'s' if len(bad) > 1 else ''} found"


# ------------------------------------------------------------------------------- 5 vendor
def stage_vendor(lr: LiveRun) -> None:
    with Stage(lr, "vendor") as st:
        f = lr.ctx["fields"]
        name = f.get("vendor_name") or ""
        inv_dom = email_domain(f.get("vendor_email"))
        all_v = db.vendors()
        if not all_v:
            st.check("Vendor master", "fail", "Vendor master is empty")
            lr.reason("VENDOR_UNKNOWN", "REJECTED", "The vendor master is empty — import your vendor list in "
                      "Settings → Data import before processing invoices.", "vendor")
            st.s["summary"] = "Vendor master empty"
            return
        best, best_sc = None, 0.0
        inv_tax = re.sub(r"\W", "", f.get("vendor_tax_id") or "")
        for v in all_v:
            names = [v["name"]] + [a for a in (v["aliases"] or "").split("|") if a]
            sc = max(name_similarity(name, n) for n in names) if name else 0
            if inv_dom and v["email_domain"] and inv_dom == v["email_domain"]:
                sc = max(sc, 95)  # registered sender domain is strong identity evidence
            elif sc < 95:
                # a weak name match is overruled by contrary evidence: another domain or another tax ID
                contrary = (inv_dom and v["email_domain"] and inv_dom != v["email_domain"]) or \
                           (inv_tax and v["tax_id"] and inv_tax != re.sub(r"\W", "", v["tax_id"]))
                if contrary:
                    sc = min(sc, 70)
            if sc > best_sc:
                best, best_sc = v, sc
        if not best or best_sc < 80:
            st.check("Vendor in vendor master", "fail", f"'{name or 'unknown'}' not found")
            lr.reason("VENDOR_UNKNOWN", "REJECTED",
                      f"'{name or 'The issuer'}' is not an onboarded vendor. Forward to Procurement for vendor "
                      "onboarding; nothing can be paid until then.", "vendor")
            st.s["summary"] = "Unknown vendor"
            return
        lr.ctx["vendor"] = best
        st.check("Vendor in vendor master", "pass" if best_sc >= 90 else "warn",
                 f"{best['name']} ({best['vendor_id']}) · {best_sc:.0f}% name match")
        if best_sc < 90:
            lr.reason("VENDOR_FUZZY_MATCH", "NEEDS_REVIEW",
                      f"The vendor name only partially matches '{best['name']}' — confirm it is the same entity.",
                      "vendor")
        status = best["status"]
        if status == "approved":
            st.check("Vendor status", "pass", "Approved for payment")
        elif status == "blocked":
            st.check("Vendor status", "fail", "Blocked")
            lr.reason("VENDOR_BLOCKED", "REJECTED", f"{best['name']} is blocked in the vendor master. Do not pay; "
                      "refer to Procurement.", "vendor")
        else:
            st.check("Vendor status", "warn", status.replace("_", " "))
            if status == "inactive":
                msg = (f"{best['name']} is marked inactive in the vendor master. Dormant vendor records are a common "
                       "fraud target, so Procurement must reactivate and re-verify the vendor (tax ID, bank account) "
                       "before anything is paid.")
            else:
                msg = (f"{best['name']} is '{status.replace('_', ' ')}' — onboarding (tax and bank verification) is "
                       "not complete, so it cannot be paid yet.")
            lr.reason("VENDOR_NOT_ACTIVE", "ON_HOLD", msg, "vendor")

        bank = f.get("bank") or {}
        acct = re.sub(r"\D", "", bank.get("account_number") or "")
        routing = re.sub(r"\D", "", bank.get("routing_number") or "")
        bank_changed = False
        master_acct = best["account_number"] or ""
        if acct or routing:
            acct_ok = (not acct) or acct == master_acct
            rout_ok = (not routing) or routing == (best["routing_number"] or "")
            if acct_ok and rout_ok:
                st.check("Remit-to bank matches master", "pass", f"Account ending {acct[-4:] or master_acct[-4:]}")
            else:
                bank_changed = True
                st.check("Remit-to bank matches master", "fail",
                         f"Invoice: {bank.get('bank_name') or ''} …{acct[-4:]} · on file: {best['bank_name']} …{master_acct[-4:]}")
                lr.reason("BANK_DETAILS_CHANGED", "ON_HOLD",
                          f"The bank account on the invoice (…{acct[-4:]}) differs from the verified account on file "
                          f"(…{master_acct[-4:]}). Changed remittance details are the most common invoice-fraud "
                          "pattern — payment is blocked until the change is verified by phone.", "vendor")
        else:
            st.check("Remit-to bank", "info", f"Not printed — pay verified account on file (…{master_acct[-4:]})")
        if any(re.search(r"bank|account", n, re.I) and re.search(r"chang|new", n, re.I) for n in f.get("notes", [])):
            st.check("Bank-change request on invoice", "warn", "Invoice asks to pay a new account")

        if inv_dom and best["email_domain"]:
            if inv_dom == best["email_domain"]:
                st.check("Sender email domain", "pass", inv_dom)
            else:
                root = best["email_domain"].split(".")[0]
                lookalike = root in inv_dom or fuzz.ratio(inv_dom, best["email_domain"]) > 70
                st.check("Sender email domain", "fail" if lookalike else "warn",
                         f"{inv_dom} ≠ {best['email_domain']}" + (" (look-alike)" if lookalike else ""))
                lr.reason("EMAIL_DOMAIN_MISMATCH", "ON_HOLD" if (bank_changed or lookalike) else "NEEDS_REVIEW",
                          f"The contact email domain '{inv_dom}' differs from the vendor's registered domain "
                          f"'{best['email_domain']}'" + (" — a look-alike domain." if lookalike else "."), "vendor")
        tax_id = f.get("vendor_tax_id")
        if tax_id and best["tax_id"]:
            ok = re.sub(r"\W", "", tax_id) == re.sub(r"\W", "", best["tax_id"])
            st.check("Tax ID matches master", "pass" if ok else "warn", tax_id)
            if not ok:
                lr.reason("TAX_ID_MISMATCH", "NEEDS_REVIEW", f"Tax ID {tax_id} differs from master {best['tax_id']}.",
                          "vendor")
        st.s["data"] = {"vendor": {k: best[k] for k in ("vendor_id", "name", "status", "email_domain", "contact_phone",
                                                       "bank_name", "payment_terms_days")},
                        "match_score": best_sc, "bank_changed": bank_changed}
        st.s["summary"] = f"{best['name']} · {status.replace('_', ' ')}"


# ------------------------------------------------------------------------------- 6 po match
def _line_desc_score(a: str, b: str) -> float:
    return fuzz.token_set_ratio(a.lower(), b.lower()) / 100


def _billed_qty(po_number: str) -> dict[int, float]:
    out: dict[int, float] = {}
    for r in db.q("SELECT po_line_qty FROM invoice_ledger WHERE po_number=?", (po_number,)):
        for part in (r["po_line_qty"] or "").split("|"):
            if ":" in part:
                ln, qty = part.split(":")
                out[int(ln)] = out.get(int(ln), 0) + float(qty)
    return out


def stage_po_match(lr: LiveRun) -> None:
    with Stage(lr, "po_match") as st:
        f, pol = lr.ctx["fields"], lr.ctx["policy"]
        cur = f["currency"]
        vendor = lr.ctx.get("vendor")
        items = f.get("line_items") or []
        net = lr.ctx.get("net") or 0.0
        pos = {p["po_number"]: p for p in db.purchase_orders()}
        by_digits = {po_digits(k): p for k, p in pos.items()}
        po, how, conf = None, None, None

        ref = f.get("po_number")
        if ref:
            po = by_digits.get(po_digits(ref))
            if po:
                how = "explicit"
                st.check("PO reference on invoice", "pass", f"'{ref}' → {po['po_number']}")
            else:
                st.check("PO reference on invoice", "warn", f"'{ref}' does not exist in the PO register")
        else:
            st.check("PO reference on invoice", "info", "None printed — searching vendor's open POs")

        cands_info = []
        if po is None and vendor:
            cands = [p for p in pos.values() if p["vendor_id"] == vendor["vendor_id"] and p["status"] == "open"]
            for p in cands:
                ls = (sum(max(1.0 if (li.get("sku") and li["sku"] == pl["sku"]) else
                              _line_desc_score(li.get("description", ""), pl["description"]) for pl in p["lines"])
                          for li in items) / len(items)) if items and p["lines"] else 0.0
                # amount closeness: to the PO's open balance, its total, or — for invoices that bill only part of a
                # PO (one month of a quarterly service) — the open value of just the PO lines the invoice matches
                billed = _billed_qty(p["po_number"])
                matched_lines = {}
                for li in items:
                    best_pl = max(p["lines"], key=lambda pl: 1.0 if (li.get("sku") and li["sku"] == pl["sku"])
                                  else _line_desc_score(li.get("description", ""), pl["description"]), default=None)
                    if best_pl and (li.get("sku") == best_pl["sku"] or
                                    _line_desc_score(li.get("description", ""), best_pl["description"]) >= 0.7):
                        matched_lines[best_pl["line_no"]] = best_pl
                line_value = sum((pl["quantity"] - billed.get(pl["line_no"], 0)) * pl["unit_price"]
                                 for pl in matched_lines.values())
                amt = 0.0
                if net:
                    for target in (p["remaining_amount"], p["total_amount"], line_value):
                        if target > 0:
                            amt = max(amt, 1 - abs(net - target) / target)
                score = round(0.6 * ls + 0.4 * max(0.0, amt), 3)
                cands_info.append({"po_number": p["po_number"], "description": p["description"],
                                   "line_score": round(ls, 2), "amount_score": round(max(0.0, amt), 2), "score": score})
            cands_info.sort(key=lambda c: -c["score"])
            for c in cands_info[:3]:
                st.check(f"Candidate {c['po_number']}", "info",
                         f"{c['description']} · lines {c['line_score'] * 100:.0f}% · amount {c['amount_score'] * 100:.0f}% "
                         f"→ {c['score'] * 100:.0f}%")
            if cands_info:
                top = cands_info[0]
                margin = top["score"] - (cands_info[1]["score"] if len(cands_info) > 1 else 0)
                if top["score"] >= pol["po_inference_min_confidence"] and margin >= 0.1:
                    po, how, conf = pos[top["po_number"]], "inferred", top["score"]
                    st.check("PO identified from content", "pass",
                             f"{po['po_number']} — {conf * 100:.0f}% confidence, {margin * 100:.0f}-point lead")
                    if ref:
                        lr.reason("PO_NOT_FOUND", "NEEDS_REVIEW",
                                  f"The PO printed on the invoice ('{ref}') does not exist. The lines match "
                                  f"{po['po_number']} — confirm with the requester before paying.", "po_match")
                    else:
                        lr.notes.append(f"No PO was printed; it was identified as {po['po_number']} from the line "
                                        f"items and amount ({conf * 100:.0f}% confidence).")
                        if not pol.get("allow_auto_approve_inferred_po", True):
                            lr.reason("PO_INFERRED", "NEEDS_REVIEW", f"PO {po['po_number']} was inferred; policy "
                                      "requires the requester to confirm.", "po_match")
                else:
                    # name only the genuinely tied POs (within 5 points) — the decision itself needs a 10-point lead
                    tied = [c["po_number"] for c in cands_info if top["score"] - c["score"] < 0.05]
                    st.check("PO identified from content", "warn",
                             f"{len(tied)} open POs match equally well: {', '.join(tied)}" if len(tied) > 1
                             else "No open PO matches confidently")
                    lr.ctx["po_tied"] = tied
            else:
                st.check("Vendor's open POs", "warn", "Vendor has no open purchase orders")
        if po is None:
            if ref:
                lr.reason("PO_NOT_FOUND", "NEEDS_REVIEW", f"PO '{ref}' does not exist in the PO register.", "po_match")
            elif lr.ctx.get("po_tied") and len(lr.ctx["po_tied"]) > 1:
                lr.reason("PO_UNDETERMINED", "NEEDS_REVIEW",
                          f"No PO on the invoice and {len(lr.ctx['po_tied'])} open POs ({', '.join(lr.ctx['po_tied'])}) "
                          "match it almost equally. The agent won't guess — the requester must say which order this bills.", "po_match")
            elif vendor:
                lr.reason("PO_UNDETERMINED", "NEEDS_REVIEW",
                          "No PO on the invoice and no single open PO of this vendor matches clearly. The requester must "
                          "confirm which order this belongs to.", "po_match")
            st.s["data"] = {"candidates": cands_info}
            st.s["summary"] = "No PO matched"
            return

        if vendor and po["vendor_id"] != vendor["vendor_id"]:
            st.check("PO issued to this vendor", "fail", f"{po['po_number']} is issued to {po['vendor_id']}")
            owner = next((v["name"] for v in db.vendors() if v["vendor_id"] == po["vendor_id"]), po["vendor_id"])
            lr.reason("PO_VENDOR_MISMATCH", "NEEDS_REVIEW",
                      f"{po['po_number']} was issued to {owner} ({po['description']}), not to {vendor['name'].rstrip('.')}. A vendor "
                      "can't bill against another vendor's order — likely a wrong PO number.",
                      "po_match")
        else:
            st.check("PO issued to this vendor", "pass", f"{po['po_number']} · {po['description']}")
        if po["status"] != "open":
            st.check("PO status", "warn", po["status"])
            lr.reason("PO_CLOSED", "NEEDS_REVIEW", f"{po['po_number']} ({po['description']}) is {po['status']}, so it has "
                      f"no budget to spend against. {po.get('requester') or 'The requester'} must reopen it or raise a "
                      "new PO before this can be paid.", "po_match")
        else:
            st.check("PO status", "pass", "Open")
        if cur != po["currency"]:
            st.check("Currency matches PO", "fail", f"Invoice in {cur}, PO in {po['currency']}")
            lr.reason("CURRENCY_MISMATCH", "NEEDS_REVIEW",
                      f"The invoice is billed in {cur} but {po['po_number']} was raised in {po['currency']}. Paying it "
                      "as-is creates an FX exposure the buyer did not approve — ask for a USD invoice or a PO change.",
                      "po_match")
        else:
            st.check("Currency matches PO", "pass", cur)

        billed_before = _billed_qty(po["po_number"])
        matched, expected, over_amt = [], 0.0, 0.0
        for li in items:
            best, bsc = None, 0.0
            for pl in po["lines"]:
                if li.get("sku") and li["sku"] == pl["sku"]:
                    sc = 1.0
                else:
                    sc = _line_desc_score(li.get("description", ""), pl["description"])
                    u_, q_ = li.get("unit_price") or 0, li.get("quantity") or 0
                    # a similar description is not enough if price AND quantity are both far off
                    # (typical of a bundled line that merely mentions one of the PO items)
                    if pl["unit_price"] and abs(u_ - pl["unit_price"]) / pl["unit_price"] > 0.5 and q_ != pl["quantity"]:
                        sc = min(sc, 0.5)
                if sc > bsc:
                    best, bsc = pl, sc
            row: dict[str, Any] = {"invoice": li, "score": round(bsc, 2)}
            if best and bsc >= 0.7:
                q_, u = li.get("quantity") or 0, li.get("unit_price") or 0
                prev = billed_before.get(best["line_no"], 0)
                remaining = round(best["quantity"] - prev, 4)
                over_qty = max(0.0, q_ - remaining)
                expected += best["unit_price"] * q_
                over_amt += over_qty * best["unit_price"]
                row.update({"po_line": best, "prev_billed_qty": prev, "remaining_qty": remaining, "over_qty": over_qty,
                            "price_variance": round((u - best["unit_price"]) * q_, 2),
                            "price_variance_pct": round((u - best["unit_price"]) / best["unit_price"] * 100, 2)
                            if best["unit_price"] else 0})
            else:
                expected += li.get("amount") or 0
                row["po_line"] = None
            matched.append(row)
        # Bundled lines: one invoice line can cover several PO lines ("deployment package — 10 seats").
        # If what's unmatched on the invoice equals the open value of the PO lines nobody matched, it is a bundle.
        loose = [m for m in matched if not m["po_line"]]
        used = {m["po_line"]["line_no"] for m in matched if m.get("po_line")}
        free = [pl for pl in po["lines"] if pl["line_no"] not in used
                and pl["quantity"] - billed_before.get(pl["line_no"], 0) > 0]
        if loose and free:
            bundle_val = round(sum((pl["quantity"] - billed_before.get(pl["line_no"], 0)) * pl["unit_price"] for pl in free), 2)
            loose_amt = round(sum(m["invoice"].get("amount") or 0 for m in loose), 2)
            diff = loose_amt - bundle_val
            if bundle_val > 0 and abs(diff) <= pol["price_tolerance_abs"] and abs(diff) / bundle_val * 100 <= pol["price_tolerance_pct"]:
                blines = [{"line_no": pl["line_no"], "description": pl["description"],
                           "qty": round(pl["quantity"] - billed_before.get(pl["line_no"], 0), 4)} for pl in free]
                for m in loose:
                    m["bundle_lines"] = blines
                    m["bundle_value"] = bundle_val
                expected += bundle_val - loose_amt
                st.check("Bundled line", "pass",
                         f"{len(loose)} invoice line(s) worth {money(loose_amt, cur)} cover PO lines "
                         + ", ".join(f"#{b['line_no']}" for b in blines) + f" (open value {money(bundle_val, cur)})")
                lr.notes.append(f"The invoice bills PO lines {', '.join('#' + str(b['line_no']) for b in blines)} as one "
                                f"bundled line; its {money(loose_amt, cur)} matches their open value of {money(bundle_val, cur)}.")

        def _sig_parts(rows):
            for m in rows:
                if m.get("po_line"):
                    yield f"{m['po_line']['line_no']}:{m['invoice'].get('quantity') or 0:g}"
                for b in m.get("bundle_lines") or []:
                    yield f"{b['line_no']}:{b['qty']:g}"

        lr.ctx["line_sig"] = "|".join(sorted(_sig_parts(matched)))

        unmatched = [m for m in matched if not m["po_line"] and not m.get("bundle_lines")]
        if unmatched:
            st.check("Every line is on the PO", "fail",
                     f"{len(unmatched)} not on PO: " + "; ".join(m["invoice"]["description"] for m in unmatched))
            lr.reason("LINE_NOT_ON_PO", "NEEDS_REVIEW",
                      "The invoice includes charges that are not on the PO: " + "; ".join(
                          f"{m['invoice']['description']} ({money(m['invoice'].get('amount'), cur)})" for m in unmatched)
                      + ". The requester must approve them or the vendor must remove them.", "po_match")
        elif items:
            nb = sum(1 for m in matched if m.get("bundle_lines"))
            st.check("Every line is on the PO", "pass", f"{len(items)} of {len(items)} lines matched"
                     + (f" ({nb} as a bundle)" if nb else ""))

        variance = round(sum(m.get("price_variance", 0) for m in matched if m.get("po_line")), 2)
        matched_expected = sum(m["po_line"]["unit_price"] * (m["invoice"].get("quantity") or 0)
                               for m in matched if m.get("po_line"))
        matched_expected += next((m["bundle_value"] for m in matched if m.get("bundle_lines")), 0)
        if not unmatched:
            variance = round(net - expected, 2)
        var_pct = round(variance / matched_expected * 100, 2) if matched_expected else 0.0
        within = abs(variance) <= pol["price_tolerance_abs"] and abs(var_pct) <= pol["price_tolerance_pct"]
        tol_txt = f"±{pol['price_tolerance_pct']:g}% / ±{money(pol['price_tolerance_abs'], cur)}"
        if not items:
            variance, var_pct, within = 0.0, 0.0, True
            st.check("Prices vs PO", "info", "No line items extracted — nothing to compare line by line")
        elif abs(variance) < 0.01:
            st.check("Prices vs PO", "pass", "Exact match")
        elif within:
            st.check("Prices vs PO", "pass", f"{money(variance, cur)} ({var_pct:+.2f}%) — within tolerance {tol_txt}")
            lr.notes.append(f"Billed {money(net, cur)} against a PO value of {money(expected, cur)}: "
                            f"{var_pct:+.2f}% ({money(variance, cur)}), inside the {tol_txt} tolerance.")
        else:
            st.check("Prices vs PO", "fail", f"{money(variance, cur)} ({var_pct:+.2f}%) — exceeds tolerance {tol_txt}")
            worst = sorted([m for m in matched if m.get("po_line") and abs(m.get("price_variance", 0)) > 0.005],
                           key=lambda m: -abs(m["price_variance"]))
            det = "; ".join(f"{m['po_line']['description']}: {money(m['invoice']['unit_price'], cur)} vs PO "
                            f"{money(m['po_line']['unit_price'], cur)} ({m['price_variance_pct']:+.1f}%)" for m in worst[:3])
            lr.reason("PRICE_VARIANCE", "NEEDS_REVIEW",
                      (f"Unit prices are {var_pct:+.1f}% ({money(variance, cur)}) above the agreed PO prices"
                       if det else f"The billed amount is {var_pct:+.1f}% ({money(variance, cur)}) away from the PO value "
                       "even though the unit prices match")
                      + f", outside the {tol_txt} tolerance." + (f" {det}." if det else ""), "po_match")

        prior_net = po["invoiced_amount"]
        if po["invoice_count"]:
            st.check("Earlier invoices on this PO", "info",
                     f"{po['invoice_count']} invoice(s), {money(prior_net, cur)} — {money(po['remaining_amount'], cur)} "
                     f"of {money(po['total_amount'], cur)} left")
        over_lines = [m for m in matched if m.get("over_qty")]
        if over_lines:
            for m in over_lines:
                st.check("Quantity within PO balance", "fail",
                         f"{m['po_line']['description']}: billing {m['invoice']['quantity']:g}, only {m['remaining_qty']:g} "
                         f"of {m['po_line']['quantity']:g} left ({m['prev_billed_qty']:g} already invoiced)")
            lr.ctx["over_billing"] = {"over_amount": round(over_amt, 2)}
            allowed = round(net - over_amt, 2)
            lr.reason("PO_OVERBILLED", "NEEDS_REVIEW",
                      f"Together with earlier invoices this bills {money(round(prior_net + net, 2), cur)} against a "
                      f"{money(po['total_amount'], cur)} PO — {money(over_amt, cur)} more than was ordered. " +
                      (f"At most {money(allowed, cur)} can be approved without a PO amendment." if allowed > 0.01
                       else "Nothing is left to bill on these PO lines."), "po_match")
        elif not items and prior_net + net > po["total_amount"] * (1 + pol["price_tolerance_pct"] / 100) + 0.01:
            # no line detail to work with: fall back to an amount-based balance check
            st.check("Invoice within PO balance", "fail",
                     f"{money(prior_net + net, cur)} cumulative vs {money(po['total_amount'], cur)} PO")
            lr.ctx["over_billing"] = {"over_amount": round(prior_net + net - po["total_amount"], 2)}
            lr.reason("PO_OVERBILLED", "NEEDS_REVIEW", f"Cumulative invoices ({money(prior_net + net, cur)}) exceed the "
                      f"PO value of {money(po['total_amount'], cur)}.", "po_match")
        else:
            st.check("Invoice within PO balance", "pass",
                     f"{money(round(prior_net + matched_expected, 2), cur)} of {money(po['total_amount'], cur)} used incl. this invoice")

        total = f.get("total") or 0
        if total > pol["auto_approve_limit"]:
            st.check("Touchless approval limit", "warn", f"{money(total, cur)} > {money(pol['auto_approve_limit'], cur)}")
            lr.reason("ABOVE_AUTO_APPROVE_LIMIT", "NEEDS_REVIEW",
                      f"{money(total, cur)} is above the {money(pol['auto_approve_limit'], cur)} touchless-approval "
                      "limit, so a person must sign off even though everything matches.", "po_match")
        lr.ctx["po"], lr.ctx["po_how"], lr.ctx["po_lines_matched"] = po, how, matched
        st.s["data"] = {"po": {k: po[k] for k in ("po_number", "description", "department", "requester", "status",
                                                 "currency", "total_amount", "invoiced_amount", "remaining_amount")},
                        "how": how, "confidence": conf, "candidates": cands_info, "lines": matched,
                        "expected": round(expected, 2), "net": net, "variance": variance, "variance_pct": var_pct,
                        "within_tolerance": within}
        st.s["summary"] = f"{po['po_number']}" + (" (identified from content)" if how == "inferred" else "") + \
            (" · exact match" if abs(variance) < 0.01 else f" · {var_pct:+.2f}%")


# ------------------------------------------------------------------------------- 7 duplicate
def stage_duplicate(lr: LiveRun) -> None:
    with Stage(lr, "duplicate") as st:
        f, pol = lr.ctx["fields"], lr.ctx["policy"]
        cur = f["currency"]
        vendor = lr.ctx.get("vendor")
        inv, total = f.get("invoice_number"), f.get("total")
        po_no = (lr.ctx.get("po") or {}).get("po_number")
        sig = lr.ctx.get("line_sig")
        found = None

        same_file = db.q1("SELECT id, created_at, decision, invoice_number FROM runs WHERE file_hash=? AND id<>? "
                          "ORDER BY rowid LIMIT 1", (lr.ctx["sha256"], lr.id))
        if same_file:
            found = "exact_file"
            st.check("Same file received before", "fail",
                     f"Identical file received {same_file['created_at'][:10]} (invoice {same_file['invoice_number'] or '—'})")
            lr.reason("DUPLICATE_EXACT_FILE", "REJECTED",
                      f"This exact file was already received on {same_file['created_at'][:10]} and processed "
                      f"({(same_file['decision'] or '').replace('_', ' ').lower()}). It is a re-send, not a new invoice.",
                      "duplicate")
            lr.ctx["duplicate_of"] = {"invoice_number": same_file["invoice_number"], "run_id": same_file["id"],
                                      "status": (same_file["decision"] or "").replace("_", " ").lower()}
        else:
            st.check("Same file received before", "pass", "No")

        if vendor:
            history = []
            for h in db.q("SELECT * FROM invoice_ledger WHERE vendor_id=?", (vendor["vendor_id"],)):
                history.append({"invoice_number": h["invoice_number"], "total": h["total"], "po_number": h["po_number"],
                                "sig": h["po_line_qty"], "status": h["status"], "pay_on": h["pay_on"],
                                "run_id": h["run_id"]})
            in_ledger = {h["run_id"] for h in history}
            for r in db.q("SELECT id, invoice_number, total, po_number, line_sig, decision FROM runs WHERE vendor_id=? "
                          "AND id<>? AND state='done' AND final_status IN ('NEEDS_REVIEW','ON_HOLD')",
                          (vendor["vendor_id"], lr.id)):
                if r["id"] not in in_ledger:
                    history.append({"invoice_number": r["invoice_number"], "total": r["total"], "po_number": r["po_number"],
                                    "sig": r["line_sig"], "status": f"awaiting review ({r['decision'].replace('_', ' ').lower()})",
                                    "pay_on": None, "run_id": r["id"]})
            st.check("Compared with", "info", f"{len(history)} earlier invoice(s) from {vendor['name']}")
            hit = None
            for h in history:
                same_amt = total is not None and h["total"] is not None and abs(h["total"] - total) <= 0.01
                if inv and h["invoice_number"]:
                    n1, n2 = norm_inv(inv), norm_inv(h["invoice_number"])
                    sim = fuzz.ratio(n1, n2) / 100
                    if n1 == n2:
                        hit = ("same_number", h, sim)
                        break
                    if same_amt and (base_inv(inv) == base_inv(h["invoice_number"]) or
                                     sim >= pol["duplicate_number_similarity"]):
                        hit = ("renumbered", h, sim)
                        break
                if same_amt and po_no and h["po_number"] == po_no and sig and h["sig"] == sig and not hit:
                    hit = ("same_charge", h, 0)
            if hit:
                kind, h, sim = hit
                when = f"scheduled for payment on {h['pay_on']}" if h.get("pay_on") else h["status"]
                if kind == "same_number":
                    st.check("Invoice number already received", "fail", f"{h['invoice_number']} — {when}")
                    lr.reason("DUPLICATE_INVOICE", "REJECTED", f"Invoice {inv} from this vendor was already received "
                              f"({when}).", "duplicate")
                elif kind == "renumbered":
                    st.check("Re-numbered resubmission", "fail",
                             f"{inv} ≈ {h['invoice_number']} ({sim * 100:.0f}% similar, same amount) — {when}")
                    lr.reason("DUPLICATE_RENUMBERED", "REJECTED",
                              f"{inv} is a resubmission of {h['invoice_number']}: same vendor, same amount "
                              f"{money(total, cur)}, and the number only differs by a suffix. The original is {when}. "
                              "Paying it would pay twice.", "duplicate")
                else:
                    st.check("Same charge already invoiced", "warn",
                             f"{h['invoice_number']}: same amount, same PO, same lines — {when}")
                    lr.reason("POSSIBLE_DUPLICATE", "NEEDS_REVIEW",
                              f"{h['invoice_number']} bills exactly the same lines and amount ({money(total, cur)}) on "
                              f"{po_no} and is {when}. Confirm this is a separate charge before paying.", "duplicate")
                lr.ctx["duplicate_of"] = h
                found = found or kind
            else:
                st.check("Same or similar invoice number / same charge", "pass", "None found")
        st.s["data"] = {"duplicate_of": lr.ctx.get("duplicate_of"), "kind": found}
        st.s["summary"] = "Duplicate found" if found else "No duplicates"


# ------------------------------------------------------------------------------- 8 decide
def _due_date(f: dict, vendor: dict | None) -> str | None:
    if f.get("due_date"):
        return f["due_date"]
    m = re.search(r"(\d+)", f.get("payment_terms") or "")
    days = int(m.group(1)) if m else (vendor["payment_terms_days"] if vendor else None)
    if f.get("invoice_date") and days is not None:
        try:
            return (date.fromisoformat(f["invoice_date"]) + timedelta(days=days)).isoformat()
        except ValueError:
            return None
    return None


def stage_decide(lr: LiveRun) -> dict[str, Any]:
    result: dict[str, Any] = {}
    with Stage(lr, "decide") as st:
        ctx, f = lr.ctx, lr.ctx["fields"]
        co = ctx["company"]
        cur = f["currency"]
        us = co.get("legal_name") or "Accounts Payable"
        ap_mail = co.get("ap_email") or "our accounts payable team"
        vendor, po = ctx.get("vendor"), ctx.get("po")
        reasons = sorted(lr.reasons, key=lambda r: -OUTCOME_RANK[r["outcome"]])
        if any(r["code"] in ("DUPLICATE_RENUMBERED", "DUPLICATE_INVOICE", "DUPLICATE_EXACT_FILE") for r in reasons):
            # a duplicate "over-bills" its PO by definition — saying so would only confuse the reader
            reasons = [r for r in reasons if r["code"] != "PO_OVERBILLED"]
        if any(r["code"] == "UNREADABLE" for r in reasons):  # everything else is a consequence of an empty page
            reasons = [r for r in reasons if r["code"] == "UNREADABLE"]
        email_codes = None
        if any(r["code"] == "LOW_OCR_CONFIDENCE" for r in reasons):
            # On a poor scan, "missing" or inconsistent values are probably misreads, not vendor errors:
            # never reject or bounce the invoice back for them — a person checks them against the image.
            read_dependent = {"MISSING_REQUIRED_FIELDS", "BILL_TO_MISMATCH", "TOTAL_MISMATCH", "SUBTOTAL_MISMATCH",
                              "TAX_RATE", "PRICE_VARIANCE", "LINE_ARITHMETIC", "VENDOR_UNKNOWN", "LINE_NOT_ON_PO",
                              "PO_NOT_FOUND", "FUTURE_DATED", "STALE_INVOICE"}
            for r in reasons:
                if r["code"] in read_dependent:
                    r["outcome"] = "NEEDS_REVIEW"
                    if not r["message"].startswith("Possibly an OCR misread"):
                        r["message"] = "Possibly an OCR misread — " + r["message"][0].lower() + r["message"][1:]
            reasons.sort(key=lambda r: (-OUTCOME_RANK[r["outcome"]], r["code"] != "LOW_OCR_CONFIDENCE"))
            email_codes = {r["code"] for r in reasons if r["code"] not in read_dependent}
        decision = reasons[0]["outcome"] if reasons else "APPROVED"
        codes = {r["code"] for r in reasons}
        primary = reasons[0] if reasons else None
        total, inv = f.get("total"), f.get("invoice_number") or "(no number)"
        vname = vendor["name"] if vendor else (f.get("vendor_name") or "Unknown vendor")
        due = _due_date(f, vendor)
        vendor_msg, internal, queue_ = None, None, None

        if decision == "APPROVED":
            headline = f"Approved for payment"
            pay_on = max(due, TODAY().isoformat()) if due else TODAY().isoformat()
            next_action = (f"Scheduled for payment on {pay_on} by ACH to the verified account on file "
                           f"(…{(vendor['account_number'] or '')[-4:]}). Posted to the AP ledger against {po['po_number']}.")
        else:
            headline = primary["title"]
            if decision == "NEEDS_REVIEW":
                if po and codes & {"PRICE_VARIANCE", "PO_OVERBILLED", "LINE_NOT_ON_PO", "ABOVE_AUTO_APPROVE_LIMIT",
                                   "CURRENCY_MISMATCH", "PO_NOT_FOUND"}:
                    queue_ = f"{po['requester']} · {po['department']}" if po.get("requester") else "PO owner"
                elif "PO_UNDETERMINED" in codes:
                    queue_ = "AP team · PO identification"
                else:
                    queue_ = "AP team"
                next_action = f"Assigned to {queue_}. Payment is paused until someone approves or rejects it."
            elif decision == "ON_HOLD":
                queue_ = "AP controller · vendor verification"
                if "EMAIL_DOMAIN_MISMATCH" in codes and "BANK_DETAILS_CHANGED" not in codes:
                    next_action = (f"Payment blocked. Confirm with {vname} through the contact on file "
                                   f"({vendor['contact_phone'] if vendor else 'n/a'}) that they really sent this invoice — "
                                   "never reply to the address it came from. Release it once confirmed.")
                elif "BANK_DETAILS_CHANGED" in codes or "EMAIL_DOMAIN_MISMATCH" in codes:
                    next_action = (f"Payment blocked. Call {vname} on the number in the vendor master "
                                   f"({vendor['contact_phone'] if vendor else 'n/a'}) — never the contact details on this "
                                   "invoice — to confirm any bank change. Update the vendor master only after verbal "
                                   "confirmation and a second approver.")
                else:
                    what = "reactivates and re-verifies" if (vendor or {}).get("status") == "inactive" else "completes onboarding for"
                    next_action = (f"Payment blocked until Procurement {what} {vname}. Release it once the vendor is "
                                   "approved in the vendor master.")
            else:
                queue_ = None
                if codes & {"DUPLICATE_RENUMBERED", "DUPLICATE_INVOICE", "DUPLICATE_EXACT_FILE"}:
                    next_action = "Do not pay. Closed as a duplicate; reply drafted for the vendor."
                elif codes & {"MISSING_REQUIRED_FIELDS", "BILL_TO_MISMATCH", "UNREADABLE"}:
                    next_action = "Returned to the vendor with the reason. Nothing was posted."
                elif codes & {"VENDOR_UNKNOWN", "VENDOR_BLOCKED"}:
                    next_action = "Do not pay. Forwarded to Procurement (vendor onboarding / vendor status)."
                else:
                    next_action = "Do not pay."

        ecodes = email_codes if email_codes is not None else codes  # no "reissue" emails for OCR misreads
        contact = vendor["contact_email"] if vendor else (f.get("vendor_email") or "")
        sign = f"Kind regards,\nAccounts Payable\n{us}"
        if "MISSING_REQUIRED_FIELDS" in ecodes:
            miss = ", ".join(m.lower() for m in ctx.get("missing", []))
            vendor_msg = {"to": contact, "subject": f"Invoice returned — {miss} required",
                          "body": f"Hello {vname} team,\n\nWe received your invoice for {money(total, cur)}"
                                  + (f" (PO {po['po_number']})" if po else "") +
                                  f", but we can't process it because it is missing: {miss}.\n\nPlease reissue it with a "
                                  f"unique invoice number and an invoice date and send it to {ap_mail}. We'll process it "
                                  f"as soon as it arrives.\n\n{sign}"}
        elif "BILL_TO_MISMATCH" in ecodes:
            vendor_msg = {"to": contact, "subject": f"Invoice {inv} — not addressed to {us}",
                          "body": f"Hello {vname} team,\n\nWe received invoice {inv} for {money(total, cur)}, but it is "
                                  f"addressed to a different company, not {us}. We have not processed it.\n\nPlease send "
                                  f"it to the correct customer, or reissue it to {us} if it is ours.\n\n{sign}"}
        elif "UNREADABLE" in ecodes:
            vendor_msg = {"to": contact or "(sender)", "subject": "Invoice could not be read",
                          "body": f"Hello,\n\nThe invoice document we received could not be read (it appears blank or "
                                  f"illegible). Please resend a clear PDF copy to {ap_mail}.\n\n{sign}"}
        elif ecodes & {"DUPLICATE_RENUMBERED", "DUPLICATE_INVOICE", "DUPLICATE_EXACT_FILE"}:
            h = ctx.get("duplicate_of") or {}
            state = (f"is scheduled for payment on {h['pay_on']}" if h.get("pay_on") else f"is already with us ({h.get('status')})")
            vendor_msg = {"to": contact, "subject": f"Re: {inv} — already received as {h.get('invoice_number') or inv}",
                          "body": f"Hello {vname} team,\n\nThank you for your message. Invoice {inv} appears to be a "
                                  f"copy of invoice {h.get('invoice_number') or inv}, which {state}.\n\nWe have not "
                                  f"processed it again to avoid a double payment. If this is a separate charge, please "
                                  f"reply with supporting details.\n\n{sign}"}
        elif "BANK_DETAILS_CHANGED" in ecodes and vendor:
            vendor_msg = {"to": f"{vendor['contact_email']} (address on file, not the one on the invoice)",
                          "subject": f"Verification needed: change of bank details on invoice {inv}",
                          "body": f"Hello {vname} team,\n\nWe received invoice {inv} for {money(total, cur)} asking us "
                                  "to pay a new bank account. For your protection we never change payment details "
                                  "based on an invoice or email alone.\n\nOur AP controller will call you on the number "
                                  f"we have on file ({vendor['contact_phone']}) to verify. Payment will be released once "
                                  f"the change is confirmed.\n\n{sign}"}
            internal = ("Possible business-email-compromise: bank details differ from master"
                        + (" and the sender uses a look-alike email domain" if "EMAIL_DOMAIN_MISMATCH" in ecodes else "")
                        + ". Do not reply to the email address on the invoice.")
        elif "EMAIL_DOMAIN_MISMATCH" in ecodes and vendor and decision == "ON_HOLD":
            inv_dom = email_domain(f.get("vendor_email")) or "an unknown domain"
            vendor_msg = {"to": f"{vendor['contact_email']} (address on file, not the one on the invoice)",
                          "subject": f"Please confirm invoice {inv}",
                          "body": f"Hello {vname} team,\n\nWe received invoice {inv} for {money(total, cur)} from "
                                  f"{inv_dom}, which is not your registered domain ({vendor['email_domain']}). Before "
                                  "we pay, please confirm that you sent this invoice.\n\nIf you did not, someone may be "
                                  "impersonating your company — please let us know.\n\n" + sign}
            internal = (f"Possible phishing: the invoice came from '{inv_dom}', imitating the vendor's domain "
                        f"'{vendor['email_domain']}'. Do not reply to that address; confirm via the contact on file.")
        elif "PO_OVERBILLED" in ecodes and po:
            ob = ctx.get("over_billing", {})
            vendor_msg = {"to": contact, "subject": f"Invoice {inv} exceeds PO {po['po_number']}",
                          "body": f"Hello {vname} team,\n\nInvoice {inv} bills {money(ctx.get('net'), cur)} against PO "
                                  f"{po['po_number']}, but only {money(po['remaining_amount'], cur)} remains on that PO "
                                  f"after earlier invoices. The excess of {money(ob.get('over_amount'), cur)} can't be paid "
                                  "without a PO amendment.\n\nPlease issue a corrected invoice or a credit note for "
                                  f"{money(ob.get('over_amount'), cur)}, or confirm whether extra units were agreed with "
                                  f"our buyer.\n\n{sign}"}
        elif "TOTAL_MISMATCH" in ecodes:
            vendor_msg = {"to": contact, "subject": f"Invoice {inv} — totals do not add up",
                          "body": f"Hello {vname} team,\n\nThe total on invoice {inv} ({money(total, cur)}) does not "
                                  f"equal the subtotal plus tax shown on the same invoice. Please send a corrected "
                                  f"invoice.\n\n{sign}"}
        elif "CURRENCY_MISMATCH" in ecodes and po:
            vendor_msg = {"to": contact, "subject": f"Invoice {inv} — wrong currency",
                          "body": f"Hello {vname} team,\n\nInvoice {inv} is billed in {cur}, but our purchase order "
                                  f"{po['po_number']} was issued in {po['currency']}. Please reissue the invoice in "
                                  f"{po['currency']} at the agreed prices.\n\n{sign}"}

        if decision == "APPROVED":
            explanation = ["Every check passed: vendor verified, no duplicate, all lines match "
                           f"{po['po_number']} and the PO has enough balance."] + lr.notes
        else:
            explanation = [r["message"] for r in reasons] + lr.notes

        for r in reasons:
            st.check(r["title"], "fail" if r["outcome"] in ("REJECTED", "ON_HOLD") else "warn", r["message"])
        if decision == "APPROVED":
            st.check("Approval policy", "pass", "No exception conditions — approved without manual touch")
            st.s["status"] = "passed"
        else:
            st.s["status"] = "failed" if decision in ("REJECTED", "ON_HOLD") else "warning"

        summary_ai = claude_summarise({"decision": decision, "headline": headline, "reasons": explanation,
                                       "next_action": next_action})
        result = {
            "decision": decision, "final_status": decision, "headline": headline, "next_action": next_action,
            "queue": queue_, "reasons": reasons, "notes": lr.notes, "explanation": explanation, "ai_summary": summary_ai,
            "vendor_message": vendor_msg, "internal_note": internal, "payment_due": due, "fields": f,
            "vendor": ({k: vendor[k] for k in ("vendor_id", "name", "contact_email", "contact_phone", "status")}
                       if vendor else None),
            "po": ({k: po[k] for k in ("po_number", "description", "requester", "department", "total_amount",
                                       "remaining_amount", "currency")} if po else None),
            "po_how": ctx.get("po_how"), "extractor": ctx.get("extractor"), "read_method": ctx.get("read_method"),
        }
        if decision == "APPROVED":
            pay_on = post_to_ledger(lr.id, result, ctx, "System (touchless)")
            result["pay_on"] = pay_on
            st.check("Posted to AP ledger", "info", f"Payment scheduled for {pay_on}")
        st.s["data"] = {"decision": decision}
        st.s["summary"] = headline
    return result


def post_to_ledger(run_id: str, result: dict, ctx: dict, approved_by: str) -> str:
    f = result["fields"]
    po = ctx.get("po") or {}
    vendor = ctx.get("vendor") or {}
    lines = ctx.get("po_lines_matched") or []
    parts = []
    for m in lines:
        if m.get("po_line"):
            parts.append(f"{m['po_line']['line_no']}:{m['invoice'].get('quantity') or 0:g}")
        for b in m.get("bundle_lines") or []:
            parts.append(f"{b['line_no']}:{b['qty']:g}")
    plq = "|".join(sorted(parts))
    due = result.get("payment_due")
    pay_on = max(due, TODAY().isoformat()) if due else TODAY().isoformat()
    db.add_ledger({"invoice_number": f.get("invoice_number"), "vendor_id": vendor.get("vendor_id"),
                   "po_number": po.get("po_number"), "invoice_date": f.get("invoice_date"), "due_date": due,
                   "net_amount": ctx.get("net"), "tax_amount": f.get("tax_amount") or 0, "total": f.get("total"),
                   "currency": f.get("currency"), "status": "scheduled", "pay_on": pay_on,
                   "bank_last4": (vendor.get("account_number") or "")[-4:], "po_line_qty": plq,
                   "file_hash": ctx.get("sha256"), "run_id": run_id, "approved_by": approved_by})
    return pay_on


def apply_review(run_id: str, action: str, reviewer: str, note: str) -> dict[str, Any]:
    run = db.q1("SELECT * FROM runs WHERE id=?", (run_id,))
    if not run or run["state"] != "done":
        raise ValueError("Invoice not found or still processing")
    if run["final_status"] not in ("NEEDS_REVIEW", "ON_HOLD"):
        raise ValueError(f"Invoice is already {run['final_status'].replace('_', ' ').lower()}")
    if not note.strip():
        raise ValueError("A note is required — it is recorded in the audit trail")
    result = json.loads(run["result"])
    if action == "approve":
        final = "APPROVED"
        trace = {s["key"]: s for s in json.loads(run["trace"])}
        vendor = db.q1("SELECT * FROM vendors WHERE vendor_id=?", (run["vendor_id"],)) if run["vendor_id"] else None
        po = next((p for p in db.purchase_orders() if result.get("po") and p["po_number"] == result["po"]["po_number"]),
                  None)
        ctx = {"po": po, "vendor": vendor, "po_lines_matched": trace.get("po_match", {}).get("data", {}).get("lines", []),
               "net": trace.get("validate", {}).get("data", {}).get("net"), "sha256": run["file_hash"]}
        result["pay_on"] = post_to_ledger(run_id, result, ctx, reviewer)
    elif action == "reject":
        final = "REJECTED"
    else:
        raise ValueError("action must be approve or reject")
    result["final_status"] = final
    result["review"] = {"action": action, "reviewer": reviewer, "note": note, "at": db.now_iso()}
    with db.tx() as c:
        c.execute("UPDATE runs SET final_status=?, result=? WHERE id=?", (final, json.dumps(result, default=str), run_id))
    db.audit(run_id, reviewer, "Approved by reviewer" if action == "approve" else "Rejected by reviewer", note)
    return result
