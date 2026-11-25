"""Build the test pack: master-data CSVs + one invoice PDF per scenario + TEST-GUIDE.md.

    .venv\\Scripts\\python scripts\\build_test_pack.py

Output: ./test-pack/
    master-data/vendors.csv            -> Settings > Data import > Vendor master
    master-data/purchase_orders.csv    -> Settings > Data import > PO register
    invoices/NN_<outcome>_<case>.pdf   -> upload (all at once is fine: processed in file-name order)
    TEST-GUIDE.md                      -> what each file tests and the expected result
"""
from __future__ import annotations

import csv
import io
import random
import re
import shutil
from pathlib import Path

import pymupdf
from PIL import Image, ImageFilter
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import LETTER
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / "test-pack"
INV = PACK / "invoices"
MD = PACK / "master-data"
W, H = LETTER
M = 48

COMPANY = {"legal_name": "Halcyon Manufacturing Inc.", "ap_email": "ap@halcyon-mfg.example"}
BUYER = ["Halcyon Manufacturing Inc.", "Attn: Accounts Payable", "400 Lakeshore Drive", "Chicago, IL 60611"]
OTHER_BUYER = ["Brookfield Plastics Corp.", "Accounts Payable Dept.", "1200 River Road", "Toledo, OH 43604"]

# ------------------------------------------------------------------ master data
VENDORS = [
    # id, name, aliases, status, tax_id, domain, email, phone, bank, routing, account, terms
    ("V-1001", "Northwind Office Supplies Inc.", "Northwind Office Supplies|Northwind Supplies", "approved",
     "74-3829105", "northwind-supplies.example", "ar@northwind-supplies.example", "+1 (312) 555-0142",
     "Chase Bank N.A.", "021000021", "483920175", 30),
    ("V-1002", "Apex Industrial Components LLC", "Apex Industrial|Apex Industrial Components", "approved",
     "36-4410982", "apex-industrial.example", "billing@apex-industrial.example", "+1 (414) 555-0187",
     "Bank of America N.A.", "026009593", "003944712286", 45),
    ("V-1003", "BrightPath IT Services Ltd.", "BrightPath IT|BrightPath IT Services", "approved",
     "81-2207634", "brightpath-it.example", "accounts@brightpath-it.example", "+1 (646) 555-0119",
     "Wells Fargo Bank", "121000248", "773100984410", 30),
    ("V-1004", "Meridian Logistics Co.", "Meridian Logistics|Meridian Freight", "approved",
     "47-9902318", "meridian-logistics.example", "invoices@meridian-logistics.example", "+1 (214) 555-0163",
     "PNC Bank", "043000096", "552011873301", 15),
    ("V-1005", "Cobalt Facilities Management", "Cobalt Facilities|Cobalt FM", "approved",
     "20-5583017", "cobaltfm.example", "finance@cobaltfm.example", "+1 (630) 555-0128",
     "JPMorgan Chase Bank", "071000013", "991022845567", 30),
    ("V-1006", "Greenleaf Catering Co.", "Greenleaf Catering", "approved",
     "61-3375590", "greenleaf-catering.example", "hello@greenleaf-catering.example", "+1 (773) 555-0154",
     "Fifth Third Bank", "071923909", "7140022618", 14),
    ("V-1007", "Summit Packaging Ltd", "Summit Packaging", "blocked",
     "58-1120449", "summitpack.example", "ar@summitpack.example", "+1 (317) 555-0171",
     "Huntington National Bank", "044000024", "0162773390", 30),
    ("V-1008", "Orion Safety Supply Co.", "Orion Safety Supply|Orion Safety", "pending_onboarding",
     "39-6610274", "orionsafety.example", "orders@orionsafety.example", "+1 (608) 555-0133",
     "U.S. Bank", "075000022", "182244719053", 30),
    ("V-1009", "Kestrel Engineering Ltd.", "Kestrel Engineering", "approved",
     "88-4417730", "kestrel-eng.example", "accounts@kestrel-eng.example", "+1 (416) 555-0190",
     "RBC Bank (USA)", "053101561", "640017755120", 30),
    ("V-1010", "Harbor Point Printing Co.", "Harbor Point Printing|Harbor Point", "inactive",
     "52-7730416", "harborpointprint.example", "billing@harborpointprint.example", "+1 (847) 555-0126",
     "BMO Bank N.A.", "071025661", "550031887264", 30),
]

POS = [
    # po, vendor, issue, description, dept, requester, status, currency, [(sku, desc, qty, unit)]
    ("PO-4500-0101", "V-1001", "2026-10-28", "Q4 office consumables & seating", "Operations", "Dana Whitfield", "open", "USD",
     [("NW-PAP-A4", "Copy paper A4 80gsm (box of 5 reams)", 40, 42.50), ("NW-TON-85A", "HP 85A toner cartridge", 12, 68.90),
      ("NW-CHR-ERG", "Ergonomic mesh office chair", 6, 189.00), ("NW-WBM-12", "Whiteboard markers assorted (12 pack)", 25, 9.75),
      ("NW-DSK-ORG", "Desk organiser set", 20, 14.20)]),
    ("PO-4500-0105", "V-1001", "2026-11-03", "Breakroom & janitorial consumables", "Facilities", "Dana Whitfield", "open", "USD",
     [("NW-COF-1KG", "Coffee beans whole roast 1kg", 30, 18.00), ("NW-TWL-CS", "Paper towels multifold (case)", 20, 32.00),
      ("NW-SOAP-1L", "Dish soap 1L", 24, 4.50)]),
    ("PO-4500-0109", "V-1001", "2026-11-06", "Workstation accessories - new hires", "IT", "Priya Raman", "open", "USD",
     [("NW-DOCK-C", "USB-C docking station", 10, 145.00), ("NW-MON-27", "27-inch QHD monitor", 10, 219.00)]),
    ("PO-4500-0110", "V-1001", "2026-11-04", "Plant 2 signage, safety & stationery refresh", "Operations", "Dana Whitfield", "open", "USD",
     None),  # lines generated below (multi-page invoice)
    ("PO-4500-0102", "V-1002", "2026-09-15", "Hydraulic pump assemblies HP-220 (blanket order)", "Plant Maintenance", "Marcus Oyelaran", "open", "USD",
     [("HP-220", "Hydraulic pump assembly HP-220", 400, 120.00)]),
    ("PO-4500-0114", "V-1002", "2026-11-02", "CNC spindle overhaul - Line 3", "Plant Maintenance", "Marcus Oyelaran", "open", "USD",
     [("SVC-CNC-OH", "CNC spindle overhaul service - Line 3", 1, 64500.00)]),
    ("PO-4500-0103", "V-1003", "2026-09-01", "Managed IT service desk - Q4 2026", "IT", "Priya Raman", "open", "USD",
     [("MSD-OCT", "Managed service desk - October 2026", 1, 8500.00), ("MSD-NOV", "Managed service desk - November 2026", 1, 8500.00),
      ("MSD-DEC", "Managed service desk - December 2026", 1, 8500.00)]),
    ("PO-4500-0090", "V-1001", "2026-07-06", "Q3 office consumables", "Operations", "Dana Whitfield", "closed", "USD",
     [("NW-PAP-A4", "Copy paper A4 80gsm (box of 5 reams)", 30, 41.00), ("NW-TON-85A", "HP 85A toner cartridge", 10, 67.50)]),
    ("PO-4500-0120", "V-1010", "2026-11-04", "Product brochure print run", "Marketing", "Owen Patel", "open", "USD",
     [("PRN-BRO-A4", "Product brochure A4, 8 pages, full colour", 5000, 0.62)]),
    ("PO-4500-0119", "V-1003", "2026-11-03", "New-hire IT setup - 10 seats", "IT", "Priya Raman", "open", "USD",
     [("LT-14-PRO", "Laptop 14-inch business (configured)", 10, 1150.00), ("DOCK-USBC", "USB-C docking station", 10, 145.00),
      ("SVC-IMG", "Imaging & configuration (per seat)", 10, 85.00)]),
    ("PO-4500-0104", "V-1004", "2026-10-05", "Inbound freight - Oct/Nov lanes", "Supply Chain", "Luis Ortega", "open", "USD",
     [("FTL-CHI-DAL", "Full truckload Chicago IL to Dallas TX", 3, 1850.00), ("LTL-CONS", "LTL consolidated shipment Midwest", 4, 420.00)]),
    ("PO-4500-0108", "V-1004", "2026-10-20", "Warehouse transfer & storage", "Supply Chain", "Luis Ortega", "open", "USD",
     [("DRY-LOC", "Local drayage move", 6, 310.00), ("STO-PAL", "Pallet storage - monthly", 1, 950.00)]),
    ("PO-4500-0106", "V-1005", "2026-10-01", "Q4 janitorial & HVAC maintenance", "Facilities", "Grace Kim", "open", "USD",
     [("JAN-MON", "Janitorial services - monthly", 3, 6200.00), ("HVAC-PM", "HVAC preventive maintenance", 2, 1450.00),
      ("CONS-RS", "Washroom consumables restock", 3, 380.00)]),
    ("PO-4500-0107", "V-1006", "2026-11-02", "All-hands staff lunch", "People Ops", "Hannah Brooks", "open", "USD",
     [("CAT-BUF", "Buffet catering (per person)", 120, 28.50), ("CAT-BEV", "Beverage package (per person)", 120, 6.00)]),
    ("PO-4500-0115", "V-1006", "2026-11-10", "Holiday party catering", "People Ops", "Hannah Brooks", "open", "USD",
     [("CAT-BUF", "Buffet catering (per person)", 150, 28.50), ("CAT-BEV", "Beverage package (per person)", 150, 6.00)]),
    ("PO-4500-0116", "V-1006", "2026-11-12", "Customer workshop catering", "Sales", "Owen Patel", "open", "USD",
     [("CAT-BUF", "Buffet catering (per person)", 150, 28.50), ("CAT-BEV", "Beverage package (per person)", 150, 6.00)]),
    ("PO-4500-0117", "V-1007", "2026-08-12", "Corrugated shipping boxes", "Supply Chain", "Luis Ortega", "open", "USD",
     [("BOX-18x12", "Corrugated box 18x12x10 double wall", 2000, 1.85)]),
    ("PO-4500-0118", "V-1008", "2026-11-09", "PPE for Plant 2", "EHS", "Grace Kim", "open", "USD",
     [("PPE-HAT", "Hard hat ANSI Type I", 50, 24.00), ("PPE-VEST", "Hi-vis safety vest class 2", 50, 12.50)]),
    ("PO-4500-0111", "V-1009", "2026-10-22", "Torque tool calibration", "Quality", "Mei Lin", "open", "USD",
     [("CAL-TRQ", "Calibration service - torque tools", 4, 1250.00)]),
    ("PO-4500-0112", "V-1009", "2026-11-05", "Sensor modules KS-200", "Engineering", "Mei Lin", "open", "USD",
     [("KS-200", "Sensor module KS-200", 20, 310.00)]),
]

