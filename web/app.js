// Financial Manager site. Plain JavaScript, no build step.
// Every number comes from the Python API (see api/main.py).

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) =>
  String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const nf = new Intl.NumberFormat("ru-RU");
const kzt = (n) => nf.format(Math.round(n)) + " ₸";
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const monthName = (m) => MONTHS[+m.slice(5, 7) - 1] + " " + m.slice(0, 4);
const shortMonth = (m) => MONTHS[+m.slice(5, 7) - 1];
const COLORS = ["#0b7fa6", "#b7851a", "#17202f", "#6aa7bd", "#8a93a3", "#2a7d55"];

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : r.statusText);
  }
  return r.json();
}
const qs = (o) => "?" + new URLSearchParams(o).toString();
const debounce = (fn, ms = 200) => {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
};

let META;
const view = $("#view");

const PAGES = [
  ["overview", "Overview"],
  ["data", "Data"],
  ["core", "Functional core"],
  ["pipelines", "Pipelines"],
  ["frp", "Async and events"],
  ["reports", "Reports"],
  ["tests", "Tests"],
  ["about", "About"],
];

// ---------- small building blocks ----------
const options = (items, sel) =>
  items.map(([v, l]) => `<option value="${esc(v)}"${v === sel ? " selected" : ""}>${esc(l)}</option>`).join("");
const catOptions = (ids, sel) => options(ids.map((id) => [id, META.names[id]]), sel);
const accName = (id) => (META.accounts.find((a) => a.id === id) || {}).name || id;
const money = (n) => `<span class="${n > 0 ? "pos" : "neg"}">${n > 0 ? "+" : "−"}${kzt(Math.abs(n))}</span>`;
const note = (kind, text) => `<div class="note ${kind}" role="status">${text}</div>`;
const head = (title, lede) => `<h1>${title}</h1><p class="lede">${lede}</p>`;
const block = (title, hint, body) =>
  `<section class="block"><h2>${title}</h2><p class="hint">${hint}</p>${body}</section>`;

function table(cols, rows, empty = "Nothing matches yet.") {
  if (!rows.length) return `<p class="empty">${empty}</p>`;
  const th = cols.map((c) => `<th class="${c.num ? "num" : ""}">${esc(c.h)}</th>`).join("");
  const body = rows
    .map((r) => "<tr>" + cols.map((c) => `<td class="${c.num ? "num" : ""}">${c.f(r)}</td>`).join("") + "</tr>")
    .join("");
  return `<div class="table-wrap" tabindex="0"><table><thead><tr>${th}</tr></thead><tbody>${body}</tbody></table></div>`;
}
const TX_COLS = [
  { h: "Date", f: (t) => esc(t.ts) },
  { h: "Account", f: (t) => esc(accName(t.account_id)) },
  { h: "Category", f: (t) => esc(META.names[t.cat_id] || t.cat_id) },
  { h: "Note", f: (t) => esc(t.note) },
  { h: "Amount", num: true, f: (t) => money(t.amount) },
];

function bars(items, { max, limit } = {}) {
  const top = max || Math.max(...items.map((i) => i.value), 1);
  return `<div class="bars">${items
    .map((i) => {
      const cls = i.over ? "over" : i.warn ? "warn" : "";
      return `<div class="bar ${cls}"><span>${esc(i.label)}</span><div class="track"><div class="fill" style="width:${Math.max(0, (i.value / top) * 100)}%"></div></div><span>${i.text ?? kzt(i.value)}</span></div>`;
    })
    .join("")}</div>`;
}

function strip(accounts) {
  const total = accounts.reduce((s, a) => s + Math.max(a.current, 0), 0) || 1;
  const segs = accounts
    .map((a, i) => `<i style="width:${(Math.max(a.current, 0) / total) * 100}%;background:${COLORS[i % COLORS.length]}" title="${esc(a.name)}: ${kzt(a.current)}"></i>`)
    .join("");
  const legend = accounts
    .map((a, i) => `<span><span class="dot" style="background:${COLORS[i % COLORS.length]}"></span>${esc(a.name)} <b>${kzt(a.current)}</b></span>`)
    .join("");
  return `<div class="strip" role="img" aria-label="Balance split by account">${segs}</div><div class="legend">${legend}</div>`;
}

