---
title: Invoice Desk
emoji: 🧾
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 8765
pinned: false
short_description: Invoice PDF to AP decision, with every check visible
---

# Invoice Desk — automated invoice processing (PS-1: from PDF to decision)

Invoice Desk takes a vendor invoice PDF (digital or scanned), reads it, checks it against your vendor master,
PO register and payment history, and makes a reasoned decision. Every check is visible while it runs.

| Outcome | When | What happens |
|---|---|---|
| **Approved** | Every check passes | Scheduled for payment on the due date to the *verified* account on file; posted to the AP ledger. |
| **Needs review** | Price over tolerance, PO over-billed, PO missing/ambiguous, charges not on PO, totals don't add up, wrong currency, above the approval limit, possible double charge | Routed to the PO owner / AP team with the exact reason; reviewer approves or rejects with a note. |
| **On hold** | Bank details changed, look-alike sender domain, vendor not yet onboarded | Payment blocked until verified by phone with the number on file. |
| **Rejected** | Duplicate (same file, same number, re-numbered resubmission), blocked/unknown vendor, missing invoice number/date, addressed to another company, unreadable | Not payable; a reply to the vendor is drafted. |

The strictest outcome wins (Rejected > On hold > Needs review > Approved).

---

## Run it

```powershell
.\start.ps1
```

