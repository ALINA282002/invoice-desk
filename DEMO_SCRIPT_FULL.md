# Invoice Desk — full demo video script (all 10 invoices, ~9½ minutes)

Covers every file in `Downloads\Invoice-Desk-Demo\interview-10\`, in order 01 → 10.
(The brief caps the video at 5 minutes — `VIDEO-SCRIPT-5-MIN.md` is the version that fits; this one is complete.)

**Before you hit record**
- Record on your laptop (`start.ps1` → http://localhost:8765) — scans take ~5 s there vs ~90 s on the free cloud server.
- Settings → Data management → **Delete all invoices** (company, vendors and POs stay).
- Open the `interview-10` folder next to the browser. Drag **one file at a time**, in number order.
- **Important:** on 08, do *not* click Reject until after 09 — 09 is only caught while 08 is still on hold.
- **[Brackets]** = what you do. Everything else = what you say.

---

### 0:00 – 0:20 · Hook — **[Overview page, empty]**
"In the next few minutes I'm going to give this agent ten invoices, each one designed to break a simpler system. It
will approve the clean ones without a human touching them, catch a vendor over-billing us, refuse to guess when the
data is ambiguous, stop a fraud attempt — twice — and refuse to pay the same invoice twice. And at every step, it
shows you why. I'm Alina; this is Invoice Desk, my answer to PS-1."

### 0:20 – 0:55 · Quick tour — **[Click down the left sidebar, ~3 seconds per page]**
"A quick tour first. **[Overview]** Overview is the AP manager's dashboard. **[Invoices]** Invoices lists every
invoice and its status. **[Exceptions]** Exceptions is the review queue — what needs a person, and who owns it.
**[Payments]** Payments is the payment run. **[Vendors]** The vendor master holds each vendor's *verified* bank
account and email domain, **[Purchase orders]** and the PO register holds what we ordered, at agreed prices — both
imported from CSV, like an ERP export. **[Audit log]** Every decision is logged, **[Settings]** and Settings holds the
approval policy, which finance can tune without touching code."

### 0:55 – 1:15 · The problem and the one rule — **[Back to Overview]**
"An AP team opens hundreds of vendor PDFs a month, hunts for the PO, checks the maths, checks it isn't already paid,
and decides. It's relentless work — exactly where expensive mistakes slip through. So I built it around one rule:
**AI reads, rules decide.** Reading a messy PDF is where automation helps; approving money is not where you want
creativity. Every decision comes from explicit, auditable rules."

### 1:15 – 2:05 · 01 — Happy path — **[Drag 01 → Processing tab]**
"Here's an invoice from Apex, a parts supplier. Watch the right side: eight stages, live. It fingerprints the file, so
a re-sent copy is recognised later. It reads it and extracts the vendor, invoice number, dates, PO, every line, tax
and bank details — and checks each key value really appears on the document, so nothing is invented. It validates:
addressed to our company, the maths adds up. Vendor: approved, and the bank account matches the one we verified.
Purchase order: every line at the agreed price. Duplicates: none."
**[Summary tab]** "Approved — and the money goes to the verified account on file, never to whatever account an
invoice asks for." **[Line match tab]** "Two hundred and fifty of four hundred pumps billed. Hold that thought — it
comes back twice."

### 2:05 – 2:45 · 02 — Scanned, no PO, price slightly off — **[Drag 02]**
"Real invoices are messy. This one is a photocopy — no text layer, no PO number, and a price that's slightly off. It
reads the image on the laptop, then plays detective: it scores every open PO from this vendor on line items and
amount. **[Line match → candidates]** One clear winner. The freight rate is eighteen dollars above the PO — a quarter
of a percent. Our tolerance has to hold on both percent and dollars — two percent and two hundred fifty — and this is
inside it, so it's approved, and the note explains why."

### 2:45 – 3:20 · 03 — Bundled line items — **[Drag 03]**
"Vendors don't always bill line by line. This IT supplier sends one line: 'deployment package, ten seats'. Our PO has
three separate lines — laptops, docking stations and imaging. A simple matcher says 'charge not on the PO' and stops.
**[Line match → 'Bundle of 3']** The agent sees the package equals the open value of all three lines — thirteen
thousand eight hundred — so it matches it as a bundle and consumes each PO line, keeping the balance correct.
Approved."

### 3:20 – 4:00 · 04 — Split order, over-billed — **[Drag 04]**
"Back to Apex. This is part two of the pump order — and on its own it's flawless: right PO, right price. A system
that looks at one invoice at a time would pay it. But the agent remembers invoice one: 250 plus 200 is 450, against
an order of 400. Six thousand dollars over. It doesn't reject a real shipment — it routes it to the PO owner, Marcus,
by name, says at most eighteen thousand can be approved, and drafts a credit-note request to the vendor."

### 4:00 – 4:35 · 05 — No PO, and two POs fit — **[Drag 05]**
"Now ambiguity. A caterer bills us with no PO number — and we have two open POs for exactly the same package: a
holiday party and a customer workshop. **[Line match → two candidates tie]** They score the same. A system chasing
automation rates would pick one and pay. This one refuses to guess: it asks the requester which event this bills.
Paying against the wrong budget is worse than one extra question."

### 4:35 – 5:10 · 06 — Wrong PO number on the invoice — **[Drag 06]**
"This invoice quotes PO-4500-0130 — which doesn't exist; it's a typo. The agent still works out from the lines that it
belongs to PO-4500-0103 and suggests it. But it won't auto-pay against a reference that's wrong on the document — a
person confirms. Helpful, not reckless."

### 5:10 – 5:55 · 07 — Poor-quality fax — **[Drag 07]**
"This is my favourite judgment call. A faint, blurry fax. The OCR misreads one thousand four hundred fifty as four
hundred fifty, and can't see the invoice number at all — yet its average confidence still says over ninety percent.
So the agent doesn't trust the average; it measures how much of the page was read uncertainly, and flags the scan.
**[Summary → exceptions]** And look how it labels everything: 'possibly an OCR misread'. My first version rejected
this invoice for a missing invoice number — which would have bounced a valid invoice back to the vendor because of
*our* scanner. Now it goes to a person, with the image right there to check."

### 5:55 – 6:40 · 08 — Payment fraud — **[Drag 08 — don't act on it yet]**
"This is the invoice that costs companies real money. Perfect PO match, right amount — but it says 'our banking
details have changed', and look at the sender: cobaltfm-**billing**.example. The real vendor is cobaltfm.example.
**[Point at the red alert and Next step]** Payment on hold, an internal alert, a verification email drafted to the
address we have on file, and a clear instruction: call the vendor on the number we already have — never the one on
the invoice. I'll leave it on hold for a moment, because a fraudster rarely stops at one attempt."

### 6:40 – 7:20 · 09 — The fraudster's follow-up — **[Drag 09]**
"A day later: a 'corrected' invoice from the same vendor. New invoice number, and this time the bank details are the
right ones — everything checks out. Except the agent notices this exact charge — same lines, same amount, same PO —
is already sitting on hold. **[Summary]** Flagged as a possible duplicate charge. Duplicate checks cover invoices still
in review, not just ones already paid."
**[Open 08 from the Invoices list → Reject → your name + "Called vendor on the number on file — no bank change. Fraud
attempt." → Reject]**
"Now I resolve the original: I've called the vendor on the number on file — they never changed banks. Rejected, and
the reason is in the audit trail, permanently. A human makes the final call."

### 7:20 – 7:55 · 10 — The disguised duplicate — **[Drag 10]**
"Last one. Apex sends a 'second notice' for invoice one — new date, new file, and the number now ends in dash-R. An
exact-match check sees a brand-new invoice and pays it twice. The agent strips the suffix, matches the vendor and the
amount, sees the original is already scheduled — rejected, with a polite reply drafted."

### 7:55 – 8:35 · What just happened — **[Overview → Exceptions → Payments → Audit log]**
"Ten invoices. **[Overview]** Three paid with no human touch. Five routed to the right person, each with a reason —
the over-billing, the ambiguous PO, the typo, the bad scan and the suspicious follow-up. Thirty-one thousand eight
hundred dollars of double payment stopped, and a fraud attempt rejected. **[Exceptions]** Every open item has an
owner. **[Payments]** The payment run — always to verified accounts. **[Audit log]** And every decision, by the
system or by me, is recorded with a reason."

### 8:35 – 9:05 · How it's built, and close
"Under the hood: Python and FastAPI, a plain-JavaScript interface, OCR running on the machine, and an extraction step
that can use Claude when an API key is set — while the decisions always stay with the rules. I tested it on 38
invoices covering every outcome; it's on my GitHub and live on Render. I built it for the person in AP on a Friday
afternoon — so the expensive mistakes simply don't happen. Thank you."

---

**Quick reference — expected results**

| File | Result | One-line story |
|---|---|---|
| 01 | Approved | Clean invoice, every check green; 250 of 400 pumps |
| 02 | Approved | Scan, no PO, +$18 — PO identified, inside tolerance |
| 03 | Approved | One bundled line = three PO lines |
| 04 | Needs review | Part 2 over-bills the PO by $6,000 (needs 01) |
| 05 | Needs review | Two POs fit — refuses to guess |
| 06 | Needs review | PO number typo — suggests the right PO, won't auto-pay |
| 07 | Needs review | Poor fax — misreads go to a person, not back to the vendor |
| 08 | On hold → you Reject | Bank change + look-alike domain (reject *after* 09) |
| 09 | Needs review | Same charge as 08 re-sent with correct bank (needs 08 on hold) |
| 10 | Rejected | Re-numbered duplicate of 01 (needs 01) |
