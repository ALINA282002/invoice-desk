"""Interview demo set: the 10 most telling invoices + a printable script.

    .venv\\Scripts\\python scripts\\build_test_pack.py      (first, so the source PDFs exist)
    .venv\\Scripts\\python scripts\\build_interview_set.py  ->  test-pack/interview-10/
Files are renamed 01_..10_ so uploading the folder in one go processes them in the right order
(two-digit prefixes: '10_' must not sort before '02_').
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_test_pack as tp  # noqa: E402

OUT = tp.PACK / "interview-10"

# (source file, new name, outcome, scenario, what it proves, what to show and say)
DEMO = [
    ("06_approved_split_po_part_1_of_2.pdf", "01_approved_happy_path_split_order_part_1.pdf", "APPROVED",
     "Happy path — clean invoice, PO printed",
     "The full touchless flow: read, extract, validate, vendor + bank verified, every line matched, no duplicate.",
     "Watch the 8 stages stream live. Line match: 250 of 400 pumps. Next step: scheduled for payment to the verified "
     "account on file. It also starts the PO consumption that 04 and 10 depend on."),
    ("03_approved_scanned_no_po_identified_from_lines.pdf", "02_approved_scanned_image_no_po_number.pdf", "APPROVED",
     "Scanned image, no PO number, amount close but not exact",
     "Three messy-input problems at once: no text layer (OCR on-device), implied PO, +$18 fuel surcharge.",
     "Processing: OCR 99%. Line match: candidate POs and scores — one clear winner. +$18 (+0.25%) is inside "
     "±2% / ±$250, so it is still approved, and the note says why."),
    ("08_approved_bundled_line_items.pdf", "03_approved_bundled_line_items.pdf", "APPROVED",
     "Bundled line vs itemised PO",
     "One line ('deployment package - 10 seats') matched to three PO lines (laptops, docks, imaging).",
     "Line match: 'Bundle of 3'. No single line matches, but $13,800 equals the open value of all three, so the PO is "
     "consumed line by line instead of raising a false 'charge not on PO'."),
    ("11_review_split_po_part_2_overbilled.pdf", "04_review_split_order_part_2_overbilled.pdf", "NEEDS_REVIEW",
     "Split PO — cumulative over-billing",
     "Reasoning across invoices: this invoice is perfect on its own (right PO, right price).",
     "With 01 approved, 200 more pumps = 450 of 400 ordered: $6,000 over. Routed to the PO owner by name, 'approve at "
     "most $18,000', credit-note request drafted."),
    ("15_review_no_po_and_two_pos_match.pdf", "05_review_no_po_two_pos_fit.pdf", "NEEDS_REVIEW",
     "Ambiguity — the agent refuses to guess",
     "No PO printed and the vendor has two open POs for the identical catering package.",
     "Line match: the two candidates tie. A naive matcher would pick one and pay; here the requester is asked which "
     "event this bills."),
    ("14_review_po_number_does_not_exist.pdf", "06_review_po_number_typo.pdf", "NEEDS_REVIEW",
     "Wrong PO number on the invoice (typo)",
     "The invoice quotes PO-4500-0130, which doesn't exist; its lines clearly belong to PO-4500-0103.",
     "The agent finds the right PO from the lines but still won't auto-pay against a reference that is wrong — it "
     "suggests PO-4500-0103 and asks the requester to confirm. Helpful, not reckless."),
    ("34_review_poor_quality_scan.pdf", "07_review_poor_quality_fax_scan.pdf", "NEEDS_REVIEW",
     "Poor-quality fax scan",
     "Faint, blurry scan: OCR misreads $1,450 as $450 and can't see the invoice number.",
     "Average OCR confidence still looks fine (~96%) — the agent measures how much text was read uncertainly (11%). "
     "Every inconsistency is labelled 'possibly an OCR misread' and sent to a person to check against the image, "
     "instead of wrongly bouncing the invoice back for 'missing fields'."),
    ("09_on_hold_bank_details_changed.pdf", "08_on_hold_bank_change_payment_fraud.pdf", "ON_HOLD",
     "Payment fraud (business email compromise)",
     "Matches the PO perfectly — but the remit-to bank account changed and the sender is cobaltfm-billing.example.",
     "Red internal alert; verification email drafted to the address on file. Reject (or Release) demands a note: "
     "'called vendor on the number on file; no change — fraud attempt'. Audit trail updates."),
    ("21_review_same_charge_billed_twice.pdf", "09_review_fraud_follow_up_same_charge.pdf", "NEEDS_REVIEW",
     "The fraudster's follow-up: same charge, new number",
     "A 'corrected' invoice CFM-2611-044 with the right bank details — but the same lines, amount and PO as 08.",
     "Number and file differ, bank is fine — yet it's flagged: the same charge is already pending (on hold). Checks run "
     "against invoices still in review, not just paid history."),
    ("38_rejected_renumbered_resubmission_of_part_1.pdf", "10_rejected_disguised_duplicate_of_part_1.pdf", "REJECTED",
     "Disguised duplicate",
     "01 re-sent as a 'second notice' AIC-88213-R: different file, date and number.",
     "Exact-match checks miss it; the agent strips the -R suffix, sees the same vendor and amount, and that the original "
     "is already scheduled. Rejected, reply drafted. Finish on Overview: duplicates stopped, fraud held."),
]
LABEL = {"APPROVED": "Approved", "NEEDS_REVIEW": "Needs review", "ON_HOLD": "On hold", "REJECTED": "Rejected"}
TINT = {"APPROVED": "#e7f6ec", "NEEDS_REVIEW": "#fff6dd", "ON_HOLD": "#fdebe3", "REJECTED": "#fde8e8"}
INK = {"APPROVED": "#067647", "NEEDS_REVIEW": "#93600a", "ON_HOLD": "#b93815", "REJECTED": "#b42318"}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in OUT.glob("*.pdf"):  # only files this script made
        if re.match(r"^\d\d_(approved|review|on_hold|rejected)_.+\.pdf$", f.name) or f.name == "INTERVIEW-SCRIPT.pdf":
            f.unlink()
    for src, dst, *_ in DEMO:
        shutil.copyfile(tp.INV / src, OUT / dst)

    base = ParagraphStyle("b", fontName="Helvetica", fontSize=8, leading=10, textColor=colors.HexColor("#344054"))
    bold = ParagraphStyle("bb", parent=base, fontName="Helvetica-Bold", textColor=colors.HexColor("#101828"))
    head = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white)
    doc = SimpleDocTemplate(str(OUT / "INTERVIEW-SCRIPT.pdf"), pagesize=landscape(LETTER), leftMargin=0.4 * inch,
                            rightMargin=0.4 * inch, topMargin=0.35 * inch, bottomMargin=0.3 * inch,
                            title="Invoice Desk - interview demo")
    story = [Paragraph("Invoice Desk — 10-invoice interview demo",
                       ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=14, leading=18)),
             Spacer(1, 2),
             Paragraph("Before you start: app at http://localhost:8765 with company, vendors and POs configured · "
                       "Settings → Data management → <b>Delete all invoices</b> · upload in number order, or drop all 10 at "
                       "once (they process in name order). <b>04 and 10 need 01 first; 09 needs 08 first.</b>", base),
             Spacer(1, 5)]
    rows = [[Paragraph(x, head) for x in ("#", "Scenario", "Result", "What it proves", "What to show and say")]]
    style = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#101828")), ("VALIGN", (0, 0), (-1, -1), "TOP"),
             ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#e4e7ec")),
             ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    for i, (_src, dst, out, title, proves, say) in enumerate(DEMO, start=1):
        rows.append([Paragraph(f"{i:02d}", bold), Paragraph(f"<b>{title}</b>", base),
                     Paragraph(f"<b>{LABEL[out]}</b>", ParagraphStyle("o", parent=base, textColor=colors.HexColor(INK[out]))),
                     Paragraph(proves, base), Paragraph(say, base)])
        style.append(("BACKGROUND", (2, i), (2, i), colors.HexColor(TINT[out])))
    t = Table(rows, colWidths=[0.3 * inch, 1.9 * inch, 0.8 * inch, 2.9 * inch, 4.3 * inch])
    t.setStyle(TableStyle(style))
    story += [t, Spacer(1, 6), Paragraph(
        "<b>Opening line:</b> \"An AP clerk opens each PDF, finds the PO, checks the numbers, checks it isn't paid already, "
        "and decides. This agent does that loop — and every check is visible.\"  <b>Design choice:</b> AI reads, rules "
        "decide — extraction can use a model, approving money never does, so the same invoice always gets the same "
        "decision and finance can change thresholds in Settings without code.  <b>Strictest outcome wins:</b> Rejected > "
        "On hold > Needs review > Approved.  <b>If asked 'what else?':</b> bill-to must be our company, wrong currency, "
        "tax-rate and date checks, approval limit, blocked/inactive/unknown vendors — 38 test invoices in "
        "test-pack/invoices.", base)]
    doc.build(story)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