SIGNAGE = [
    ("SG-EXIT-A4", "Exit sign photoluminescent A4", 24, 18.40), ("SG-FIRE-EXT", "Fire extinguisher location sign", 30, 9.60),
    ("SG-PPE-REQ", "PPE required sign 300x400mm", 16, 14.25), ("SG-FLOOR-TP", "Floor marking tape yellow 50mm", 40, 11.80),
    ("SG-AISLE-NO", "Aisle number sign set 1-20", 2, 96.00), ("SG-FORK-ZN", "Forklift zone floor sign", 10, 42.50),
    ("SG-EYE-WASH", "Eye wash station sign", 8, 12.75), ("SG-FIRST-AID", "First aid point sign", 8, 12.75),
    ("SG-HV-WARN", "High voltage warning label (10 pack)", 6, 21.30), ("SG-NO-SMOKE", "No smoking sign", 12, 7.90),
    ("ST-BINDER-2", "Lever arch binder 2 inch", 60, 4.35), ("ST-PEN-BL50", "Ballpoint pens blue (50 pack)", 12, 13.60),
    ("ST-NOTE-A5", "Notebook A5 ruled", 80, 2.95), ("ST-STAPLE", "Heavy duty stapler", 10, 27.40),
    ("ST-CLIP-LG", "Binder clips large (12 pack)", 30, 3.85), ("ST-LABEL-L7", "Shipping labels L7163 (100 sheets)", 15, 24.90),
    ("ST-TAPE-PK", "Packing tape 48mm (6 pack)", 25, 12.20), ("ST-ENV-C4", "Envelopes C4 (250 box)", 6, 31.50),
    ("ST-FOLD-MN", "Manila folders (100 pack)", 10, 18.75), ("ST-HILITE", "Highlighters assorted (12 pack)", 15, 8.40),
    ("FA-KIT-25", "First aid kit 25 person", 6, 58.00), ("FA-GLOVE-M", "Nitrile gloves medium (100 box)", 20, 9.95),
    ("FA-EARPLUG", "Disposable earplugs (200 box)", 8, 26.40), ("CL-WIPE-IND", "Industrial wipes (tub of 150)", 18, 14.60),
    ("CL-SPILL-KT", "Spill kit general purpose 50L", 3, 112.00), ("CL-BIN-60L", "Recycling bin 60 litre", 12, 36.80),
]
for p in POS:
    if p[0] == "PO-4500-0110":
        POS[POS.index(p)] = p[:8] + (SIGNAGE,)
        break


def write_master_data() -> None:
    MD.mkdir(parents=True, exist_ok=True)
    with open(MD / "vendors.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["vendor_id", "name", "aliases", "status", "tax_id", "email_domain", "contact_email", "contact_phone",
                    "bank_name", "routing_number", "account_number", "payment_terms_days", "currency"])
        for v in VENDORS:
            w.writerow(list(v) + ["USD"])
    with open(MD / "purchase_orders.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["po_number", "vendor_id", "issue_date", "po_description", "department", "requester", "status",
                    "currency", "line_no", "sku", "line_description", "quantity", "unit_price"])
        for po, vid, issue, desc, dept, req, status, cur, lines in POS:
            for i, (sku, ld, q, u) in enumerate(lines, start=1):
                w.writerow([po, vid, issue, desc, dept, req, status, cur, i, sku, ld, q, f"{u:.2f}"])


# ------------------------------------------------------------------ invoice rendering
def fmt(v: float, sym: str = "") -> str:
    return f"{sym}{v:,.2f}"


VEND = {v[0]: v for v in VENDORS}
ADDR = {
    "V-1001": "1180 W Fulton Market, Chicago, IL 60607", "V-1002": "2200 Industrial Pkwy, Milwaukee, WI 53204",
    "V-1003": "55 Water Street, New York, NY 10041", "V-1004": "77 Commerce St, Dallas, TX 75202",
    "V-1005": "900 Oak Brook Rd, Oak Brook, IL 60523", "V-1006": "3120 N Clark St, Chicago, IL 60657",
    "V-1007": "45 Monument Circle, Indianapolis, IN 46204", "V-1008": "18 Gateway Blvd, Madison, WI 53703",
    "V-1009": "200 Bay Street, Toronto, ON M5J 2J2", "V-1010": "75 Lake Cook Rd, Deerfield, IL 60015",
}


