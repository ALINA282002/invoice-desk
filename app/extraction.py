"""Document reading + field extraction.

Reading:   text layer (pdfplumber)  ->  OCR fallback (RapidOCR, offline) for scanned pages.
Extraction: Claude structured output when ANTHROPIC_API_KEY is set, else a deterministic
            label/regex parser. Either way, values are grounded against the raw document text.
"""
from __future__ import annotations

import base64
import io
import json
import logging
import os
import re
import threading
from datetime import date, datetime
from typing import Any

import pdfplumber
import pymupdf

log = logging.getLogger("extraction")

MIN_TEXT_CHARS_PER_PAGE = 40

# --------------------------------------------------------------------------------------
# Reading
# --------------------------------------------------------------------------------------
_ocr_engine = None
_ocr_lock = threading.Lock()


def get_ocr():
    global _ocr_engine
    with _ocr_lock:
        if _ocr_engine is None:
            logging.getLogger("RapidOCR").setLevel(logging.WARNING)
            from rapidocr import RapidOCR

            _ocr_engine = RapidOCR()
        return _ocr_engine


def _ocr_page(page: pymupdf.Page) -> tuple[str, float, float]:
    """Returns (text, mean confidence, share of text boxes read with < 90% confidence).
    The mean alone hides damage: a faint fax can average 89% while misreading the total."""
    import numpy as np
    from PIL import Image

    pix = page.get_pixmap(dpi=200)
    img = np.array(Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB"))
    res = get_ocr()(img)
    if res is None or res.txts is None:
        return "", 0.0, 0.0
    items = []
    for box, txt, score in zip(res.boxes, res.txts, res.scores):
        ys = [float(p[1]) for p in box]
        xs = [float(p[0]) for p in box]
        items.append({"x": min(xs), "yc": sum(ys) / 4, "h": max(ys) - min(ys), "t": txt, "s": float(score)})
    if not items:
        return "", 0.0, 0.0
    items.sort(key=lambda i: i["yc"])
    med_h = sorted(i["h"] for i in items)[len(items) // 2]
    rows: list[list[dict]] = []
    for it in items:
        if rows and abs(it["yc"] - sum(r["yc"] for r in rows[-1]) / len(rows[-1])) < med_h * 0.6:
            rows[-1].append(it)
        else:
            rows.append([it])
    lines = [" ".join(i["t"] for i in sorted(r, key=lambda i: i["x"])) for r in rows]
    conf = sum(i["s"] for i in items) / len(items)
    low_share = sum(1 for i in items if i["s"] < 0.9) / len(items)
    return "\n".join(lines), conf, low_share


def read_document(pdf_bytes: bytes) -> dict[str, Any]:
    """Return text + how it was obtained, per page."""
    pages_out = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        layer = [(p.extract_text() or "") for p in pdf.pages]
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    for i, page in enumerate(doc):
        txt = layer[i] if i < len(layer) else ""
        if len(txt.strip()) >= MIN_TEXT_CHARS_PER_PAGE:
            pages_out.append({"page": i + 1, "method": "text_layer", "text": txt, "confidence": 1.0, "low_share": 0.0})
        else:
            otxt, conf, low = _ocr_page(page)
            pages_out.append({"page": i + 1, "method": "ocr", "text": otxt, "confidence": round(conf, 3),
                              "low_share": round(low, 3)})
    doc.close()
    methods = {p["method"] for p in pages_out}
    return {
        "pages": pages_out,
        "page_count": len(pages_out),
        "method": "ocr" if methods == {"ocr"} else ("mixed" if len(methods) > 1 else "text_layer"),
        "text": "\n".join(p["text"] for p in pages_out),
        "ocr_confidence": round(min((p["confidence"] for p in pages_out), default=0.0), 3),
    }


def render_page_png(pdf_bytes: bytes, page_no: int = 1, dpi: int = 110) -> bytes:
    doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    page = doc[max(0, min(page_no - 1, len(doc) - 1))]
    png = page.get_pixmap(dpi=dpi).tobytes("png")
    doc.close()
    return png


# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
NUM = r"-?[\$€£]?\s?\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?(?!\d)|-?[\$€£]?\s?\d+(?:\.\d{1,2})?(?!\d)"
MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}


def to_num(s: str | None) -> float | None:
    if s is None:
        return None
    s = re.sub(r"[\$€£,\s]", "", s).strip()
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def parse_date(s: str | None) -> str | None:
    """Normalise many date styles to ISO yyyy-mm-dd."""
    if not s:
        return None
    s = s.strip().rstrip(".,")
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", s)
    if m:
        y, mo, d = map(int, m.groups())
        return _iso(y, mo, d)
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", s)  # US style mm/dd/yyyy
    if m:
        mo, d, y = map(int, m.groups())
        if mo > 12:
            mo, d = d, mo
        return _iso(y, mo, d)
    m = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", s)  # EU dd.mm.yyyy
    if m:
        d, mo, y = map(int, m.groups())
        return _iso(y, mo, d)
    m = re.search(r"([A-Za-z]{3,9})\.?\s+(\d{1,2}),?\s+(\d{4})", s)  # November 18, 2026
    if m and m.group(1)[:3].lower() in MONTHS:
        return _iso(int(m.group(3)), MONTHS[m.group(1)[:3].lower()], int(m.group(2)))
    m = re.search(r"(\d{1,2})[\s\-]+([A-Za-z]{3,9})\.?[\s\-,]+(\d{4})", s)  # 18 Nov 2026 / 18-Nov-2026
    if m and m.group(2)[:3].lower() in MONTHS:
        return _iso(int(m.group(3)), MONTHS[m.group(2)[:3].lower()], int(m.group(1)))
    return None


def _iso(y: int, mo: int, d: int) -> str | None:
    try:
        return date(y, mo, d).isoformat()
    except ValueError:
        return None


DATE_PAT = (r"(\d{4}-\d{1,2}-\d{1,2}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}\.\d{1,2}\.\d{4}|"
            r"[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4}|\d{1,2}[\s\-]+[A-Za-z]{3,9}\.?[\s\-,]+\d{4})")


def _find(patterns: list[str], text: str, flags=re.I) -> str | None:
    for p in patterns:
        m = re.search(p, text, flags)
        if m:
            return m.group(1).strip()
    return None


def _last_amount_on_line(text: str, label_regex: str) -> float | None:
    for line in text.splitlines():
        if re.search(label_regex, line, re.I):
            nums = re.findall(NUM, line)
            nums = [n for n in nums if re.search(r"\d", n)]
            if nums:
                return to_num(nums[-1])
    return None


# --------------------------------------------------------------------------------------
# Rule-based parser (deterministic, offline)
# --------------------------------------------------------------------------------------
GENERIC_NAME_WORDS = {
    "inc", "llc", "ltd", "co", "corp", "corporation", "company", "limited", "plc", "gmbh", "group", "the", "and",
    "office", "supplies", "supply", "services", "service", "solutions", "management", "logistics", "industrial",
    "components", "engineering", "systems", "technologies", "technology", "it", "facilities", "facility", "catering",
    "packaging", "safety", "international", "global", "partners", "consulting", "enterprises", "trading", "foods",
    "manufacturing", "products", "freight", "fm",
}


def _norm_name(s: str) -> str:
    s = re.sub(r"[^a-z0-9 ]", " ", (s or "").lower())
    return " ".join(s.split())


def name_core(s: str) -> str:
    """The distinctive part of a company name: 'Apex Office Supplies LLC' -> 'apex'."""
    words = _norm_name(s).split()
    core = [w for w in words if w not in GENERIC_NAME_WORDS]
    return " ".join(core) or " ".join(words)


def name_similarity(a: str, b: str) -> float:
    """0-100. Both the distinctive core AND the full name must agree, so shared generic words
    ('Office Supplies') can never make two different companies look alike."""
    from rapidfuzz import fuzz
    if not a or not b:
        return 0.0
    legal = {"inc", "llc", "ltd", "co", "corp", "corporation", "company", "limited", "plc", "gmbh", "the"}
    strip = lambda s: " ".join(w for w in _norm_name(s).split() if w not in legal)  # noqa: E731
    full = fuzz.token_sort_ratio(strip(a), strip(b))
    core = fuzz.ratio(name_core(a), name_core(b))
    return float(min(full, core))


def rule_extract(text: str, vendor_names: list[tuple[str, str]]) -> dict[str, Any]:
    """vendor_names: list of (vendor_id, name_or_alias) used to recognise the issuer."""
    from rapidfuzz import fuzz

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    head = "\n".join(lines[:6])
    head_n = _norm_name(head)

    # Vendor: recognise the issuer against vendor-master names in the letterhead area. The name's distinctive
    # core must appear too, so 'Apex Office Supplies' is never read as 'Northwind Office Supplies'.
    vendor_name, best = None, 0
    for _vid, nm in vendor_names:
        sc = fuzz.partial_ratio(_norm_name(nm), head_n)
        if fuzz.partial_ratio(name_core(nm), head_n) < 90:
            sc = min(sc, 60)
        if sc > best:
            best, vendor_name = sc, nm
    if best < 85:
        first = re.sub(r"\b(INVOICE|FREIGHT INVOICE|BILL|TAX INVOICE)\b", "", lines[0] if lines else "", flags=re.I)
        vendor_name = first.strip() or None

    inv_no = _find([
        r"invoice\s*(?:no\.?|number|num\.?|#)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]{2,})",
        r"\binv\.?\s*(?:no\.?|#)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]{2,})",
        r"bill\s*(?:no\.?|number|#)\s*[:#]?\s*([A-Z0-9][A-Z0-9\-/]{2,})",
        # bare label: "Invoice TN-55102" (identifier must contain a digit early on)
        r"\binvoice[ \t]+([A-Z]{1,6}-?\d[A-Z0-9\-/]{2,})",
    ], text)
    if inv_no and re.fullmatch(r"(date|dated|total|amount)", inv_no, re.I):
        inv_no = None

    inv_date = parse_date(_find([
        r"invoice\s*date\s*[:#]?\s*" + DATE_PAT,
        r"date\s*of\s*issue\s*[:#]?\s*" + DATE_PAT,
        r"dated\s*[:#]?\s*" + DATE_PAT,
    ], text))
    if inv_date is None:  # bare "Date 11/13/2026" — but not due/event/ship/delivery/service dates
        for m in re.finditer(r"(?<![a-z])date\b[ \t]*[:#]?[ \t]*" + DATE_PAT, text, re.I):
            before = text[max(0, m.start() - 12):m.start()].lower()
            if not re.search(r"(due|event|ship(ping)?|delivery|service|order|payment|start|end)\s*$", before):
                inv_date = parse_date(m.group(1))
                if inv_date:
                    break
    due_date = parse_date(_find([r"(?:due\s*date|payment\s*due|due)\s*[:#]?\s*" + DATE_PAT], text))

    po = _find([
        r"(?:customer\s+|your\s+)?(?:\bP\.?\s?O\.?|purchase\s*order)\s*(?:no\.?|number|ref\.?|#)?\s*[:#]?\s*"
        r"((?:PO[-\s]?)?\d[\d\-]{2,})",
        r"(?:order|your)\s*ref(?:erence)?\.?\s*[:#]?\s*((?:PO[-\s]?)?\d[\d\-]{2,})",
    ], text)

    terms = _find([r"terms\s*[:#]?\s*(net\s*\d+|due on receipt|\d+\s*days)"], text)

    # Line items: any line whose trailing numbers satisfy qty * unit == amount.
    items = []
    prev_was_item = False
    for line in lines:
        if re.search(r"\b(subtotal|total|tax|vat|amount due|balance)\b", line, re.I):
            prev_was_item = False
            continue
        # wrapped description: "(hardware, docking," / "imaging & configuration)" continues the previous item
        if prev_was_item and items and ":" not in line and \
                len([t for t in re.findall(NUM, line) if re.search(r"\d", t)]) < 3:
            d = items[-1]["description"]
            if d.count("(") > d.count(")") or d.rstrip().endswith((",", "&", "and", "-", "—")) or line[:1].islower():
                items[-1]["description"] = (d + " " + line).strip()
                continue
        prev_was_item = False
        toks = re.findall(NUM, line)
        toks = [t for t in toks if re.search(r"\d", t)]
        if len(toks) < 3:
            continue
        q, u, a = to_num(toks[-3]), to_num(toks[-2]), to_num(toks[-1])
        if q is None or u is None or a is None or q <= 0:
            continue
        if abs(q * u - a) > 0.02 + 0.0005 * a:
            continue
        # strip trailing numeric columns to get description
        body = line
        for t in reversed(toks[-3:]):
            idx = body.rfind(t.strip())
            if idx >= 0:
                body = body[:idx]
        body = re.sub(r"^\d{1,3}[.)]?\s+(?=[A-Za-z])", "", body.strip(" -|"))  # leading row number "1 ", "2."
        sku = None
        msku = re.match(r"^([A-Z0-9]{2,}(?:-[A-Z0-9]+)+)\s+(.*)$", body)
        if msku:
            sku, body = msku.group(1), msku.group(2)
        items.append({"sku": sku, "description": body.strip(), "quantity": q, "unit_price": u, "amount": a})
        prev_was_item = True

    subtotal = _last_amount_on_line(text, r"\bsub\s*-?\s*total\b")
    tax = None
    tax_rate = None
    for line in lines:
        if re.search(r"\b(sales\s*tax|tax|vat|gst)\b", line, re.I) and not re.search(r"tax\s*id|exempt", line, re.I):
            nums = [n for n in re.findall(NUM, line) if re.search(r"\d", n)]
            if nums:
                tax = to_num(nums[-1])
                mr = re.search(r"(\d+(?:\.\d+)?)\s*%", line)
                tax_rate = float(mr.group(1)) if mr else None
                break
    shipping = None  # only a totals-area line ("Shipping  85.00"), never a billed line item
    for line in lines:
        if re.search(r"\b(shipping|freight charge|delivery charge)\b", line, re.I):
            nums = [n for n in re.findall(NUM, line) if re.search(r"\d", n)]
            if len(nums) == 1:
                shipping = to_num(nums[0])
    total = None
    for lab in [r"\b(total\s*due|amount\s*due|balance\s*due|grand\s*total|invoice\s*total)\b", r"^\s*total\b"]:
        total = _last_amount_on_line(text, lab)
        if total is not None:
            break
    if total is None:
        total = _last_amount_on_line(text, r"\btotal\b")

    cur = re.search(r"\b(USD|EUR|GBP|CAD|INR|AUD)\b", text)
    currency = cur.group(1) if cur else ("EUR" if "€" in text else "GBP" if "£" in text else
                                         "USD" if "$" in text else None)

    routing = _find([r"(?:routing|aba)\s*(?:no\.?|number|#)?\s*[:#]?\s*(\d{9})\b"], text)
    account = _find([r"(?<!tax\s)account\s*(?:no\.?|number|#)?\s*[:#]\s*([0-9][0-9 \-]{5,}[0-9])",
                     r"acct\.?\s*(?:no\.?|#)?\s*[:#]?\s*([0-9][0-9 \-]{5,}[0-9])"], text)
    bank_name = _find([r"(?i:bank)[ \t]*:[ \t]*([^\n]+)",
                       r"^((?:[A-Z][\w&.]*[ \t]){0,5}(?:Bank|Credit Union)\b[^\n]*)$"], text, re.M)
    tax_id = _find([r"(?:tax\s*id|ein|vat\s*(?:no|number))\s*[:#]?\s*([0-9A-Z][0-9A-Z\-]{5,})"], text)
    emails = re.findall(r"[A-Za-z0-9._+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+", text)

    notes = [l for l in lines if re.search(
        r"(bank(ing)? details (have )?changed|new (bank|account)|remit .* new|reminder|second notice|overdue|"
        r"reissued|partial shipment|duplicate invoice|re-?sent)", l, re.I)]

    return {
        "vendor_name": vendor_name,
        "vendor_email": emails[0] if emails else None,
        "vendor_tax_id": tax_id,
        "invoice_number": inv_no,
        "invoice_date": inv_date,
        "due_date": due_date,
        "po_number": po,
        "payment_terms": terms,
        "currency": currency,
        "line_items": items,
        "subtotal": subtotal,
        "tax_amount": tax,
        "tax_rate_pct": tax_rate,
        "shipping_amount": shipping,
        "total": total,
        "bank": {"bank_name": bank_name, "routing_number": routing,
                 "account_number": re.sub(r"[\s\-]", "", account) if account else None},
        "notes": notes,
    }


# --------------------------------------------------------------------------------------
# Claude extraction (optional; used when ANTHROPIC_API_KEY is present)
# --------------------------------------------------------------------------------------
_nullable_str = {"type": ["string", "null"]}
_nullable_num = {"type": ["number", "null"]}
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "vendor_name": _nullable_str,
        "vendor_email": _nullable_str,
        "vendor_tax_id": _nullable_str,
        "invoice_number": _nullable_str,
        "invoice_date": {"type": ["string", "null"], "description": "ISO yyyy-mm-dd"},
        "due_date": {"type": ["string", "null"], "description": "ISO yyyy-mm-dd"},
        "po_number": _nullable_str,
        "payment_terms": _nullable_str,
        "currency": _nullable_str,
        "line_items": {"type": "array", "items": {
            "type": "object",
            "properties": {"sku": _nullable_str, "description": {"type": "string"},
                           "quantity": _nullable_num, "unit_price": _nullable_num, "amount": _nullable_num},
            "required": ["sku", "description", "quantity", "unit_price", "amount"],
            "additionalProperties": False}},
        "subtotal": _nullable_num,
        "tax_amount": _nullable_num,
        "tax_rate_pct": _nullable_num,
        "shipping_amount": _nullable_num,
        "total": _nullable_num,
        "bank": {"type": "object", "properties": {"bank_name": _nullable_str, "routing_number": _nullable_str,
                                                  "account_number": _nullable_str},
                 "required": ["bank_name", "routing_number", "account_number"], "additionalProperties": False},
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["vendor_name", "vendor_email", "vendor_tax_id", "invoice_number", "invoice_date", "due_date",
                 "po_number", "payment_terms", "currency", "line_items", "subtotal", "tax_amount", "tax_rate_pct",
                 "shipping_amount", "total", "bank", "notes"],
    "additionalProperties": False,
}

