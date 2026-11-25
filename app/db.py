"""SQLite persistence.

The application starts EMPTY: no vendors, no purchase orders, no invoice history, no runs.
Master data (vendor master, PO register) is imported by the user from CSV exports; every ledger
entry is created by an invoice that this system actually processed and approved.
"""
from __future__ import annotations

import csv
import io
import json
import re
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STORAGE = ROOT / "storage"
DB_PATH = STORAGE / "invoice_desk.db"
FILES = STORAGE / "files"

DEFAULT_POLICY = {
    "price_tolerance_pct": 2.0,
    "price_tolerance_abs": 250.0,
    "auto_approve_limit": 50000.0,
    "duplicate_number_similarity": 0.85,
    "max_invoice_age_days": 180,
    "max_tax_rate_pct": 12.0,
    "po_inference_min_confidence": 0.80,
    "allow_auto_approve_inferred_po": True,
    "min_extraction_confidence": 0.70,
}
DEFAULT_COMPANY = {"legal_name": "", "ap_email": "", "currency": "USD"}

_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS vendors (
  vendor_id TEXT PRIMARY KEY, name TEXT NOT NULL, aliases TEXT, status TEXT, tax_id TEXT, email_domain TEXT,
  contact_email TEXT, contact_phone TEXT, bank_name TEXT, routing_number TEXT, account_number TEXT,
  payment_terms_days INTEGER, currency TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS purchase_orders (
  po_number TEXT PRIMARY KEY, vendor_id TEXT, issue_date TEXT, description TEXT, department TEXT,
  requester TEXT, status TEXT, currency TEXT, updated_at TEXT);
CREATE TABLE IF NOT EXISTS po_lines (
  po_number TEXT, line_no INTEGER, sku TEXT, description TEXT, quantity REAL, unit_price REAL,
  PRIMARY KEY (po_number, line_no));
CREATE TABLE IF NOT EXISTS invoice_ledger (
  id INTEGER PRIMARY KEY AUTOINCREMENT, invoice_number TEXT, vendor_id TEXT, po_number TEXT,
  invoice_date TEXT, due_date TEXT, net_amount REAL, tax_amount REAL, total REAL, currency TEXT, status TEXT,
  pay_on TEXT, bank_last4 TEXT, po_line_qty TEXT, file_hash TEXT, run_id TEXT, approved_by TEXT, created_at TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY, created_at TEXT, finished_at TEXT, source TEXT, filename TEXT, file_hash TEXT,
  state TEXT, decision TEXT, final_status TEXT, vendor_id TEXT, vendor_name TEXT, invoice_number TEXT,
  invoice_date TEXT, due_date TEXT, po_number TEXT, total REAL, currency TEXT, duration_ms INTEGER,
  extractor TEXT, read_method TEXT, pages INTEGER, headline TEXT, reason_codes TEXT, queue TEXT,
  line_sig TEXT, trace TEXT, result TEXT, error TEXT);
CREATE TABLE IF NOT EXISTS audit (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, ts TEXT, actor TEXT, action TEXT, note TEXT);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


_con: sqlite3.Connection | None = None


def con() -> sqlite3.Connection:
    global _con
    if _con is None:
        STORAGE.mkdir(exist_ok=True)
        FILES.mkdir(exist_ok=True)
        _con = sqlite3.connect(DB_PATH, check_same_thread=False)
        _con.row_factory = sqlite3.Row
        _con.executescript(SCHEMA)
        _con.execute("INSERT OR IGNORE INTO settings VALUES ('policy', ?)", (json.dumps(DEFAULT_POLICY),))
        _con.execute("INSERT OR IGNORE INTO settings VALUES ('company', ?)", (json.dumps(DEFAULT_COMPANY),))
        _con.commit()
    return _con


@contextmanager
def tx():
    with _lock:
        c = con()
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise


def q(sql: str, args: tuple = ()) -> list[dict[str, Any]]:
    with _lock:
        return [dict(r) for r in con().execute(sql, args).fetchall()]


def q1(sql: str, args: tuple = ()) -> dict[str, Any] | None:
    rows = q(sql, args)
    return rows[0] if rows else None


# ---------------------------------------------------------------- settings
def _get_setting(key: str, default: dict) -> dict[str, Any]:
    row = q1("SELECT value FROM settings WHERE key=?", (key,))
    val = dict(default)
    if row:
        val.update(json.loads(row["value"]))
    return val


def get_policy() -> dict[str, Any]:
    return _get_setting("policy", DEFAULT_POLICY)


def set_policy(p: dict[str, Any]) -> None:
    with tx() as c:
        c.execute("INSERT OR REPLACE INTO settings VALUES ('policy', ?)", (json.dumps(p),))


def get_company() -> dict[str, Any]:
    return _get_setting("company", DEFAULT_COMPANY)


def set_company(p: dict[str, Any]) -> None:
    with tx() as c:
        c.execute("INSERT OR REPLACE INTO settings VALUES ('company', ?)", (json.dumps(p),))


# ---------------------------------------------------------------- reference data
def vendors() -> list[dict[str, Any]]:
    return q("SELECT * FROM vendors ORDER BY name")


def ledger() -> list[dict[str, Any]]:
    return q("SELECT * FROM invoice_ledger ORDER BY id DESC")


def purchase_orders() -> list[dict[str, Any]]:
    pos = q("SELECT * FROM purchase_orders ORDER BY po_number")
    lines = q("SELECT * FROM po_lines ORDER BY po_number, line_no")
    led = ledger()
    for p in pos:
        p["lines"] = [l for l in lines if l["po_number"] == p["po_number"]]
        p["total_amount"] = round(sum(l["quantity"] * l["unit_price"] for l in p["lines"]), 2)
        p["invoiced_amount"] = round(sum(r["net_amount"] or 0 for r in led if r["po_number"] == p["po_number"]), 2)
        p["remaining_amount"] = round(p["total_amount"] - p["invoiced_amount"], 2)
        p["invoice_count"] = sum(1 for r in led if r["po_number"] == p["po_number"])
    return pos


def add_ledger(e: dict[str, Any]) -> None:
    cols = ("invoice_number", "vendor_id", "po_number", "invoice_date", "due_date", "net_amount", "tax_amount",
            "total", "currency", "status", "pay_on", "bank_last4", "po_line_qty", "file_hash", "run_id",
            "approved_by")
    with tx() as c:
        c.execute(f"INSERT INTO invoice_ledger ({','.join(cols)}, created_at) VALUES ({','.join('?' * len(cols))}, ?)",
                  tuple(e.get(k) for k in cols) + (now_iso(),))


def audit(run_id: str | None, actor: str, action: str, note: str = "") -> None:
    with tx() as c:
        c.execute("INSERT INTO audit (run_id, ts, actor, action, note) VALUES (?,?,?,?,?)",
                  (run_id, now_iso(), actor, action, note))


# ---------------------------------------------------------------- CSV import
class ImportError_(ValueError):
    pass


def _rows(csv_text: str, required: list[str]) -> list[dict[str, str]]:
    text = csv_text.lstrip("﻿")
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ImportError_("The file is empty.")
    headers = [h.strip().lower() for h in reader.fieldnames]
    missing = [r for r in required if r not in headers]
    if missing:
        raise ImportError_(f"Missing required column(s): {', '.join(missing)}. Found: {', '.join(headers)}")
    out = []
    for raw in reader:
        out.append({(k or "").strip().lower(): (v or "").strip() for k, v in raw.items()})
    if not out:
        raise ImportError_("The file has a header row but no data rows.")
    return out


def _num(v: str, field: str, rown: int) -> float:
    try:
        return float(v.replace(",", "").replace("$", ""))
    except ValueError:
        raise ImportError_(f"Row {rown}: '{field}' must be a number (got '{v}').")


VENDOR_STATUSES = {"approved", "blocked", "pending_onboarding", "inactive"}


def import_vendors(csv_text: str) -> dict[str, Any]:
    rows = _rows(csv_text, ["vendor_id", "name", "status"])
    added = updated = 0
    with tx() as c:
        for i, r in enumerate(rows, start=2):
            if not r["vendor_id"] or not r["name"]:
                raise ImportError_(f"Row {i}: vendor_id and name are required.")
            status = r["status"].lower() or "approved"
            if status not in VENDOR_STATUSES:
                raise ImportError_(f"Row {i}: status must be one of {', '.join(sorted(VENDOR_STATUSES))}.")
            exists = c.execute("SELECT 1 FROM vendors WHERE vendor_id=?", (r["vendor_id"],)).fetchone()
            email = r.get("contact_email", "")
            domain = r.get("email_domain") or (email.split("@", 1)[1] if "@" in email else "")
            c.execute("""INSERT OR REPLACE INTO vendors VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (
                r["vendor_id"], r["name"], r.get("aliases", ""), status, r.get("tax_id", ""), domain.lower(), email,
                r.get("contact_phone", ""), r.get("bank_name", ""), re.sub(r"\D", "", r.get("routing_number", "")),
                re.sub(r"\D", "", r.get("account_number", "")),
                int(_num(r.get("payment_terms_days") or "30", "payment_terms_days", i)),
                (r.get("currency") or "USD").upper(), now_iso()))
            updated += bool(exists)
            added += not exists
    return {"rows": len(rows), "added": added, "updated": updated}


def import_purchase_orders(csv_text: str) -> dict[str, Any]:
    """One row per PO line (the usual spreadsheet export shape)."""
    rows = _rows(csv_text, ["po_number", "vendor_id", "line_no", "line_description", "quantity", "unit_price"])
    known_vendors = {v["vendor_id"] for v in vendors()}
    pos: dict[str, dict] = {}
    for i, r in enumerate(rows, start=2):
        if r["vendor_id"] not in known_vendors:
            raise ImportError_(f"Row {i}: vendor_id '{r['vendor_id']}' is not in the vendor master. Import vendors first.")
        p = pos.setdefault(r["po_number"], {"head": r, "lines": []})
        p["lines"].append((int(_num(r["line_no"], "line_no", i)), r.get("sku", ""), r["line_description"],
                           _num(r["quantity"], "quantity", i), _num(r["unit_price"], "unit_price", i)))
    added = updated = 0
    with tx() as c:
        for po_number, p in pos.items():
            h = p["head"]
            exists = c.execute("SELECT 1 FROM purchase_orders WHERE po_number=?", (po_number,)).fetchone()
            c.execute("INSERT OR REPLACE INTO purchase_orders VALUES (?,?,?,?,?,?,?,?,?)", (
                po_number, h["vendor_id"], h.get("issue_date", ""), h.get("po_description", "") or h.get("description", ""),
                h.get("department", ""), h.get("requester", ""), (h.get("status") or "open").lower(),
                (h.get("currency") or "USD").upper(), now_iso()))
            c.execute("DELETE FROM po_lines WHERE po_number=?", (po_number,))
            for ln in p["lines"]:
                c.execute("INSERT INTO po_lines VALUES (?,?,?,?,?,?)", (po_number,) + ln)
            updated += bool(exists)
            added += not exists
    return {"rows": len(rows), "purchase_orders": len(pos), "added": added, "updated": updated}


def upsert_vendor(v: dict[str, Any]) -> None:
    if not v.get("vendor_id") or not v.get("name"):
        raise ImportError_("Vendor ID and name are required.")
    status = (v.get("status") or "approved").lower()
    if status not in VENDOR_STATUSES:
        raise ImportError_("Invalid status.")
    email = v.get("contact_email", "")
    with tx() as c:
        c.execute("INSERT OR REPLACE INTO vendors VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            v["vendor_id"], v["name"], v.get("aliases", ""), status, v.get("tax_id", ""),
            (v.get("email_domain") or (email.split("@", 1)[1] if "@" in email else "")).lower(), email,
            v.get("contact_phone", ""), v.get("bank_name", ""), re.sub(r"\D", "", v.get("routing_number", "")),
            re.sub(r"\D", "", v.get("account_number", "")), int(v.get("payment_terms_days") or 30),
            (v.get("currency") or "USD").upper(), now_iso()))


def set_vendor_status(vendor_id: str, status: str) -> None:
    if status not in VENDOR_STATUSES:
        raise ImportError_("Invalid status.")
    with tx() as c:
        c.execute("UPDATE vendors SET status=?, updated_at=? WHERE vendor_id=?", (status, now_iso(), vendor_id))


def delete_invoices() -> None:
    with tx() as c:
        for t in ("runs", "invoice_ledger", "audit"):
            c.execute(f"DELETE FROM {t}")
    for f in FILES.glob("*.pdf"):
        try:
            f.unlink()
        except OSError:
            pass


def delete_all() -> None:
    delete_invoices()
    with tx() as c:
        for t in ("vendors", "purchase_orders", "po_lines", "settings"):
            c.execute(f"DELETE FROM {t}")
        c.execute("INSERT INTO settings VALUES ('policy', ?)", (json.dumps(DEFAULT_POLICY),))
        c.execute("INSERT INTO settings VALUES ('company', ?)", (json.dumps(DEFAULT_COMPANY),))