class Inv:
    """Small invoice layout engine with a few house styles; supports multi-page line tables."""

    def __init__(self, path: Path, d: dict):
        self.d, self.path = d, path
        self.st = d.get("style", "modern")
        self.accent = HexColor(d.get("accent", "#1f4e8c"))
        self.font, self.bold = {"classic": ("Times-Roman", "Times-Bold"), "typewriter": ("Courier", "Courier-Bold")}.get(
            self.st, ("Helvetica", "Helvetica-Bold"))
        self.c = canvas.Canvas(str(path), pagesize=LETTER)
        self.c.setTitle(f"Invoice {d.get('number') or ''}".strip())
        self.c.setAuthor(d["vendor_name"])
        self.page = 1

    # -- pieces
    def logo(self, x, y, size=34):
        c = self.c
        c.setFillColor(self.accent)
        c.roundRect(x, y - size, size, size, 6, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 14)
        initials = "".join(w[0] for w in self.d["vendor_name"].split()[:2]).upper()
        c.drawCentredString(x + size / 2, y - size / 2 - 5, initials)
        c.setFillColor(black)

    def header(self):
        c, d = self.c, self.d
        title = d.get("title", "INVOICE")
        vaddr = ADDR[d["vendor_id"]] if d["vendor_id"] in ADDR else d.get("vendor_address", "")
        email = d.get("email") or (VEND[d["vendor_id"]][6] if d["vendor_id"] in VEND else "")
        phone = d.get("phone") or (VEND[d["vendor_id"]][7] if d["vendor_id"] in VEND else "")
        if self.st == "modern":
            c.setFillColor(self.accent)
            c.rect(0, H - 100, W, 100, fill=1, stroke=0)
            c.setFillColor(white)
            c.setFont(self.bold, 20)
            c.drawString(M, H - 50, d["vendor_name"])
            c.setFont(self.font, 9)
            c.drawString(M, H - 66, vaddr)
            c.drawString(M, H - 79, f"{email}  |  {phone}")
            c.setFont(self.bold, 26)
            c.drawRightString(W - M, H - 58, title)
            c.setFillColor(black)
            return H - 132
        if self.st == "classic":
            c.setFont(self.bold, 19)
            c.drawCentredString(W / 2, H - 56, d["vendor_name"])
            c.setFont(self.font, 9.5)
            c.drawCentredString(W / 2, H - 71, vaddr)
            c.drawCentredString(W / 2, H - 84, f"{email}  ·  {phone}")
            c.setStrokeColor(self.accent)
            c.setLineWidth(1.4)
            c.line(M, H - 96, W - M, H - 96)
            c.setFont(self.bold, 15)
            c.setFillColor(self.accent)
            c.drawCentredString(W / 2, H - 118, title)
            c.setFillColor(black)
            return H - 146
        # industrial / typewriter: logo left, title right
        if self.st != "typewriter":
            self.logo(M, H - 42)
        x0 = M + (44 if self.st != "typewriter" else 0)
        c.setFont(self.bold, 16)
        c.drawString(x0, H - 56, d["vendor_name"])
        c.setFont(self.font, 8.8)
        c.drawString(x0, H - 69, vaddr)
        c.drawString(x0, H - 81, f"{email}   Tel {phone}")
        c.setFont(self.bold, 22)
        c.setFillColor(self.accent)
        c.drawRightString(W - M, H - 60, title)
        c.setFillColor(black)
        c.setStrokeColor(HexColor("#999999"))
        c.setLineWidth(0.8)
        c.line(M, H - 96, W - M, H - 96)
        return H - 124

    def parties_and_meta(self, y):
        c, d = self.c, self.d
        if d.get("banner"):
            c.setFillColor(HexColor(d.get("banner_color", "#b3261e")))
            c.setFont(self.bold, 11)
            c.drawString(M, y + 4, d["banner"])
            c.setFillColor(black)
            y -= 20
        c.setFont(self.bold, 8.5)
        c.setFillColor(HexColor("#555555"))
        c.drawString(M, y, d.get("billto_label", "BILL TO"))
        c.setFillColor(black)
        c.setFont(self.font, 9.2)
        for i, line in enumerate(d.get("bill_to", BUYER)):
            c.drawString(M, y - 13 * (i + 1), line)
        if d.get("ship_to"):
            c.setFont(self.bold, 8.5)
            c.setFillColor(HexColor("#555555"))
            c.drawString(M + 175, y, "SHIP TO")
            c.setFillColor(black)
            c.setFont(self.font, 9.2)
            for i, line in enumerate(d["ship_to"]):
                c.drawString(M + 175, y - 13 * (i + 1), line)
        mx = W - M - 220
        meta = d["meta"]
        if self.st == "industrial":
            c.setStrokeColor(HexColor("#bbbbbb"))
            c.rect(mx - 8, y - 13 * len(meta) - 2, 228, 13 * len(meta) + 14, stroke=1, fill=0)
        for i, (k, v) in enumerate(meta):
            c.setFont(self.bold, 9)
            c.drawString(mx, y - 13 * i, k)
            c.setFont(self.font, 9)
            c.drawString(mx + 100, y - 13 * i, v)
        return y - max(13 * len(d.get("bill_to", BUYER)), 13 * len(meta)) - 34

    def table_head(self, y):
        c, d = self.c, self.d
        cols = d.get("cols", ["sku", "desc", "qty", "unit", "amount"])
        lab = {"sku": "Item", "desc": "Description", "qty": "Qty", "unit": "Unit price", "amount": "Amount"}
        lab.update(d.get("col_labels", {}))
        c.setFillColor(HexColor(d.get("table_head", "#e9eef6")))
        c.rect(M, y - 6, W - 2 * M, 20, fill=1, stroke=0)
        c.setFillColor(black)
        c.setFont(self.bold, 8.8)
        xs = self.xs(cols)
        for col in cols:
            (c.drawRightString if col in ("qty", "unit", "amount") else c.drawString)(xs[col], y, lab[col])
        return y - 21

    def xs(self, cols):
        x = {"sku": M + 5, "desc": M + 90, "qty": W - M - 185, "unit": W - M - 95, "amount": W - M - 5}
        if "sku" not in cols:
            x["desc"] = M + 5
        return x

    def footer(self, last: bool):
        c, d = self.c, self.d
        c.setFont(self.font, 7.5)
        c.setFillColor(HexColor("#777777"))
        txt = d.get("footnote", "Thank you for your business.")
        if d.get("pages_label"):
            txt = f"{d['vendor_name']} · Invoice {d.get('number')} · Page {self.page}" + ("" if last else " · continued")
        c.drawCentredString(W / 2, 28, txt)
        c.setFillColor(black)

    def build(self):
        c, d = self.c, self.d
        sym = d.get("sym", "")
        y = self.parties_and_meta(self.header())
        cols = d.get("cols", ["sku", "desc", "qty", "unit", "amount"])
        xs = self.xs(cols)
        y = self.table_head(y)
        c.setFont(self.font, 9)
        for ln in d["lines"]:
            if y < 150:
                self.footer(last=False)
                c.showPage()
                self.page += 1
                c.setFont(self.bold, 11)
                c.drawString(M, H - 54, f"{d['vendor_name']} — invoice {d.get('number')} (continued)")
                y = self.table_head(H - 86)
                c.setFont(self.font, 9)
            amt = ln.get("amount", round(ln["qty"] * ln["unit"], 2))
            for col in cols:
                if col == "sku":
                    c.drawString(xs["sku"], y, ln.get("sku", ""))
                elif col == "desc":
                    c.drawString(xs["desc"], y, ln["desc"])
                    if ln.get("wrap"):
                        c.drawString(xs["desc"], y - 12, ln["wrap"])
                elif col == "qty":
                    c.drawRightString(xs["qty"], y, f"{ln['qty']:g}")
                elif col == "unit":
                    c.drawRightString(xs["unit"], y, fmt(ln["unit"], sym))
                else:
                    c.drawRightString(xs["amount"], y, fmt(amt, sym))
            if ln.get("wrap"):
                y -= 12
            if self.st == "industrial":
                c.setStrokeColor(HexColor("#dddddd"))
                c.line(M, y - 5, W - M, y - 5)
            y -= 16
        c.setStrokeColor(HexColor("#aaaaaa"))
        c.setLineWidth(0.6)
        c.line(M, y + 6, W - M, y + 6)
        y -= 14
        if y < 170:
            self.footer(last=False)
            c.showPage()
            self.page += 1
            y = H - 80
        for k, v, b in d["totals"]:
            c.setFont(self.bold if b else self.font, 10 if b else 9.2)
            c.drawString(W - M - 230, y, k)
            c.drawRightString(W - M - 5, y, v)
            y -= 16
        y -= 14
        for blk in d.get("blocks", []):
            c.setFont(self.bold, 9)
            if blk.get("color"):
                c.setFillColor(HexColor(blk["color"]))
            c.drawString(M, y, blk["title"])
            c.setFillColor(black)
            c.setFont(self.font, 9)
            for i, line in enumerate(blk["lines"]):
                c.drawString(M, y - 13 * (i + 1), line)
            y -= 13 * (len(blk["lines"]) + 1) + 12
        self.footer(last=True)
        c.save()


def to_scan(src: Path, dst: Path, rotate=0.6, noise=0.004, blur=0.45, quality=72, seed=7, blank=False,
            dpi=170, fade=0.0) -> None:
    """Rasterise to an image-only PDF that looks photocopied: grayscale, skew, speckle, blur, JPEG.
    dpi < 100 and fade > 0 (faint toner) simulate a bad fax."""
    random.seed(seed)
    doc = pymupdf.open(src)
    out = pymupdf.open()
    for page in doc:
        if blank:
            img = Image.new("L", (int(page.rect.width * 170 / 72), int(page.rect.height * 170 / 72)), 246)
        else:
            pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
            img = Image.open(io.BytesIO(pix.tobytes("png"))).convert("L")
            if fade:
                img = img.point(lambda v: int(v + (255 - v) * fade))
            if dpi < 170:  # upscale back so the page size looks normal, keeping the lost detail lost
                img = img.resize((int(page.rect.width * 170 / 72), int(page.rect.height * 170 / 72)), Image.BILINEAR)
        img = img.rotate(rotate, resample=Image.BICUBIC, expand=False, fillcolor=255)
        px = img.load()
        w, h = img.size
        for _ in range(int(w * h * noise)):
            px[random.randrange(w), random.randrange(h)] = random.choice([110, 150, 190])
        img = img.filter(ImageFilter.GaussianBlur(blur))
        img = Image.merge("RGB", (img, img.point(lambda v: int(v * 0.985)), img.point(lambda v: int(v * 0.95))))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        p = out.new_page(width=page.rect.width, height=page.rect.height)
        p.insert_image(p.rect, stream=buf.getvalue())
    out.save(dst)
    out.close()
    doc.close()
    src.unlink()


