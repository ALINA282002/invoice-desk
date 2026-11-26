# Invoice Desk — 5-minute demo video script

**The brief:** show the happy path running live, then at least one edge case; narrate what the process does at each
step, the decisions it makes, and anything interesting about how it was built. **5 minutes max**, no slides, no
editing.

**Before you hit record**
- Record on your laptop (`start.ps1` → http://localhost:8765): scans take ~5 s there vs ~90 s on the free cloud server.
- Settings → Data management → **Delete all invoices** (company, vendors and POs stay).
- Open `Downloads\Invoice-Desk-Demo\interview-10\` next to the browser. Files used: **01, 02, 04, 08, 10** — in that order.
- **[Brackets]** = what you do. Everything else = what you say. Calm but energetic: ~150 words a minute.
- Do one dry run first; then reset and record in a single take.

---

### 0:00 – 0:20 · Hook — **[Overview page, empty]**
"In the next five minutes, this agent is going to approve invoices without a human touching them, catch a vendor
over-billing us by six thousand dollars, stop a fraud attempt that looks completely legitimate, and refuse to pay the
same invoice twice — and show you why at every step. I'm Alina; this is Invoice Desk, my answer to PS-1."

### 0:20 – 0:55 · Quick tour — **[Click down the left sidebar, one page each, ~3 seconds per page]**
"A quick tour first. **[Overview]** Overview is the AP manager's dashboard. **[Invoices]** Invoices lists every
invoice and its status. **[Exceptions]** Exceptions is the review queue — what needs a person, and who owns it.
**[Payments]** Payments is the payment run. **[Vendors]** The vendor master holds each vendor's *verified* bank
account and email domain, **[Purchase orders]** and the PO register holds what we ordered, at agreed prices — both
imported from CSV, like an ERP export. **[Audit log]** Every decision is logged, **[Settings]** and Settings holds the
approval policy, which finance can tune without touching code."

### 0:55 – 1:15 · The problem and the one rule — **[Back to Overview]**
"An AP team opens hundreds of vendor PDFs a month, hunts for the PO, checks the maths, checks it isn't already paid,
and decides. It's relentless work — exactly where expensive mistakes slip through. So I built it around one rule:
**AI reads, rules decide.** Approving money is not where you want creativity."

### 1:15 – 2:00 · Happy path — **[Drag 01 onto the window → Processing tab]**
"Here's an invoice from Apex, a parts supplier. Watch the right side: eight stages, live. It fingerprints the file,
reads it, and extracts the vendor, invoice number, dates, PO, every line, tax and bank details — and checks each key
value really appears on the document, so nothing is invented. It validates: addressed to our company, the maths adds
up. Vendor: approved, and the bank account matches the one we verified. Purchase order: every line at the agreed
price. Duplicates: none."
**[Summary tab]** "Approved — and the money goes to the verified account on file, never to whatever account an
invoice asks for." **[Line match tab]** "Two hundred and fifty of four hundred pumps billed. Hold that thought."

### 2:00 – 2:35 · Edge case 1: the messy reality — **[Drag 02]**
"Real invoices are messy. This one is a photocopy — no text, no PO number, and a price that's slightly off. It reads
the image on the laptop, then scores every open PO from this vendor on line items and amount.
**[Line match → candidates]** One clear winner. The rate is eighteen dollars above the PO — a quarter of a percent,
inside tolerance — so it's approved, and it writes down why."

### 2:35 – 3:10 · Edge case 2: the split order — **[Drag 04]**
"Remember those 250 pumps? This is part two — and on its own it's flawless. Right PO, right price. A system that
looks at one invoice at a time would pay it. But the agent remembers: 250 plus 200 is 450, against an order of 400.
Six thousand over. It sends it to the PO owner by name, says at most eighteen thousand is payable, and drafts the
credit-note request."

### 3:10 – 3:55 · Edge case 3: the fraud — **[Drag 08]**
"This is the invoice that costs companies real money. Perfect PO match, right amount — but 'our banking details have
changed', and look at the sender: cobaltfm-**billing**.example. The real vendor is cobaltfm.example. On hold, red
alert, and the instruction: call the vendor on the number we already have — never the one on the invoice. A human
makes the final call."
**[Reject → your name + "Called vendor on the number on file — no bank change. Fraud attempt." → Reject]**
"Rejected — and the reason is in the audit trail, permanently."

### 3:55 – 4:25 · Edge case 4: the disguised duplicate — **[Drag 10]**
"Last one: Apex sends a 'second notice' for that first invoice — new date, new file, and the number now ends in
dash-R. An exact-match check pays it twice. The agent strips the suffix, matches vendor and amount, sees the original
is already scheduled — rejected, with a polite reply drafted."

### 4:25 – 4:42 · What just happened — **[Overview]**
"Five invoices: two paid with no human touch, an over-billing caught, thirty-one thousand eight hundred dollars of
double payment stopped, a fraud attempt held — and every decision explained."

### 4:42 – 4:55 · Close
"Python, FastAPI, on-device OCR and deterministic rules, tested on 38 invoices — on my GitHub and live on Render.
Built for the person in AP on a Friday afternoon, so the expensive mistakes don't happen. Thank you."

---

**Timing safety valve:** if you're running long, skip the Line-match click in 02 and click only four pages in the
tour (Overview, Invoices, Vendors, Settings). If you're short, add 05 (two POs fit — it refuses to guess) before the
fraud case.