// Grouped bars: income vs expenses per month, inline SVG.
function monthChart(rows) {
  const W = 640, H = 230, L = 8, B = 28, T = 20;
  const max = Math.max(...rows.flatMap((r) => [r.income, r.expenses]), 1);
  const step = (W - L) / rows.length, bw = Math.min(34, step / 3);
  const y = (v) => T + (H - T - B) * (1 - v / max);
  const g = rows
    .map((r, i) => {
      const x = L + step * i + step / 2;
      return `
        <rect x="${x - bw - 2}" y="${y(r.income)}" width="${bw}" height="${H - B - y(r.income)}" rx="3" fill="#0b7fa6"/>
        <rect x="${x + 2}" y="${y(r.expenses)}" width="${bw}" height="${H - B - y(r.expenses)}" rx="3" fill="#17202f"/>
        <text x="${x - bw / 2 - 2}" y="${y(r.income) - 5}" text-anchor="middle" class="v">${Math.round(r.income / 1000)}k</text>
        <text x="${x + bw / 2 + 2}" y="${y(r.expenses) - 5}" text-anchor="middle" class="v">${Math.round(r.expenses / 1000)}k</text>
        <text x="${x}" y="${H - 8}" text-anchor="middle">${shortMonth(r.month)}</text>`;
    })
    .join("");
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Income and expenses per month">
    <line x1="${L}" x2="${W}" y1="${H - B}" y2="${H - B}" stroke="#e2e6ec"/>${g}</svg>
    <div class="legend"><span><span class="dot" style="background:#0b7fa6"></span>Income</span><span><span class="dot" style="background:#17202f"></span>Expenses</span><span>Amounts in thousands of tenge</span></div>`;
}

// ---------- pages ----------
async function overview() {
  const o = await api("/api/overview");
  const first = META.months[0];
  view.innerHTML =
    head(`Your accounts hold ${kzt(o.total_balance)}`, `From ${monthName(first)} to ${monthName(META.months.at(-1))}: ${o.counts.transactions} transactions across ${o.counts.accounts} accounts and ${o.counts.categories} categories.`) +
    `<section class="block"><h2>Where the money sits</h2><p class="hint">Today's balance of each account, start money plus every transaction.</p>${strip(o.accounts)}</section>` +
    `<div class="stats">
      <div class="stat"><span>Income</span><strong>${kzt(o.income)}</strong></div>
      <div class="stat"><span>Expenses</span><strong>${kzt(o.expenses)}</strong></div>
      <div class="stat good"><span>Saved</span><strong>${kzt(o.saved)}</strong></div>
      <div class="stat"><span>Transactions</span><strong>${o.counts.transactions}</strong></div></div>` +
    block("Income and expenses by month", "Expenses are computed per month with asyncio.gather in the Python core.", monthChart(o.by_month)) +
    block("Spending by category", "All months together, biggest first.", bars(Object.entries(o.by_category).slice(0, 10).map(([label, value]) => ({ label, value }))));
}

