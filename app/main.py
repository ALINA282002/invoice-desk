"""FastAPI app: REST API, live processing stream (SSE), watched AP mailbox folder, static UI."""
from __future__ import annotations

import asyncio
import csv
import io
import json
import logging
import os
import shutil
import threading
import time
from collections import Counter
from datetime import date
from typing import Any

from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import db, pipeline
from .extraction import claude_available, get_ocr, render_page_png

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("RapidOCR").setLevel(logging.WARNING)
log = logging.getLogger("app")

ROOT = db.ROOT
STATIC = ROOT / "static"
INBOX = ROOT / "inbox"
OCR_READY = {"ready": False}

app = FastAPI(title="Invoice Desk", version="2.0")


@app.middleware("http")
async def no_cache_ui(request, call_next):
    resp = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        resp.headers["Cache-Control"] = "no-cache"
    return resp


def _bootstrap() -> None:
    """On a fresh install (no company, no vendors), load the configuration in BOOTSTRAP_DIR if one is set:
    company.json, vendors.csv, purchase_orders.csv. Hosted demo instances start with empty disks, so this keeps
    them configured across restarts. Invoices are never bootstrapped."""
    d = os.environ.get("BOOTSTRAP_DIR")
    if not d:
        return
    from pathlib import Path
    p = Path(d)
    if not p.is_absolute():
        p = ROOT / p
    if db.get_company().get("legal_name") or db.q1("SELECT COUNT(*) n FROM vendors")["n"]:
        return
    try:
        if (p / "company.json").exists():
            db.set_company({**db.get_company(), **json.loads((p / "company.json").read_text(encoding="utf-8"))})
        if (p / "vendors.csv").exists():
            db.import_vendors((p / "vendors.csv").read_text(encoding="utf-8-sig"))
        if (p / "purchase_orders.csv").exists():
            db.import_purchase_orders((p / "purchase_orders.csv").read_text(encoding="utf-8-sig"))
        db.audit(None, "System", "Configuration loaded", f"from {p.name}/ on first start")
        log.info("bootstrap: loaded configuration from %s", p)
    except Exception as e:
        log.warning("bootstrap failed: %s", e)


@app.on_event("startup")
def _startup() -> None:
    db.con()
    _bootstrap()
    # runs interrupted by a restart can't resume; mark them so they don't look stuck
    with db.tx() as c:
        c.execute("UPDATE runs SET state='error', error='Interrupted by a server restart — upload again' "
                  "WHERE state IN ('queued','running')")

    def warm():
        try:
            get_ocr()
            OCR_READY["ready"] = True
            log.info("OCR engine ready")
        except Exception as e:
            log.warning("OCR unavailable: %s", e)

    threading.Thread(target=warm, daemon=True).start()
    if os.environ.get("INBOX_WATCH", "1") == "1":
        threading.Thread(target=_watch_inbox, daemon=True).start()


def _watch_inbox() -> None:
    """The AP mailbox: any PDF saved into ./inbox is picked up and processed (oldest first)."""
    INBOX.mkdir(exist_ok=True)
    done = INBOX / "processed"
    done.mkdir(exist_ok=True)
    while True:
        try:
            for f in sorted(INBOX.glob("*.pdf"), key=lambda p: p.name.lower()):
                size = f.stat().st_size
                time.sleep(0.5)
                if f.stat().st_size != size:
                    continue
                pipeline.start_run(f.read_bytes(), f.name, "inbox")
                shutil.move(str(f), str(done / f"{int(time.time())}_{f.name}"))
                log.info("inbox: picked up %s", f.name)
        except Exception as e:
            log.warning("inbox watcher: %s", e)
        time.sleep(2)


# ----------------------------------------------------------------------------- helpers
SUMMARY_KEYS = ("id", "created_at", "finished_at", "source", "filename", "state", "decision", "final_status",
                "vendor_id", "vendor_name", "invoice_number", "invoice_date", "due_date", "po_number", "total",
                "currency", "duration_ms", "extractor", "read_method", "pages", "headline", "reason_codes", "queue",
                "error")


def _summary(r: dict[str, Any]) -> dict[str, Any]:
    return {k: r.get(k) for k in SUMMARY_KEYS}


def _run_or_404(run_id: str) -> dict[str, Any]:
    r = db.q1("SELECT * FROM runs WHERE id=?", (run_id,))
    if not r:
        raise HTTPException(404, "Invoice not found")
    return r


