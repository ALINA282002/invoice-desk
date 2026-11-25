# 5-minute demo script

**Before recording:** start the app (`.\start.ps1`). If you have run it before: *Settings → Data management →
Delete everything*, so the setup screen appears. Keep `test-pack\` open in Explorer.

---

**0:00 – 0:40 · Setup (it starts empty)**
"This is an AP tool that starts with no data — like a real install. It needs three things: who we are, who we
buy from, and what we ordered." Add company *Halcyon Manufacturing Inc.*, import `vendors.csv`, import
`purchase_orders.csv`. "Note the vendor master holds the *verified* bank account and email domain for each vendor."

**0:40 – 1:40 · Happy path — drag `01_approved_clean_exact_match.pdf` onto the window**
The invoice page opens with the PDF on the left and the live processing log on the right. Narrate as stages tick:
"It reads the text layer, extracts the fields and traces each one back to the document, checks it's billed to us,
the maths adds up, the vendor is approved and the remit-to bank matches what's on file, all five lines match
PO-4500-0101 at the agreed price, and it's not a duplicate." → **Approved**, scheduled for Dec 18 to the account on
file. Open *Line match*.

**1:40 – 2:20 · Edge: scanned invoice with no PO — upload `03_…`**
"No text at all — it's a photocopy — so it runs OCR on-device. No PO number, so it scores the vendor's open POs on
line items and amount; one clearly wins. The LTL rate is $18 over the PO — 0.25%, inside tolerance — so it's still
touchless, and the note says so."

**2:20 – 3:00 · Edge: split PO — upload `06_…` then `11_…`**
"Part 1 bills 250 of 400 pumps and is approved. Part 2 is perfect on its own — right price, right PO — but 200 more
is 450 of 400. It tracks consumption across invoices: $6,000 over, routed to the PO owner, credit-note email
drafted."

**3:00 – 3:50 · Edge: bank details changed — upload `09_…`**
"Everything matches — except the vendor 'changed banks' and the email is cobaltfm-**billing**.example instead of
cobaltfm.example. Most common invoice-fraud pattern. On hold; it says to call the number *on file*." Click
**Reject**, type the reason ("called vendor; no change — fraud attempt") → audit trail.

**3:50 – 4:20 · Edge: disguised duplicate — upload `07_…` then `22_…`**
"A 'second notice' for BP-2026-0457-R — different file, date and number. It strips the re-issue suffix, sees the
same vendor and amount, and that the original is already scheduled. Rejected; reply drafted."

**4:20 – 5:00 · Batch + overview**
Drop the rest of the folder in one go; show the Invoices list processing live, then Overview (touchless rate,
duplicates stopped, fraud held, exception reasons), Exceptions, and Payments. "AI only reads; approving money is
done by rules finance can change in Settings — and every decision is explained."