async function data() {
  const d = await api("/api/data");
  view.innerHTML =
    head("Data", "Everything loaded from data/seed.json. The core never edits it: every change returns a new copy.") +
    `<div class="tabs" role="group" aria-label="Table">${["Transactions", "Accounts", "Categories", "Budgets"]
      .map((t, i) => `<button class="ghost" aria-pressed="${i === 0}" data-tab="${t}">${t}</button>`)
      .join("")}</div><section class="block" id="tab"></section>`;
  const draw = (tab) => {
    $$("[data-tab]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.tab === tab));
    const t = $("#tab");
    if (tab === "Transactions") {
      t.innerHTML = `<div class="row"><label>Search<input id="q" type="search" placeholder="Category, note or date"></label><span class="hint" id="cnt"></span></div><div id="tx"></div>`;
      const show = () => {
        const q = $("#q").value.trim().toLowerCase();
        const rows = d.transactions.filter((x) => !q || [x.ts, x.note, META.names[x.cat_id], accName(x.account_id)].join(" ").toLowerCase().includes(q));
        $("#cnt").textContent = `${rows.length} of ${d.transactions.length} transactions`;
        $("#tx").innerHTML = table(TX_COLS, rows.slice(0, 300), "No transaction matches this search.");
      };
      $("#q").addEventListener("input", debounce(show, 120));
      show();
    } else if (tab === "Accounts") {
      t.innerHTML = table([{ h: "Name", f: (a) => esc(a.name) }, { h: "Id", f: (a) => `<code>${esc(a.id)}</code>` }, { h: "Start balance", num: true, f: (a) => kzt(a.balance) }, { h: "Currency", f: (a) => esc(a.currency) }], d.accounts);
    } else if (tab === "Categories") {
      t.innerHTML = table([{ h: "Name", f: (c) => (c.parent_id ? "&emsp;" : "") + esc(c.name) }, { h: "Id", f: (c) => `<code>${esc(c.id)}</code>` }, { h: "Parent", f: (c) => esc(c.parent_id ? META.names[c.parent_id] : "none") }, { h: "Type", f: (c) => esc(c.type) }], d.categories);
    } else {
      t.innerHTML = table([{ h: "Category", f: (b) => esc(META.names[b.cat_id]) }, { h: "Limit", num: true, f: (b) => kzt(b.limit) }, { h: "Period", f: (b) => esc(b.period) }], d.budgets);
    }
  };
  $$("[data-tab]").forEach((b) => b.addEventListener("click", () => draw(b.dataset.tab)));
  draw("Transactions");
}

// Wire inputs inside a root: call fn(root) on every change, show errors in place.
function live(root, fn, ms = 200) {
  const out = $(".out", root);
  const run = debounce(async () => {
    try { out.innerHTML = await fn(root); } catch (e) { out.innerHTML = note("bad", esc(e.message)); }
  }, ms);
  $$("input, select", root).forEach((el) => el.addEventListener("input", run));
  const b = $("button[data-run]", root);
  if (b) b.addEventListener("click", run);
  run();
}
const val = (root, n) => $(`[name="${n}"]`, root).value;

async function core() {
  const bal = await api("/api/core/balances");
  view.innerHTML =
    head("Functional core", "The building blocks from labs 1 and 2. Change a value and the Python function runs again.") +
    block("Account balances", "account_balance sums the transactions of one account.", `<dl class="kv">${bal.map((b) => `<dt>${esc(b.name)}</dt><dd>${money(b.balance)}</dd>`).join("")}</dl>`) +
    `<section class="block" id="imm"><h2>Changing data without changing it</h2><p class="hint">add_transaction and update_budget return new tuples. The original stays exactly as it was.</p>
      <div class="row"><label>New limit for the first budget, ₸<input name="limit" type="number" step="1000" value="${(await api("/api/core/immutability")).old_limit + 10000}"></label></div><div class="out"></div></section>` +
    `<section class="block" id="flt"><h2>Filters built with closures</h2><p class="hint">by_category, by_amount_range and by_date_range each return a function. We combine the three.</p>
      <div class="row">
        <label>Category<select name="cat">${catOptions(META.leaf_ids, "cafe")}</select></label>
        <label>Min amount<input name="min" type="number" step="1000" value="-200000"></label>
        <label>Max amount<input name="max" type="number" step="1000" value="400000"></label>
        <label>From<input name="start" type="date" value="${META.first_date}" min="${META.first_date}" max="${META.last_date}"></label>
        <label>To<input name="end" type="date" value="${META.last_date}" min="${META.first_date}" max="${META.last_date}"></label>
      </div><div class="out"></div></section>` +
    `<div class="cols"><section class="block" id="may"><h2>Maybe</h2><p class="hint">safe_category returns a value or nothing, so a missing id never raises.</p>
      <div class="row"><label>Category id<input name="id" value="food" autocomplete="off"></label></div><div class="out"></div></section>
    <section class="block" id="cmp"><h2>compose and pipe</h2><p class="hint">Same two functions, abs then double, chained in two directions.</p>
      <div class="row"><label>Amount<input name="x" type="number" step="500" value="-5000"></label></div><div class="out"></div></section></div>`;

  live($("#imm"), async (r) => {
    const d = await api("/api/core/immutability" + qs({ limit: val(r, "limit") || 0 }));
    return `<dl class="kv"><dt>Transactions before</dt><dd>${d.old_count}</dd><dt>Transactions after adding one</dt><dd>${d.new_count}</dd><dt>Limit (${esc(META.names[d.budget_cat])})</dt><dd>${kzt(d.old_limit)} then ${kzt(d.new_limit)}</dd></dl>`;
  });
  live($("#flt"), async (r) => {
    const d = await api("/api/core/filter" + qs({ cat: val(r, "cat"), min_amount: val(r, "min") || -1e7, max_amount: val(r, "max") || 1e7, start: val(r, "start") || "0000-01-01", end: val(r, "end") || "9999-12-31" }));
    return `<p><b>${d.count}</b> transactions found.</p>` + table(TX_COLS, d.transactions, "No transaction matches these filters. Widen the range.");
  });
  live($("#may"), async (r) => {
    const d = await api("/api/core/maybe" + qs({ cat_id: val(r, "id") }));
    return d.found ? note("good", `Found: <b>${esc(d.name)}</b>`) : note("gold", `No category with id “${esc(d.cat_id)}”. Nothing was raised.`);
  });
  live($("#cmp"), async (r) => {
    const d = await api("/api/core/compose" + qs({ x: val(r, "x") || 0 }));
    return `<dl class="kv"><dt>compose(double, abs)(${d.x})</dt><dd>${d.compose}</dd><dt>pipe(${d.x}, abs, double)</dt><dd>${d.pipe}</dd></dl>`;
  });
}

async function pipelines() {
  view.innerHTML =
    head("Pipelines", "Recursion over the category tree and lazy streams from labs 2 and 5.") +
    `<section class="block" id="hier"><h2>Category tree</h2><p class="hint">flatten_categories walks the tree and sum_expenses_recursive adds up every branch below the root.</p>
      <div class="row"><label>Root category<select name="root">${catOptions(META.root_ids, META.root_ids[0])}</select></label></div><div class="out"></div></section>` +
    `<section class="block" id="str"><h2>Lazy stream</h2><p class="hint">iter_transactions is a generator. It checks transactions one by one and never builds the full list, so the repeated stream below costs almost no memory.</p>
      <div class="row"><label>Count expenses of ₸ or more<input name="max" type="number" step="1000" value="5000" min="0"></label>
      <label>Repeat the data (times)<input name="rep" type="number" min="1" max="5000" step="50" value="100"></label></div><div class="out"></div></section>`;
  live($("#hier"), async (r) => {
    const d = await api("/api/pipelines/hierarchy" + qs({ root: val(r, "root") }));
    const items = Object.entries(d.by_category).map(([label, value]) => ({ label, value }));
    return `<p>Total expenses in <b>${esc(META.names[d.root])}</b>: <b>${kzt(d.total)}</b></p>` + bars(items, { max: d.total });
  });
  live($("#str"), async (r) => {
    const d = await api("/api/pipelines/stream" + qs({ max_amount: -(val(r, "max") || 0), repeat: val(r, "rep") || 1 }));
    return `<dl class="kv"><dt>Stream size</dt><dd>${nf.format(d.stream_size)} transactions</dd><dt>Matching expenses</dt><dd>${nf.format(d.matching)}</dd></dl>`;
  });
}

async function frp() {
  view.innerHTML =
    head("Async and events", "Lab 6 event bus with pure handlers, and lab 8 parallel totals. The bus lives on the server, so this state stays until you reset it.") +
    `<section class="block" id="bus"><h2>Live balances</h2><p class="hint">Publish a transaction and three handlers run in order: update the balance, check the budget, check for low balance.</p>
      <div id="live"></div>
      <div class="row" style="margin-top:16px">
        <label>Account<select id="acc">${options(META.accounts.map((a) => [a.id, a.name]), "acc3")}</select></label>
        <label>Category<select id="cat">${catOptions(META.leaf_ids, "cafe")}</select></label>
        <label>Amount, ₸<input id="amt" type="number" step="1000" value="-5000"></label>
        <button id="add">Add transaction</button>
      </div>
      <div class="row"><button class="ghost" id="ba">Send a budget alert</button><button class="ghost" id="bb">Send a low balance alert</button><button class="ghost" id="rs">Reset</button></div>
      <p class="hint">Try a big expense on Cash: its balance drops under 10 000 ₸ and an alert appears. Several cafe expenses trigger a budget alert.</p></section>
     <section class="block"><h2>Alerts</h2><div id="alerts"></div></section>
     <section class="block"><h2>Parallel totals</h2><p class="hint">One coroutine per month and per account, started together with asyncio.gather.</p><div id="asy"><p class="loading">Loading…</p></div></section>`;
  const draw = (s) => {
    const accs = s.accounts.map((a) => ({ name: a.name, current: a.balance }));
    $("#live").innerHTML = strip(accs);
    $("#alerts").innerHTML = s.notifications.length ? s.notifications.map((n) => note(/^Low|balance/i.test(n) ? "gold" : "bad", esc(n))).join("") : `<p class="empty">No alerts yet. Add a transaction above.</p>`;
  };
  const send = async (body) => {
    try { draw(await api("/api/frp/publish", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })); }
    catch (e) { $("#alerts").innerHTML = note("bad", esc(e.message)); }
  };
  draw(await api("/api/frp/state"));
  $("#add").onclick = () => send({ name: "TRANSACTION_ADDED", account_id: $("#acc").value, cat_id: $("#cat").value, amount: +$("#amt").value });
  $("#ba").onclick = () => send({ name: "BUDGET_ALERT", cat_id: $("#cat").value });
  $("#bb").onclick = () => send({ name: "BALANCE_ALERT", account_id: $("#acc").value });
  $("#rs").onclick = async () => draw(await api("/api/frp/reset", { method: "POST" }));
  const a = await api("/api/async");
  $("#asy").innerHTML =
    `<div class="cols"><div><h3>Expenses by month</h3>${bars(Object.entries(a.expenses_by_month).map(([m, value]) => ({ label: monthName(m), value })))}</div>
     <div><h3>Balance forecast per account</h3><p class="hint">Balance now plus the average monthly change.</p><dl class="kv">${META.accounts.map((x) => `<dt>${esc(x.name)}</dt><dd>${kzt(a.balance_forecast[x.id])}</dd>`).join("")}</dl></div></div>`;
}