def _csv_response(rows: list[dict], cols: list[str], name: str) -> Response:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="{name}"'})


# ----------------------------------------------------------------------------- system
@app.get("/api/health")
def health():
    return {"ok": True, "extractor": "claude" if claude_available() else "rules", "ocr_ready": OCR_READY["ready"],
            "model": os.environ.get("CLAUDE_MODEL", "claude-opus-5-5") if claude_available() else None,
            "inbox": str(INBOX), "busy": pipeline.busy()}


@app.get("/api/setup")
def setup_status():
    co = db.get_company()
    nv = db.q1("SELECT COUNT(*) n FROM vendors")["n"]
    npo = db.q1("SELECT COUNT(*) n FROM purchase_orders")["n"]
    return {"company": bool(co.get("legal_name")), "vendors": nv, "purchase_orders": npo,
            "complete": bool(co.get("legal_name")) and nv > 0 and npo > 0, "company_name": co.get("legal_name")}


@app.get("/api/settings")
def get_settings():
    return {"company": db.get_company(), "policy": db.get_policy()}


@app.put("/api/settings/company")
def put_company(payload: dict = Body(...)):
    co = db.get_company()
    for k in ("legal_name", "ap_email", "currency"):
        if k in payload:
            co[k] = str(payload[k]).strip()[:200]
    db.set_company(co)
    db.audit(None, "Administrator", "Company profile updated", co.get("legal_name", ""))
    return co


@app.put("/api/settings/policy")
def put_policy(payload: dict = Body(...)):
    pol = db.get_policy()
    for k, v in payload.items():
        if k in pol and isinstance(pol[k], bool):
            pol[k] = bool(v)
        elif k in pol:
            try:
                pol[k] = float(v)
            except (TypeError, ValueError):
                raise HTTPException(400, f"{k} must be a number")
    db.set_policy(pol)
    db.audit(None, "Administrator", "Approval policy updated", json.dumps(pol))
    return pol


# ----------------------------------------------------------------------------- master data
async def _read_csv(file: UploadFile) -> str:
    data = await file.read()
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    raise HTTPException(400, "Could not read the file as text CSV")


@app.post("/api/import/vendors")
async def import_vendors(file: UploadFile = File(...)):
    try:
        res = db.import_vendors(await _read_csv(file))
    except db.ImportError_ as e:
        raise HTTPException(400, str(e))
    db.audit(None, "Administrator", "Vendor master imported", f"{file.filename}: {res['added']} added, {res['updated']} updated")
    return res


@app.post("/api/import/purchase-orders")
async def import_pos(file: UploadFile = File(...)):
    try:
        res = db.import_purchase_orders(await _read_csv(file))
    except db.ImportError_ as e:
        raise HTTPException(400, str(e))
    db.audit(None, "Administrator", "PO register imported",
             f"{file.filename}: {res['purchase_orders']} POs ({res['added']} new, {res['updated']} updated)")
    return res


@app.get("/api/vendors")
def list_vendors():
    vs = db.vendors()
    stats = {r["vendor_id"]: r for r in db.q(
        "SELECT vendor_id, COUNT(*) n, SUM(total) v FROM runs WHERE state='done' GROUP BY vendor_id")}
    for v in vs:
        s = stats.get(v["vendor_id"]) or {}
        v["invoice_count"], v["invoice_value"] = s.get("n", 0), round(s.get("v") or 0, 2)
        v["account_last4"] = (v.pop("account_number") or "")[-4:]
    return vs


@app.post("/api/vendors")
def add_vendor(payload: dict = Body(...)):
    try:
        db.upsert_vendor(payload)
    except db.ImportError_ as e:
        raise HTTPException(400, str(e))
    db.audit(None, "Administrator", "Vendor saved", f"{payload.get('vendor_id')} {payload.get('name')}")
    return {"ok": True}


@app.patch("/api/vendors/{vendor_id}")
def patch_vendor(vendor_id: str, payload: dict = Body(...)):
    try:
        db.set_vendor_status(vendor_id, payload.get("status", ""))
    except db.ImportError_ as e:
        raise HTTPException(400, str(e))
    db.audit(None, "Administrator", f"Vendor status → {payload.get('status')}", vendor_id)
    return {"ok": True}


