/* Invoice Desk — single-page UI (no build step). */
(() => {
  "use strict";

  // ================================================================ icons
  const P = (d, extra = "") => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" ${extra}>${d}</svg>`;
  const ICONS = {
    menu: P('<path d="M4 6h16M4 12h16M4 18h16"/>'),
    search: P('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>'),
    upload: P('<path d="M12 15V3"/><path d="m7 8 5-5 5 5"/><path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/>'),
    download: P('<path d="M12 3v12"/><path d="m7 10 5 5 5-5"/><path d="M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4"/>'),
    home: P('<path d="M3 10.5 12 3l9 7.5"/><path d="M5 9v11h14V9"/>'),
    file: P('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/><path d="M8 13h8M8 17h5"/>'),
    flag: P('<path d="M4 22V4"/><path d="M4 4h12l-2 4 2 4H4"/>'),
    bank: P('<path d="M3 10h18"/><path d="M12 3 3 8h18z"/><path d="M5 10v8M9 10v8M15 10v8M19 10v8"/><path d="M3 21h18"/>'),
    users: P('<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M18 14a6.5 6.5 0 0 1 3.5 6"/>'),
    clipboard: P('<rect x="5" y="4" width="14" height="18" rx="2"/><path d="M9 2h6v4H9z"/><path d="M9 12h6M9 16h4"/>'),
    history: P('<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/>'),
    gear: P('<circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-1.1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.5-1.1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3H9a1.7 1.7 0 0 0 1-1.5V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8V9a1.7 1.7 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z"/>'),
    check: P('<path d="M20 6 9 17l-5-5"/>', 'stroke-width="3"'),
    checkc: P('<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/>'),
    warn: P('<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4"/><path d="M12 17h.01"/>'),
    x: P('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>', 'stroke-width="3"'),
    xc: P('<circle cx="12" cy="12" r="9"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>'),
    close: P('<path d="M18 6 6 18"/><path d="m6 6 12 12"/>'),
    info: P('<circle cx="12" cy="12" r="9"/><path d="M12 16v-4"/><path d="M12 8h.01"/>'),
    eye: P('<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>'),
    lock: P('<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>'),
    ban: P('<circle cx="12" cy="12" r="9"/><path d="m5.7 5.7 12.6 12.6"/>'),
    spin: P('<path d="M21 12a9 9 0 1 1-6.2-8.6"/>', 'class="spin"'),
    dot: P('<circle cx="12" cy="12" r="3" fill="currentColor"/>'),
    copy: P('<rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>'),
    mail: P('<rect x="2" y="4" width="20" height="16" rx="2"/><path d="m22 7-10 6L2 7"/>'),
    shield: P('<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>'),
    dollar: P('<path d="M12 2v20"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'),
    clock: P('<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>'),
    zin: P('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/><path d="M11 8v6M8 11h6"/>'),
    zout: P('<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/><path d="M8 11h6"/>'),
    left: P('<path d="m15 18-6-6 6-6"/>'), right: P('<path d="m9 18 6-6-6-6"/>'),
    ext: P('<path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M21 14v5a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5"/>'),
    plus: P('<path d="M12 5v14M5 12h14"/>'),
    table: P('<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 10h18M9 4v16"/>'),
    sparkle: P('<path d="M12 3v4M12 17v4M3 12h4M17 12h4M6 6l2.5 2.5M15.5 15.5 18 18M6 18l2.5-2.5M15.5 8.5 18 6"/>'),
    trash: P('<path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M19 6l-1 14H6L5 6"/>'),
    moon: P('<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/>'),
  };
  const ic = (n, cls = "") => `<span class="i ${cls}">${ICONS[n] || ""}</span>`;
  const paintIcons = (root = document) => root.querySelectorAll("[data-icon]").forEach((el) => { if (!el.innerHTML) el.innerHTML = ICONS[el.dataset.icon] || ""; });
  paintIcons();

  // ================================================================ helpers
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const money = (v, cur) => (v === null || v === undefined || v === "" ? "—" :
    new Intl.NumberFormat("en-US", { style: "currency", currency: cur || "USD" }).format(v));
  const compact = (v) => (v == null ? "—" : v >= 1e6 ? "$" + (v / 1e6).toFixed(2) + "M" : v >= 1e3 ? "$" + (v / 1e3).toFixed(1) + "k" : "$" + Math.round(v));
  const dateFmt = (iso) => { if (!iso) return "—"; const d = new Date(iso.length === 10 ? iso + "T00:00:00" : iso); return isNaN(d) ? iso : d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }); };
  const dtFmt = (iso) => { if (!iso) return "—"; const d = new Date(iso); return d.toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }); };
  const ago = (iso) => { if (!iso) return ""; const s = (Date.now() - new Date(iso)) / 1000; if (s < 60) return "just now"; if (s < 3600) return Math.floor(s / 60) + " min ago"; if (s < 86400) return Math.floor(s / 3600) + " h ago"; return Math.floor(s / 86400) + " d ago"; };
  const secs = (ms) => (ms == null ? "—" : ms < 1000 ? `${ms} ms` : `${(ms / 1000).toFixed(1)} s`);
  const initials = (s) => (s || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
  const store = { get: (k, d) => { try { return localStorage.getItem(k) ?? d; } catch (_) { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch (_) {} } };

  const STATUS = {
    APPROVED: { label: "Approved", icon: "checkc", desc: "Scheduled for payment" },
    NEEDS_REVIEW: { label: "Needs review", icon: "eye", desc: "Waiting for a reviewer" },
    ON_HOLD: { label: "On hold", icon: "lock", desc: "Payment blocked pending verification" },
    REJECTED: { label: "Rejected", icon: "ban", desc: "Not payable as submitted" },
  };
  const COLOR = { APPROVED: "var(--good)", NEEDS_REVIEW: "var(--warning)", ON_HOLD: "var(--serious)", REJECTED: "var(--critical)" };
  const badge = (status, state) => {
    if (state === "error") return `<span class="badge ERROR"><span class="dot" style="background:var(--critical)"></span>Failed</span>`;
    if (state && state !== "done") return `<span class="badge PROCESSING">${ic("spin")}${state === "queued" ? "Queued" : "Processing"}</span>`;
    const m = STATUS[status]; if (!m) return `<span class="badge plain"><span class="dot"></span>${esc(status || "—")}</span>`;
    return `<span class="badge ${status}"><span class="dot"></span>${m.label}</span>`;
  };
  const vBadge = (s) => ({ approved: `<span class="badge APPROVED"><span class="dot"></span>Approved</span>`, blocked: `<span class="badge REJECTED"><span class="dot"></span>Blocked</span>`,
    pending_onboarding: `<span class="badge ON_HOLD"><span class="dot"></span>Onboarding</span>`, inactive: `<span class="badge plain"><span class="dot"></span>Inactive</span>` }[s] || esc(s));

  const api = async (path, opts = {}) => {
    const headers = opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {};
    const r = await fetch(path, { ...opts, headers });
    if (!r.ok) { let m = r.statusText; try { m = (await r.json()).detail || m; } catch (_) {} throw new Error(m); }
    return r.json();
  };
  const toast = (msg) => { const t = $("#toast"); t.textContent = msg; t.classList.add("show"); clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 2800); };
  const tip = $("#tip");
  document.addEventListener("mousemove", (e) => {
    const el = e.target.closest?.("[data-tip]");
    if (!el) { tip.classList.remove("show"); return; }
    tip.innerHTML = el.dataset.tip; tip.classList.add("show");
    tip.style.left = Math.min(e.clientX + 12, innerWidth - tip.offsetWidth - 8) + "px"; tip.style.top = e.clientY + 16 + "px";
  });
  const savedTheme = store.get("idesk-theme"); if (savedTheme) document.documentElement.dataset.theme = savedTheme;

  // ================================================================ global state + polling
  let HEALTH = {}, SETUP = { complete: true }, STATS = {}, firstRoute = true;
  let cleanup = [];
  const onLeave = (fn) => cleanup.push(fn);

  async function poll() {
    try {
      [HEALTH, SETUP, STATS] = await Promise.all([api("/api/health"), api("/api/setup"), api("/api/stats")]);
      const n = STATS.processing;
      const pi = $("#proc-indicator"); pi.hidden = !n; pi.innerHTML = `${ic("spin")}Processing ${n}`;
      const ec = $("#exc-count"); ec.hidden = !STATS.open_exceptions; ec.textContent = STATS.open_exceptions;
      $("#org-chip").innerHTML = `<span>${esc(SETUP.company_name || "Company not set")}</span><div class="avatar">${esc(initials(SETUP.company_name || "AP"))}</div>`;
      $("#sys-status").innerHTML = `
        <div class="row"><span class="dot" style="background:var(--good)"></span>Extraction: ${HEALTH.extractor === "claude" ? "Claude" : "On-device parser"}</div>
        <div class="row"><span class="dot" style="background:${HEALTH.ocr_ready ? "var(--good)" : "var(--warning)"}"></span>OCR ${HEALTH.ocr_ready ? "ready" : "starting…"}</div>
        <div class="row" data-tip="PDFs saved to this folder are processed automatically:<br>${esc(HEALTH.inbox)}"><span class="dot" style="background:var(--good)"></span>Mailbox folder watched</div>
        <button class="btn ghost sm" id="theme-btn">${ic("moon")}Theme</button>`;
      $("#theme-btn").onclick = () => {
        const cur = document.documentElement.dataset.theme || (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
        document.documentElement.dataset.theme = cur === "dark" ? "light" : "dark"; store.set("idesk-theme", document.documentElement.dataset.theme);
      };
    } catch (_) {
      $("#sys-status").innerHTML = `<div class="row"><span class="dot" style="background:var(--critical)"></span>Server unreachable</div>`;
    }
  }
  setInterval(poll, 3000);

  // ================================================================ shell wiring
  $("#global-search").onsubmit = (e) => { e.preventDefault(); location.hash = `#/invoices?q=${encodeURIComponent($("#global-q").value.trim())}`; };
  $("#upload-btn").onclick = () => openUpload();
  $("#menu-btn").onclick = (e) => { e.stopPropagation(); $("#side").classList.toggle("open"); };
  $("#view").addEventListener("click", () => $("#side").classList.remove("open"));
  let dragDepth = 0;
  window.addEventListener("dragenter", (e) => { if ([...(e.dataTransfer?.types || [])].includes("Files") && !$("#dlg").open) { dragDepth++; $("#drop-overlay").classList.add("on"); } });
  window.addEventListener("dragleave", () => { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) $("#drop-overlay").classList.remove("on"); });
  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", (e) => {
    e.preventDefault(); dragDepth = 0; $("#drop-overlay").classList.remove("on");
    if (!$("#dlg").open && e.dataTransfer?.files?.length) openUpload([...e.dataTransfer.files]);
  });

  // ================================================================ dialogs
  const dlg = $("#dlg");
  const openDialog = (html) => { dlg.innerHTML = html; paintIcons(dlg); dlg.showModal(); $$("[data-close]", dlg).forEach((b) => (b.onclick = () => dlg.close())); };
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });

  function openUpload(initial = []) {
    let files = [];
    const warn = !SETUP.complete ? `<div class="alert crit">${ic("warn")}<div>Setup isn't finished${SETUP.vendors ? "" : " — no vendor master"}${SETUP.purchase_orders ? "" : " — no PO register"}${SETUP.company ? "" : " — company not set"}. Invoices will be checked against incomplete data. <a href="#/setup" data-close>Finish setup</a></div></div>` : "";
    openDialog(`
      <div class="dlg-h"><div><h2>Upload invoices</h2><p>PDF invoices, digital or scanned. Several files are processed one after another, in file-name order.</p></div>
        <button class="icon-btn" data-close aria-label="Close">${ic("close")}</button></div>
      <div class="dlg-b">${warn}
        <label class="dropzone" id="dz"><input type="file" id="dz-in" accept="application/pdf,.pdf" multiple hidden>
          <div class="dz-ico">${ic("upload")}</div><div><b>Choose files</b> or drag them here</div><div class="muted" style="font-size:12px;margin-top:2px">PDF · up to 25 MB each</div></label>
        <ul class="filelist" id="fl" hidden></ul>
      </div>
      <div class="dlg-f"><button class="btn" data-close>Cancel</button><button class="btn primary" id="dz-go" disabled>Process</button></div>`);
    const render = () => {
      const fl = $("#fl"); fl.hidden = !files.length;
      fl.innerHTML = files.map((f, i) => `<li>${ic("file")}<span class="fn">${esc(f.name)}</span><span class="muted">${(f.size / 1024).toFixed(0)} KB</span><button class="icon-btn" data-rm="${i}" aria-label="Remove">${ic("close")}</button></li>`).join("");
      $$("[data-rm]", fl).forEach((b) => (b.onclick = () => { files.splice(+b.dataset.rm, 1); render(); }));
      const go = $("#dz-go"); go.disabled = !files.length; go.textContent = files.length > 1 ? `Process ${files.length} invoices` : "Process invoice";
    };
    const add = (list) => {
      const pdfs = [...list].filter((f) => /\.pdf$/i.test(f.name) || f.type === "application/pdf");
      if (pdfs.length < list.length) toast("Only PDF files can be uploaded");
      files = files.concat(pdfs).sort((a, b) => a.name.localeCompare(b.name)); render();
    };
    const dz = $("#dz");
    $("#dz-in").onchange = (e) => add(e.target.files);
    ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); e.stopPropagation(); dz.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); e.stopPropagation(); dz.classList.remove("over"); }));
    dz.addEventListener("drop", (e) => add(e.dataTransfer.files));
    $("#dz-go").onclick = async () => {
      const go = $("#dz-go"); go.disabled = true; go.innerHTML = `${ic("spin")}Uploading…`;
      const fd = new FormData(); files.forEach((f) => fd.append("files", f));
      try {
        const r = await api("/api/runs", { method: "POST", body: fd });
        dlg.close(); poll();
        if (r.run_ids.length === 1) location.hash = `#/invoices/${r.run_ids[0]}`;
        else { toast(`${r.run_ids.length} invoices queued for processing`); location.hash = "#/invoices"; if (location.hash === "#/invoices") route(); }
      } catch (e) { toast(e.message); go.disabled = false; go.textContent = "Process"; }
    };
    if (initial.length) add(initial);
  }

  function openImport(kind, after) {
    const meta = kind === "vendors"
      ? { title: "Import vendor master", url: "/api/import/vendors", cols: "vendor_id, name, status, aliases, tax_id, email_domain, contact_email, contact_phone, bank_name, routing_number, account_number, payment_terms_days, currency", req: "vendor_id, name, status" }
      : { title: "Import PO register", url: "/api/import/purchase-orders", cols: "po_number, vendor_id, issue_date, po_description, department, requester, status, currency, line_no, sku, line_description, quantity, unit_price", req: "po_number, vendor_id, line_no, line_description, quantity, unit_price" };
    openDialog(`
      <div class="dlg-h"><div><h2>${meta.title}</h2><p>CSV export from your ERP or spreadsheet. Existing records with the same ID are updated.</p></div>
        <button class="icon-btn" data-close aria-label="Close">${ic("close")}</button></div>
      <div class="dlg-b">
        <label class="dropzone" id="dz"><input type="file" id="dz-in" accept=".csv,text/csv" hidden>
          <div class="dz-ico">${ic("table")}</div><div id="dz-name"><b>Choose a CSV file</b> or drag it here</div></label>
        <div><div class="field"><span>Columns</span></div><div class="cols mono" style="font-size:11.5px;color:var(--text-2);background:var(--panel-2);border:1px solid var(--border);border-radius:6px;padding:8px 10px;margin-top:6px;overflow-x:auto;white-space:nowrap">${meta.cols}</div>
          <small class="muted">Required: ${meta.req}${kind === "pos" ? " · one row per PO line · vendors must exist first" : " · status: approved, blocked, pending_onboarding or inactive"}</small></div>
        <div id="imp-res"></div>
      </div>
      <div class="dlg-f"><button class="btn" data-close>Close</button><button class="btn primary" id="imp-go" disabled>Import</button></div>`);
    let file = null;
    const pick = (f) => { file = f; $("#dz-name").innerHTML = `<b>${esc(f.name)}</b> · ${(f.size / 1024).toFixed(1)} KB`; $("#imp-go").disabled = false; };
    $("#dz-in").onchange = (e) => e.target.files[0] && pick(e.target.files[0]);
    const dz = $("#dz");
    ["dragenter", "dragover"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); e.stopPropagation(); dz.classList.add("over"); }));
    ["dragleave", "drop"].forEach((ev) => dz.addEventListener(ev, (e) => { e.preventDefault(); e.stopPropagation(); dz.classList.remove("over"); }));
    dz.addEventListener("drop", (e) => e.dataTransfer.files[0] && pick(e.dataTransfer.files[0]));
    $("#imp-go").onclick = async () => {
      const fd = new FormData(); fd.append("file", file);
      try {
        const r = await api(meta.url, { method: "POST", body: fd });
        $("#imp-res").innerHTML = `<div class="result ok">Imported ${kind === "vendors" ? `${r.rows} vendors` : `${r.purchase_orders} purchase orders (${r.rows} lines)`} — ${r.added} new, ${r.updated} updated.</div>`;
        $("#imp-go").disabled = true; poll(); after && after();
      } catch (e) { $("#imp-res").innerHTML = `<div class="result err">${esc(e.message)}</div>`; }
    };
  }

  function openReview(run, action, done) {
    const isHold = run.final_status === "ON_HOLD";
    const approve = action === "approve";
    openDialog(`
      <div class="dlg-h"><div><h2>${approve ? (isHold ? "Release for payment" : "Approve for payment") : "Reject invoice"}</h2>
        <p>${esc(run.vendor_name || "")} · ${esc(run.invoice_number || "no number")} · ${money(run.total, run.currency)}</p></div>
        <button class="icon-btn" data-close aria-label="Close">${ic("close")}</button></div>
      <div class="dlg-b">
        ${approve && isHold ? `<div class="alert crit">${ic("shield")}<div>Only release after you have confirmed the change by phone using the number in the vendor master — never the contact details on the invoice.</div></div>` : ""}
        ${approve ? `<div class="muted">The invoice is posted to the AP ledger and scheduled on its due date to the verified account on file.</div>` : ""}
        <label class="field"><span>Your name</span><input type="text" id="rv-name" value="${esc(store.get("idesk-reviewer", ""))}" placeholder="e.g. Jordan Lee"></label>
        <label class="field"><span>Reason <span class="muted">(required — recorded in the audit log)</span></span>
          <textarea id="rv-note" placeholder="${approve ? (isHold ? "Called vendor on +1 … from the vendor master; change confirmed by …" : "Price increase agreed by buyer on …") : "Duplicate of …  /  Vendor to reissue …"}"></textarea></label>
        <div id="rv-err"></div>
      </div>
      <div class="dlg-f"><button class="btn" data-close>Cancel</button><button class="btn ${approve ? "success" : "danger solid"}" id="rv-go">${approve ? (isHold ? "Release payment" : "Approve") : "Reject"}</button></div>`);
    $("#rv-go").onclick = async () => {
      const name = $("#rv-name").value.trim(), note = $("#rv-note").value.trim();
      if (!name || note.length < 4) { $("#rv-err").innerHTML = `<div class="result err">Enter your name and a reason.</div>`; return; }
      store.set("idesk-reviewer", name);
      try { await api(`/api/runs/${run.id}/review`, { method: "POST", body: JSON.stringify({ action, note, reviewer: name }) });
        dlg.close(); toast(approve ? "Approved and scheduled for payment" : "Invoice rejected"); poll(); done && done();
      } catch (e) { $("#rv-err").innerHTML = `<div class="result err">${esc(e.message)}</div>`; }
    };
  }

  // ================================================================ router
  async function route() {
    cleanup.forEach((f) => { try { f(); } catch (_) {} }); cleanup = [];
    $("#side").classList.remove("open");
    const raw = location.hash.replace(/^#\/?/, "");
    const [path, qs] = raw.split("?");
    const parts = path.split("/").filter(Boolean);
    const params = new URLSearchParams(qs || "");
    let page = parts[0] || "overview";
    if (firstRoute) {
      firstRoute = false;
      try { SETUP = await api("/api/setup"); } catch (_) {}
      if (!SETUP.complete && (page === "overview") && !(STATS.total_runs > 0)) { location.replace("#/setup"); return; }
    }
    $$(".side a").forEach((a) => a.classList.toggle("active", a.dataset.nav === page));
    if (page !== "invoices") $("#global-q").value = "";
    const view = $("#view"); view.innerHTML = ""; window.scrollTo(0, 0);
    try {
      const V = { overview: viewOverview, invoices: parts[1] ? (v) => viewInvoice(v, parts[1]) : (v) => viewInvoices(v, params),
        exceptions: viewExceptions, payments: viewPayments, vendors: viewVendors, "purchase-orders": viewPOs, audit: viewAudit,
        settings: (v) => viewSettings(v, parts[1] || "company"), setup: viewSetup }[page] || viewOverview;
      await V(view);
      paintIcons(view);
    } catch (e) { view.innerHTML = `<div class="card card-b"><b>Couldn't load this page.</b><div class="muted">${esc(e.message)}</div></div>`; }
  }
  window.addEventListener("hashchange", route);

  const head = (title, sub, actions = "", crumbs = "") => `
    <div class="page-head"><div>${crumbs ? `<div class="crumbs">${crumbs}</div>` : ""}<h1>${title}</h1>${sub ? `<div class="sub">${sub}</div>` : ""}</div>
    <div class="actions">${actions}</div></div>`;
  const emptyState = (icon, title, text, action = "") => `<div class="empty"><div class="e-ico">${ic(icon)}</div><h3>${title}</h3><p>${text}</p>${action}</div>`;

  // ================================================================ SETUP
  async function viewSetup(view) {
    const [st, settings] = await Promise.all([api("/api/setup"), api("/api/settings")]);
    SETUP = st;
    const co = settings.company;
    const step = (n, done, title, text, body) => `<div class="step ${done ? "done" : ""}"><div class="sn">${done ? ic("check") : n}</div>
      <div><h3>${title}</h3><p>${text}</p></div><div>${body}</div></div>`;
    view.innerHTML = head("Set up Invoice Desk", "Three steps before the first invoice: who you are, who you buy from, and what you ordered. Invoices are checked against exactly this data.") + `
      <div class="card" style="max-width:860px">
        <div class="steps">
          ${step(1, st.company, "Company profile", st.company ? `Invoices must be addressed to <b>${esc(co.legal_name)}</b>.` : "Your legal entity name — invoices addressed to anyone else are returned.",
            `<button class="btn ${st.company ? "" : "primary"}" id="s-co">${st.company ? "Edit" : "Add company"}</button>`)}
          ${step(2, st.vendors > 0, "Vendor master", st.vendors ? `${st.vendors} vendors imported.` : "Approved vendors with their verified bank accounts, sender domains and terms (CSV).",
            `<button class="btn ${st.vendors ? "" : "primary"}" id="s-v">${st.vendors ? "Re-import" : "Import CSV"}</button>`)}
          ${step(3, st.purchase_orders > 0, "PO register", st.purchase_orders ? `${st.purchase_orders} purchase orders imported.` : "Open purchase orders with line items and agreed prices (CSV, one row per line).",
            `<button class="btn ${st.purchase_orders ? "" : "primary"}" id="s-po" ${st.vendors ? "" : "disabled"}>${st.purchase_orders ? "Re-import" : "Import CSV"}</button>`)}
        </div>
        <div class="card-h" style="border-top:1px solid var(--border);border-bottom:0">
          <span class="muted">${st.complete ? "Setup complete — you can start processing invoices." : "You can change all of this later in Settings."}</span>
          <div class="actions"><a class="btn ${st.complete ? "primary" : ""}" href="#/overview">${st.complete ? "Go to overview" : "Skip for now"}</a>${st.complete ? `<button class="btn" id="s-up">${ic("upload")}Upload invoices</button>` : ""}</div>
        </div>
      </div>`;
    $("#s-co").onclick = () => companyDialog(co, () => viewSetup(view).then(() => paintIcons(view)));
    $("#s-v").onclick = () => openImport("vendors", () => viewSetup(view).then(() => paintIcons(view)));
    $("#s-po").onclick = () => openImport("pos", () => viewSetup(view).then(() => paintIcons(view)));
    if ($("#s-up")) $("#s-up").onclick = () => openUpload();
  }

  function companyDialog(co, after) {
    openDialog(`
      <div class="dlg-h"><div><h2>Company profile</h2><p>Used to verify the bill-to party and to sign vendor emails.</p></div><button class="icon-btn" data-close>${ic("close")}</button></div>
      <div class="dlg-b">
        <label class="field"><span>Legal entity name</span><input type="text" id="co-name" value="${esc(co.legal_name)}" placeholder="e.g. Acme Manufacturing Inc."></label>
        <label class="field"><span>Accounts payable email</span><input type="email" id="co-mail" value="${esc(co.ap_email)}" placeholder="ap@yourcompany.com"></label>
        <label class="field"><span>Base currency</span><select id="co-cur">${["USD", "EUR", "GBP", "CAD"].map((c) => `<option ${co.currency === c ? "selected" : ""}>${c}</option>`).join("")}</select></label>
        <div id="co-err"></div>
      </div>
      <div class="dlg-f"><button class="btn" data-close>Cancel</button><button class="btn primary" id="co-go">Save</button></div>`);
    $("#co-go").onclick = async () => {
      const legal_name = $("#co-name").value.trim();
      if (legal_name.length < 3) { $("#co-err").innerHTML = `<div class="result err">Enter the legal entity name.</div>`; return; }
      await api("/api/settings/company", { method: "PUT", body: JSON.stringify({ legal_name, ap_email: $("#co-mail").value.trim(), currency: $("#co-cur").value }) });
      dlg.close(); toast("Company profile saved"); poll(); after && after();
    };
  }

  // ================================================================ OVERVIEW
  async function viewOverview(view) {
    const load = async () => {
      const [s, runs, st] = await Promise.all([api("/api/stats"), api("/api/runs?limit=8"), api("/api/setup")]);
      const n = s.total_runs;
      const setupCard = !st.complete ? `<div class="card setup-card" style="margin-bottom:16px"><div class="card-h"><div><h2>Finish setting up</h2><div class="muted" style="font-size:12.5px">Invoices are checked against your company profile, vendor master and PO register.</div></div><a class="btn primary" href="#/setup">Continue setup</a></div></div>` : "";
      const kpi = (icon, l, v, s_) => `<div class="card kpi"><div class="l">${ic(icon)}${l}</div><div class="v">${v}</div><div class="s">${s_}</div></div>`;
      let body;
      if (!n) {
        body = `<div class="card">${emptyState("file", "No invoices processed yet", "Upload vendor invoices (PDF, digital or scanned). Each one is read, matched to its purchase order and either approved for payment or routed to the right person — with every check visible.",
          `<button class="btn primary" id="ov-up">${ic("upload")}Upload invoices</button>`)}</div>`;
      } else {
        const order = ["APPROVED", "NEEDS_REVIEW", "ON_HOLD", "REJECTED"], fin = s.final_statuses;
        const rc = s.reason_counts || [], max = Math.max(1, ...rc.map((r) => r[1]));
        body = `
          <div class="kpis">
            ${kpi("file", "Invoices processed", n, s.processing ? `${s.processing} processing now` : `${s.read_methods.ocr || 0} scanned · ${s.read_methods.text_layer || 0} digital`)}
            ${kpi("checkc", "Touchless rate", s.touchless_rate + "%", `${s.decisions.APPROVED || 0} approved without manual work`)}
            ${kpi("flag", "Open exceptions", s.open_exceptions, `${compact(s.open_value)} waiting for a decision`)}
            ${kpi("bank", "Scheduled payments", compact(s.scheduled.value), `${s.scheduled.count} invoice${s.scheduled.count === 1 ? "" : "s"} in the payment run`)}
            ${kpi("ban", "Duplicates stopped", compact(s.duplicates_prevented.value), `${s.duplicates_prevented.count} double payment${s.duplicates_prevented.count === 1 ? "" : "s"} prevented`)}
            ${kpi("shield", "Fraud signals held", compact(s.fraud_held.value), `${s.fraud_held.count} bank-detail change${s.fraud_held.count === 1 ? "" : "s"}`)}
          </div>
          <div class="grid2 gap">
            <div class="card"><div class="card-h"><h2>Outcomes</h2><span class="muted">current status · ${n} invoices</span></div><div class="card-b">
              <div class="stack">${order.filter((k) => fin[k]).map((k) => `<div style="flex:${fin[k]};background:${COLOR[k]}" data-tip="${STATUS[k].label}: ${fin[k]}"></div>`).join("")}</div>
              <div class="legend-rows">${order.map((k) => `<div class="lr"><div>${badge(k)} <span class="muted" style="margin-left:6px">${STATUS[k].desc}</span></div><div class="num"><b>${fin[k] || 0}</b></div><div class="num muted">${Math.round(((fin[k] || 0) / n) * 100)}%</div></div>`).join("")}</div>
            </div></div>
            <div class="card"><div class="card-h"><h2>Why invoices need attention</h2><span class="muted">invoices affected</span></div><div class="card-b">
              ${rc.length ? `<div class="bars">${rc.slice(0, 8).map(([c, k]) => `<div class="bar-row" data-tip="${esc(s.reason_titles[c] || c)}: ${k}"><div class="lab">${esc(s.reason_titles[c] || c)}</div><div class="track"><div class="fill" style="width:${(k / max) * 100}%"></div></div><div class="v">${k}</div></div>`).join("")}</div>`
                : `<div class="muted">No exceptions — every invoice so far was approved.</div>`}
            </div></div>
          </div>
          <div class="grid3 gap">
            <div class="card"><div class="card-h"><h2>Recent invoices</h2><a href="#/invoices" class="btn ghost sm">View all</a></div>
              <div class="tbl-wrap"><table class="t compact"><tbody>${runs.map((r) => `<tr class="click" data-id="${esc(r.id)}">
                <td><div class="cell-strong">${esc(r.vendor_name || r.filename)}</div><div class="sub mono">${esc(r.invoice_number || "—")}</div></td>
                <td class="num">${money(r.total, r.currency)}</td><td>${badge(r.final_status, r.state)}</td><td class="num muted">${ago(r.created_at)}</td></tr>`).join("")}</tbody></table></div></div>
            <div class="card"><div class="card-h"><h2>Open exceptions by owner</h2></div><div class="card-b">
              ${(s.owners || []).length ? `<div class="bars">${s.owners.map(([o, k]) => `<div class="bar-row"><div class="lab">${esc(o)}</div><div class="track"><div class="fill" style="width:${(k / Math.max(...s.owners.map((x) => x[1]))) * 100}%"></div></div><div class="v">${k}</div></div>`).join("")}</div>`
                : `<div class="muted">Nothing waiting.</div>`}
            </div></div>
          </div>`;
      }
      view.innerHTML = head("Overview", st.company_name ? `Accounts payable · ${esc(st.company_name)}` : "Accounts payable") + setupCard + body;
      paintIcons(view);
      $("#ov-up") && ($("#ov-up").onclick = () => openUpload());
      $$("tr.click", view).forEach((tr) => (tr.onclick = () => (location.hash = `#/invoices/${tr.dataset.id}`)));
    };
    await load();
    const iv = setInterval(() => { if (STATS.processing || document.visibilityState === "visible") load().catch(() => {}); }, 4000);
    onLeave(() => clearInterval(iv));
  }

  // ================================================================ INVOICES
  async function viewInvoices(view, params) {
    let status = params.get("status") || "ALL", q = params.get("q") || "";
    $("#global-q").value = q;
    view.innerHTML = head("Invoices", "Every invoice received, with its current status.",
      `<a class="btn" id="exp" href="#">${ic("download")}Export CSV</a><button class="btn primary" id="up2">${ic("upload")}Upload</button>`) + `
      <div class="card"><div class="tabs" id="st-tabs"></div>
        <div class="toolbar"><div class="search-in"><span data-icon="search"></span><input type="search" id="q" placeholder="Search vendor, invoice #, PO…" value="${esc(q)}"></div><span class="muted" id="cnt"></span></div>
        <div class="tbl-wrap" id="list"></div></div>`;
    $("#up2").onclick = () => openUpload();
    let all = [];
    const tabs = [["ALL", "All"], ["PROCESSING", "Processing"], ["NEEDS_REVIEW", "Needs review"], ["ON_HOLD", "On hold"], ["APPROVED", "Approved"], ["REJECTED", "Rejected"]];
    const match = (r, s) => s === "ALL" || (s === "PROCESSING" ? ["queued", "running"].includes(r.state) : r.state === "done" && r.final_status === s);
    const render = () => {
      $("#st-tabs").innerHTML = tabs.map(([k, l]) => `<button class="${status === k ? "on" : ""}" data-s="${k}">${l}<span class="n">${all.filter((r) => match(r, k)).length}</span></button>`).join("");
      $$("#st-tabs button").forEach((b) => (b.onclick = () => { status = b.dataset.s; render(); }));
      const rows = all.filter((r) => match(r, status)).filter((r) => !q || [r.vendor_name, r.invoice_number, r.po_number, r.filename, r.headline, r.total].join(" ").toLowerCase().includes(q.toLowerCase()));
      $("#cnt").textContent = `${rows.length} invoice${rows.length === 1 ? "" : "s"}`;
      $("#exp").href = `/api/runs/export.csv?status=${status}&q=${encodeURIComponent(q)}`;
      $("#list").innerHTML = rows.length ? `<table class="t"><thead><tr><th>Status</th><th>Vendor</th><th>Invoice #</th><th>Invoice date</th><th>Due</th><th>PO</th><th class="num">Amount</th><th>Exception</th><th>Received</th></tr></thead><tbody>
        ${rows.map((r) => `<tr class="click" data-id="${esc(r.id)}" tabindex="0">
          <td>${badge(r.final_status, r.state)}</td>
          <td>${r.state === "done" || r.vendor_name ? `<div class="cell-strong">${esc(r.vendor_name || "Unknown vendor")}</div><div class="sub">${esc(r.filename)}</div>`
            : `<div class="cell-strong" style="font-weight:500">${esc(r.filename)}</div><div class="sub">${r.state === "queued" ? "Waiting in queue" : r.state === "error" ? "Failed" : "Reading document…"}</div>`}</td>
          <td class="mono">${esc(r.invoice_number || "—")}</td>
          <td class="nowrap">${dateFmt(r.invoice_date)}</td><td class="nowrap">${dateFmt(r.due_date)}</td>
          <td class="mono">${esc(r.po_number || "—")}</td>
          <td class="num cell-strong">${money(r.total, r.currency)}</td>
          <td class="t2" style="max-width:240px">${r.state === "done" && r.final_status !== "APPROVED" ? esc(r.headline || "") : r.state === "error" ? esc(r.error || "") : ""}</td>
          <td class="nowrap muted">${dtFmt(r.created_at)}</td></tr>`).join("")}</tbody></table>`
        : (all.length ? emptyState("search", "No invoices match", "Try another status or search term.") :
          emptyState("file", "No invoices yet", "Upload PDF invoices, or save them into the watched mailbox folder.", `<button class="btn primary" id="up3">${ic("upload")}Upload invoices</button>`));
      paintIcons($("#list"));
      $("#up3") && ($("#up3").onclick = () => openUpload());
      $$("#list tr.click").forEach((tr) => { tr.onclick = () => (location.hash = `#/invoices/${tr.dataset.id}`); tr.onkeydown = (e) => e.key === "Enter" && tr.click(); });
    };
    $("#q").oninput = (e) => { q = e.target.value; render(); };
    const load = async () => { all = await api("/api/runs"); render(); };
    await load();
    const iv = setInterval(() => { if (all.some((r) => r.state !== "done" && r.state !== "error") || STATS.processing) load().catch(() => {}); }, 2000);
    onLeave(() => clearInterval(iv));
  }

  // ================================================================ INVOICE DETAIL (live)
  const stIco = { pending: "dot", running: "spin", passed: "check", warning: "warn", failed: "x" };
  const ckIco = { pass: "checkc", warn: "warn", fail: "xc", info: "info" };

  async function viewInvoice(view, id) {
    const S = { id, stages: {}, order: [], result: null, run: null, done: false, error: null, tab: null, userTab: false, page: 1, zoom: 100, collapsed: new Set(), t0: Date.now() };
    view.innerHTML = `<div id="ih"></div><div class="split"><div class="card viewer" id="vw"></div><div class="card" id="panel"><div class="tabs" id="ptabs"></div><div class="card-b" id="pbody"></div></div></div>`;

    const R = () => S.run || {};
    const fields = () => S.result?.fields || S.stages.extract?.data?.fields || {};
    const pages = () => R().pages || S.stages.read?.data?.pages || 1;

    const renderHead = () => {
      const r = R(), f = fields(), res = S.result;
      const status = S.done ? (res?.final_status || r.final_status) : null;
      const open = S.done && ["NEEDS_REVIEW", "ON_HOLD"].includes(status);
      $("#ih").innerHTML = `
        <div class="crumbs"><a href="#/invoices">Invoices</a> / <span class="mono">${esc(f.invoice_number || r.filename || S.filename || id)}</span></div>
        <div class="inv-head">
          <div><div class="inv-title"><h1>${esc(res?.vendor?.name || f.vendor_name || r.vendor_name || "Reading invoice…")}</h1>${S.error ? badge(null, "error") : S.done ? badge(status) : badge(null, "running")}</div>
            <div class="inv-meta"><span>Invoice <b class="mono">${esc(f.invoice_number || "—")}</b></span><span>Dated ${dateFmt(f.invoice_date)}</span><span>PO <b class="mono">${esc(res?.po?.po_number || f.po_number || "—")}</b></span><span class="muted">${esc(r.filename || S.filename || "")}</span></div></div>
          <div class="actions">
            <div class="inv-amt" style="margin-right:8px"><div class="a">${money(f.total, f.currency)}</div><div class="c">${res?.payment_due ? `Due ${dateFmt(res.payment_due)}` : "&nbsp;"}</div></div>
            ${open ? `<button class="btn danger" id="act-rej">${ic("x")}Reject</button><button class="btn success" id="act-app">${ic("check")}${status === "ON_HOLD" ? "Release" : "Approve"}</button>` : ""}
            <a class="btn" href="/api/runs/${id}/pdf" target="_blank" rel="noopener" data-tip="Open original PDF">${ic("ext")}</a>
          </div></div>`;
      const reviewRun = () => ({ ...R(), final_status: status, vendor_name: res?.vendor?.name || f.vendor_name, invoice_number: f.invoice_number, total: f.total, currency: f.currency, id });
      $("#act-app") && ($("#act-app").onclick = () => openReview(reviewRun(), "approve", loadFull));
      $("#act-rej") && ($("#act-rej").onclick = () => openReview(reviewRun(), "reject", loadFull));
    };

    const renderViewer = () => {
      const n = pages();
      $("#vw").innerHTML = `<div class="viewer-tools">
          <button class="icon-btn" id="pg-prev" ${S.page <= 1 ? "disabled" : ""} aria-label="Previous page">${ic("left")}</button>
          <span class="pg">Page ${S.page} of ${n}</span>
          <button class="icon-btn" id="pg-next" ${S.page >= n ? "disabled" : ""} aria-label="Next page">${ic("right")}</button>
          <span style="flex:1"></span>
          <button class="icon-btn" id="z-out" aria-label="Zoom out">${ic("zout")}</button><span class="pg">${S.zoom}%</span><button class="icon-btn" id="z-in" aria-label="Zoom in">${ic("zin")}</button>
          <a class="btn ghost sm" href="/api/runs/${id}/pdf" download>${ic("download")}Download</a></div>
        <div class="viewer-body"><img src="/api/runs/${id}/page/${S.page}.png?dpi=150" alt="Invoice page ${S.page}" style="width:${S.zoom}%"></div>`;
      $("#pg-prev").onclick = () => { S.page--; renderViewer(); }; $("#pg-next").onclick = () => { S.page++; renderViewer(); };
      $("#z-in").onclick = () => { S.zoom = Math.min(200, S.zoom + 20); renderViewer(); }; $("#z-out").onclick = () => { S.zoom = Math.max(60, S.zoom - 20); renderViewer(); };
    };

    const logHtml = () => {
      const keys = S.order;
      return `<ol class="steps-log">${keys.map((k) => {
        const s = S.stages[k], open = s.status !== "pending" && !S.collapsed.has(k);
        return `<li class="sl ${s.status}" data-k="${k}"><div class="sl-ico">${ic(stIco[s.status] || "dot")}</div>
          <div class="sl-row"><span class="sl-t">${esc(s.title)}</span><span class="sl-ms">${s.status === "running" ? "running…" : s.compute_ms != null ? s.compute_ms + " ms" : ""}</span></div>
          <div class="sl-s">${esc(s.summary || s.description)}</div>
          ${open && s.checks?.length ? `<ul class="checks">${s.checks.map((c) => `<li class="${c.status}">${ic(ckIco[c.status] || "info")}<div><span class="cl">${esc(c.label)}</span>${c.detail ? ` <span class="cd">— ${esc(c.detail)}</span>` : ""}</div></li>`).join("")}</ul>` : ""}</li>`;
      }).join("")}</ol>`;
    };
    const progressPct = () => { const k = S.order; return k.length ? (k.filter((x) => ["passed", "warning", "failed"].includes(S.stages[x].status)).length / k.length) * 100 : 0; };

    const TABS = [["summary", "Summary"], ["lines", "Line match"], ["log", "Processing"], ["activity", "Activity"], ["text", "Text"]];
    const renderPanel = () => {
      if (!S.tab) S.tab = "summary";
      $("#ptabs").innerHTML = TABS.map(([k, l]) => `<button class="${S.tab === k ? "on" : ""}" data-t="${k}">${l}</button>`).join("");
      $$("#ptabs button").forEach((b) => (b.onclick = () => { S.tab = b.dataset.t; S.userTab = true; renderPanel(); }));
      const body = $("#pbody");
      if (S.tab === "summary") body.innerHTML = summaryHtml();
      else if (S.tab === "lines") body.innerHTML = linesHtml();
      else if (S.tab === "log") body.innerHTML = `<div class="progress"><div style="width:${progressPct()}%"></div></div>` + logHtml() + (S.done ? `<div class="muted" style="font-size:12.5px">Processed in ${secs(R().duration_ms)} · extraction: ${R().extractor === "claude" ? "Claude" : "on-device parser"}</div>` : "");
      else if (S.tab === "activity") body.innerHTML = activityHtml();
      else if (S.tab === "text") { const d = S.stages.read?.data; body.innerHTML = d?.text ? `<div class="muted" style="margin-bottom:8px">${d.method === "ocr" ? `OCR output · confidence ${(d.ocr_confidence * 100).toFixed(1)}%` : "PDF text layer"} · ${d.pages} page(s)</div><pre class="rawtext">${esc(d.text)}</pre>` : `<div class="muted">Not read yet.</div>`; }
      paintIcons(body);
      $$(".sl-row", body).forEach((row) => (row.onclick = () => { const k = row.parentElement.dataset.k; S.collapsed.has(k) ? S.collapsed.delete(k) : S.collapsed.add(k); renderPanel(); }));
      const ce = $("#copy-mail", body);
      if (ce) ce.onclick = () => { const m = S.result.vendor_message; navigator.clipboard?.writeText(`To: ${m.to}\nSubject: ${m.subject}\n\n${m.body}`); toast("Email copied"); };
    };

    const summaryHtml = () => {
      if (S.error) return `<div class="decision REJECTED"><div class="dt">${ic("xc")}Processing failed</div><div class="dd">${esc(S.error)}</div></div>`;
      if (!S.done) {
        const cur = S.order.map((k) => S.stages[k]).find((s) => s.status === "running");
        return `<div class="decision PROCESSING"><div class="dt">${ic("spin")}Processing${cur ? ` — ${esc(cur.title.toLowerCase())}` : "…"}</div>
          <div class="dd">Reading the document and checking it against the vendor master, PO register and payment history.</div>
          <div class="progress" style="margin-top:12px"><div style="width:${progressPct()}%"></div></div></div>` + logHtml();
      }
      const res = S.result, f = res.fields || {}, st = res.final_status, m = STATUS[st] || STATUS[res.decision];
      const rv = res.review;
      const reasons = res.reasons || [];
      const b = f.bank || {};
      const kv = (l, v) => `<div><span>${l}</span><b>${v ?? "—"}</b></div>`;
      return `
        <div class="decision ${st}"><div class="dt">${ic(m.icon)}${m.label}${rv ? ` <span class="muted" style="font-weight:500;font-size:12.5px">by ${esc(rv.reviewer)} · system said ${esc(STATUS[res.decision].label.toLowerCase())}</span>` : ""}</div>
          <div class="dd">${esc(st === "APPROVED" && !rv ? "Every check passed — approved without manual touch." : rv ? `“${rv.note}”` : res.headline)}</div>
          <div class="next"><b>${rv ? "Outcome" : "Next step"}</b>${esc(rv ? (rv.action === "approve" ? `Approved by ${rv.reviewer} on ${dtFmt(rv.at)}; scheduled for payment on ${res.pay_on || res.payment_due || "the due date"}.` : `Rejected by ${rv.reviewer} on ${dtFmt(rv.at)}.`) : res.next_action)}${res.queue && !rv ? `<div class="muted" style="margin-top:3px">Owner: ${esc(res.queue)}</div>` : ""}</div>
          ${res.internal_note ? `<div class="alert crit">${ic("shield")}<div>${esc(res.internal_note)}</div></div>` : ""}
        </div>
        ${res.ai_summary ? `<div class="alert info">${ic("sparkle")}<div>${esc(res.ai_summary)}</div></div>` : ""}
        ${reasons.length ? `<div class="sec-title">Exceptions (${reasons.length})</div>${reasons.map((r) => `<div class="exc ${r.outcome}">${ic(r.outcome === "NEEDS_REVIEW" ? "warn" : "xc")}<div><div class="et">${esc(r.title)} <span class="badge ${r.outcome}" style="height:20px;margin-left:4px"><span class="dot"></span>${STATUS[r.outcome].label}</span></div><div class="em">${esc(r.message)}</div></div></div>`).join("")}` : ""}
        ${(res.notes || []).length ? `<div class="sec-title">Notes</div>${res.notes.map((n) => `<div class="exc note">${ic("info")}<div class="em">${esc(n)}</div></div>`).join("")}` : ""}
        <div class="sec-title">Invoice details</div>
        <div class="kv">
          ${kv("Vendor", esc(res.vendor?.name || f.vendor_name))}${kv("Vendor ID", res.vendor ? `<span class="mono">${esc(res.vendor.vendor_id)}</span>` : "—")}${kv("Invoice number", f.invoice_number ? `<span class="mono">${esc(f.invoice_number)}</span>` : `<span class="bad">missing</span>`)}
          ${kv("Invoice date", f.invoice_date ? dateFmt(f.invoice_date) : `<span class="bad">missing</span>`)}${kv("Due date", dateFmt(res.payment_due))}${kv("Terms", esc(f.payment_terms))}
          ${kv("Purchase order", res.po ? `<span class="mono">${esc(res.po.po_number)}</span>${res.po_how === "inferred" ? ' <span class="chip">identified</span>' : ""}` : esc(f.po_number))}${kv("PO owner", res.po ? esc(`${res.po.requester} · ${res.po.department}`) : "—")}${kv("Currency", esc(f.currency))}
          ${kv("Subtotal", money(f.subtotal, f.currency))}${kv("Tax", money(f.tax_amount, f.currency))}${kv("Total", `<b>${money(f.total, f.currency)}</b>`)}
          ${kv("Remit-to on invoice", b.account_number ? esc(`${b.bank_name || ""} …${String(b.account_number).slice(-4)}`) : "Not printed")}${kv("Read via", res.read_method === "ocr" ? "OCR (scanned)" : "Text layer")}${kv("Received via", R().source === "inbox" ? "Mailbox folder" : "Upload")}
        </div>
        ${res.vendor_message ? `<div class="sec-title">Drafted email to vendor</div><div class="mail"><div class="mail-h"><span><b>To</b> ${esc(res.vendor_message.to)}</span><span><b>Subject</b> ${esc(res.vendor_message.subject)}</span></div>
          <pre>${esc(res.vendor_message.body)}</pre><div class="mail-f"><button class="btn sm" id="copy-mail">${ic("copy")}Copy</button>
          <a class="btn sm" href="mailto:${encodeURIComponent((res.vendor_message.to || "").split(" ")[0])}?subject=${encodeURIComponent(res.vendor_message.subject)}&body=${encodeURIComponent(res.vendor_message.body)}">${ic("mail")}Open in email</a></div></div>` : ""}`;
    };

    const linesHtml = () => {
      const po = S.stages.po_match?.data || {}, f = fields(), cur = f.currency;
      if (!S.stages.po_match || S.stages.po_match.status === "pending" || S.stages.po_match.status === "running") return `<div class="muted">Line matching appears once the purchase-order stage finishes.</div>`;
      const items = f.line_items || [];
      const cand = po.candidates || [];
      return `
        ${po.po ? `<div class="kv" style="margin-bottom:14px">
          <div><span>Purchase order</span><b class="mono">${esc(po.po.po_number)}</b> ${po.how === "inferred" ? `<span class="chip">identified · ${(po.confidence * 100).toFixed(0)}%</span>` : `<span class="chip">printed on invoice</span>`}</div>
          <div><span>Description</span><b>${esc(po.po.description)}</b></div><div><span>Owner</span><b>${esc(po.po.requester)} · ${esc(po.po.department)}</b></div>
          <div><span>PO value</span><b>${money(po.po.total_amount, po.po.currency)}</b></div><div><span>Invoiced before</span><b>${money(po.po.invoiced_amount, po.po.currency)}</b></div><div><span>Remaining before</span><b>${money(po.po.remaining_amount, po.po.currency)}</b></div>
        </div>` : `<div class="alert crit" style="margin:0 0 14px">${ic("warn")}<div>No purchase order matched this invoice.</div></div>`}
        ${cand.length ? `<div class="sec-title" style="margin-top:4px">PO candidates considered</div><div class="tbl-wrap"><table class="t compact"><thead><tr><th>PO</th><th>Description</th><th class="num">Lines</th><th class="num">Amount</th><th class="num">Score</th></tr></thead><tbody>
          ${cand.map((c) => `<tr><td class="mono">${esc(c.po_number)}</td><td>${esc(c.description)}</td><td class="num">${(c.line_score * 100).toFixed(0)}%</td><td class="num">${(c.amount_score * 100).toFixed(0)}%</td><td class="num"><b>${(c.score * 100).toFixed(0)}%</b></td></tr>`).join("")}</tbody></table></div>
          <div class="muted" style="font-size:12px;margin:6px 0 4px">Score = 60% line-item similarity + 40% amount closeness. Needs a clear winner (10-point lead).</div>` : ""}
        <div class="sec-title">Invoice lines</div>
        <div class="tbl-wrap"><table class="t compact"><thead><tr><th>Invoice line</th><th>Matched PO line</th><th class="num">Qty · left</th><th class="num">Unit · PO</th><th class="num">Amount</th></tr></thead><tbody>
          ${(po.lines || items.map((li) => ({ invoice: li }))).map((m) => { const li = m.invoice, pl = m.po_line;
            const varied = pl && Math.abs(m.price_variance) > 0.005;
            return `<tr><td><div class="cell-strong">${esc(li.description)}</div>${li.sku ? `<div class="sub mono">${esc(li.sku)}</div>` : ""}</td>
              <td>${pl ? `<span class="mono">#${pl.line_no}</span> ${esc(pl.description)}` : m.bundle_lines ? `<span class="chip">Bundle of ${m.bundle_lines.length}</span>${m.bundle_lines.map((x) => `<div class="sub"><span class="mono">#${x.line_no}</span> ${esc(x.description)} × ${x.qty}</div>`).join("")}` : po.po ? `<span class="bad">Not on PO</span>` : "—"}</td>
              <td class="num"><span class="${m.over_qty ? "bad" : ""}">${li.quantity ?? "—"}</span>${pl ? `<div class="sub">${m.remaining_qty} of ${pl.quantity} left</div>` : m.bundle_lines ? `<div class="sub">all open</div>` : ""}</td>
              <td class="num"><span class="${varied ? "warn" : ""}">${money(li.unit_price, cur)}</span>${pl ? `<div class="sub">PO ${money(pl.unit_price, po.po?.currency)}</div>` : m.bundle_value ? `<div class="sub">PO ${money(m.bundle_value, po.po?.currency)}</div>` : ""}</td>
              <td class="num">${money(li.amount, cur)}</td></tr>`; }).join("") || `<tr><td colspan="5" class="muted">No line items found on the invoice.</td></tr>`}
        </tbody></table></div>
        ${po.po ? `<div class="kv" style="margin-top:14px"><div><span>Billed (net)</span><b>${money(po.net, cur)}</b></div><div><span>At PO prices</span><b>${money(po.expected, cur)}</b></div>
          <div><span>Price variance</span><b class="${po.within_tolerance ? "" : "warn"}">${money(po.variance, cur)} (${po.variance_pct >= 0 ? "+" : ""}${po.variance_pct}%) · ${po.within_tolerance ? "within tolerance" : "over tolerance"}</b></div></div>` : ""}`;
    };

    const activityHtml = () => {
      const a = (S.run?.audit || []).slice().reverse();
      const rec = `<div class="exc note">${ic("upload")}<div><div class="et">Received</div><div class="em">${esc(R().source === "inbox" ? "Picked up from the mailbox folder" : "Uploaded")} · ${dtFmt(R().created_at)} · ${esc(R().filename || "")}</div></div></div>`;
      return a.map((x) => `<div class="exc note">${ic(x.actor === "System" ? "sparkle" : "users")}<div><div class="et">${esc(x.action)} <span class="muted" style="font-weight:400">· ${esc(x.actor)} · ${dtFmt(x.ts)}</span></div>${x.note ? `<div class="em">${esc(x.note)}</div>` : ""}</div></div>`).join("") + rec;
    };

    const renderAll = () => { renderHead(); renderPanel(); paintIcons(view); };
    const loadFull = async () => {
      S.run = await api(`/api/runs/${id}`);
      if (S.run.result) { S.result = S.run.result; S.done = true; }
      if (S.run.error) { S.error = S.run.error; S.done = true; }
      (S.run.trace || []).forEach((s) => { S.stages[s.key] = s; if (!S.order.includes(s.key)) S.order.push(s.key); });
      renderAll(); renderViewer(); paintIcons(view);
    };

    S.run = await api(`/api/runs/${id}`);
    renderHead(); renderViewer(); renderPanel(); paintIcons(view);
    const es = new EventSource(`/api/runs/${id}/events`);
    onLeave(() => es.close());
    es.onmessage = async (e) => {
      const ev = JSON.parse(e.data);
      if (ev.type === "run_queued") {
        S.filename = ev.filename; (ev.stages || []).forEach((s) => { S.stages[s.key] = s; if (!S.order.includes(s.key)) S.order.push(s.key); });
        renderAll();
      } else if (ev.type === "stage") {
        S.stages[ev.stage.key] = ev.stage; if (!S.order.includes(ev.stage.key)) S.order.push(ev.stage.key);
        if (ev.stage.key === "read" && ev.stage.status !== "running") renderViewer();
        if (["extract", "po_match", "read"].includes(ev.stage.key) && ev.stage.status !== "running") renderHead();
        renderPanel();
      } else if (ev.type === "run_completed") {
        S.result = ev.result; S.done = true;
        if (!S.userTab) S.tab = "summary";
        await loadFull(); poll();
      } else if (ev.type === "run_error") { S.error = ev.error; S.done = true; renderAll(); }
    };
    es.addEventListener("end", () => { es.close(); if (!S.done) loadFull().catch(() => {}); });
    es.onerror = () => { es.close(); setTimeout(() => loadFull().catch(() => {}), 600); };
  }

  // ================================================================ EXCEPTIONS
  async function viewExceptions(view) {
    const runs = await api("/api/runs?status=OPEN");
    const age = (iso) => Math.max(0, Math.floor((Date.now() - new Date(iso)) / 86400000));
    view.innerHTML = head("Exceptions", "Invoices the system would not pay on its own. Oldest first — each one says why and who owns it.") + `
      <div class="card">${runs.length ? `<div class="tbl-wrap"><table class="t"><thead><tr><th>Age</th><th>Status</th><th>Vendor</th><th>Invoice #</th><th class="num">Amount</th><th>Exception</th><th>Owner</th><th></th></tr></thead><tbody>
        ${runs.slice().reverse().map((r) => `<tr class="click" data-id="${esc(r.id)}">
          <td class="nowrap">${age(r.created_at) ? age(r.created_at) + " d" : "Today"}</td><td>${badge(r.final_status)}</td>
          <td><div class="cell-strong">${esc(r.vendor_name || "Unknown")}</div><div class="sub mono">${esc(r.po_number || "")}</div></td>
          <td class="mono">${esc(r.invoice_number || "—")}</td><td class="num cell-strong">${money(r.total, r.currency)}</td>
          <td>${esc(r.headline)}</td><td class="t2">${esc(r.queue || "AP team")}</td>
          <td class="num"><a class="btn sm" href="#/invoices/${esc(r.id)}">Review</a></td></tr>`).join("")}</tbody></table></div>`
        : emptyState("checkc", "No open exceptions", "Every processed invoice has been approved, rejected or resolved.")}</div>`;
    $$("tr.click", view).forEach((tr) => (tr.onclick = (e) => { if (!e.target.closest("a")) location.hash = `#/invoices/${tr.dataset.id}`; }));
  }

  // ================================================================ PAYMENTS
  async function viewPayments(view) {
    const rows = await api("/api/payments");
    const total = rows.reduce((a, r) => a + (r.total || 0), 0);
    view.innerHTML = head("Payments", "Approved invoices scheduled for payment. Payment always goes to the verified bank account in the vendor master.",
      rows.length ? `<a class="btn" href="/api/payments/export.csv">${ic("download")}Export payment file</a>` : "") + `
      ${rows.length ? `<div class="kpis" style="grid-template-columns:repeat(3,minmax(0,1fr));margin-bottom:16px">
        <div class="card kpi"><div class="l">${ic("bank")}Scheduled</div><div class="v">${money(total)}</div><div class="s">${rows.length} invoice${rows.length === 1 ? "" : "s"}</div></div>
        <div class="card kpi"><div class="l">${ic("clock")}Next payment date</div><div class="v">${dateFmt(rows.map((r) => r.pay_on).sort()[0])}</div><div class="s">earliest scheduled date</div></div>
        <div class="card kpi"><div class="l">${ic("users")}Vendors</div><div class="v">${new Set(rows.map((r) => r.vendor_id)).size}</div><div class="s">in this payment run</div></div></div>` : ""}
      <div class="card">${rows.length ? `<div class="tbl-wrap"><table class="t"><thead><tr><th>Pay on</th><th>Vendor</th><th>Invoice #</th><th>PO</th><th class="num">Amount</th><th>Pay to</th><th>Approved by</th></tr></thead><tbody>
        ${rows.slice().sort((a, b) => (a.pay_on || "").localeCompare(b.pay_on || "")).map((r) => `<tr class="click" data-id="${esc(r.run_id)}">
          <td class="nowrap cell-strong">${dateFmt(r.pay_on)}</td><td>${esc(r.vendor_name)}</td><td class="mono">${esc(r.invoice_number)}</td><td class="mono">${esc(r.po_number || "—")}</td>
          <td class="num cell-strong">${money(r.total, r.currency)}</td><td class="mono">ACH …${esc(r.bank_last4 || "")}</td><td class="t2">${esc(r.approved_by)}</td></tr>`).join("")}</tbody></table></div>`
        : emptyState("bank", "Nothing scheduled yet", "Approved invoices appear here with their payment date.")}</div>`;
    $$("tr.click", view).forEach((tr) => (tr.onclick = () => tr.dataset.id && (location.hash = `#/invoices/${tr.dataset.id}`)));
  }

  // ================================================================ VENDORS
  async function viewVendors(view) {
    let q = "";
    const draw = async () => {
      const vs = await api("/api/vendors");
      view.innerHTML = head("Vendors", "Vendor master: who may be paid, their verified bank account and registered email domain.",
        `<button class="btn" id="v-imp">${ic("upload")}Import CSV</button><button class="btn primary" id="v-add">${ic("plus")}Add vendor</button>`) + `
        <div class="card"><div class="toolbar"><div class="search-in"><span data-icon="search"></span><input type="search" id="vq" placeholder="Search vendors…" value="${esc(q)}"></div><span class="muted">${vs.length} vendors</span></div>
        <div class="tbl-wrap" id="vt"></div></div>`;
      const render = () => {
        const rows = vs.filter((v) => !q || [v.name, v.vendor_id, v.email_domain, v.aliases].join(" ").toLowerCase().includes(q.toLowerCase()));
        $("#vt").innerHTML = vs.length ? `<table class="t"><thead><tr><th>Vendor</th><th>Status</th><th>Tax ID</th><th>Email domain</th><th>Verified phone</th><th>Bank on file</th><th>Terms</th><th class="num">Invoices</th><th></th></tr></thead><tbody>
          ${rows.map((v) => `<tr><td style="min-width:220px"><div class="cell-strong">${esc(v.name)}</div><div class="sub mono">${esc(v.vendor_id)}</div></td><td>${vBadge(v.status)}</td>
            <td class="mono">${esc(v.tax_id || "—")}</td><td class="mono">${esc(v.email_domain || "—")}</td><td class="nowrap">${esc(v.contact_phone || "—")}</td>
            <td style="min-width:150px">${esc(v.bank_name || "—")}<div class="sub mono">…${esc(v.account_last4)}</div></td><td class="nowrap">Net ${v.payment_terms_days}</td>
            <td class="num">${v.invoice_count}<div class="sub">${v.invoice_value ? compact(v.invoice_value) : ""}</div></td>
            <td><select data-v="${esc(v.vendor_id)}" style="min-width:150px" aria-label="Vendor status">${["approved", "pending_onboarding", "blocked", "inactive"].map((s) => `<option value="${s}" ${v.status === s ? "selected" : ""}>${{ approved: "Approved", pending_onboarding: "Onboarding", blocked: "Blocked", inactive: "Inactive" }[s]}</option>`).join("")}</select></td></tr>`).join("")}</tbody></table>`
          : emptyState("users", "No vendors yet", "Import your vendor master as CSV, or add vendors one by one.", `<button class="btn primary" id="v-imp2">${ic("upload")}Import CSV</button>`);
        paintIcons($("#vt"));
        $$("select[data-v]").forEach((s) => (s.onchange = async () => { try { await api(`/api/vendors/${encodeURIComponent(s.dataset.v)}`, { method: "PATCH", body: JSON.stringify({ status: s.value }) }); toast("Vendor status updated"); } catch (e) { toast(e.message); } }));
        $("#v-imp2") && ($("#v-imp2").onclick = () => openImport("vendors", draw));
      };
      $("#vq").oninput = (e) => { q = e.target.value; render(); };
      $("#v-imp").onclick = () => openImport("vendors", draw);
      $("#v-add").onclick = () => vendorDialog(draw);
      render(); paintIcons(view);
    };
    await draw();
  }

  function vendorDialog(after) {
    const f = (id, label, ph = "", type = "text") => `<label class="field"><span>${label}</span><input type="${type}" id="nv-${id}" placeholder="${ph}"></label>`;
    openDialog(`
      <div class="dlg-h"><div><h2>Add vendor</h2><p>Only add bank details you have verified independently.</p></div><button class="icon-btn" data-close>${ic("close")}</button></div>
      <div class="dlg-b"><div class="form-grid">
        ${f("vendor_id", "Vendor ID", "V-2001")}${f("name", "Legal name", "Acme Supplies Inc.")}
        ${f("contact_email", "Billing email", "billing@acme.com", "email")}${f("contact_phone", "Verified phone", "+1 …")}
        ${f("tax_id", "Tax ID", "12-3456789")}${f("payment_terms_days", "Payment terms (days)", "30", "number")}
        ${f("bank_name", "Bank", "")}${f("routing_number", "Routing number", "")}${f("account_number", "Account number", "")}
        <label class="field"><span>Status</span><select id="nv-status"><option value="approved">Approved</option><option value="pending_onboarding">Onboarding</option><option value="blocked">Blocked</option></select></label>
      </div><div id="nv-err"></div></div>
      <div class="dlg-f"><button class="btn" data-close>Cancel</button><button class="btn primary" id="nv-go">Save vendor</button></div>`);
    $("#nv-go").onclick = async () => {
      const v = {}; ["vendor_id", "name", "contact_email", "contact_phone", "tax_id", "payment_terms_days", "bank_name", "routing_number", "account_number", "status"].forEach((k) => (v[k] = $("#nv-" + k).value.trim()));
      try { await api("/api/vendors", { method: "POST", body: JSON.stringify(v) }); dlg.close(); toast("Vendor saved"); poll(); after(); }
      catch (e) { $("#nv-err").innerHTML = `<div class="result err">${esc(e.message)}</div>`; }
    };
  }

  // ================================================================ PURCHASE ORDERS
  async function viewPOs(view) {
    let q = "", openRow = null;
    const draw = async () => {
      const pos = await api("/api/purchase-orders");
      view.innerHTML = head("Purchase orders", "Open orders with agreed prices. Each approved invoice consumes the PO; split invoices can never bill more than was ordered.",
        `<button class="btn" id="p-imp">${ic("upload")}Import CSV</button>`) + `
        <div class="card"><div class="toolbar"><div class="search-in"><span data-icon="search"></span><input type="search" id="pq" placeholder="Search PO, vendor, owner…"></div><span class="muted">${pos.length} purchase orders</span></div><div class="tbl-wrap" id="pt"></div></div>`;
      const render = () => {
        const rows = pos.filter((p) => !q || [p.po_number, p.vendor_name, p.description, p.requester, p.department].join(" ").toLowerCase().includes(q.toLowerCase()));
        $("#pt").innerHTML = pos.length ? `<table class="t"><thead><tr><th>PO</th><th>Vendor</th><th>Description</th><th>Owner</th><th>Status</th><th class="num">Value</th><th style="min-width:170px">Consumed</th></tr></thead><tbody>
          ${rows.map((p) => { const pct = p.total_amount ? Math.min(100, (p.invoiced_amount / p.total_amount) * 100) : 0;
            return `<tr class="click" data-po="${esc(p.po_number)}"><td class="mono cell-strong">${esc(p.po_number)}<div class="sub">${dateFmt(p.issue_date)}</div></td><td>${esc(p.vendor_name)}</td>
              <td>${esc(p.description)}<div class="sub">${p.lines.length} line${p.lines.length === 1 ? "" : "s"}</div></td><td class="t2">${esc(p.requester)}<div class="sub">${esc(p.department)}</div></td>
              <td>${p.status === "open" ? `<span class="badge APPROVED"><span class="dot"></span>Open</span>` : `<span class="badge plain"><span class="dot"></span>${esc(p.status)}</span>`}</td>
              <td class="num cell-strong">${money(p.total_amount, p.currency)}</td>
              <td><div class="track" style="border-radius:4px" data-tip="${money(p.invoiced_amount, p.currency)} invoiced of ${money(p.total_amount, p.currency)}"><div class="fill" style="width:${pct}%;border-radius:4px"></div></div>
                <div class="sub">${money(p.invoiced_amount, p.currency)} invoiced · ${p.remaining_amount < -0.005 ? `${money(-p.remaining_amount, p.currency)} over` : `${money(p.remaining_amount, p.currency)} left`}</div></td></tr>
              ${openRow === p.po_number ? `<tr><td colspan="7" style="background:var(--panel-2)"><table class="t compact"><thead><tr><th>#</th><th>SKU</th><th>Description</th><th class="num">Qty</th><th class="num">Unit price</th><th class="num">Line value</th></tr></thead><tbody>
                ${p.lines.map((l) => `<tr><td>${l.line_no}</td><td class="mono">${esc(l.sku)}</td><td>${esc(l.description)}</td><td class="num">${l.quantity}</td><td class="num">${money(l.unit_price, p.currency)}</td><td class="num">${money(l.quantity * l.unit_price, p.currency)}</td></tr>`).join("")}</tbody></table></td></tr>` : ""}`; }).join("")}</tbody></table>`
          : emptyState("clipboard", "No purchase orders yet", "Import your PO register as CSV (one row per PO line). Import vendors first.", `<button class="btn primary" id="p-imp2">${ic("upload")}Import CSV</button>`);
        paintIcons($("#pt"));
        $$("#pt tr.click").forEach((tr) => (tr.onclick = () => { openRow = openRow === tr.dataset.po ? null : tr.dataset.po; render(); }));
        $("#p-imp2") && ($("#p-imp2").onclick = () => openImport("pos", draw));
      };
      $("#pq").oninput = (e) => { q = e.target.value; render(); };
      $("#p-imp").onclick = () => openImport("pos", draw);
      render(); paintIcons(view);
    };
    await draw();
  }

  // ================================================================ AUDIT
  async function viewAudit(view) {
    const rows = await api("/api/audit");
    view.innerHTML = head("Audit log", "Every decision, review and configuration change — who, what and when.") + `
      <div class="card">${rows.length ? `<div class="tbl-wrap"><table class="t"><thead><tr><th>Time</th><th>Actor</th><th>Action</th><th>Invoice</th><th>Details</th></tr></thead><tbody>
        ${rows.map((a) => `<tr><td class="nowrap muted">${dtFmt(a.ts)}</td><td class="nowrap">${esc(a.actor)}</td><td class="nowrap cell-strong">${esc(a.action)}</td>
          <td>${a.run_id ? `<a href="#/invoices/${esc(a.run_id)}">${esc(a.vendor_name || "")} ${esc(a.invoice_number || "")}</a>` : "—"}</td><td class="t2" style="max-width:520px">${esc(a.note)}</td></tr>`).join("")}</tbody></table></div>`
        : emptyState("history", "No activity yet", "Decisions, reviews and data imports are recorded here.")}</div>`;
  }

  // ================================================================ SETTINGS
  async function viewSettings(view, tab) {
    const [s, st] = await Promise.all([api("/api/settings"), api("/api/setup")]);
    const nav = [["company", "Company profile"], ["policy", "Approval policy"], ["import", "Data import"], ["data", "Data management"]];
    view.innerHTML = head("Settings", "") + `<div class="settings"><nav class="subnav">${nav.map(([k, l]) => `<a href="#/settings/${k}" class="${tab === k ? "on" : ""}">${l}</a>`).join("")}</nav><div id="sb"></div></div>`;
    const sb = $("#sb");
    if (tab === "company") {
      const co = s.company;
      sb.innerHTML = `<div class="card"><div class="card-h"><h2>Company profile</h2><button class="btn" id="co-edit">Edit</button></div><div class="card-b kv">
        <div><span>Legal entity name</span><b>${esc(co.legal_name || "Not set")}</b></div><div><span>AP email</span><b>${esc(co.ap_email || "Not set")}</b></div><div><span>Base currency</span><b>${esc(co.currency)}</b></div></div>
        <div class="card-b muted" style="border-top:1px solid var(--border);font-size:12.8px">Invoices must name this legal entity as the bill-to party; otherwise they are returned to the vendor. Drafted vendor emails are signed with it.</div></div>`;
      $("#co-edit").onclick = () => companyDialog(co, () => viewSettings(view, tab).then(() => paintIcons(view)));
    } else if (tab === "policy") {
      const p = s.policy;
      const rules = [
        ["price_tolerance_pct", "Price tolerance (%)", "Billed prices may exceed PO prices by at most this percentage…", "%"],
        ["price_tolerance_abs", "Price tolerance (amount)", "…and at most this amount per invoice. Both limits must hold.", "$"],
        ["auto_approve_limit", "Touchless approval limit", "Invoices above this amount always need a person to approve, even if everything matches.", "$"],
        ["po_inference_min_confidence", "PO identification confidence", "When no PO is printed, the best-matching open PO must score at least this (0–1) and clearly beat the next one.", ""],
        ["duplicate_number_similarity", "Duplicate number similarity", "Two invoices with the same amount whose numbers are at least this similar (0–1) are treated as a resubmission.", ""],
        ["max_tax_rate_pct", "Maximum plausible tax rate (%)", "Effective tax above this rate is flagged for review.", "%"],
        ["max_invoice_age_days", "Maximum invoice age (days)", "Older invoices are flagged as stale.", ""],
        ["min_extraction_confidence", "Minimum extraction confidence", "Below this (0–1), extractions that can't be traced back to the document go to review.", ""],
      ];
      sb.innerHTML = `<form class="card" id="pol"><div class="card-h"><div><h2>Approval policy</h2><div class="muted" style="font-size:12.5px">Decisions are made by these rules. Changes apply to the next invoice processed.</div></div><button class="btn primary" type="submit">Save changes</button></div>
        ${rules.map(([k, l, d]) => `<div class="rule"><div><h3>${l}</h3><p>${d}</p></div><input type="number" step="any" name="${k}" value="${p[k]}" aria-label="${l}"></div>`).join("")}
        <div class="rule"><div><h3>Touchless approval when the PO was identified</h3><p>If off, invoices without a printed PO always go to the requester, even when one PO clearly matches.</p></div>
          <select name="allow_auto_approve_inferred_po"><option value="1" ${p.allow_auto_approve_inferred_po ? "selected" : ""}>Allowed</option><option value="0" ${p.allow_auto_approve_inferred_po ? "" : "selected"}>Require confirmation</option></select></div>
        <div class="rule"><div><h3>Always enforced</h3><p>Bank details on an invoice are never trusted · blocked and unknown vendors are never paid · invoices without a number or date are returned · duplicates are rejected · the strictest outcome always wins.</p></div><div></div></div></form>`;
      $("#pol").onsubmit = async (e) => {
        e.preventDefault(); const fd = new FormData(e.target), out = {};
        rules.forEach(([k]) => (out[k] = parseFloat(fd.get(k)))); out.allow_auto_approve_inferred_po = fd.get("allow_auto_approve_inferred_po") === "1";
        try { await api("/api/settings/policy", { method: "PUT", body: JSON.stringify(out) }); toast("Approval policy saved"); } catch (err) { toast(err.message); }
      };
    } else if (tab === "import") {
      sb.innerHTML = `<div class="grid2">
        <div class="card import-card"><div class="card-h"><h2>Vendor master</h2><span class="muted">${st.vendors} vendors</span></div><div class="card-b">
          <p class="t2">Approved vendors, their verified bank accounts, registered email domain and payment terms.</p>
          <div class="cols">vendor_id, name, status, aliases, tax_id, email_domain, contact_email, contact_phone, bank_name, routing_number, account_number, payment_terms_days, currency</div>
          <div class="actions" style="margin-top:12px"><button class="btn primary" id="i-v">${ic("upload")}Import CSV</button><a class="btn ghost" href="#/vendors">View vendors</a></div></div></div>
        <div class="card import-card"><div class="card-h"><h2>PO register</h2><span class="muted">${st.purchase_orders} POs</span></div><div class="card-b">
          <p class="t2">Purchase orders with line items and agreed unit prices — one row per PO line.</p>
          <div class="cols">po_number, vendor_id, issue_date, po_description, department, requester, status, currency, line_no, sku, line_description, quantity, unit_price</div>
          <div class="actions" style="margin-top:12px"><button class="btn primary" id="i-p" ${st.vendors ? "" : "disabled"}>${ic("upload")}Import CSV</button><a class="btn ghost" href="#/purchase-orders">View POs</a></div></div></div></div>`;
      const again = () => viewSettings(view, tab).then(() => paintIcons(view));
      $("#i-v").onclick = () => openImport("vendors", again); $("#i-p").onclick = () => openImport("pos", again);
    } else {
      sb.innerHTML = `<div class="card"><div class="card-h"><h2>Export</h2></div><div class="card-b actions">
          <a class="btn" href="/api/runs/export.csv">${ic("download")}All invoices (CSV)</a><a class="btn" href="/api/payments/export.csv">${ic("download")}Payment run (CSV)</a></div></div>
        <div class="card gap"><div class="card-h"><h2>Danger zone</h2></div>
          <div class="rule"><div><h3>Delete all invoices</h3><p>Removes every processed invoice, scheduled payment and the audit log. Company profile, vendors and POs are kept.</p></div><button class="btn danger" id="d-inv">${ic("trash")}Delete invoices</button></div>
          <div class="rule"><div><h3>Delete everything</h3><p>Also removes the company profile, vendor master, PO register and approval policy — back to a fresh install.</p></div><button class="btn danger" id="d-all">${ic("trash")}Delete everything</button></div></div>`;
      const confirmDel = (title, url) => {
        openDialog(`<div class="dlg-h"><div><h2>${title}?</h2><p>This can't be undone. Type <b>DELETE</b> to confirm.</p></div><button class="icon-btn" data-close>${ic("close")}</button></div>
          <div class="dlg-b"><input type="text" id="del-c" autocomplete="off"><div id="del-e"></div></div>
          <div class="dlg-f"><button class="btn" data-close>Cancel</button><button class="btn danger solid" id="del-go">${title}</button></div>`);
        $("#del-go").onclick = async () => {
          if ($("#del-c").value !== "DELETE") { $("#del-e").innerHTML = `<div class="result err">Type DELETE to confirm.</div>`; return; }
          try { await api(url, { method: "POST" }); dlg.close(); toast("Deleted"); poll(); firstRoute = url.includes("all"); route(); } catch (e) { $("#del-e").innerHTML = `<div class="result err">${esc(e.message)}</div>`; }
        };
      };
      $("#d-inv").onclick = () => confirmDel("Delete all invoices", "/api/admin/delete-invoices");
      $("#d-all").onclick = () => confirmDel("Delete everything", "/api/admin/delete-all");
    }
    paintIcons(view);
  }

  poll().then(route);
})();
