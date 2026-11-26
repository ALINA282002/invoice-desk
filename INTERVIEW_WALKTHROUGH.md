# Invoice Desk — 10-minute live interview walkthrough

For the follow-up interview ("you'll run your process live — a happy path and the edge cases you've prepared —
and walk us through your decisions"). No hard time limit, so this goes deeper than the video and covers all 10
interview invoices. Pause after each case — interviewers usually ask questions there.

**Setup:** app open (local http://localhost:8765 is fastest), Settings → Delete all invoices, the
`interview-10` folder open. Upload in number order (04 and 10 need 01; 09 needs 08).

---

## 1. Opening (45 s)
"Thanks for having me. Before I run anything, the one-sentence version: Invoice Desk takes a vendor invoice as a
PDF — clean or scanned — and produces a decision a finance team can trust: approve, send to a person, hold, or
reject, with every check it made visible. I'll run ten invoices that each test something different, and I'd love
you to stop me anywhere.

Three design choices shaped everything, and you'll see each of them live:
**one — AI reads, rules decide**; **two — it never trusts what an invoice says about where to send money**;
**three — when it isn't sure, it refuses to guess and hands it to the right person.**"

## 2. Tour of the tool (75 s) — **[Click down the left sidebar]**
"A quick tour before we process anything.
**[Overview]** This is the AP manager's view — touchless rate, open exceptions, what's scheduled for payment,
duplicates stopped and fraud held. It's empty because we haven't processed anything yet — every number here comes from
real invoices, nothing is seeded.
**[Invoices]** Every invoice received, with status tabs and search; it updates live while a batch is processing.
**[Exceptions]** The review queue — invoices the system wouldn't pay on its own, oldest first, each with an owner.
**[Payments]** The payment run — pay date, amount, and the *verified* account it goes to; exportable as a file.
**[Vendors]** The vendor master — ten vendors, including one blocked, one still onboarding and one inactive, each with
the bank account and email domain we've verified.
**[Purchase orders]** Twenty POs with line items and agreed prices — and a bar showing how much of each has already
been invoiced.
**[Audit log]** Who did what, when and why.
**[Settings]** Company profile, the approval policy — tolerance, approval limit, PO-matching confidence — and data
import. Vendors and POs come in as CSV, the way they come out of an ERP; there's no fake history: the app starts
empty, like a real install."
**[Upload invoices button, top right]** "Invoices come in by upload — drag-and-drop anywhere — or from a watched
mailbox folder."

## 3. Happy path — 01 (75 s)
"An Apex invoice for hydraulic pumps. **[Processing tab]** Eight stages, streaming live:
receive and fingerprint; read — text layer or OCR; extract; validate; verify vendor; match the PO; duplicate check;
decide. The interesting bit in extraction is grounding: every key value — invoice number, PO, totals, date — must be
found verbatim in the document text. If an extractor can't show where a value came from, it doesn't get to approve
money.
**[Summary]** Approved, scheduled on the due date to the account on file. **[Line match]** 250 of 400 pumps — this
matters in two minutes."

**If asked "why not let the AI decide?"** — "Because the same invoice should always get the same decision, a finance
controller should be able to read the rule that decided it, and thresholds should change without retraining
anything. The model is great at reading; it shouldn't be the one holding the chequebook."

## 4. Messy input — 02 (60 s)
"A photocopy, no text layer, no PO number, and an eighteen-dollar difference. OCR runs on the laptop — no data
leaves the building. Then PO identification: it scores every open PO for this vendor — 60 percent line-item
similarity, 40 percent amount closeness, against the open value of the lines it actually matches — and requires a
clear winner, ten points ahead. **[Line match → candidates]** One winner. Eighteen dollars is a quarter percent; the
tolerance must hold on *both* percent and dollars — two percent and two hundred fifty — so small percentages on big
invoices can't sneak through. Approved, with the reasoning written down."

## 5. Bundled lines — 03 (45 s)
"The brief mentions line items that are itemised or bundled. Here the vendor bills one line — 'deployment package,
10 seats' — against a PO with laptops, docks and imaging as three lines. No single line matches, so a naive matcher
flags 'charge not on PO'. **[Line match → Bundle of 3]** The agent sees the bundle equals the open value of all three
lines and consumes them line by line, so the PO balance stays correct."

## 6. Split PO over-billed — 04 (60 s)
"Part two of the Apex order. On its own: perfect. But duplicate and balance checks look at history — paid invoices
*and* ones still in review. 250 plus 200 is 450 against 400: six thousand over. It routes to the PO owner, Marcus, by
name — not a generic queue — says at most eighteen thousand can be approved, and drafts the credit-note email."

**If asked "what if part 2 arrives first?"** — "Then part 2 is approved — correctly, because 200 of 400 is fine — and
part 1 is the one that over-bills. The system is order-independent in outcome: whichever invoice crosses the line
gets flagged. That's why processing is strictly one at a time, first in first out."

## 7. Refusing to guess — 05 (45 s)
"No PO printed, and Greenleaf has two open POs for the identical catering package — a holiday party and a customer
workshop. **[Line match]** They tie. A system optimised for touchless rate would pick one and pay. This one asks the
requester which event it bills. A slightly lower automation rate is a better trade than paying against the wrong
budget."

## 8. PO typo — 06 (45 s)
"The invoice quotes PO-4500-0130, which doesn't exist. The agent still works out from the lines that it belongs to
PO-4500-0103 and suggests it — but it won't auto-pay against a reference that's wrong on the document. Helpful, not
reckless."

## 9. Poor fax — 07 (60 s)
"This is my favourite judgment call. A faint fax: the OCR reads one thousand four hundred fifty as four hundred
fifty and can't see the invoice number. Average OCR confidence still says over 90 percent — which is why I don't
trust the average. The agent measures how much of the text was read uncertainly — more than one line in ten here —
and flags the scan.
Crucially, it labels every inconsistency 'possibly an OCR misread' and sends it to a person to check against the
image. My first version rejected this invoice for 'missing invoice number' — which would have bounced a valid
invoice back to the vendor because of *our* scanner. That's the kind of mistake I wanted to design out."

## 10. Payment fraud — 08 (75 s)
"Perfect PO match, right amount — but a bank change and a look-alike sender domain. On hold, an internal alert, and
a drafted verification email to the address *on file*. **[Open the Release dialog, then Cancel]** Releasing payment
requires a verification note — 'called the vendor on the number in the vendor master'. I'll leave it on hold for a
moment, because fraudsters rarely stop at one attempt." *(Don't reject 08 yet — 09 is only caught while 08 is on hold.)*

## 11. The fraudster's follow-up — 09 (45 s)
"What does a smart fraudster do next? Sends a 'corrected' invoice with the *right* bank details and a new number.
Everything checks out — except this exact charge, same lines, same amount, same PO, is already sitting on hold. It's
flagged as a possible duplicate charge. Duplicate checks include invoices still in review, not just paid ones."
**[Open 08 → Reject → note: "Called vendor on the number on file — no bank change. Fraud attempt."]** "Now I resolve
the original as fraud. Every action is in the audit log with who, when and why."

## 12. Disguised duplicate — 10 (45 s)
"Apex re-sends part one as a 'second notice', AIC-88213-R — new date, new file, new number. The agent strips common
re-issue suffixes, matches vendor and amount, sees the original is already scheduled, and rejects it — with a polite
reply, not a silent drop."

## 13. The operator's view (45 s) — **[Overview → Exceptions → Payments → Audit log → Settings]**
"Overview: touchless rate, open exceptions, what's scheduled, duplicates stopped, fraud held. Exceptions: who owns
what, oldest first. Payments: the payment run — always to verified accounts. Audit log: every decision and review.
Settings: every threshold is editable — tolerance, approval limit, PO confidence — so finance owns the policy."

## 14. Close (30 s)
"So: it reads messy invoices, it checks them the way a careful clerk would — including across invoices — and when it
isn't sure, it says so and routes to the right person. Next I'd add three-way matching with goods receipts, a real
mailbox connector, and posting straight into the ERP. Happy to go deeper on anything."

---

## Likely questions — short answers
- **How accurate is extraction?** "On the 38-invoice test pack every decision is correct; the parser is tuned to
  common invoice conventions. For unseen layouts there's a Claude extractor with structured output — and grounding
  means a misread can't silently approve money."
- **What happens with a new vendor format?** "Claude handles layout variety; the rules stay identical. If a value
  can't be grounded in the document, it goes to review."
- **Why SQLite / how would it scale?** "It processes one invoice at a time on purpose, so duplicate and PO-balance
  checks always see every earlier invoice. At scale: a queue per entity, Postgres, the same rules."
- **False positives?** "Every exception says exactly why, and tolerances are tunable. The design accepts a few
  extra reviews to never pay twice or pay a fraudster."
- **What did you learn building it?** "That the hard part isn't reading invoices — it's judgment: when to be
  confident, when to refuse, and never letting a scanner error become a vendor's problem."
- **Hardest bug?** "A vendor called 'Apex Office Supplies' was matched to 'Northwind Office Supplies' because the
  generic words matched. Now the distinctive part of the name must match too, and a different email domain or tax
  ID overrules a weak name match."