Open **http://localhost:8765**. First run creates `.venv` and installs dependencies. It runs fully on-device; no API
key is needed. To use Claude for field extraction (more robust on unfamiliar layouts), set the key first:

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."; .\start.ps1
```

The app starts **empty** — no vendors, no POs, no invoices, no history. The first-launch setup asks for:

1. **Company profile** — your legal entity name (invoices billed to anyone else are returned) and AP email.
2. **Vendor master** (CSV) — vendor ID, name, status, verified bank account, registered email domain, terms.
3. **PO register** (CSV, one row per PO line) — PO number, vendor, owner, line items, quantities, agreed prices.

Then upload invoices (drag-and-drop anywhere, or the **Upload invoices** button), or save PDFs into `inbox/`
(the watched AP mailbox).

## Test pack

`test-pack/` contains everything needed to exercise every path — see **`test-pack/TEST-GUIDE.md`**:

- `master-data/vendors.csv`, `master-data/purchase_orders.csv` — import in setup
- `invoices/` — **38 invoice PDFs**: 8 approved, 17 needs review, 5 on hold, 8 rejected; digital, scanned
  (OCR), multi-page, different layouts and date formats, bundled lines, split POs, duplicates, fraud signals, etc.
- `interview-10/` — the **10 best demo invoices** (01–10, upload in order) + `INTERVIEW-SCRIPT.pdf`

Select all 38 PDFs and upload them in one go; a batch is processed in file-name order, which satisfies the cases
that depend on an earlier invoice (e.g. the second half of a split PO). Rebuild the pack with
`.venv\Scripts\python scripts\build_test_pack.py` (only its own files are replaced).

## What's in the product

| Area | Purpose |
|---|---|
| **Overview** | Touchless rate, open exceptions, scheduled payments, duplicates stopped, fraud held, outcome mix, top exception reasons, open work by owner. |
| **Invoices** | Every invoice with status tabs and counts, search, CSV export; updates live while a batch processes. |
| **Invoice page** | Document viewer (pages, zoom, download) beside the decision: exceptions, next step and owner, invoice details, line-by-line PO match, live **processing log** of all 8 stages with each check, activity trail, drafted vendor email, Approve / Release / Reject with a mandatory reason. |
| **Exceptions** | The review queue, oldest first, with owner. |
| **Payments** | The payment run: pay date, vendor, amount, masked verified account, who approved; export file. |
| **Vendors / Purchase orders** | Master data, CSV import, add vendor, change vendor status, PO consumption. |
| **Audit log** | Every decision, review and configuration change. |
| **Settings** | Company profile, approval policy (all thresholds editable), data import, export, delete. |

## How a decision is made — 8 stages

1. **Receive** — fingerprint the file (catches re-sent files).
2. **Read** — PDF text layer, or on-device OCR (RapidOCR) for scanned pages, with confidence.
3. **Extract** — vendor, invoice #, dates, PO, line items, subtotal/tax/total, remit-to bank, notes. Claude (structured JSON) when a key is set, else an on-device parser. Key values are traced back to the document text.
4. **Validate** — required fields, bill-to is our company, line maths, subtotal + tax = total, tax-rate plausibility, future/stale dates.
5. **Verify vendor** — vendor master match (distinctive name *and* full name must agree; domain and tax ID can overrule a weak match), status, remit-to bank vs verified account, sender domain, tax ID.
6. **Match purchase order** — printed PO, or identified from the vendor's open POs by lines + amount (only with a clear winner). Line-level price check vs tolerance (both % and $ must hold), bundled lines, currency, quantity left after earlier invoices (split POs), approval limit.
7. **Duplicate check** — same file, same number, re-numbered resubmission (-R, -COPY…) with the same amount, and the same lines + amount + PO billed again — against paid history *and* invoices still in review.
8. **Decide** — strictest outcome, plain-language reasons, owner, next action, drafted email, ledger posting.

### Design choices

- **AI reads, rules decide.** Extraction may use a model; approving money never does. Same input → same decision, and finance can change thresholds without code.
- **Never trust bank details on an invoice.** Payment always goes to the verified account in the vendor master.
- **Run every check, every time** — reviewers see the whole picture in one pass.
- **Refuse to guess** — when two POs fit, or a printed PO doesn't exist, a human decides.
- **One invoice at a time, in order** — so duplicate and PO-balance checks always see every earlier invoice.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | unset | Use Claude (`claude-opus-5-5`, structured output) for extraction; falls back to the on-device parser on any error. |
| `CLAUDE_MODEL` | `claude-opus-5-5` | Model override. |
| `STAGE_MIN_MS` | `350` | Minimum time per stage so people can follow the live view (`0` = full speed). Real compute time is shown per stage. |
| `INBOX_WATCH` | `1` | Watch `./inbox/` for PDFs. |

## Deploy (live link)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/ALINA282002/invoice-desk)

The repo includes a `Dockerfile` and a Render Blueprint (`render.yaml`, free plan). Render builds the image from
this GitHub repo and redeploys on every push. With `BOOTSTRAP_DIR=demo-config` a fresh instance loads the company
profile, vendor master and PO register from `demo-config/`, so it is ready for the test invoices in `test-pack/`
straight away (free instances sleep after ~15 min idle and take about a minute to wake).

Any Docker host works the same way:
`docker build -t invoice-desk . && docker run -p 8765:8765 -e BOOTSTRAP_DIR=demo-config invoice-desk`.

## Project layout

```
app/main.py           FastAPI: REST API, live processing stream (SSE), mailbox watcher, static UI
app/pipeline.py       The 8 stages, decision policy, review actions, ledger posting, FIFO queue
app/extraction.py     Text layer / OCR, on-device parser, Claude extractor, grounding, vendor-name matching
app/db.py             SQLite (starts empty) + CSV import of vendor master and PO register
static/               Single-page UI (vanilla JS, no build step)
scripts/build_test_pack.py      Generates test-pack/ (master data CSVs, 38 invoice PDFs, TEST-GUIDE.md)
scripts/build_demo_sheet.py     Generates test-pack/DEMO-CHEAT-SHEET.pdf (all 38 cases)
scripts/build_interview_set.py  Generates test-pack/interview-10/ (10 best demo invoices + INTERVIEW-SCRIPT.pdf)
scripts/build_demo_sheet.py  Generates test-pack/DEMO-CHEAT-SHEET.pdf (printable interview cheat sheet)
```

## Limitations / next steps

- 2-way match (invoice ↔ PO). 3-way match with goods receipts is the next stage to add.
- The on-device parser covers common invoice label conventions; truly novel layouts are what the Claude extractor is for.
- Single legal entity and base currency; real mailbox (IMAP/Graph) and ERP posting connectors would replace the watched folder and the payment-file export.