# ------------------------------------------------------------------ scenarios
def lines_of(po: str, picks=None) -> list[dict]:
    p = next(x for x in POS if x[0] == po)
    out = []
    for i, (sku, desc, q, u) in enumerate(p[8], start=1):
        if picks is None or i in picks:
            out.append({"sku": sku, "desc": desc, "qty": picks[i] if isinstance(picks, dict) else q, "unit": u})
    return out


def totals(lines, tax_rate=None, tax_label=None, total_label="Total Due", total_override=None, sym=""):
    sub = round(sum(round(l["qty"] * l["unit"], 2) for l in lines), 2)
    tax = round(sub * tax_rate / 100 + 1e-9, 2) if tax_rate else 0.0
    tot = total_override if total_override is not None else round(sub + tax, 2)
    rows = [("Subtotal", fmt(sub, sym), False)]
    rows.append((tax_label or (f"Sales Tax ({tax_rate:g}%)" if tax_rate else "Tax"), fmt(tax, sym), False))
    rows.append((total_label, fmt(tot, sym), True))
    return rows, sub, tax, tot


def bank_block(vid, title="PAYMENT DETAILS"):
    v = VEND[vid]
    return {"title": title, "lines": [f"Bank: {v[8]}", f"Routing No: {v[9]}", f"Account No: {v[10]}"]}


SCEN: list[dict] = []


def scen(file, outcome, what, why, depends=None, wrap=None, **inv):
    for i, extra in (wrap or {}).items():
        inv["lines"][i]["wrap"] = extra
    SCEN.append({"file": file, "outcome": outcome, "what": what, "why": why, "depends": depends, "inv": inv})