EXTRACTION_PROMPT = """You are an accounts-payable data-entry specialist. Extract the fields of this vendor invoice.

Rules:
- Copy values exactly as printed. Never invent or infer a value that is not on the document: use null instead.
- invoice_number: the vendor's invoice identifier only (not a PO, order, or customer number). null if absent.
- po_number: the buyer's purchase-order reference if printed anywhere (e.g. "PO", "Customer PO", "Your PO"); null if absent.
- Dates as ISO yyyy-mm-dd. US-style numeric dates are month/day/year.
- Amounts as plain numbers (no currency symbols or thousands separators).
- line_items: one entry per billed line, in document order.
- bank: the remit-to / payment bank details printed on the invoice; nulls if none are printed.
- notes: verbatim any statements about changed bank details, reminders/second notices, reissued invoices,
  partial shipments, or anything an AP clerk should notice. Empty list if none."""


def claude_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-5-5")


def claude_extract(pdf_bytes: bytes) -> dict[str, Any]:
    import anthropic

    client = anthropic.Anthropic()
    content = [
        {"type": "document", "source": {"type": "base64", "media_type": "application/pdf",
                                        "data": base64.standard_b64encode(pdf_bytes).decode()}},
        {"type": "text", "text": EXTRACTION_PROMPT},
    ]
    kwargs = dict(
        model=CLAUDE_MODEL,
        max_tokens=16000,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA}},
        messages=[{"role": "user", "content": content}],
    )
    try:
        resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
    except anthropic.BadRequestError:
        resp = client.messages.create(**kwargs)
    if resp.stop_reason == "refusal":
        raise RuntimeError("Model declined to process this document")
    text = next(b.text for b in resp.content if getattr(b, "type", "") == "text")
    return json.loads(text)