async function reports() {
  view.innerHTML =
    head("Reports", "Forecasts, validation and budget checks from labs 3, 4, 5, 7 and 8.") +
    `<section class="block" id="fin"><h2>Final report</h2><p class="hint">One call runs the whole scenario: filter by dates, find top categories lazily, forecast them from the cache, and total months and accounts in parallel.</p>
      <div class="row"><label>From<input name="start" type="date" value="${META.first_date}" min="${META.first_date}" max="${META.last_date}"></label>
      <label>To<input name="end" type="date" value="${META.last_date}" min="${META.first_date}" max="${META.last_date}"></label></div><div class="out"></div></section>` +
    `<section class="block" id="bud"><h2>Monthly budgets</h2><p class="hint">BudgetService pipes a validator and a calculator over one month. A limit applies to one month only.</p>
      <div class="row"><label>Month<select name="month">${options(META.months.map((m) => [m, monthName(m)]), META.months.at(-1))}</select></label></div><div class="out"></div></section>` +
    `<div class="cols"><section class="block" id="fc"><h2>Forecast with cache</h2><p class="hint">lru_cache returns the saved answer on the second call.</p>
      <div class="row"><label>Category<select name="cat">${catOptions(META.leaf_ids, "cafe")}</select></label><label>Periods (months)<input name="p" type="number" min="1" value="${META.months.length}"></label></div><div class="out"></div></section>
     <section class="block" id="val"><h2>Check a transaction</h2><p class="hint">validate_transaction returns the first problem found, or the transaction itself.</p>
      <div class="row"><label>Transaction<select name="t">${options(META.transaction_ids.map((i) => [i, i]), META.transaction_ids[0])}</select></label></div><div class="out"></div></section></div>` +
    `<div class="cols"><section class="block" id="top"><h2>Top categories</h2><p class="hint">lazy_top_categories reads the expense stream once.</p>
      <div class="row"><label>How many<input name="k" type="number" min="1" max="10" value="3"></label></div><div class="out"></div></section>
     <section class="block" id="cr"><h2>Category report</h2><p class="hint">ReportService with one injected aggregator.</p>
      <div class="row"><label>Category<select name="cat">${catOptions(META.leaf_ids, "groceries")}</select></label></div><div class="out"></div></section></div>`;

  live($("#fin"), async (r) => {
    const d = await api("/api/reports/final" + qs({ start: val(r, "start") || META.first_date, end: val(r, "end") || META.last_date }));
    const total = Object.values(d.balances).reduce((s, x) => s + x, 0);
    const over = d.exceeded_budgets.length ? d.exceeded_budgets.map((c) => note("bad", `Budget exceeded in ${monthName(d.month)}: <b>${esc(META.names[c] || c)}</b>`)).join("") : note("good", "No budget is exceeded.");
    const months = Object.entries(d.expenses_by_month).map(([m, value]) => ({ label: monthName(m), value }));
    return `<div class="stats" style="margin-top:8px"><div class="stat"><span>Income</span><strong>${kzt(d.income)}</strong></div><div class="stat"><span>Expenses</span><strong>${kzt(d.expenses)}</strong></div><div class="stat"><span>Total balance</span><strong>${kzt(total)}</strong></div></div>${over}
      <div class="cols" style="margin-top:14px"><div><h3>Expenses by month</h3>${months.length ? bars(months) : `<p class="empty">No transactions in this period.</p>`}</div>
      <div><h3>Top categories and forecast per month</h3>${d.top_categories.length ? table([{ h: "Category", f: (x) => esc(x[0]) }, { h: "Spent", num: true, f: (x) => kzt(x[1]) }, { h: "Per month", num: true, f: (x) => kzt(d.forecasts[d.top_categories.indexOf(x)][1]) }], d.top_categories) : `<p class="empty">No expenses in this period.</p>`}
      <h3 style="margin-top:14px">Balance forecast for next month</h3><dl class="kv">${META.accounts.map((a) => `<dt>${esc(a.name)}</dt><dd>${kzt(d.balance_forecast[a.id])}</dd>`).join("")}</dl></div></div>`;
  });
  live($("#bud"), async (r) => {
    const d = await api("/api/reports/budget" + qs({ month: val(r, "month") }));
    const items = d.status.map((s) => ({ label: META.names[s.cat_id], value: s.spent, over: s.exceeded, text: `${kzt(s.spent)} of ${kzt(s.limit)}`, max: s.limit }));
    const rows = d.status.map((s) => `<div class="bar ${s.exceeded ? "over" : ""}"><span>${esc(META.names[s.cat_id])}</span><div class="track"><div class="fill" style="width:${Math.min(100, (s.spent / s.limit) * 100)}%"></div></div><span>${kzt(s.spent)} of ${kzt(s.limit)}${s.exceeded ? " · over" : ""}</span></div>`).join("");
    const bad = d.status.filter((s) => s.exceeded);
    return (bad.length ? bad.map((s) => note("bad", `Budget exceeded: <b>${esc(META.names[s.cat_id])}</b>, ${kzt(s.spent)} of ${kzt(s.limit)}`)).join("") : note("good", "Every budget is within its limit this month.")) +
      `<div class="bars" style="margin-top:12px">${rows}</div><p class="hint" style="margin-top:12px">Pipeline steps: ${d.steps.map(esc).join(" → ")}</p>`;
  });
  live($("#fc"), async (r) => {
    const d = await api("/api/reports/forecast" + qs({ cat: val(r, "cat"), period: val(r, "p") || 1 }));
    return `<p>Expected spending per period: <b>${kzt(d.value)}</b></p><dl class="kv"><dt>First call</dt><dd>${d.before_ms.toFixed(4)} ms</dd><dt>Cached call</dt><dd>${d.after_ms.toFixed(4)} ms</dd></dl>`;
  });
  live($("#val"), async (r) => {
    const d = await api("/api/reports/validate" + qs({ t_id: val(r, "t") }));
    const t = d.transaction;
    const line = `${esc(t.ts)}, ${esc(META.names[t.cat_id])}, ${money(t.amount)}`;
    return d.valid ? note("good", `${line}<br>Valid: account and category exist, budget is within its limit.`) : note("bad", `${line}<br>Rejected: ${esc(d.error.error)}${d.error.spent ? ` (${kzt(d.error.spent)} of ${kzt(d.error.limit)})` : ""}`);
  });
  live($("#top"), async (r) => {
    const d = await api("/api/reports/top" + qs({ k: val(r, "k") || 3 }));
    return bars(d.map((x) => ({ label: x.name, value: x.spent })));
  });
  live($("#cr"), async (r) => {
    const d = await api("/api/reports/category" + qs({ cat: val(r, "cat") }));
    return `<dl class="kv"><dt>Total</dt><dd>${money(d.total)}</dd><dt>Transactions</dt><dd>${d.count}</dd></dl>`;
  });
}