def add_all():
    # 01 clean exact match
    L = lines_of("PO-4500-0101")
    T, *_ = totals(L, 8.25, total_label="Total Due (USD)")
    scen("01_approved_clean_exact_match.pdf", "APPROVED", "Clean digital invoice, PO printed, 5 itemised lines, separate sales tax.",
         "Every check passes, so it is approved and scheduled with no human touch.",
         vendor_id="V-1001", vendor_name=VEND["V-1001"][1], style="modern", accent="#1f4e8c", number="NW-10342",
         meta=[("Invoice Number:", "NW-10342"), ("Invoice Date:", "November 18, 2026"), ("Due Date:", "December 18, 2026"),
               ("PO Number:", "PO-4500-0101"), ("Terms:", "Net 30")],
         lines=L, totals=T, blocks=[bank_block("V-1001") | {"lines": bank_block("V-1001")["lines"] + ["Tax ID: 74-3829105"]}])
    # 02 scanned with PO
    L = lines_of("PO-4500-0108", {1: 3, 2: 1})
    T, *_ = totals(L, None, total_label="Amount Due")
    scen("02_approved_scanned_with_po.pdf", "APPROVED", "Photocopied/scanned invoice (no text layer) with the PO printed.",
         "OCR reads the image; lines match PO-4500-0108 exactly.", scan=dict(rotate=-0.9, noise=0.005, seed=3),
         vendor_id="V-1004", vendor_name=VEND["V-1004"][1], style="typewriter", accent="#333333", title="FREIGHT INVOICE",
         number="ML-77801", cols=["desc", "qty", "unit", "amount"], table_head="#eeeeee",
         col_labels={"desc": "Service", "unit": "Rate"},
         meta=[("Invoice #:", "ML-77801"), ("Date:", "11/12/2026"), ("PO Number:", "PO-4500-0108"), ("Terms:", "Net 15")],
         lines=L, totals=T, blocks=[{"title": "NOTES", "lines": ["Payment by ACH to account on file."]}])
    # 03 scanned, no PO -> identified
    L = [{"desc": "Full truckload Chicago IL to Dallas TX", "qty": 3, "unit": 1850.00},
         {"desc": "LTL consolidated shipment Midwest", "qty": 4, "unit": 424.50}]
    T, *_ = totals(L, None, total_label="Amount Due")
    scen("03_approved_scanned_no_po_identified_from_lines.pdf", "APPROVED",
         "Scanned invoice with NO PO number; LTL rate is $4.50 higher than the PO (fuel surcharge).",
         "PO-4500-0104 is identified from the vendor's open POs by line items + amount (one clear winner). "
         "+$18.00 (+0.25%) is inside the ±2% / ±$250 tolerance, so it is still approved.", scan=dict(),
         vendor_id="V-1004", vendor_name=VEND["V-1004"][1], style="typewriter", accent="#333333", title="FREIGHT INVOICE",
         number="ML-77812", cols=["desc", "qty", "unit", "amount"], table_head="#eeeeee",
         col_labels={"desc": "Service", "unit": "Rate"},
         meta=[("Invoice #:", "ML-77812"), ("Date:", "11/16/2026"), ("Terms:", "Net 15"), ("Shipper Ref:", "HAL-NOV-INBOUND")],
         lines=L, totals=T, blocks=[{"title": "NOTES", "lines": ["LTL rate includes November fuel surcharge adjustment.",
                                                                 "Payment by ACH to account on file."]}])
    # 04 multi-page
    L = lines_of("PO-4500-0110")
    T, *_ = totals(L, 8.25, total_label="Total Due (USD)")
    scen("04_approved_multipage_invoice.pdf", "APPROVED", "Two-page invoice with 26 line items; totals are on page 2.",
         "All pages are read, all 26 lines match PO-4500-0110.",
         vendor_id="V-1001", vendor_name=VEND["V-1001"][1], style="modern", accent="#1f4e8c", number="NW-10360",
         pages_label=True,
         meta=[("Invoice Number:", "NW-10360"), ("Invoice Date:", "November 19, 2026"), ("Due Date:", "December 19, 2026"),
               ("PO Number:", "PO-4500-0110"), ("Terms:", "Net 30")],
         ship_to=["Halcyon Manufacturing - Plant 2", "88 Kingsbury St", "Chicago, IL 60642"],
         lines=L, totals=T, blocks=[bank_block("V-1001")])
    # 05 alternate layout, dd.mm.yyyy, "Order ref"
    L = lines_of("PO-4500-0111")
    T, *_ = totals(L, None, tax_label="Tax (export, 0%)", total_label="Invoice Total")
    scen("05_approved_alternate_layout_and_date_format.pdf", "APPROVED",
         "Different house style (serif, centred), day.month.year dates, PO given as 'Order ref'.",
         "Layout and date format don't matter: fields are found, PO-4500-0111 matches exactly.",
         vendor_id="V-1009", vendor_name=VEND["V-1009"][1], style="classic", accent="#4b3f72", title="TAX INVOICE",
         number="KE-2026-1187",
         meta=[("Invoice No.:", "KE-2026-1187"), ("Invoice date:", "12.11.2026"), ("Due date:", "12.12.2026"),
               ("Order ref:", "PO-4500-0111"), ("Currency:", "USD")],
         lines=L, totals=T, blocks=[bank_block("V-1009", "REMITTANCE")])
    # 06 split PO part 1
    L = lines_of("PO-4500-0102", {1: 250})
    T, *_ = totals(L, 6.0, tax_label="Sales Tax 6.0%", total_label="Invoice Total")
    scen("06_approved_split_po_part_1_of_2.pdf", "APPROVED", "First partial shipment: 250 of the 400 pumps on a blanket PO.",
         "Approved; the PO now shows 250 units / $30,000 consumed. Needed before file 11.",
         vendor_id="V-1002", vendor_name=VEND["V-1002"][1], style="industrial", accent="#8a4b08", table_head="#f1ece4",
         number="AIC-88213",
         meta=[("Invoice Number:", "AIC-88213"), ("Invoice Date:", "20-Oct-2026"), ("Customer PO:", "4500-0102"),
               ("Ship Ref:", "Partial shipment 1"), ("Terms:", "Net 45")],
         lines=L, totals=T, blocks=[{"title": "SHIPMENT", "lines": ["Partial shipment 1 of blanket order PO 4500-0102."]},
                                    bank_block("V-1002", "REMIT TO")])
    # 07 monthly service October
    L = lines_of("PO-4500-0103", {1: 1})
    T, *_ = totals(L, None, tax_label="Tax (0%)")
    scen("07_approved_monthly_service_october.pdf", "APPROVED", "Monthly managed-service invoice for October.",
         "Approved and scheduled. Needed before file 22 (its re-numbered duplicate).",
         vendor_id="V-1003", vendor_name=VEND["V-1003"][1], style="industrial", accent="#5b2a86", table_head="#efe8f6",
         number="BP-2026-0457",
         meta=[("Invoice No:", "BP-2026-0457"), ("Invoice Date:", "2026-10-31"), ("PO Ref:", "PO-4500-0103"),
               ("Service Period:", "October 2026"), ("Terms:", "Net 30")],
         lines=L, totals=T, blocks=[bank_block("V-1003", "BANK DETAILS")])
    # 08 bundled line items
    L = [{"desc": "New-hire IT deployment package - 10 seats (laptops, docking", "qty": 1, "unit": 13800.00}]
    T, *_ = totals(L, 8.875, tax_label="Sales Tax (8.875%)")
    scen("08_approved_bundled_line_items.pdf", "APPROVED",
         "One bundled line ('deployment package - 10 seats') for a PO that lists laptops, docks and imaging separately.",
         "No single PO line matches, but the bundle's $13,800 equals the open value of all three PO lines, so it is "
         "matched as a bundle and the PO is consumed line by line.",
         vendor_id="V-1003", vendor_name=VEND["V-1003"][1], style="industrial", accent="#5b2a86", table_head="#efe8f6",
         number="BP-2026-0519", cols=["desc", "qty", "unit", "amount"],
         meta=[("Invoice No:", "BP-2026-0519"), ("Invoice Date:", "2026-11-21"), ("PO Ref:", "PO-4500-0119"),
               ("Terms:", "Net 30")],
         lines=L, wrap={0: "stations, imaging & configuration)"}, totals=T, blocks=[bank_block("V-1003", "BANK DETAILS")])
    # 08 bank details changed
    L = [{"sku": "JAN-NOV", "desc": "Janitorial services - November 2026", "qty": 1, "unit": 6200.00},
         {"sku": "HVAC-PM", "desc": "HVAC preventive maintenance", "qty": 1, "unit": 1450.00},
         {"sku": "CONS-RS", "desc": "Washroom consumables restock", "qty": 1, "unit": 380.00}]
    T, *_ = totals(L, None, total_label="Total")
    scen("09_on_hold_bank_details_changed.pdf", "ON_HOLD",
         "Everything matches the PO, but the remit-to bank account is new and the sender email is a look-alike domain.",
         "Classic payment-fraud (business email compromise) pattern: payment blocked until verified by phone using the "
         "number on file.", vendor_id="V-1005", vendor_name=VEND["V-1005"][1], style="modern", accent="#1d6b52",
         email="accounts@cobaltfm-billing.example", phone="+1 (630) 555-0199", number="CFM-2611-031",
         meta=[("Invoice #:", "CFM-2611-031"), ("Date:", "19 Nov 2026"), ("PO:", "PO-4500-0106"), ("Due:", "19 Dec 2026")],
         lines=L, totals=T,
         blocks=[{"title": "IMPORTANT: OUR BANKING DETAILS HAVE CHANGED", "color": "#b3261e",
                  "lines": ["Effective immediately please remit all payments to our new account:",
                            "Bank: Metro Community Credit Union", "Routing No: 322271627", "Account No: 665044710093",
                            "Questions? Contact accounts@cobaltfm-billing.example"]}])
    # 09 vendor pending onboarding
    L = lines_of("PO-4500-0118")
    T, *_ = totals(L, 5.5, tax_label="Sales Tax 5.5%")
    scen("10_on_hold_vendor_not_yet_approved.pdf", "ON_HOLD",
         "New vendor whose onboarding is not complete (status 'pending_onboarding'); invoice itself is correct.",
         "Can't pay a vendor before tax and bank verification are done: held until Procurement approves the vendor.",
         vendor_id="V-1008", vendor_name=VEND["V-1008"][1], style="industrial", accent="#c2410c", table_head="#fdeee4",
         number="OSS-1042",
         meta=[("Invoice Number:", "OSS-1042"), ("Invoice Date:", "Nov 17, 2026"), ("PO Number:", "PO-4500-0118"),
               ("Terms:", "Net 30")], lines=L, totals=T, blocks=[bank_block("V-1008")])
    # 10 split PO part 2 over-billed
    L = lines_of("PO-4500-0102", {1: 200})
    T, *_ = totals(L, 6.0, tax_label="Sales Tax 6.0%", total_label="Invoice Total")
    scen("11_review_split_po_part_2_overbilled.pdf", "NEEDS_REVIEW",
         "Second partial shipment: 200 more pumps at the correct price.",
         "On its own it looks perfect — but with file 06 that is 450 of 400 units ordered: $6,000 over the PO. "
         "Routed to the PO owner; credit-note request drafted.", depends="06",
         vendor_id="V-1002", vendor_name=VEND["V-1002"][1], style="industrial", accent="#8a4b08", table_head="#f1ece4",
         number="AIC-88391",
         meta=[("Invoice Number:", "AIC-88391"), ("Invoice Date:", "18-Nov-2026"), ("Customer PO:", "4500-0102"),
               ("Ship Ref:", "Partial shipment 2"), ("Terms:", "Net 45")],
         lines=L, totals=T, blocks=[{"title": "SHIPMENT", "lines": ["Partial shipment 2 - balance of blanket order PO 4500-0102."]},
                                    bank_block("V-1002", "REMIT TO")])
    # 11 price above tolerance
    L = [{"sku": "NW-COF-1KG", "desc": "Coffee beans whole roast 1kg", "qty": 30, "unit": 19.80},
         {"sku": "NW-TWL-CS", "desc": "Paper towels multifold (case)", "qty": 20, "unit": 34.90},
         {"sku": "NW-SOAP-1L", "desc": "Dish soap 1L", "qty": 24, "unit": 4.50}]
    T, *_ = totals(L, 8.25, total_label="Total Due (USD)")
    scen("12_review_unit_prices_above_tolerance.pdf", "NEEDS_REVIEW",
         "Coffee and towels billed 10% and 9% above the PO price.",
         "$112 over is below the $250 cap, but +8.7% is above the 2% cap — both must hold. Buyer must sign off.",
         vendor_id="V-1001", vendor_name=VEND["V-1001"][1], style="modern", accent="#1f4e8c", number="NW-10351",
         meta=[("Invoice Number:", "NW-10351"), ("Invoice Date:", "November 20, 2026"), ("Due Date:", "December 20, 2026"),
               ("PO Number:", "PO-4500-0105"), ("Terms:", "Net 30")], lines=L, totals=T, blocks=[bank_block("V-1001")])
    # 12 charge not on PO
    L = lines_of("PO-4500-0109") + [{"sku": "NW-SHIP-EXP", "desc": "Expedited shipping surcharge", "qty": 1, "unit": 85.00}]
    T, *_ = totals(L, 8.25, total_label="Total Due (USD)")
    scen("13_review_charge_not_on_po.pdf", "NEEDS_REVIEW",
         "Docking stations and monitors match the PO, plus an 'expedited shipping' line nobody ordered.",
         "Charges not on the PO need the requester's approval (or the vendor removes them).",
         vendor_id="V-1001", vendor_name=VEND["V-1001"][1], style="modern", accent="#1f4e8c", number="NW-10355",
         meta=[("Invoice Number:", "NW-10355"), ("Invoice Date:", "November 21, 2026"), ("Due Date:", "December 21, 2026"),
               ("PO Number:", "PO-4500-0109"), ("Terms:", "Net 30")], lines=L, totals=T, blocks=[bank_block("V-1001")])
    # 13 PO does not exist
    L = lines_of("PO-4500-0103", {3: 1})
    T, *_ = totals(L, None, tax_label="Tax (0%)")
    scen("14_review_po_number_does_not_exist.pdf", "NEEDS_REVIEW",
         "PO printed as PO-4500-0130 — a typo; no such PO exists.",
         "Never auto-approved on a wrong PO. The lines point to PO-4500-0103, which is suggested to the reviewer.",
         vendor_id="V-1003", vendor_name=VEND["V-1003"][1], style="industrial", accent="#5b2a86", table_head="#efe8f6",
         number="BP-2026-0502",
         meta=[("Invoice No:", "BP-2026-0502"), ("Invoice Date:", "2026-11-23"), ("PO Ref:", "PO-4500-0130"),
               ("Service Period:", "December 2026"), ("Terms:", "Net 30")],
         lines=L, totals=T, blocks=[bank_block("V-1003", "BANK DETAILS")])
    # 14 no PO, two POs fit
    L = [{"desc": "Buffet catering (per person)", "qty": 150, "unit": 28.50},
         {"desc": "Beverage package (per person)", "qty": 150, "unit": 6.00}]
    T, *_ = totals(L, None, total_label="Total")
    scen("15_review_no_po_and_two_pos_match.pdf", "NEEDS_REVIEW",
         "No PO on the invoice; the vendor has two open POs for exactly the same catering package.",
         "The agent refuses to guess: several open POs fit almost equally, so the requester must say which event this bills.",
         vendor_id="V-1006", vendor_name=VEND["V-1006"][1], style="classic", accent="#3d7a1f", title="INVOICE",
         number="GL-5521", cols=["desc", "qty", "unit", "amount"], table_head="#edf5e6",
         meta=[("Invoice No:", "GL-5521"), ("Date:", "November 22, 2026"), ("Event date:", "Dec 12, 2026"),
               ("Guests:", "150")], lines=L, totals=T, blocks=[bank_block("V-1006")])
    # 15 totals don't add up
    L = lines_of("PO-4500-0115")
    T, *_ = totals(L, None, total_label="Total", total_override=5715.00)
    scen("16_review_totals_do_not_add_up.pdf", "NEEDS_REVIEW",
         "Subtotal $5,175.00 + tax $0.00, but the total says $5,715.00 (digits transposed).",
         "The arithmetic check catches it; a request for a corrected invoice is drafted.",
         vendor_id="V-1006", vendor_name=VEND["V-1006"][1], style="classic", accent="#3d7a1f", title="INVOICE",
         number="GL-5530", cols=["desc", "qty", "unit", "amount"], table_head="#edf5e6",
         meta=[("Invoice No:", "GL-5530"), ("Date:", "November 23, 2026"), ("PO Number:", "PO-4500-0115"),
               ("Event:", "Holiday party")], lines=L, totals=T, blocks=[bank_block("V-1006")])
    # 16 above approval limit
    L = lines_of("PO-4500-0114")
    T, *_ = totals(L, None, tax_label="Tax (service, 0%)", total_label="Invoice Total")
    scen("17_review_above_approval_limit.pdf", "NEEDS_REVIEW",
         "$64,500 service invoice that matches its PO exactly.",
         "Above the $50,000 touchless-approval limit, so a person must sign off even though nothing is wrong.",
         vendor_id="V-1002", vendor_name=VEND["V-1002"][1], style="industrial", accent="#8a4b08", table_head="#f1ece4",
         number="AIC-88402",
         meta=[("Invoice Number:", "AIC-88402"), ("Invoice Date:", "21-Nov-2026"), ("Customer PO:", "PO-4500-0114"),
               ("Terms:", "Net 45")], lines=L, totals=T, blocks=[bank_block("V-1002", "REMIT TO")])
    # 17 future dated
    L = lines_of("PO-4500-0103", {2: 1})
    T, *_ = totals(L, None, tax_label="Tax (0%)")
    scen("18_review_future_dated.pdf", "NEEDS_REVIEW", "Invoice dated November 15, 2027 — a year in the future (typo).",
         "Future dates break payment terms and period cut-off, so it goes to review.",
         vendor_id="V-1003", vendor_name=VEND["V-1003"][1], style="industrial", accent="#5b2a86", table_head="#efe8f6",
         number="BP-2026-0511",
         meta=[("Invoice No:", "BP-2026-0511"), ("Invoice Date:", "November 15, 2027"), ("PO Ref:", "PO-4500-0103"),
               ("Service Period:", "November 2026"), ("Terms:", "Net 30")],
         lines=L, totals=T, blocks=[bank_block("V-1003", "BANK DETAILS")])
    # 18 tax rate too high
    L = [{"sku": "JAN-DEC", "desc": "Janitorial services - December 2026", "qty": 1, "unit": 6200.00},
         {"sku": "CONS-RS", "desc": "Washroom consumables restock", "qty": 1, "unit": 380.00}]
    T, *_ = totals(L, 18.0, tax_label="Service Tax (18%)", total_label="Total")
    scen("19_review_tax_rate_too_high.pdf", "NEEDS_REVIEW", "18% tax charged on facility services.",
         "Effective tax rate is above the 12% plausibility ceiling — the vendor likely applied the wrong rate.",
         vendor_id="V-1005", vendor_name=VEND["V-1005"][1], style="modern", accent="#1d6b52", number="CFM-2612-007",
         meta=[("Invoice #:", "CFM-2612-007"), ("Date:", "24 Nov 2026"), ("PO:", "PO-4500-0106"), ("Due:", "24 Dec 2026")],
         lines=L, totals=T, blocks=[bank_block("V-1005", "REMIT TO")])
    # 19 wrong currency
    L = lines_of("PO-4500-0112")
    T, *_ = totals(L, None, tax_label="VAT (reverse charge, 0%)", total_label="Total (EUR)", sym="€")
    scen("20_review_billed_in_wrong_currency.pdf", "NEEDS_REVIEW", "Invoice billed in EUR against a PO raised in USD.",
         "Paying in a different currency creates FX exposure nobody approved; vendor asked to reissue in USD.",
         vendor_id="V-1009", vendor_name=VEND["V-1009"][1], style="classic", accent="#4b3f72", title="TAX INVOICE",
         number="KE-2026-1203", sym="€",
         meta=[("Invoice No.:", "KE-2026-1203"), ("Invoice date:", "20.11.2026"), ("Due date:", "20.12.2026"),
               ("Order ref:", "PO-4500-0112"), ("Currency:", "EUR")],
         lines=L, totals=T, blocks=[bank_block("V-1009", "REMITTANCE")])
    # 20 same charge twice
    L = [{"sku": "JAN-NOV", "desc": "Janitorial services - November 2026", "qty": 1, "unit": 6200.00},
         {"sku": "HVAC-PM", "desc": "HVAC preventive maintenance", "qty": 1, "unit": 1450.00},
         {"sku": "CONS-RS", "desc": "Washroom consumables restock", "qty": 1, "unit": 380.00}]
    T, *_ = totals(L, None, total_label="Total")
    scen("21_review_same_charge_billed_twice.pdf", "NEEDS_REVIEW",
         "Correct bank details this time, new invoice number — but the same November services and amount as file 09.",
         "Same vendor, PO, lines and amount under a different number: flagged as a possible double charge.",
         depends="09", vendor_id="V-1005", vendor_name=VEND["V-1005"][1], style="modern", accent="#1d6b52",
         number="CFM-2611-044",
         meta=[("Invoice #:", "CFM-2611-044"), ("Date:", "24 Nov 2026"), ("PO:", "PO-4500-0106"), ("Due:", "24 Dec 2026")],
         lines=L, totals=T, blocks=[bank_block("V-1005", "REMIT TO")])
    # 21 renumbered duplicate
    L = lines_of("PO-4500-0103", {1: 1})
    T, *_ = totals(L, None, tax_label="Tax (0%)")
    scen("22_rejected_renumbered_duplicate_of_paid_invoice.pdf", "REJECTED",
         "October invoice re-sent as a 'second notice' with a -R suffix, new date and a different file.",
         "Exact-match checks miss it; the agent strips the suffix and sees same vendor + same amount as file 07.",
         depends="07", vendor_id="V-1003", vendor_name=VEND["V-1003"][1], style="industrial", accent="#5b2a86",
         table_head="#efe8f6", number="BP-2026-0457-R", banner="PAYMENT REMINDER - SECOND NOTICE",
         meta=[("Invoice No:", "BP-2026-0457-R"), ("Invoice Date:", "2026-11-20"), ("PO Ref:", "PO-4500-0103"),
               ("Service Period:", "October 2026"), ("Terms:", "Net 30")],
         lines=L, totals=T, blocks=[{"title": "NOTE", "lines": ["Reissued invoice. Please process at your earliest convenience."]},
                                    bank_block("V-1003", "BANK DETAILS")])
    # 22 same file again -> copied from 01 after build
    scen("23_rejected_same_file_sent_again.pdf", "REJECTED", "Byte-for-byte copy of file 01 (vendor emailed it twice).",
         "Same file fingerprint as an invoice already received.", depends="01", copy_of="01_approved_clean_exact_match.pdf")
    # 23 missing invoice number and date
    L = lines_of("PO-4500-0107")
    scen("24_rejected_missing_invoice_number_and_date.pdf", "REJECTED",
         "Valid vendor and PO, but no invoice number and no invoice date anywhere.",
         "Can't be booked or duplicate-checked: returned to the vendor with a drafted request.",
         vendor_id="V-1006", vendor_name=VEND["V-1006"][1], style="classic", accent="#3d7a1f", title="Bill",
         number="", cols=["desc", "qty", "unit", "amount"], table_head="#edf5e6",
         meta=[("Event:", "All-hands staff lunch"), ("Your PO:", "4500-0107"), ("Guests:", "120")],
         lines=L, totals=[("Total", "4,140.00", True)],
         blocks=[{"title": "Thank you!", "lines": ["Please pay by bank transfer to Fifth Third Bank."]}])
    # 24 blocked vendor
    L = lines_of("PO-4500-0117")
    T, *_ = totals(L, 7.0, tax_label="Sales Tax 7%")
    scen("25_rejected_blocked_vendor.pdf", "REJECTED", "Invoice from a vendor that is blocked in the vendor master.",
         "Blocked vendors are never paid, whatever the invoice says.",
         vendor_id="V-1007", vendor_name=VEND["V-1007"][1], style="industrial", accent="#475569", table_head="#eef2f6",
         number="SP-33019",
         meta=[("Invoice Number:", "SP-33019"), ("Invoice Date:", "Nov 14, 2026"), ("PO Number:", "PO-4500-0117"),
               ("Terms:", "Net 30")], lines=L, totals=T, blocks=[bank_block("V-1007")])
    # 25 unknown vendor
    L = [{"sku": "VX-DESK-160", "desc": "Sit-stand desk 160x80", "qty": 4, "unit": 689.00},
         {"sku": "VX-ACOU-PNL", "desc": "Acoustic wall panel 120x60", "qty": 12, "unit": 74.50}]
    T, *_ = totals(L, 10.25, tax_label="Sales Tax (10.25%)")
    scen("26_rejected_unknown_vendor.pdf", "REJECTED", "Invoice from a company that is not in the vendor master at all.",
         "Unknown vendors can't be paid; forwarded to Procurement for onboarding.",
         vendor_id="X", vendor_name="Vertex Office Interiors LLC", vendor_address="910 W Randolph St, Chicago, IL 60607",
         email="billing@vertex-interiors.example", phone="+1 (312) 555-0177", style="modern", accent="#0e7490",
         number="VOI-2291",
         meta=[("Invoice Number:", "VOI-2291"), ("Invoice Date:", "November 20, 2026"), ("Terms:", "Net 30")],
         lines=L, totals=T, blocks=[{"title": "PAYMENT DETAILS", "lines": ["Bank: Lakeside Bank", "Routing No: 071006486",
                                                                          "Account No: 300045528817"]}])
    # 26 addressed to another company
    L = [{"sku": "NW-PAP-A4", "desc": "Copy paper A4 80gsm (box of 5 reams)", "qty": 20, "unit": 42.50},
         {"sku": "NW-TON-85A", "desc": "HP 85A toner cartridge", "qty": 6, "unit": 68.90}]
    T, *_ = totals(L, 7.25, total_label="Total Due (USD)")
    scen("27_rejected_addressed_to_another_company.pdf", "REJECTED",
         "Genuine Northwind invoice — but billed to a different customer (Brookfield Plastics), sent to us by mistake.",
         "The bill-to party is not our legal entity, so it is returned to the vendor.",
         vendor_id="V-1001", vendor_name=VEND["V-1001"][1], style="modern", accent="#1f4e8c", number="NW-10377",
         bill_to=OTHER_BUYER,
         meta=[("Invoice Number:", "NW-10377"), ("Invoice Date:", "November 21, 2026"), ("Due Date:", "December 21, 2026"),
               ("PO Number:", "PO-7731-0042"), ("Terms:", "Net 30")], lines=L, totals=T, blocks=[bank_block("V-1001")])
    # 27 blank scan
    scen("28_rejected_blank_unreadable_scan.pdf", "REJECTED", "A scanned page that is blank (the scanner fed an empty sheet).",
         "Nothing readable: returned with a request for a legible copy.", blank=True)

    # ---------------- additional edge cases (one per remaining rule) ----------------
    # 29 stale invoice
    L = lines_of("PO-4500-0108", {1: 1})
    T, *_ = totals(L, None, total_label="Amount Due")
    scen("29_review_invoice_older_than_180_days.pdf", "NEEDS_REVIEW",
         "Freight invoice dated March 2, 2026 — almost nine months old, surfacing only now.",
         "Older than the 180-day limit: it may already have been paid another way or be outside the accrual period.",
         vendor_id="V-1004", vendor_name=VEND["V-1004"][1], style="typewriter", accent="#333333", title="FREIGHT INVOICE",
         number="ML-76210", cols=["desc", "qty", "unit", "amount"], table_head="#eeeeee",
         col_labels={"desc": "Service", "unit": "Rate"},
         meta=[("Invoice #:", "ML-76210"), ("Date:", "03/02/2026"), ("PO Number:", "PO-4500-0108"), ("Terms:", "Net 15")],
         lines=L, totals=T, blocks=[{"title": "NOTES", "lines": ["Payment by ACH to account on file."]}])
    # 30 PO closed
    L = lines_of("PO-4500-0090")
    T, *_ = totals(L, 8.25, total_label="Total Due (USD)")
    scen("30_review_po_already_closed.pdf", "NEEDS_REVIEW",
         "Late invoice against last quarter's PO, which has since been closed.",
         "A closed PO has no budget left to spend against; the requester must reopen it or raise a new PO.",
         vendor_id="V-1001", vendor_name=VEND["V-1001"][1], style="modern", accent="#1f4e8c", number="NW-10211",
         meta=[("Invoice Number:", "NW-10211"), ("Invoice Date:", "November 17, 2026"), ("Due Date:", "December 17, 2026"),
               ("PO Number:", "PO-4500-0090"), ("Terms:", "Net 30")], lines=L, totals=T, blocks=[bank_block("V-1001")])
    # 31 PO belongs to another vendor
    L = [{"desc": "Full truckload Chicago IL to Dallas TX", "qty": 1, "unit": 1850.00}]
    T, *_ = totals(L, None, total_label="Amount Due")
    scen("31_review_po_belongs_to_another_vendor.pdf", "NEEDS_REVIEW",
         "Meridian quotes PO-4500-0101 — a real PO, but it was issued to Northwind for office supplies.",
         "A vendor can't bill against another vendor's PO; the lines don't exist on it either.",
         vendor_id="V-1004", vendor_name=VEND["V-1004"][1], style="typewriter", accent="#333333", title="FREIGHT INVOICE",
         number="ML-77840", cols=["desc", "qty", "unit", "amount"], table_head="#eeeeee",
         col_labels={"desc": "Service", "unit": "Rate"},
         meta=[("Invoice #:", "ML-77840"), ("Date:", "11/20/2026"), ("PO Number:", "PO-4500-0101"), ("Terms:", "Net 15")],
         lines=L, totals=T, blocks=[{"title": "NOTES", "lines": ["Payment by ACH to account on file."]}])
    # 32 lines don't add up to the subtotal
    L = [{"sku": "HVAC-PM", "desc": "HVAC preventive maintenance", "qty": 1, "unit": 1450.00},
         {"sku": "CONS-RS", "desc": "Washroom consumables restock", "qty": 1, "unit": 380.00}]
    scen("32_review_lines_do_not_add_up_to_subtotal.pdf", "NEEDS_REVIEW",
         "Two lines totalling $1,830.00, but the subtotal (and total) says $1,930.00.",
         "The lines and the subtotal disagree by $100 — the vendor is overcharging or mis-typed; ask for a corrected invoice.",
         vendor_id="V-1005", vendor_name=VEND["V-1005"][1], style="modern", accent="#1d6b52", number="CFM-2611-052",
         meta=[("Invoice #:", "CFM-2611-052"), ("Date:", "23 Nov 2026"), ("PO:", "PO-4500-0106"), ("Due:", "23 Dec 2026")],
         lines=L, totals=[("Subtotal", "1,930.00", False), ("Tax", "0.00", False), ("Total", "1,930.00", True)],
         blocks=[bank_block("V-1005", "REMIT TO")])
    # 33 tax ID mismatch
    L = lines_of("PO-4500-0112", {1: 10})
    T, *_ = totals(L, None, tax_label="Tax (export, 0%)", total_label="Invoice Total")
    scen("33_review_tax_id_does_not_match.pdf", "NEEDS_REVIEW",
         "Correct vendor, PO and prices — but the tax ID printed on the invoice differs from the one on file.",
         "A different tax ID can mean a different legal entity (or a tampered invoice); confirm before paying.",
         vendor_id="V-1009", vendor_name=VEND["V-1009"][1], style="classic", accent="#4b3f72", title="TAX INVOICE",
         number="KE-2026-1210",
         meta=[("Invoice No.:", "KE-2026-1210"), ("Invoice date:", "21.11.2026"), ("Due date:", "21.12.2026"),
               ("Order ref:", "PO-4500-0112"), ("Currency:", "USD")],
         lines=L, totals=T, blocks=[{"title": "REMITTANCE", "lines": bank_block("V-1009")["lines"] + ["Tax ID: 88-4417731"]}])
    # 34 poor quality scan
    L = lines_of("PO-4500-0109", {1: 10})
    T, *_ = totals(L, 8.25, total_label="Total Due (USD)")
    scen("34_review_poor_quality_scan.pdf", "NEEDS_REVIEW",
         "A faint, blurry, speckled fax-quality scan of an otherwise valid invoice.",
         "Over 5% of the text is read with low confidence (numbers may be misread), so a person must confirm the values against the image before it is paid.",
         scan=dict(dpi=62, fade=0.6, blur=1.0, noise=0.035, quality=22, rotate=1.8, seed=21),
         vendor_id="V-1001", vendor_name=VEND["V-1001"][1], style="modern", accent="#1f4e8c", number="NW-10368",
         meta=[("Invoice Number:", "NW-10368"), ("Invoice Date:", "November 22, 2026"), ("Due Date:", "December 22, 2026"),
               ("PO Number:", "PO-4500-0109"), ("Terms:", "Net 30")], lines=L, totals=T, blocks=[bank_block("V-1001")])

    # ---------------- on-hold variants: one per hold trigger ----------------
    # 35 bank change only — from the vendor's genuine email domain
    L = lines_of("PO-4500-0107")
    T, *_ = totals(L, None, total_label="Total")
    scen("35_on_hold_bank_change_from_genuine_email.pdf", "ON_HOLD",
         "Real Greenleaf invoice from their genuine email domain, matching the PO exactly — but it asks to pay a new account.",
         "A real-looking sender is not proof: vendors' own mailboxes get hacked. Any bank change is held until verified "
         "by phone using the number on file.",
         vendor_id="V-1006", vendor_name=VEND["V-1006"][1], style="classic", accent="#3d7a1f", title="INVOICE",
         number="GL-5544", cols=["desc", "qty", "unit", "amount"], table_head="#edf5e6",
         meta=[("Invoice No:", "GL-5544"), ("Date:", "November 24, 2026"), ("PO Number:", "PO-4500-0107"),
               ("Event:", "All-hands staff lunch")],
         lines=L, totals=T,
         blocks=[{"title": "Please note: we have moved our business account", "color": "#b3261e",
                  "lines": ["Bank: Northshore Savings Bank", "Routing No: 271972572", "Account No: 860044129931",
                            "Questions? hello@greenleaf-catering.example"]}])
    # 36 look-alike sender domain only — bank details are the verified ones
    L = lines_of("PO-4500-0102", {1: 50})
    T, *_ = totals(L, 6.0, tax_label="Sales Tax 6.0%", total_label="Invoice Total")
    scen("36_on_hold_lookalike_sender_domain.pdf", "ON_HOLD",
         "Apex invoice with the correct bank account and PO, sent from billing@apex-industria1.example (a '1' instead of an 'l').",
         "A look-alike domain is a phishing set-up even when nothing else is wrong yet: held, and the vendor is contacted "
         "through the details on file.",
         vendor_id="V-1002", vendor_name=VEND["V-1002"][1], style="industrial", accent="#8a4b08", table_head="#f1ece4",
         email="billing@apex-industria1.example", number="AIC-88415",
         meta=[("Invoice Number:", "AIC-88415"), ("Invoice Date:", "24-Nov-2026"), ("Customer PO:", "4500-0102"),
               ("Terms:", "Net 45")],
         lines=L, totals=T, blocks=[bank_block("V-1002", "REMIT TO")])
    # 37 inactive vendor
    L = lines_of("PO-4500-0120")
    T, *_ = totals(L, 7.0, tax_label="Sales Tax 7%")
    scen("37_on_hold_vendor_marked_inactive.pdf", "ON_HOLD",
         "Correct invoice from a vendor that is marked 'inactive' in the vendor master (dormant for over a year).",
         "Dormant vendor records are a classic fraud target; payment waits until Procurement reactivates and re-verifies "
         "the vendor.",
         vendor_id="V-1010", vendor_name=VEND["V-1010"][1], style="modern", accent="#0f766e", number="HPP-7781",
         meta=[("Invoice Number:", "HPP-7781"), ("Invoice Date:", "November 23, 2026"), ("PO Number:", "PO-4500-0120"),
               ("Terms:", "Net 30")], lines=L, totals=T, blocks=[bank_block("V-1010")])

    # 38 re-numbered resubmission of file 06 (used in the 7-file interview set)
    L = lines_of("PO-4500-0102", {1: 250})
    T, *_ = totals(L, 6.0, tax_label="Sales Tax 6.0%", total_label="Invoice Total")
    scen("38_rejected_renumbered_resubmission_of_part_1.pdf", "REJECTED",
         "Apex's billing system re-sends part 1 as a 'second notice' numbered AIC-88213-R, with a new date and a new file.",
         "Exact-match checks miss it; the agent strips the -R suffix, sees same vendor + same amount as file 06, which is "
         "already scheduled — paying it would pay twice.", depends="06",
         vendor_id="V-1002", vendor_name=VEND["V-1002"][1], style="industrial", accent="#8a4b08", table_head="#f1ece4",
         number="AIC-88213-R", banner="PAYMENT REMINDER - SECOND NOTICE",
         meta=[("Invoice Number:", "AIC-88213-R"), ("Invoice Date:", "22-Nov-2026"), ("Customer PO:", "4500-0102"),
               ("Ship Ref:", "Partial shipment 1"), ("Terms:", "Net 45")],
         lines=L, totals=T, blocks=[{"title": "NOTE", "lines": ["Our records show this invoice as outstanding. Please remit."]},
                                    bank_block("V-1002", "REMIT TO")])