def claude_summarise(context: dict[str, Any]) -> str | None:
    """Plain-English explanation for a non-technical approver. Never changes the decision."""
    if not claude_available():
        return None
    try:
        import anthropic

        client = anthropic.Anthropic()
        resp = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=2000,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content":
                       "Write a 2-3 sentence plain-English explanation of this accounts-payable decision for a "
                       "finance manager. State the decision, the main reason, and what happens next. Use only the "
                       "facts given; do not add new ones.\n\n" + json.dumps(context, default=str)}],
        )
        return next((b.text for b in resp.content if getattr(b, "type", "") == "text"), None)
    except Exception as e:  # summary is a nice-to-have
        log.warning("summary failed: %s", e)
        return None


# --------------------------------------------------------------------------------------
# Grounding: does each extracted value literally appear in the document text?
# --------------------------------------------------------------------------------------
def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def grounding_report(fields: dict[str, Any], text: str) -> dict[str, bool]:
    nt = _norm(text)
    nums = {to_num(n) for n in re.findall(NUM, text) if re.search(r"\d", n)}
    out = {}
    for k in ("invoice_number", "po_number"):
        v = fields.get(k)
        if v:
            out[k] = _norm(str(v)) in nt
    for k in ("total", "subtotal", "tax_amount"):
        v = fields.get(k)
        if v is not None:
            out[k] = round(float(v), 2) in nums
    if fields.get("invoice_date"):
        out["invoice_date"] = True  # dates are reformatted; checked via parse below
        try:
            d = datetime.fromisoformat(fields["invoice_date"]).date()
            cands = {parse_date(m) for m in re.findall(DATE_PAT, text)}
            out["invoice_date"] = d.isoformat() in cands
        except ValueError:
            out["invoice_date"] = False
    return out