async function tests() {
  const t = await api("/api/tests");
  view.innerHTML =
    head("Tests", `${t.total} automated tests check the core. Run them here, the server starts pytest for you.`) +
    `<section class="block"><h2>Run the suite</h2><p class="hint">Runs <code>pytest -v</code> on this machine, in a separate process. It takes about a second.</p>
      <div class="row"><button id="run">Run all tests</button></div><div id="res"></div></section>` +
    `<section class="block"><h2>Tests per lab</h2><p class="hint">Counted from the files in tests/.</p>` +
    bars(Object.entries(t.counts).map(([f, value]) => ({ label: f.replace("test_", "").replace(".py", ""), value, text: `${value} tests` })), { max: Math.max(...Object.values(t.counts)) }) +
    `</section>`;
  $("#run").onclick = async () => {
    const btn = $("#run");
    btn.disabled = true;
    btn.textContent = "Running…";
    try {
      const r = await api("/api/tests/run", { method: "POST" });
      const files = Object.entries(r.files)
        .map(([f, list]) => {
          const bad = list.filter((x) => x.status !== "PASSED").length;
          const items = list.map((x) => `<li class="${x.status === "PASSED" ? "pos" : "err"}">${x.status === "PASSED" ? "✓" : "✗"} ${esc(x.name)}</li>`).join("");
          return `<details style="margin:6px 0"><summary>${note(bad ? "bad" : "good", `<b>${esc(f)}</b>: ${list.length - bad} of ${list.length} passed`)}</summary><ul style="margin:4px 0 8px;font-family:var(--mono);font-size:.85rem;list-style:none">${items}</ul></details>`;
        })
        .join("");
      $("#res").innerHTML = note(r.ok ? "good" : "bad", `<b>${r.ok ? "All tests passed" : "Some tests failed"}</b>: ${esc(r.summary)}`) + files + (r.log ? `<pre>${esc(r.log)}</pre>` : "");
    } catch (e) {
      $("#res").innerHTML = note("bad", esc(e.message));
    }
    btn.disabled = false;
    btn.textContent = "Run all tests again";
  };
}

