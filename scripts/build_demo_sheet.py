"""Printable interview cheat sheet: every test invoice, its expected outcome and what it demonstrates.

    .venv\\Scripts\\python scripts\\build_demo_sheet.py   ->  test-pack/DEMO-CHEAT-SHEET.pdf
"""
from __future__ import annotations

import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_test_pack as tp  # noqa: E402

OUT = tp.PACK / "DEMO-CHEAT-SHEET.pdf"
LABEL = {"APPROVED": "Approved", "NEEDS_REVIEW": "Needs review", "ON_HOLD": "On hold", "REJECTED": "Rejected"}
TINT = {"APPROVED": "#e7f6ec", "NEEDS_REVIEW": "#fff6dd", "ON_HOLD": "#fdebe3", "REJECTED": "#fde8e8"}
INK = {"APPROVED": "#067647", "NEEDS_REVIEW": "#93600a", "ON_HOLD": "#b93815", "REJECTED": "#b42318"}

base = ParagraphStyle("b", fontName="Helvetica", fontSize=8, leading=10)
small = ParagraphStyle("s", parent=base, fontSize=7.4, leading=9.2, textColor=colors.HexColor("#344054"))
head = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white)
h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=16, leading=20)
h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=10.5, leading=14, spaceBefore=6, spaceAfter=3)
body = ParagraphStyle("p", fontName="Helvetica", fontSize=8.6, leading=11.5, textColor=colors.HexColor("#344054"))

DEMO_ORDER = [
    ("1. Happy path", "01", "Clean invoice: every check green, approved and scheduled. Open Line match + Processing."),
    ("2. OCR + no PO", "03", "Scanned image, no PO printed: OCR, PO identified from lines; $18 variance inside tolerance."),
    ("3. Split PO", "06 then 11", "Part 1 approved; part 2 looks perfect alone but over-bills the PO by 50 units / $6,000."),
    ("4. Payment fraud", "09", "Bank details changed + look-alike email domain: on hold; Reject with the call note."),
    ("   other holds", "35, 36, 37", "Each hold trigger alone: bank change from the vendor's genuine mailbox; look-alike "
                                     "domain with correct bank; inactive vendor. Show Release (needs a verification note)."),
    ("5. Disguised duplicate", "07 then 22", "Paid invoice re-sent as BP-2026-0457-R: suffix stripped, rejected, reply drafted."),
    ("6. Poor scan", "34", "Faint fax: misreads are sent to a person to check, never bounced back to the vendor."),
    ("7. The rest", "all others", "Drop the remaining files in one go; show Invoices live, Exceptions, Payments, Overview."),
]


def main():
    tp.add_all()
    doc = SimpleDocTemplate(str(OUT), pagesize=landscape(LETTER), leftMargin=0.45 * inch, rightMargin=0.45 * inch,
                            topMargin=0.45 * inch, bottomMargin=0.45 * inch, title="Invoice Desk - demo cheat sheet")
    story = [Paragraph("Invoice Desk — demo cheat sheet", h1), Spacer(1, 3),
             Paragraph(f"{len(tp.SCEN)} test invoices in <b>test-pack/invoices</b> · company <b>{tp.COMPANY['legal_name']}</b> · "
                       f"{len(tp.VENDORS)} vendors and {len(tp.POS)} POs already imported · app: <b>http://localhost:8765</b> · "
                       "reset between rehearsals: Settings → Data management → <b>Delete all invoices</b> (keeps vendors and POs).",
                       body), Spacer(1, 6), Paragraph("Suggested 5-minute order", h2)]
    t = Table([[Paragraph(a, ParagraphStyle("x", parent=base, fontName="Helvetica-Bold")), Paragraph(b, base), Paragraph(c, base)]
               for a, b, c in DEMO_ORDER], colWidths=[1.5 * inch, 0.9 * inch, 7.6 * inch])
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e4e7ec")),
                           ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    story += [t, Spacer(1, 4), Paragraph(
        "Order matters for 11 (after 06), 21 (after 09), 22 (after 07) and 23 (after 01) — uploading the whole folder at "
        "once processes files in name order, so that is always safe. Re-uploading a file that was already processed is "
        "(correctly) rejected as a duplicate.", small), Paragraph("All test invoices", h2)]

    rows = [[Paragraph(x, head) for x in ("#", "File", "Expected", "What's in the PDF", "Why the system decides this")]]
    style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#101828")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e4e7ec")),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    for i, s in enumerate(tp.SCEN, start=1):
        why = s["why"] + (f" <i>(upload after {s['depends']})</i>" if s["depends"] else "")
        rows.append([Paragraph(s["file"][:2], base), Paragraph(s["file"][3:-4].replace("_", " "), small),
                     Paragraph(f"<b>{LABEL[s['outcome']]}</b>", ParagraphStyle("o", parent=base, textColor=colors.HexColor(INK[s["outcome"]]))),
                     Paragraph(s["what"], small), Paragraph(why, small)])
        style.append(("BACKGROUND", (2, i), (2, i), colors.HexColor(TINT[s["outcome"]])))
    tbl = Table(rows, colWidths=[0.3 * inch, 2.1 * inch, 0.85 * inch, 3.15 * inch, 3.6 * inch], repeatRows=1)
    tbl.setStyle(TableStyle(style))
    story.append(tbl)
    story += [Spacer(1, 8), KeepTogether([Paragraph("Talking points", h2), Paragraph(
        "<b>AI reads, rules decide</b> — extraction can use a model, approving money never does; same input, same decision. "
        "<b>Never trust bank details on an invoice</b> — pay the verified account on file. "
        "<b>Refuse to guess</b> — two matching POs, a non-existent PO or a poor scan go to a person. "
        "<b>History-aware</b> — split POs and duplicates are checked against paid history and invoices still in review. "
        "<b>Strictest outcome wins</b> — Rejected > On hold > Needs review > Approved. "
        "<b>Everything explained</b> — every check is visible, every exception has an owner and a drafted message.", body)])]
    doc.build(story)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