def build_pdfs():
    INV.mkdir(parents=True, exist_ok=True)
    for s in SCEN:
        dst = INV / s["file"]
        inv = s["inv"]
        if inv.get("copy_of"):
            shutil.copyfile(INV / inv["copy_of"], dst)
            continue
        if inv.get("blank"):
            tmp = INV / ("_tmp_" + s["file"])
            c = canvas.Canvas(str(tmp), pagesize=LETTER)
            c.showPage()
            c.save()
            to_scan(tmp, dst, rotate=0.4, noise=0.0008, seed=11, blank=True)
            continue
        if "scan" in inv:
            tmp = INV / ("_tmp_" + s["file"])
            Inv(tmp, inv).build()
            to_scan(tmp, dst, **inv["scan"])
        else:
            Inv(dst, inv).build()


def write_guide():
    lab = {"APPROVED": "Approved", "NEEDS_REVIEW": "Needs review", "ON_HOLD": "On hold", "REJECTED": "Rejected"}
    rows = "\n".join(
        f"| {s['file'][:2]} | `{s['file']}` | **{lab[s['outcome']]}** | {s['what']} | {s['why']}"
        f"{' *(upload after ' + s['depends'] + ')*' if s['depends'] else ''} |" for s in SCEN)
    counts = {k: sum(1 for s in SCEN if s["outcome"] == k) for k in lab}
    (PACK / "TEST-GUIDE.md").write_text(f"""# Invoice Desk — test pack

{len(SCEN)} invoice PDFs covering every decision the system can make
({counts['APPROVED']} approved, {counts['NEEDS_REVIEW']} needs review, {counts['ON_HOLD']} on hold, {counts['REJECTED']} rejected),
plus the master data they are checked against.

## 1. One-time setup (≈1 minute)

1. Start the app and open http://localhost:8765. A setup screen appears on first launch.
2. **Company profile** — legal name: `{COMPANY['legal_name']}` · AP email: `{COMPANY['ap_email']}`
3. **Vendor master** — import `master-data/vendors.csv` ({len(VENDORS)} vendors; one is blocked, one is still in onboarding, one is inactive)
4. **PO register** — import `master-data/purchase_orders.csv` ({len(POS)} POs, one row per PO line)

## 2. Upload invoices

Select all files in `invoices/` and drop them on **Upload invoices** — a batch is processed one by one in file-name
order, which satisfies the dependencies below. You can also upload them one at a time, or copy them into the
`inbox/` folder (the watched AP mailbox).

Some cases depend on an earlier invoice (that is the point — e.g. a split PO only over-bills after the first part
is approved). Files marked *(upload after NN)* must come after that file.

## 3. Expected results

| # | File | Expected | What's in the PDF | Why the system decides this |
|---|---|---|---|---|
{rows}

## Notes

- Files 02, 03, 28 and 34 are image-only scans (no text layer) — they exercise the OCR path; 34 is deliberately poor.
- File 04 has two pages.
- Files 29–34 each exercise one more rule (stale invoice, closed PO, another vendor's PO, lines ≠ subtotal,
  tax-ID mismatch, poor scan).
- Re-running: **Settings → Data management → Delete all invoices** clears invoices, payments and the audit log but
  keeps your company profile, vendors and POs.
- Today's date matters for file 18 (future-dated) and file 29 (180-day age rule); most invoices are dated Oct–Nov 2026.
""", encoding="utf-8")


def main():
    # remove only what this builder produced earlier; anything else you put in test-pack/ is left alone
    for old in list(INV.glob("*.pdf")) if INV.exists() else []:
        if re.match(r"^(_tmp_)?\d\d_(approved|review|on_hold|rejected)_.+\.pdf$", old.name):
            old.unlink()
    write_master_data()
    add_all()
    build_pdfs()
    write_guide()
    print(f"Built {len(SCEN)} invoices, {len(VENDORS)} vendors, {len(POS)} POs -> {PACK}")


if __name__ == "__main__":
    main()