@app.get("/api/purchase-orders")
def list_pos():
    vn = {v["vendor_id"]: v["name"] for v in db.vendors()}
    pos = db.purchase_orders()
    for p in pos:
        p["vendor_name"] = vn.get(p["vendor_id"], p["vendor_id"])
    return pos


@app.get("/api/payments")
def payments():
    vn = {v["vendor_id"]: v["name"] for v in db.vendors()}
    rows = db.ledger()
    for r in rows:
        r["vendor_name"] = vn.get(r["vendor_id"], r["vendor_id"])
    return rows


@app.get("/api/audit")
def audit_log(limit: int = 500):
    rows = db.q("SELECT a.*, r.invoice_number, r.vendor_name FROM audit a LEFT JOIN runs r ON r.id=a.run_id "
                "ORDER BY a.id DESC LIMIT ?", (limit,))
    return rows


# ----------------------------------------------------------------------------- invoices
@app.post("/api/runs")
async def create_runs(files: list[UploadFile] = File(...)):
    items = []
    for f in files:
        data = await f.read()
        if data[:5] != b"%PDF-":
            raise HTTPException(400, f"{f.filename} is not a PDF file")
        if len(data) > 25 * 1024 * 1024:
            raise HTTPException(400, f"{f.filename} is larger than 25 MB")
        items.append((f.filename or "invoice.pdf", data))
    items.sort(key=lambda t: t[0].lower())  # batch is processed in file-name order
    return {"run_ids": [pipeline.start_run(d, n, "upload") for n, d in items]}


def _filter(rows, status, q):
    out = []
    for r in rows:
        if status and status != "ALL":
            if status == "PROCESSING" and r["state"] not in ("queued", "running"):
                continue
            if status == "OPEN" and r["final_status"] not in ("NEEDS_REVIEW", "ON_HOLD"):
                continue
            if status not in ("PROCESSING", "OPEN") and r["final_status"] != status:
                continue
        if q:
            hay = " ".join(str(r.get(k) or "") for k in ("filename", "vendor_name", "invoice_number", "po_number",
                                                         "id", "headline", "total")).lower()
            if q.lower() not in hay:
                continue
        out.append(r)
    return out


@app.get("/api/runs")
def list_runs(status: str | None = None, q: str | None = None, limit: int = 500):
    rows = db.q("SELECT * FROM runs ORDER BY rowid DESC LIMIT ?", (limit,))
    return [_summary(r) for r in _filter(rows, status, q)]


@app.get("/api/runs/export.csv")
def export_runs(status: str | None = None, q: str | None = None):
    rows = _filter(db.q("SELECT * FROM runs ORDER BY rowid DESC"), status, q)
    return _csv_response(rows, ["id", "created_at", "vendor_name", "invoice_number", "invoice_date", "due_date",
                                "po_number", "total", "currency", "final_status", "decision", "headline",
                                "reason_codes", "queue", "filename"], f"invoices-{date.today()}.csv")


@app.get("/api/payments/export.csv")
def export_payments():
    return _csv_response(payments(), ["pay_on", "vendor_name", "vendor_id", "invoice_number", "invoice_date",
                                      "po_number", "net_amount", "tax_amount", "total", "currency", "bank_last4",
                                      "approved_by", "status"], f"payment-run-{date.today()}.csv")


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    r = _run_or_404(run_id)
    out = _summary(r)
    out["trace"] = json.loads(r["trace"]) if r["trace"] else None
    out["result"] = json.loads(r["result"]) if r["result"] else None
    out["audit"] = db.q("SELECT * FROM audit WHERE run_id=? ORDER BY id", (run_id,))
    return out


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str):
    lr = pipeline.LIVE.get(run_id)
    if lr is None:
        r = _run_or_404(run_id)

        async def replay():
            trace = json.loads(r["trace"]) if r["trace"] else []
            yield f"data: {json.dumps({'type': 'run_queued', 'run_id': run_id, 'filename': r['filename'], 'source': r['source'], 'stages': trace})}\n\n"
            if r["result"]:
                yield f"data: {json.dumps({'type': 'run_completed', 'run_id': run_id, 'result': json.loads(r['result']), 'duration_ms': r['duration_ms']})}\n\n"
            elif r["error"]:
                yield f"data: {json.dumps({'type': 'run_error', 'error': r['error']})}\n\n"
            yield "event: end\ndata: {}\n\n"

        return StreamingResponse(replay(), media_type="text/event-stream")

    async def stream():
        i = 0
        while True:
            evs = lr.events[i:]
            for ev in evs:
                yield f"data: {json.dumps(ev, default=str)}\n\n"
            i += len(evs)
            if lr.done and i >= len(lr.events):
                yield "event: end\ndata: {}\n\n"
                return
            await asyncio.sleep(0.12)

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/runs/{run_id}/pdf")
def run_pdf(run_id: str):
    r = _run_or_404(run_id)
    p = db.FILES / f"{run_id}.pdf"
    if not p.exists():
        raise HTTPException(404)
    return FileResponse(p, media_type="application/pdf", filename=r["filename"])