function about() {
  view.innerHTML =
    head("About", "A personal finance manager for students, written in Python in a functional style and shown on this site.") +
    block("What it does", "Track accounts, categories, transactions and monthly budgets in tenge, then get forecasts and alerts.",
      `<p>The Python core uses pure functions, immutable data, recursion, lazy generators, caching, Maybe and Either, an event bus and asyncio. This site is a thin FastAPI layer over that core, so every number you see was calculated by the same functions the tests check.</p>`) +
    block("Team", "Course project for Functional Programming.", `<ul><li>Erik Nurgulde</li><li>Dimasena</li><li>Zhangir</li></ul>`);
}

// ---------- router ----------
const ROUTES = { overview, data, core, pipelines, frp, reports, tests, about };

async function route() {
  const id = (location.hash.slice(1) || "overview");
  const page = ROUTES[id] ? id : "overview";
  $$("#nav a").forEach((a) => (a.getAttribute("href") === "#" + page ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
  view.innerHTML = `<p class="loading">Loading…</p>`;
  document.title = PAGES.find((p) => p[0] === page)[1] + " · Financial Manager";
  try { await ROUTES[page](); } catch (e) { view.innerHTML = `<h1>Something went wrong</h1><p class="err">${esc(e.message)}</p><p class="lede">Check that the server is running, then reload the page.</p>`; }
  view.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}

(async function start() {
  $("#nav").innerHTML = PAGES.map(([id, label]) => `<a href="#${id}">${label}</a>`).join("");
  try { META = await api("/api/meta"); } catch (e) { view.innerHTML = `<h1>The server did not answer</h1><p class="err">${esc(e.message)}</p>`; return; }
  window.addEventListener("hashchange", route);
  route();
})();
