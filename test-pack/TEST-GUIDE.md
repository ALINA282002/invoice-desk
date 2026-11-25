# Invoice Desk — test pack

38 invoice PDFs covering every decision the system can make
(8 approved, 17 needs review, 5 on hold, 8 rejected),
plus the master data they are checked against.

## 1. One-time setup (≈1 minute)

1. Start the app and open http://localhost:8765. A setup screen appears on first launch.
2. **Company profile** — legal name: `Halcyon Manufacturing Inc.` · AP email: `ap@halcyon-mfg.example`
3. **Vendor master** — import `master-data/vendors.csv` (10 vendors; one is blocked, one is still in onboarding, one is inactive)
4. **PO register** — import `master-data/purchase_orders.csv` (20 POs, one row per PO line)

## 2. Upload invoices

Select all files in `invoices/` and drop them on **Upload invoices** — a batch is processed one by one in file-name
order, which satisfies the dependencies below. You can also upload them one at a time, or copy them into the
`inbox/` folder (the watched AP mailbox).

Some cases depend on an earlier invoice (that is the point — e.g. a split PO only over-bills after the first part
is approved). Files marked *(upload after NN)* must come after that file.

## 3. Expected results

| # | File | Expected | What's in the PDF | Why the system decides this |
|---|---|---|---|---|
| 01 | `01_approved_clean_exact_match.pdf` | **Approved** | Clean digital invoice, PO printed, 5 itemised lines, separate sales tax. | Every check passes, so it is approved and scheduled with no human touch. |
| 02 | `02_approved_scanned_with_po.pdf` | **Approved** | Photocopied/scanned invoice (no text layer) with the PO printed. | OCR reads the image; lines match PO-4500-0108 exactly. |
| 03 | `03_approved_scanned_no_po_identified_from_lines.pdf` | **Approved** | Scanned invoice with NO PO number; LTL rate is $4.50 higher than the PO (fuel surcharge). | PO-4500-0104 is identified from the vendor's open POs by line items + amount (one clear winner). +$18.00 (+0.25%) is inside the ±2% / ±$250 tolerance, so it is still approved. |
| 04 | `04_approved_multipage_invoice.pdf` | **Approved** | Two-page invoice with 26 line items; totals are on page 2. | All pages are read, all 26 lines match PO-4500-0110. |
| 05 | `05_approved_alternate_layout_and_date_format.pdf` | **Approved** | Different house style (serif, centred), day.month.year dates, PO given as 'Order ref'. | Layout and date format don't matter: fields are found, PO-4500-0111 matches exactly. |
| 06 | `06_approved_split_po_part_1_of_2.pdf` | **Approved** | First partial shipment: 250 of the 400 pumps on a blanket PO. | Approved; the PO now shows 250 units / $30,000 consumed. Needed before file 11. |
| 07 | `07_approved_monthly_service_october.pdf` | **Approved** | Monthly managed-service invoice for October. | Approved and scheduled. Needed before file 22 (its re-numbered duplicate). |
| 08 | `08_approved_bundled_line_items.pdf` | **Approved** | One bundled line ('deployment package - 10 seats') for a PO that lists laptops, docks and imaging separately. | No single PO line matches, but the bundle's $13,800 equals the open value of all three PO lines, so it is matched as a bundle and the PO is consumed line by line. |
| 09 | `09_on_hold_bank_details_changed.pdf` | **On hold** | Everything matches the PO, but the remit-to bank account is new and the sender email is a look-alike domain. | Classic payment-fraud (business email compromise) pattern: payment blocked until verified by phone using the number on file. |
| 10 | `10_on_hold_vendor_not_yet_approved.pdf` | **On hold** | New vendor whose onboarding is not complete (status 'pending_onboarding'); invoice itself is correct. | Can't pay a vendor before tax and bank verification are done: held until Procurement approves the vendor. |
| 11 | `11_review_split_po_part_2_overbilled.pdf` | **Needs review** | Second partial shipment: 200 more pumps at the correct price. | On its own it looks perfect — but with file 06 that is 450 of 400 units ordered: $6,000 over the PO. Routed to the PO owner; credit-note request drafted. *(upload after 06)* |
| 12 | `12_review_unit_prices_above_tolerance.pdf` | **Needs review** | Coffee and towels billed 10% and 9% above the PO price. | $112 over is below the $250 cap, but +8.7% is above the 2% cap — both must hold. Buyer must sign off. |
| 13 | `13_review_charge_not_on_po.pdf` | **Needs review** | Docking stations and monitors match the PO, plus an 'expedited shipping' line nobody ordered. | Charges not on the PO need the requester's approval (or the vendor removes them). |
| 14 | `14_review_po_number_does_not_exist.pdf` | **Needs review** | PO printed as PO-4500-0130 — a typo; no such PO exists. | Never auto-approved on a wrong PO. The lines point to PO-4500-0103, which is suggested to the reviewer. |
| 15 | `15_review_no_po_and_two_pos_match.pdf` | **Needs review** | No PO on the invoice; the vendor has two open POs for exactly the same catering package. | The agent refuses to guess: several open POs fit almost equally, so the requester must say which event this bills. |
| 16 | `16_review_totals_do_not_add_up.pdf` | **Needs review** | Subtotal $5,175.00 + tax $0.00, but the total says $5,715.00 (digits transposed). | The arithmetic check catches it; a request for a corrected invoice is drafted. |
| 17 | `17_review_above_approval_limit.pdf` | **Needs review** | $64,500 service invoice that matches its PO exactly. | Above the $50,000 touchless-approval limit, so a person must sign off even though nothing is wrong. |
| 18 | `18_review_future_dated.pdf` | **Needs review** | Invoice dated November 15, 2027 — a year in the future (typo). | Future dates break payment terms and period cut-off, so it goes to review. |
| 19 | `19_review_tax_rate_too_high.pdf` | **Needs review** | 18% tax charged on facility services. | Effective tax rate is above the 12% plausibility ceiling — the vendor likely applied the wrong rate. |
| 20 | `20_review_billed_in_wrong_currency.pdf` | **Needs review** | Invoice billed in EUR against a PO raised in USD. | Paying in a different currency creates FX exposure nobody approved; vendor asked to reissue in USD. |
| 21 | `21_review_same_charge_billed_twice.pdf` | **Needs review** | Correct bank details this time, new invoice number — but the same November services and amount as file 09. | Same vendor, PO, lines and amount under a different number: flagged as a possible double charge. *(upload after 09)* |
| 22 | `22_rejected_renumbered_duplicate_of_paid_invoice.pdf` | **Rejected** | October invoice re-sent as a 'second notice' with a -R suffix, new date and a different file. | Exact-match checks miss it; the agent strips the suffix and sees same vendor + same amount as file 07. *(upload after 07)* |
| 23 | `23_rejected_same_file_sent_again.pdf` | **Rejected** | Byte-for-byte copy of file 01 (vendor emailed it twice). | Same file fingerprint as an invoice already received. *(upload after 01)* |
| 24 | `24_rejected_missing_invoice_number_and_date.pdf` | **Rejected** | Valid vendor and PO, but no invoice number and no invoice date anywhere. | Can't be booked or duplicate-checked: returned to the vendor with a drafted request. |
| 25 | `25_rejected_blocked_vendor.pdf` | **Rejected** | Invoice from a vendor that is blocked in the vendor master. | Blocked vendors are never paid, whatever the invoice says. |
| 26 | `26_rejected_unknown_vendor.pdf` | **Rejected** | Invoice from a company that is not in the vendor master at all. | Unknown vendors can't be paid; forwarded to Procurement for onboarding. |
| 27 | `27_rejected_addressed_to_another_company.pdf` | **Rejected** | Genuine Northwind invoice — but billed to a different customer (Brookfield Plastics), sent to us by mistake. | The bill-to party is not our legal entity, so it is returned to the vendor. |
| 28 | `28_rejected_blank_unreadable_scan.pdf` | **Rejected** | A scanned page that is blank (the scanner fed an empty sheet). | Nothing readable: returned with a request for a legible copy. |
| 29 | `29_review_invoice_older_than_180_days.pdf` | **Needs review** | Freight invoice dated March 2, 2026 — almost nine months old, surfacing only now. | Older than the 180-day limit: it may already have been paid another way or be outside the accrual period. |
| 30 | `30_review_po_already_closed.pdf` | **Needs review** | Late invoice against last quarter's PO, which has since been closed. | A closed PO has no budget left to spend against; the requester must reopen it or raise a new PO. |
| 31 | `31_review_po_belongs_to_another_vendor.pdf` | **Needs review** | Meridian quotes PO-4500-0101 — a real PO, but it was issued to Northwind for office supplies. | A vendor can't bill against another vendor's PO; the lines don't exist on it either. |
| 32 | `32_review_lines_do_not_add_up_to_subtotal.pdf` | **Needs review** | Two lines totalling $1,830.00, but the subtotal (and total) says $1,930.00. | The lines and the subtotal disagree by $100 — the vendor is overcharging or mis-typed; ask for a corrected invoice. |
| 33 | `33_review_tax_id_does_not_match.pdf` | **Needs review** | Correct vendor, PO and prices — but the tax ID printed on the invoice differs from the one on file. | A different tax ID can mean a different legal entity (or a tampered invoice); confirm before paying. |
| 34 | `34_review_poor_quality_scan.pdf` | **Needs review** | A faint, blurry, speckled fax-quality scan of an otherwise valid invoice. | Over 5% of the text is read with low confidence (numbers may be misread), so a person must confirm the values against the image before it is paid. |
| 35 | `35_on_hold_bank_change_from_genuine_email.pdf` | **On hold** | Real Greenleaf invoice from their genuine email domain, matching the PO exactly — but it asks to pay a new account. | A real-looking sender is not proof: vendors' own mailboxes get hacked. Any bank change is held until verified by phone using the number on file. |
| 36 | `36_on_hold_lookalike_sender_domain.pdf` | **On hold** | Apex invoice with the correct bank account and PO, sent from billing@apex-industria1.example (a '1' instead of an 'l'). | A look-alike domain is a phishing set-up even when nothing else is wrong yet: held, and the vendor is contacted through the details on file. |
| 37 | `37_on_hold_vendor_marked_inactive.pdf` | **On hold** | Correct invoice from a vendor that is marked 'inactive' in the vendor master (dormant for over a year). | Dormant vendor records are a classic fraud target; payment waits until Procurement reactivates and re-verifies the vendor. |
| 38 | `38_rejected_renumbered_resubmission_of_part_1.pdf` | **Rejected** | Apex's billing system re-sends part 1 as a 'second notice' numbered AIC-88213-R, with a new date and a new file. | Exact-match checks miss it; the agent strips the -R suffix, sees same vendor + same amount as file 06, which is already scheduled — paying it would pay twice. *(upload after 06)* |

## Notes

- Files 02, 03, 28 and 34 are image-only scans (no text layer) — they exercise the OCR path; 34 is deliberately poor.
- File 04 has two pages.
- Files 29–34 each exercise one more rule (stale invoice, closed PO, another vendor's PO, lines ≠ subtotal,
  tax-ID mismatch, poor scan).
- Re-running: **Settings → Data management → Delete all invoices** clears invoices, payments and the audit log but
  keeps your company profile, vendors and POs.
- Today's date matters for file 18 (future-dated) and file 29 (180-day age rule); most invoices are dated Oct–Nov 2026.