@app.get("/api/runs/{run_id}/page/{n}.png")
def run_page(run_id: str, n: int, dpi: int = 130):
    p = db.FILES / f"{run_id}.pdf"
    if not p.exists():
        raise HTTPException(404)
    return Response(render_page_png(p.read_bytes(), n, max(60, min(dpi, 200))), media_type="image/png",
                    headers={"Cache-Control": "max-age=3600"})


@app.post("/api/runs/{run_id}/review")
def review(run_id: str, payload: dict = Body(...)):
    try:
        res = pipeline.apply_review(run_id, payload.get("action", ""), (payload.get("reviewer") or "Reviewer")[:60],
                                    (payload.get("note") or "")[:1000])
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "final_status": res["final_status"]}


# ----------------------------------------------------------------------------- overview
@app.get("/api/stats")
def stats():
    runs = db.q("SELECT * FROM runs WHERE state='done' ORDER BY rowid")
    n = len(runs)
    dec = Counter(r["decision"] for r in runs)
    fin = Counter(r["final_status"] for r in runs)
    reasons = Counter(c for r in runs for c in (r["reason_codes"] or "").split(",") if c)
    val = lambda rs: round(sum((r["total"] or 0) for r in rs), 2)  # noqa: E731
    dup = [r for r in runs if "DUPLICATE" in (r["reason_codes"] or "")]
    fraud = [r for r in runs if "BANK_DETAILS_CHANGED" in (r["reason_codes"] or "")]
    open_ = [r for r in runs if r["final_status"] in ("NEEDS_REVIEW", "ON_HOLD")]
    sched = db.q("SELECT COALESCE(SUM(total),0) v, COUNT(*) n FROM invoice_ledger")[0]
    return {
        "total_runs": n,
        "processing": db.q1("SELECT COUNT(*) n FROM runs WHERE state IN ('queued','running')")["n"],
        "errors": db.q1("SELECT COUNT(*) n FROM runs WHERE state='error'")["n"],
        "decisions": dict(dec), "final_statuses": dict(fin),
        "touchless_rate": round(dec.get("APPROVED", 0) / n * 100, 1) if n else None,
        "open_exceptions": len(open_), "open_value": val(open_),
        "value_processed": val(runs),
        "scheduled": {"count": sched["n"], "value": round(sched["v"], 2)},
        "duplicates_prevented": {"count": len(dup), "value": val(dup)},
        "fraud_held": {"count": len(fraud), "value": val(fraud)},
        "avg_duration_ms": round(sum(r["duration_ms"] or 0 for r in runs) / n) if n else None,
        "reason_counts": reasons.most_common(12),
        "read_methods": dict(Counter(r["read_method"] for r in runs)),
        "owners": Counter(r["queue"] for r in open_ if r["queue"]).most_common(6),
        "reason_titles": pipeline.REASON_TITLES,
    }


# ----------------------------------------------------------------------------- data management
@app.post("/api/admin/delete-invoices")
def delete_invoices():
    if pipeline.busy():
        raise HTTPException(409, "Wait until processing finishes")
    pipeline.LIVE.clear()
    db.delete_invoices()
    return {"ok": True}


@app.post("/api/admin/delete-all")
def delete_all():
    if pipeline.busy():
        raise HTTPException(409, "Wait until processing finishes")
    pipeline.LIVE.clear()
    db.delete_all()
    return {"ok": True}


# ----------------------------------------------------------------------------- UI
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.exception_handler(Exception)
async def unhandled(_req, exc):
    log.exception("unhandled")
    return JSONResponse({"detail": str(exc)}, status_code=500)
