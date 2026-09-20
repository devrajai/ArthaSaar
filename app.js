/* MARKET BRAIN app — fetches live repo JSON, renders all sections.
   No libraries. Mobile-first. No sticky, no backdrop-filter. */
"use strict";
if (window.MB_LOCKED) throw new Error("locked");
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s == null ? "" : s).replace(/[&<>"']/g,
  (c) => ({"&":"\u0026amp;","<":"\u0026lt;",">":"\u0026gt;",'"':"\u0026quot;","'":"\u0026#39;"}[c]));
const nfIN = new Intl.NumberFormat("en-IN", {maximumFractionDigits: 2});
const nf2 = (x) => (x == null || isNaN(x)) ? "—" :
  Number(x).toLocaleString("en-IN", {maximumFractionDigits: 2});
const pctCls = (x) => (x > 0.05 ? "pos" : x < -0.05 ? "neg" : "neu");
const sign = (x, d) => (x == null || isNaN(x)) ? "—" :
  (x > 0 ? "+" : "") + Number(x).toFixed(d == null ? 2 : d) + "%";
const agoUTC = (iso) => { try { return iso ? iso.slice(11, 16) + " UTC" : ""; } catch (e) { return ""; } };

const BASE = "./data/";
const IPO_URL = "https://raw.githubusercontent.com/devrajai/ipo-terminal/main/data/ipo-data.json";
const cache = {};
function jload(key, url) {
  if (!cache[key]) cache[key] =
    fetch((url || BASE + key + ".json") + "?t=" + Date.now())
      .then((r) => { if (!r.ok) throw new Error(r.status); return r.json(); });
  return cache[key];
}
const fail = (id) => (e) => {
  const n = document.getElementById(id);
  if (n) n.innerHTML = '<div class="loading load-err">load failed — tap ⟳ refresh (' +
    esc(e && e.message || "error") + ")</div>";
};

/* ---------- theme / clock / market status ---------- */
(function theme() {
  const html = document.documentElement, btn = $("#themeBtn");
  const set = (t) => { html.setAttribute("data-theme", t);
    btn.textContent = t === "dark" ? "☀" : "☾";
    localStorage.setItem("mb-theme", t); };
  set(localStorage.getItem("mb-theme") || "dark");
  btn.onclick = () => set(html.getAttribute("data-theme") === "dark" ? "light" : "dark");
})();
(function clock() {
  const tf = new Intl.DateTimeFormat("en-IN", {timeZone: "Asia/Kolkata",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false});
  const df = new Intl.DateTimeFormat("en-IN", {timeZone: "Asia/Kolkata",
    weekday: "short", day: "2-digit", month: "short", year: "numeric"});
  const tick = () => { const now = new Date();
    $("#clock").textContent = tf.format(now);
    $("#clockdate").textContent = df.format(now) + " IST";
    const parts = new Intl.DateTimeFormat("en-GB", {timeZone: "Asia/Kolkata",
      weekday: "short", hour: "2-digit", minute: "2-digit", hour12: false})
      .formatToParts(now);
    const gv = (t) => (parts.find((p) => p.type === t) || {}).value || "";
    const day = gv("weekday"), hm = gv("hour") + gv("minute");
    let txt = "CLOSED", cls = "closed";
    if (!["Sat", "Sun"].includes(day)) {
      if (hm >= "0900" && hm < "0915") { txt = "PRE-OPEN"; cls = "pre"; }
      if (hm >= "0915" && hm <= "1530") { txt = "NSE OPEN"; cls = "open"; }
    }
    $("#mktTxt").textContent = txt; $("#mktDot").className = "dot " + cls;
  };
  tick(); setInterval(tick, 1000);
})();
$("#refreshBtn").onclick = () => location.reload();

/* ---------- tabs active state ---------- */
const tabs = document.querySelectorAll(".tab");
tabs.forEach((t) => t.addEventListener("click", () => {
  tabs.forEach((x) => x.classList.remove("active")); t.classList.add("active");
}));

/* ---------- dashboard ---------- */
function idxByName(list, name) {
  return list.find((i) => i.index === name) ||
    list.find((i) => (i.index || "").includes(name));
}
function kpi(name, idx) {
  if (!idx) return "";
  return '<div class="kpi"><div class="k-name">' + esc(name) + '</div>' +
    '<div class="k-val">' + nf2(idx.price) + "</div>" +
    '<div class="k-chg ' + pctCls(idx.change_pct) + '">' + sign(idx.change_pct) + "</div></div>";
}
function renderDash() {
  const fresh = [];
  const P = [];
  P.push(jload("breadth").then((d) => {
    fresh.push("breadth " + agoUTC(d.updated));
    const pct = d.above_ema200_pct || 0;
    $("#breadthBox").innerHTML =
      '<div class="statline"><span>Above 200-day EMA</span><b>' + pct + "% of " + d.stocks + "</b></div>" +
      '<div class="meter"><i style="width:' + Math.min(100, pct) + '%"></i></div>' +
      '<div class="statline"><span>RSI > 60 (strong)</span><b class="pos">' + d.rsi_above_60 + "</b></div>" +
      '<div class="statline"><span>RSI < 40 (weak)</span><b class="neg">' + d.rsi_below_40 + "</b></div>" +
      '<div class="statline"><span>Up 3+ days</span><b class="pos">' + d.up_3plus_days + "</b>" +
      "<span>Down 3+ days</span><b class=\"neg\">" + d.down_3plus_days + "</b></div>" +
      '<div class="statline"><span>Near 52w high</span><b>' + d.near_52w_high + "</b></div>" +
      "<span>Volume spike 2×</span><b>" + d.volume_spike_2x + "</b></div>";
  }, fail("breadthBox")));
  P.push(jload("fii-dii").then((d) => {
    fresh.push("FII/DII " + esc(d.date || ""));
    const c = d.categories || {};
    const row = (k) => { const v = c[k] || {};
      return '<div class="statline"><span>' + esc(k) + " net</span><b class=\"" +
        pctCls(v.net_cr) + '">' + (v.net_cr == null ? "—" :
        (v.net_cr > 0 ? "+" : "") + nfIN.format(v.net_cr) + " Cr") + "</b></div>"; };
    $("#fiiBox").innerHTML = row("FII/FPI") + row("DII") +
      '<div class="note" style="margin-top:6px">data date: ' + esc(d.date || "—") + "</div>";
  }, fail("fiiBox")));
  P.push(jload("indices-all").then((d) => {
    fresh.push("indices " + agoUTC(d.updated));
    const L = d.indices || [];
    $("#kpiRow").innerHTML =
      kpi("NIFTY 50", idxByName(L, "NIFTY 50")) +
      kpi("BANK NIFTY", idxByName(L, "NIFTY BANK")) +
      kpi("MIDCAP 100", idxByName(L, "NIFTY MIDCAP 100")) +
      kpi("SMALLCAP 100", idxByName(L, "NIFTY SMALLCAP 100")) +
      kpi("INDIA VIX", idxByName(L, "INDIA VIX")) +
      kpi("NIFTY IT", idxByName(L, "NIFTY IT"));
  }, fail("kpiRow")));
  P.push(jload("preopen").then((d) => {
    fresh.push("preopen " + agoUTC(d.updated));
    const g = d.gainer_buckets || {}, l = d.loser_buckets || {};
    const row = (x) => "<tr><td>" + esc(x.symbol) + "</td><td>" + nf2(x.iep) +
      "</td><td class=\"" + pctCls(x.change_pct) + "\">" + sign(x.change_pct) + "</td></tr>";
    $("#preopenBox").innerHTML =
      '<div class="statline" style="margin-bottom:6px"><span class="pos">Up ≥2%: ' +
      (g.up_ge_2pct || 0) + " · ≥5%: " + (g.up_ge_5pct || 0) +
      '</span><span class="neg">Down ≥2%: ' + (l.down_ge_2pct || 0) + " · ≥5%: " +
      (l.down_ge_5pct || 0) + "</span></div>" +
      '<div class="grid g2"><div><div class="subhead">Top gainers</div><table><tbody>' +
      (d.top20_gainers || []).slice(0, 5).map(row).join("") +
      '</tbody></table></div><div><div class="subhead">Top losers</div><table><tbody>' +
      (d.top20_losers || []).slice(0, 5).map(row).join("") +
      "</tbody></table></div></div>";
  }, fail("preopenBox")));
  P.push(jload("crypto").then((d) => {
    fresh.push("crypto " + agoUTC(d.updated));
    const btc = (d.top || []).find((c) => c.symbol === "BTC");
    const eth = (d.top || []).find((c) => c.symbol === "ETH");
    const fg = d.fear_greed || {};
    $("#cryptoMini").innerHTML =
      (btc ? '<div class="statline"><span>BTC $' + nf2(btc.price_usd) +
        '</span><b class="' + pctCls(btc.chg_24h_pct) + '">' + sign(btc.chg_24h_pct) + "</b></div>" : "") +
      (eth ? '<div class="statline"><span>ETH $' + nf2(eth.price_usd) +
        '</span><b class="' + pctCls(eth.chg_24h_pct) + '">' + sign(eth.chg_24h_pct) + "</b></div>" : "") +
      '<div class="statline"><span>Fear & Greed</span><b>' + esc(fg.value || "—") + " · " +
      esc(fg.label || "") + "</b></div>" +
      '<div class="note" style="margin-top:4px">BTC dominance ' + ((d.global || {}).btc_dominance || "—") + "%</div>";
  }, fail("cryptoMini")));
  P.push(jload("timesfm_forecasts").then((d) => {
    fresh.push("TimesFM " + (d.updated || "").slice(0, 10));
    const F = d.forecasts || [];
    const nifty = F.find((x) => x.symbol === "^NSEI");
    const btc = F.find((x) => x.symbol === "BTC-USD");
    const ups = F.filter((x) => x.direction === "up").length;
    $("#aiMini").innerHTML =
      (nifty ? '<div class="statline"><span>Nifty 21d median</span><b class="' +
        pctCls(nifty.median_chg_pct) + '">' + sign(nifty.median_chg_pct) + "</b></div>" : "") +
      (btc ? '<div class="statline"><span>BTC 21d median</span><b class="' +
        pctCls(btc.median_chg_pct) + '">' + sign(btc.median_chg_pct) + "</b></div>" : "") +
      '<div class="statline"><span>Bias</span><b>' + ups + " up / " + (F.length - ups) +
      ' down</b></div><div class="note" style="margin-top:4px">statistical bands — not signals</div>';
  }, fail("aiMini")));
  Promise.allSettled(P).then(() => {
    $("#dataFresh").textContent = "data: " + fresh.join(" · ");
  });
}

/* ---------- indices ---------- */
const IDX_SHORT = {"NIFTY 50": "NIFTY", "NIFTY BANK": "BANK", "INDIA VIX": "VIX",
  "NIFTY MIDCAP 100": "MIDCAP", "NIFTY SMALLCAP 100": "SMALLCAP", "NIFTY NEXT 50": "NEXT 50",
  "NIFTY MIDCAP 150": "MIDCAP 150", "NIFTY SMALLCAP 250": "SMALLCAP 250",
  "NIFTY FINANCIAL SERVICES": "FIN SERV", "NIFTY FIN SERVICE": "FIN SERV",
  "NIFTY SERV SECTOR": "SERV SEC", "NIFTY DIVIDEND OPPS 50": "DIV OPPS",
  "NIFTY LOW VOLATILITY 50": "LOW VOL 50", "NIFTY HIGH BETA 50": "HI BETA 50",
  "NIFTY ALPHA 50": "ALPHA 50", "NIFTY QUALITY 30": "QUALITY 30", "NIFTY VALUE 20": "VALUE 20",
  "NIFTY GROWSECT 15": "GROW SEC 15", "NIFTY PSU BANK": "PSU BANK",
  "NIFTY PRIVATE BANK": "PVT BANK", "NIFTY BANKING": "BANKING"};
function idxShort(n) {
  if (IDX_SHORT[n]) return IDX_SHORT[n];
  return String(n)
    .replace(/^(S&P CNX |S&P BSE |CNX |BSE |NSE )/, "")
    .replace(/^(NIFTY|NIFTY50) ?/, "")
    .replace(/ (INDEX|TR|PR)$/, "")
    .replace(/ (50|100|150|200|250|500|1000)$/, "") || String(n);
}
function renderIndices() {
  jload("indices-all").then((d) => {
    const body = $("#idxBody"), all = d.indices || [];
    const draw = (q) => {
      const list = !q ? all : all.filter((i) =>
        (i.index || "").toLowerCase().includes(q));
      body.innerHTML = list.map((i) => {
        const pos = (i.year_high && i.year_high > i.year_low) ?
          Math.round((i.price - i.year_low) / (i.year_high - i.year_low) * 100) : null;
        return '<tr><td class="idxnm"><span class="sym">' + esc(idxShort(i.index)) + '</span><span class="cname">' + esc(i.index) + "</span></td><td>" + nf2(i.price) +
          '</td><td class="' + pctCls(i.change_pct) + '">' + sign(i.change_pct) +
          "</td><td>" + (pos == null ? "—" : pos + "%") +
          "</td><td>" + esc(i.pe || "—") + "</td><td>" + esc(i.pb || "—") + "</td></tr>";
      }).join("") || '<tr><td colspan="6" class="loading">no match</td></tr>';
    };
    draw("");
    $("#idxSearch").oninput = (e) => draw(e.target.value.trim().toLowerCase());
  }, fail("idxBody"));
}

/* ---------- screener ---------- */
let scrData = null, scrShown = 0;
function filteredStocks() {
  const q = $("#scrSearch").value.trim().toLowerCase();
  const tier = +$("#scrTier").value, rsi = $("#scrRsi").value, ema = $("#scrEma").value;
  const sort = $("#scrSort").value;
  let L = (scrData.stocks || []).filter((s) =>
    (!q || s.symbol.toLowerCase().includes(q) || (s.company || "").toLowerCase().includes(q)) &&
    (!tier || s.tier === tier) &&
    (!ema || (ema === "above" ? s.above_ema200 : !s.above_ema200)));
  if (rsi === "os") L = L.filter((s) => s.rsi14 != null && s.rsi14 < 30);
  if (rsi === "lt40") L = L.filter((s) => s.rsi14 != null && s.rsi14 < 40);
  if (rsi === "gt60") L = L.filter((s) => s.rsi14 != null && s.rsi14 > 60);
  if (rsi === "ob") L = L.filter((s) => s.rsi14 != null && s.rsi14 > 70);
  const cmp = {
    chg: (a, b) => (b.change_pct || 0) - (a.change_pct || 0),
    rsi: (a, b) => (a.rsi14 || 99) - (b.rsi14 || 99),
    rsid: (a, b) => (b.rsi14 || 0) - (a.rsi14 || 0),
    "52w": (a, b) => (a.from_52w_high_pct || 0) - (b.from_52w_high_pct || 0),
    up: (a, b) => (b.from_52w_high_pct || 0) - (a.from_52w_high_pct || 0),
    vol: (a, b) => (b.vol_vs_avg20 || 0) - (a.vol_vs_avg20 || 0),
  }[sort];
  return L.sort(cmp);
}
function renderScreener() {
  if (scrData) return;
  $("#scrBody").innerHTML = '<tr><td colspan="8" class="loading">loading 2,085 stocks…</td></tr>';
  jload("brain-screener").then((d) => {
    scrData = d;
    const draw = () => {
      const L = filteredStocks();
      $("#scrCount").textContent = L.length + " stocks match · showing " + Math.min(scrShown, L.length);
      $("#scrBody").innerHTML = L.slice(0, scrShown).map((s) =>
        "<tr><td><span class=\"sym\"><a href=\"#company/" + esc(s.symbol) + "\">" + esc(s.symbol) + "</a>" +
        '<span class="cname">' + esc(s.company || "") + "</span></a></span></td>" +
        "<td>" + nf2(s.price) + '</td><td class="' + pctCls(s.change_pct) + '">' +
        sign(s.change_pct) + "</td><td>" + nf2(s.rsi14) + "</td><td>" +
        (s.from_52w_high_pct == null ? "—" : s.from_52w_high_pct + "%") +
        "</td><td>" + (s.above_ema200 ? '<span class="pos">above</span>' : '<span class="neg">below</span>') +
        "</td><td>" + (s.vol_vs_avg20 == null ? "—" :
          Number(s.vol_vs_avg20).toFixed(1) + "×") + "</td><td>" +
        (s.consec_days == null ? "—" : s.consec_days) + "</td></tr>").join("") ||
        '<tr><td colspan="8" class="loading">no match</td></tr>';
      $("#scrMore").style.display = scrShown < L.length ? "block" : "none";
    };
    scrShown = 60;
    draw();
    ["scrSearch", "scrTier", "scrRsi", "scrEma", "scrSort"].forEach((id) =>
      $("#" + id).addEventListener("input", () => { scrShown = 60; draw(); }));
    $("#scrMore").onclick = () => { scrShown += 100; draw(); };
  }, fail("scrBody"));
}

/* ---------- fundamentals ---------- */
let fndData = null, fndShown = 0;
function renderFundamentals() {
  if (fndData) return;
  $("#fndBody").innerHTML = '<tr><td colspan="7" class="loading">loading fundamentals…</td></tr>';
  jload("fundamentals").then((d) => {
    fndData = d;
    const rows = () => Object.keys(d).filter((k) => !k.startsWith("_"));
    const draw = () => {
      const q = $("#fndSearch").value.trim().toLowerCase();
      const pe = +$("#fndPE").value, roe = +$("#fndROE").value;
      let L = rows().filter((k) => {
        const v = d[k];
        if (q && !k.toLowerCase().includes(q)) return false;
        if (pe && !(v.trailingPE != null && v.trailingPE < pe)) return false;
        if (roe && !(v.returnOnEquity != null && v.returnOnEquity * 100 > roe)) return false;
        return true;
      });
      $("#fndCount").textContent = L.length + " stocks · showing " + Math.min(fndShown, L.length);
      $("#fndBody").innerHTML = L.slice(0, fndShown).map((k) => {
        const v = d[k] || {};
        return "<tr><td class=\"sym\"><a href=\"#company/" + esc(k) + "\">" + esc(k) + "</a></td><td>" + nf2(v.trailingPE) +
          "</td><td>" + nf2(v.priceToBook) + "</td><td>" +
          (v.returnOnEquity == null ? "—" :
            (v.returnOnEquity * 100).toFixed(1) + "%") + "</td><td>" +
          nf2(v.debtToEquity) + "</td><td>" +
          (v.heldPercentInsiders == null ? "—" : (v.heldPercentInsiders * 100).toFixed(1) + "%") +
          "</td><td>" + (v.heldPercentInstitutions == null ? "—" :
          (v.heldPercentInstitutions * 100).toFixed(1) + "%") + "</td></tr>";
      }).join("");
      $("#fndMore").style.display = fndShown < L.length ? "block" : "none";
    };
    fndShown = 60; draw();
    ["fndSearch", "fndPE", "fndROE"].forEach((id) =>
      $("#" + id).addEventListener("input", () => { fndShown = 60; draw(); }));
    $("#fndMore").onclick = () => { fndShown += 100; draw(); };
    $("#fndValue").onclick = () => {
      $("#fndPE").value = "20"; $("#fndROE").value = "15";
      fndShown = 60; draw();
    };
  }, fail("fndBody"));
}

/* ---------- IPO ---------- */
function renderIPO() {
  $("#ipoBox").innerHTML = '<div class="loading">loading IPO data…</div>';
  jload("ipo", IPO_URL).then((d) => {
    const ipos = d.ipos || [];
    const card = (x) => '<div class="card" style="margin-bottom:10px"><div style="display:flex;' +
      'gap:8px;align-items:baseline;flex-wrap:wrap"><b style="font-size:14.5px">' + esc(x.name) +
      '</b><span class="badge-tier">' + esc(x.type || "") + "</span>" +
      (x.status ? '<span class="chg-badge ' + (/list/i.test(x.status) ? "neu" : "pos") +
        '">' + esc(x.status) + "</span>" : "") + "</div>" +
      '<div class="kv" style="margin-top:8px">' +
      "<span>Price band</span><b>" + esc(x.price || "—") + "</b>" +
      "<span>Lot</span><b>" + esc(x.lot || "—") + "</b>" +
      "<span>Open → Close</span><b>" + esc(x.open || "—") + " → " + esc(x.close || "—") + "</b>" +
      "<span>Listing</span><b>" + esc(x.listing || "—") + "</b>" +
      "<span>GMP</span><b class=\"" + pctCls(parseFloat(x.gmp_pct)) + "\">" + esc(x.gmp || "—") +
      " (" + esc(x.gmp_pct || "—") + ")</b>" +
      "<span>Est. listing</span><b>" + esc(x.est_list || "—") + "</b>" +
      "<span>Subscription</span><b>" + esc(x.sub || "—") + "</b>" +
      (x.sector && x.sector !== "—" ? "<span>Sector</span><b>" + esc(x.sector) + "</b>" : "") +
      "</div></div>";
    const live = ipos.filter((x) => !/list/i.test(x.status || ""));
    const done = ipos.filter((x) => /list/i.test(x.status || ""));
    $("#ipoBox").innerHTML =
      '<div class="subhead">Open & upcoming (' + live.length + ")</div>" +
      (live.map(card).join("") || '<div class="note">none right now</div>') +
      (done.length ? '<div class="subhead" style="margin-top:14px">Recently listed (' +
        done.length + ")</div>" + done.slice(0, 6).map(card).join("") : "") +
      '<div class="footer-note">source: ' + esc(d.source || "ipo-terminal") +
      " · updated " + esc((d.updated_at || "").slice(0, 16)) + "</div>";
  }, fail("ipoBox"));
}

/* ---------- crypto ---------- */
function renderCrypto() {
  jload("crypto").then((d) => {
    const g = d.global || {}, fg = d.fear_greed || {};
    $("#cryptoGlobal").innerHTML =
      '<div class="kpi"><div class="k-name">TOTAL MARKET CAP</div><div class="k-val">$' +
      (g.total_market_cap_usd / 1e12).toFixed(2) + "T</div>" +
      '<div class="k-chg ' + pctCls(g.mcap_chg_24h_pct) + '">' + sign(g.mcap_chg_24h_pct) + "</div></div>" +
      '<div class="kpi"><div class="k-name">BTC DOMINANCE</div><div class="k-val">' +
      (g.btc_dominance || "—") + '%</div><div class="k-chg neu">ETH ' + (g.eth_dominance || "—") + "%</div></div>" +
      '<div class="kpi"><div class="k-name">24H VOLUME</div><div class="k-val">$' +
      (g.total_volume_usd / 1e9).toFixed(0) + "B</div><div class=\"k-chg neu\">source: " +
      esc(d.source) + "</div></div>";
    const v = fg.value == null ? 50 : fg.value;
    $("#fgBox").innerHTML = '<div class="fg-wrap"><div class="fg-bar">' +
      '<div class="fg-marker" style="left:' + v + '%"></div></div>' +
      '<div class="fg-labels"><span>0 extreme fear</span><span>50 neutral</span><span>100 extreme greed</span></div></div>' +
      '<div class="statline"><span>Current</span><b>' + esc(fg.value) + " — " + esc(fg.label) + "</b></div>";
    const draw = () => {
      const q = $("#crySearch").value.trim().toLowerCase();
      const L = (d.top || []).filter((c) => !q ||
        c.symbol.toLowerCase().includes(q) || (c.name || "").toLowerCase().includes(q));
      $("#cryBody").innerHTML = L.slice(0, cryShown).map((c) => "<tr><td>" + c.rank +
        "</td><td><b>" + esc(c.symbol) + '</b><span class="cname">' + esc(c.name) + "</span></td><td>" +
        nf2(c.price_usd) + '</td><td class="' + pctCls(c.chg_24h_pct) + '">' + sign(c.chg_24h_pct) +
        '</td><td class="' + pctCls(c.chg_7d_pct) + '">' + sign(c.chg_7d_pct) +
        '</td><td class="' + pctCls(c.chg_30d_pct) + '">' + sign(c.chg_30d_pct) +
        "</td><td>" + (c.market_cap == null ? "—" : (c.market_cap / 1e9).toFixed(1)) +
        "</td><td>" + (c.from_ath_pct == null ? "—" : c.from_ath_pct + "%") + "</td></tr>").join("");
      $("#cryMore").style.display = cryShown < L.length ? "block" : "none";
    };
    let cryShown = 30;
    draw();
    $("#crySearch").oninput = () => { cryShown = 30; draw(); };
    $("#cryMore").onclick = () => { cryShown += 50; draw(); };
  }, fail("cryBody"));
}

/* ---------- TimesFM AI ---------- */
function sparkline(path) {
  if (!path || !path.length) return "";
  const w = 220, h = 38, mn = Math.min(...path), mx = Math.max(...path), r = (mx - mn) || 1;
  const pts = path.map((v, i) =>
    (i / (path.length - 1) * w).toFixed(1) + "," + (h - 3 - (v - mn) / r * (h - 6)).toFixed(1));
  const up = path[path.length - 1] >= path[0];
  return '<svg class="spark" viewBox="0 0 ' + w + " " + h + '" preserveAspectRatio="none">' +
    '<polyline points="' + pts.join(" ") + '" fill="none" stroke="' +
    (up ? "#2dd4a7" : "#fb5c7d") + '" stroke-width="2.2" stroke-linejoin="round"/></svg>';
}
function renderAI() {
  jload("timesfm_forecasts").then((d) => {
    const F = d.forecasts || [];
    const up = F.filter((f) => f.direction === "up").length;
    $("#aiHead").innerHTML = '<div class="kv"><span>Model</span><b>' + esc(d.model) +
      "</b><span>Coverage</span><b>" + F.length + " series — indices, top 50 stocks, crypto, global</b>" +
      "<span>Forecast</span><b>" + esc(d.horizon_days) + " trading days ahead (weekly, Sundays)</b>" +
      "<span>Updated</span><b>" + esc((d.updated || "").slice(0, 10)) + "</b>" +
      '<span>Bias</span><b>' + up + " up · " + (F.length - up) + " down / flat</b></div>" +
      '<div class="note" style="margin-top:8px">' + esc(d.disclaimer) + "</div>";
    const catName = {index: "Indices", stock: "Top 50 stocks", crypto: "Crypto top 10", global: "Global and FX"};
    const card = (f) =>
      '<div class="kpi"><div class="k-name">' + esc(f.name) + "</div>" +
      '<div class="k-val" style="font-size:15px">' + nf2(f.as_of_last_close) + " → " +
      nf2(f.median_end) + "</div>" +
      '<div class="k-chg ' + pctCls(f.median_chg_pct) + '">median ' + sign(f.median_chg_pct) +
      ' · band <span class="neg">' + sign(f.low10_chg_pct, 1) + "</span> … <span class=\"pos\">" +
      sign(f.high90_chg_pct, 1) + "</span></div>" + sparkline(f.median_path) + "</div>";
    if (F.some((f) => f.cat)) {
      $("#aiGrid").className = "";
      $("#aiGrid").innerHTML = ["index", "stock", "crypto", "global"].map((c) => {
        const L = F.filter((f) => f.cat === c);
        if (!L.length) return "";
        return '<div class="hgroup">' + (catName[c] || c) + " (" + L.length + ")</div>" +
          '<div class="grid g2">' + L.map(card).join("") + "</div>";
      }).join("");
    } else {
      $("#aiGrid").innerHTML = F.map(card).join("");
    }
  }, fail("aiGrid"));
}

/* ---------- filings ---------- */
function renderFilings() {
  $("#filBox").innerHTML = '<div class="loading">loading filings…</div>';
  jload("filings").then((d) => {
    const fils = d.filings || [];
    const cats = [...new Set(fils.map((f) => f.category))].filter(Boolean);
    let active = "All";
    const chips = () => {
      $("#filChips").innerHTML = ["All"].concat(cats).map((c) =>
        '<button class="chip' + (c === active ? " on" : "") + '" data-c="' + esc(c) + '">' +
        esc(c) + "</button>").join("");
      $("#filChips").querySelectorAll(".chip").forEach((b) =>
        b.onclick = () => { active = b.dataset.c; draw(); });
    };
    const draw = () => {
      chips();
      const L = active === "All" ? fils : fils.filter((f) => f.category === active);
      L.sort((a, b) => (b.date || "").localeCompare(a.date || ""));
      $("#filBox").innerHTML = L.slice(0, 60).map((f) =>
        '<details class="gl"><summary><span class="sym">' + esc(f.symbol) + " — " +
        esc((f.subject || f.nse_desc || "").slice(0, 90)) +
        '<span class="badge-tier" style="margin-left:auto">' + esc(f.date) + " · " +
        esc(f.category) + "</span></summary><ul>" +
        "<li><b>" + esc(f.company) + "</b> (" + esc(f.industry || "—") + ", tier " + f.tier + ")</li>" +
        "<li>" + esc(f.subject || "") + "</li>" +
        (f.pdf ? '<li><a href="' + esc(f.pdf) + '" target="_blank" rel="noopener">open PDF ↗</a></li>' : "") +
        "</ul></details>").join("") || '<div class="note">no filings</div>';
      $("#filBox").insertAdjacentHTML("beforeend", '<div class="footer-note">showing 60 of ' +
        L.length + " tier-1 filings (last " + d.window_days + " days) · more in Notion library</div>");
    };
    draw();
  }, fail("filBox"));
}

/* ---------- learn: education hub ---------- */
let lcData = null, eduData = null, learnTab = "course", stratType = "intraday";
function renderLearn() {
  $("#eduBox").innerHTML = '<div class="loading">loading learning hub…</div>';
  const P = [];
  P.push(jload("learn-content").then((d) => { lcData = d; }, () => {}));
  P.push(jload("education").then((d) => { eduData = d; }, () => {}));
  Promise.allSettled(P).then(drawLearn);
}
function learnChips() {
  const tabs = [["course", "Course"], ["strategies", "Strategies"], ["glossary", "Glossary"],
    ["rules", "Rules"], ["psychology", "Psychology"], ["selection", "Pick Stocks"],
    ["media", "Videos & Books"]];
  $("#learnChips").innerHTML = tabs.map(([id, label]) =>
    '<button class="chip' + (learnTab === id ? " on" : "") + '" data-lt="' + id + '">' + label + "</button>").join("");
  $("#learnChips").querySelectorAll(".chip").forEach((b) =>
    b.onclick = () => { learnTab = b.dataset.lt; drawLearn(); });
}
function drawLearn() {
  learnChips();
  const box = $("#eduBox");
  const d = lcData || {};
  const ul = (items) => '<ul style="margin:8px 0 4px 16px;font-size:13px;line-height:1.7">' +
    items.map((x) => "<li>" + esc(x) + "</li>").join("") + "</ul>";
  if (learnTab === "course") {
    const lvl = (name, key) => (d.levels && d.levels[key] ?
      '<div class="card"><div class="subhead">' + name + " (" + d.levels[key].length + ")</div>" +
      ul(d.levels[key]) + "</div>" : "");
    box.innerHTML =
      '<div class="note" style="margin-bottom:10px">' + esc(d.note || "") +
      " Read in order: Beginner first, then Intermediate, then Advanced.</div>" +
      lvl("Beginner — first 6 months", "beginner") +
      lvl("Intermediate — 6 to 18 months", "intermediate") +
      lvl("Advanced — 18 months plus", "advanced") +
      (d.quick_tips ? '<div class="card"><div class="subhead">Quick tips — one line each</div>' +
        ul(d.quick_tips) + "</div>" : "");
  } else if (learnTab === "glossary") {
    box.innerHTML = '<div class="controls"><input id="glosSearch" type="search" placeholder="Search a word… e.g. ROCE, OI, circuit"></div><div id="glosBox"></div>';
    const drawG = () => {
      const q = $("#glosSearch").value.trim().toLowerCase();
      const L = (d.glossary || []).filter((x) => !q ||
        x.term.toLowerCase().includes(q) || x.meaning.toLowerCase().includes(q));
      $("#glosBox").innerHTML = L.map((x) =>
        '<details class="gl"><summary><span class="sym">' + esc(x.term) +
        "</span></summary><ul><li>" + esc(x.meaning) + "</li></ul></details>").join("") ||
        '<div class="note">no match</div>';
    };
    drawG();
    $("#glosSearch").oninput = drawG;
  } else if (learnTab === "rules") {
    box.innerHTML = (d.rules || []).map((x) =>
      '<details class="gl"><summary><span class="sym">' + esc(x.rule) +
      "</span></summary><ul><li>Why: " + esc(x.why) + "</li></ul></details>").join("");
  } else if (learnTab === "psychology") {
    box.innerHTML = (d.psychology || []).map((x) =>
      '<details class="gl"><summary><span class="sym">' + esc(x.topic) +
      "</span></summary><ul><li>" + esc(x.point) + "</li></ul></details>").join("");
  } else if (learnTab === "strategies") {
    const types = [["intraday", "Intraday"], ["short_term", "Swing"], ["long_term", "Long term"],
      ["options", "Options"], ["futures", "Futures"]];
    const st = (d.strategies || {})[stratType] || [];
    box.innerHTML = '<div class="controls">' + types.map(([k, n]) =>
      '<button class="chip' + (stratType === k ? " on" : "") + '" data-st="' + k + '">' + n + "</button>").join("") + "</div>" +
      st.map((s) => '<div class="card"><div style="font-weight:600;font-size:14px;margin-bottom:6px">' +
        esc(s.name) + ' <span class="badge-tier">' + esc(s.level || "") + "</span></div>" +
        '<div class="kv"><span>How</span><b style="text-align:right">' + esc(s.how) + "</b>" +
        '<span>When</span><b style="text-align:right">' + esc(s.when) + "</b>" +
        '<span>Risk</span><b style="text-align:right">' + esc(s.risk) + "</b></div></div>").join("") ||
        '<div class="note">choose a trading style above</div>';
    box.querySelectorAll("[data-st]").forEach((b) =>
      b.onclick = () => { stratType = b.getAttribute("data-st"); drawLearn(); });
  } else if (learnTab === "selection") {
    const sel = d.stock_selection || {};
    const list = (title, key) => (sel[key] ?
      '<div class="card"><div class="subhead">' + title + " (" + sel[key].length + " checks)</div>" +
      ul(sel[key]) + "</div>" : "");
    box.innerHTML =
      list("Intraday stock selection — 10-point checklist", "intraday_checklist") +
      list("Short-term / swing selection — 10-point checklist", "short_term_checklist") +
      list("Long-term investment selection — 12-point checklist", "long_term_checklist");
  } else if (learnTab === "media") {
    const e = eduData || {};
    const dl = (t, items) => items && items.length ?
      '<div class="card"><div class="subhead">' + t + " (" + items.length + ")</div>" +
      items.map((x) => '<details class="gl"><summary>' + esc(x.title || x.name || x.rule) +
      "</summary><ul>" +
      (x.author ? "<li>by " + esc(x.author) + "</li>" : "") +
      (x.host ? "<li>host: " + esc(x.host) + "</li>" : "") +
      (x.lang ? "<li>language: " + esc(x.lang) + "</li>" : "") +
      (x.level ? "<li>level: " + esc(x.level) + "</li>" : "") +
      (x.why ? "<li>" + esc(x.why) + "</li>" : "") +
      (x.note ? "<li>" + esc(x.note) + "</li>" : "") +
      (x.url ? '<li><a href="' + esc(x.url) + '" target="_blank" rel="noopener">open ↗</a></li>' : "") +
      (x.source ? '<li class="note">saved: ' + esc(x.source) + "</li>" : "") +
      "</ul></details>").join("") + "</div>" : "";
    const ma = e.market_analysis_videos || {};
    const pl = e.devs_learning_playlists || {};
    const it = e.inspiring_traders || {};
    box.innerHTML = '<div class="note" style="margin-bottom:10px">Dev\'s collected library — books, podcasts, videos.</div>' +
      dl("Books", e.books) + dl("Podcasts", e.podcasts) + dl("YouTube channels", e.youtube) +
      dl("Free courses & articles", e.free_courses_and_articles) +
      dl("My collected rules", e.devs_collected_rules) +
      (ma.videos ? '<div class="card"><div class="subhead">Daily market analysis videos (' +
        ma.videos.length + ")</div><div class=\"note\">" + esc(ma.note || "") + "</div>" +
        ma.videos.slice(0, 12).map((v) => '<details class="gl"><summary>' +
        esc((v.title || "").slice(0, 80)) + '<span class="badge-tier">' + esc(v.channel) +
        "</span></summary><ul><li><a href=\"" + esc(v.url) +
        '" target="_blank" rel="noopener">watch ↗</a></li></ul></details>').join("") + "</div>" : "") +
      (pl.playlists ? '<div class="card"><div class="subhead">My course playlists — POWER OF STOCKS (' +
        pl.playlists.reduce((a, p) => a + (p.count || (p.videos || []).length), 0) +
        " videos)</div>" + pl.playlists.map((p) => '<details class="gl"><summary>' +
        esc(p.name) + '<span class="badge-tier">' + (p.count || (p.videos || []).length) +
        " videos</span></summary><ul>" +
        '<li><a href="' + esc(p.url) + '" target="_blank" rel="noopener">playlist ↗</a></li>' +
        (p.videos || []).map((v) => '<li><a href="' + esc(v.url) +
          '" target="_blank" rel="noopener">' + esc((v.title || "video").slice(0, 75)) + " ↗</a></li>").join("") +
        "</ul></details>").join("") + "</div>" : "") +
      (it.playlist ? '<div class="card"><div class="subhead">Inspiring Traders</div><div class="note">' +
        esc(it.note || "") + '</div><ul style="margin:8px 0 4px 16px;font-size:12.5px;color:var(--dim)">' +
        '<li>channel: ' + esc(it.channel || "—") + '</li><li><a href="' + esc(it.playlist) +
        '" target="_blank" rel="noopener">open playlist ↗</a></li></ul></div>' : "");
  }
}

/* ---------- studies ---------- */
function renderStudies() {
  Promise.allSettled([jload("devs_notes_digest"), jload("budget-study")]).then(([D, B]) => {
    if (D.status === "fulfilled") {
      const s = (D.value.sensex_history_dev_study || {}).years || [];
      const max = Math.max(...s.map((y) => Math.abs(y.ret_pct || 0)), 1);
      const greens = s.filter((y) => (y.ret_pct || 0) > 0).length;
      $("#sensexCard").innerHTML = '<div class="subhead">Sensex yearly returns 1979–2024 (' +
        greens + " green / " + (s.length - greens) + " red) — from Dev's own handwritten study</div>" +
        s.map((y) => { const r = y.ret_pct || 0, w = Math.abs(r) / max * 50;
          return '<div class="yearbar"><span class="yb-label">' + y.year + '</span>' +
            '<span class="yb-track"><span class="yb-bar ' + (r >= 0 ? "g" : "r") +
            '" style="width:' + (w.toFixed(1)) + '%"></span></span>' +
            '<span class="yb-val ' + pctCls(r) + '">' + (r > 0 ? "+" : "") + r.toFixed(1) +
            "%</span></div>"; }).join("") +
        '<div class="footer-note">worst: 2008 (−52%) · best years: 1991, 2009, 2021</div>';
    } else fail("sensexCard")(D.reason);
    if (B.status === "fulfilled") {
      const bs = B.value.budgets || [];
      $("#budgetCard").innerHTML = '<div class="subhead">Nifty on Budget day — 2015 onwards</div>' +
        '<div class="tblwrap"><table><thead><tr><th>Year</th><th>Date</th><th>FM</th><th>Budget day</th></tr></thead><tbody>' +
        bs.map((b) => "<tr><td>" + esc(b.year) + "</td><td>" + esc(b.date) + "</td><td>" +
          esc(b.finance_minister || "—") + '</td><td class="' + pctCls(b.nifty_budget_day_pct) +
          '">' + sign(b.nifty_budget_day_pct, 1) + "</td></tr>").join("") +
        "</tbody></table></div>" +
        '<div class="footer-note">14 budgets measured: 5 positive, 8 negative · avg ' +
        esc(((B.value.summary || {}).avg_budget_day_pct ?? "—")) + "%</div>";
    } else fail("budgetCard")(B.reason);
  });
}

/* ---------- my notes ---------- */
function renderNotes() {
  $("#notesBox").innerHTML = '<div class="loading">loading notes…</div>';
  jload("devs_notes_digest").then((d) => {
    const topics = (d.course_notes_advance_pdf || []).map((t) =>
      '<details class="gl"><summary>' + esc(t.topic) + "</summary><ul>" +
      (t.points || []).map((p) => "<li>" + esc(p) + "</li>").join("") + "</ul></details>").join("");
    $("#notesBox").innerHTML = '<div class="note" style="margin-bottom:10px">' + esc(d.note || "") + "</div>" + topics;
  }, fail("notesBox"));
}

/* ---------- deep fundamentals (screener.in weekly) ---------- */
let dfData = null, dfShown = 0;
function renderDeepFund() {
  if (dfData) return;
  $("#dfBody").innerHTML = '<tr><td colspan="12" class="loading">loading deep fundamentals…</td></tr>';
  jload("screener-fundamentals").then((d) => {
    dfData = d;
    const keys = () => Object.keys(d.stocks || {});
    const draw = () => {
      const q = $("#dfSearch").value.trim().toLowerCase();
      const pe = +$("#dfPE").value, roce = +$("#dfROCE").value, sort = $("#dfSort").value;
      let L = keys().filter((k) => {
        const v = d.stocks[k] || {};
        if (q && !k.toLowerCase().includes(q)) return false;
        if (pe && !(v["Stock P/E"] != null && v["Stock P/E"] < pe)) return false;
        if (roce && !(v.ROCE != null && v.ROCE > roce)) return false;
        return true;
      });
      const g = (x) => (x == null ? -1e9 : x);
      L.sort((x, y) => {
        const A = d.stocks[x] || {}, B = d.stocks[y] || {};
        if (sort === "roce") return g(B.ROCE) - g(A.ROCE);
        if (sort === "pe") return g(A["Stock P/E"] == null ? 1e9 : A["Stock P/E"]) - g(B["Stock P/E"] == null ? 1e9 : B["Stock P/E"]);
        if (sort === "growth") return g(B["Net Profit_yoy"]) - g(A["Net Profit_yoy"]);
        if (sort === "prom") return g(B.promoters_pct) - g(A.promoters_pct);
        return g(B["Market Cap"]) - g(A["Market Cap"]);
      });
      $("#dfCount").textContent = L.length + " of " + keys().length + " Nifty-500 stocks · showing " + Math.min(dfShown, L.length) + " · screener.in weekly";
      $("#dfBody").innerHTML = L.slice(0, dfShown).map((k) => {
        const v = d.stocks[k] || {};
        const yoy = (x) => (x == null ? "—" : '<span class="' + pctCls(x) + '">' + sign(x, 1) + "</span>");
        const pl = v.pledge_pct;
        return '<tr><td class="sym"><a href="#company/' + esc(k) + '">' + esc(k) + "</a></td><td>" + nf2(v["Market Cap"]) +
          "</td><td>" + nf2(v["Stock P/E"]) + "</td><td>" + nf2(v.ROCE) +
          "</td><td>" + nf2(v.ROE) + "</td><td>" + nf2(v["Dividend Yield"]) +
          "</td><td>" + (v.promoters_pct == null ? "—" : v.promoters_pct.toFixed(1) + "%") +
          "</td><td>" + (v.fii_pct == null ? "—" : v.fii_pct.toFixed(1) + "%") +
          "</td><td>" + (v.dii_pct == null ? "—" : v.dii_pct.toFixed(1) + "%") +
          "</td><td>" + yoy(v.Sales_yoy) + "</td><td>" + yoy(v["Net Profit_yoy"]) +
          "</td><td>" + (pl == null ? "—" : '<span class="' + (pl > 5 ? "neg" : "neu") + '">' + pl.toFixed(1) + "%</span>") + "</td></tr>";
      }).join("");
      $("#dfMore").style.display = dfShown < L.length ? "block" : "none";
    };
    dfShown = 60; draw();
    ["dfSearch", "dfPE", "dfROCE", "dfSort"].forEach((id) =>
      $("#" + id).addEventListener("input", () => { dfShown = 60; draw(); }));
    $("#dfQuality").onclick = () => {
      $("#dfPE").value = "20"; $("#dfROCE").value = "15"; $("#dfSort").value = "growth";
      dfShown = 60; draw();
    };
    $("#dfMore").onclick = () => { dfShown += 100; draw(); };
  }, fail("dfBody"));
}

/* ---------- futures ---------- */
function renderFutures() {
  $("#futIdx").innerHTML = '<div class="loading">loading futures…</div>';
  jload("futures").then((d) => {
    $("#futIdx").innerHTML = (d.indices || []).map((i) =>
      '<div class="card"><div class="subhead">' + esc(i.symbol) + " futures — spot " + nf2(i.underlying) + "</div>" +
      '<div class="tblwrap"><table><thead><tr><th>Expiry</th><th>Close</th><th>Open interest</th><th>OI change</th><th>Volume</th></tr></thead><tbody>' +
      (i.contracts || []).map((c) => "<tr><td>" + esc(c.expiry) + "</td><td>" + nf2(c.close) +
        "</td><td>" + c.oi.toLocaleString("en-IN") + "</td><td>" +
        (c.oi_chg > 0 ? '<span class="pos">+' : c.oi_chg < 0 ? '<span class="neg">' : '<span class="neu">') +
        c.oi_chg.toLocaleString("en-IN") + "</span></td><td>" + c.volume.toLocaleString("en-IN") + "</td></tr>").join("") +
      "</tbody></table></div></div>").join("");
    $("#futBody").innerHTML = (d.stocks || []).map((s) =>
      '<tr><td class="sym">' + esc(s.symbol) + "</td><td>" + esc(s.expiry) + "</td><td>" + nf2(s.close) +
      "</td><td>" + nf2(s.underlying) + "</td><td>" +
      (s.basis_pct == null ? "—" : '<span class="' + pctCls(s.basis_pct) + '">' + sign(s.basis_pct) + "</span>") +
      "</td><td>" + s.oi.toLocaleString("en-IN") + "</td><td>" +
      (s.oi_chg > 0 ? '<span class="pos">+' : s.oi_chg < 0 ? '<span class="neg">' : '<span class="neu">') +
      s.oi_chg.toLocaleString("en-IN") + "</span></td></tr>").join("");
    $("#futNote").textContent = (d.stock_count || 0) + " F&O stocks · data of " + esc(d.date || "") + " · EOD bhavcopy — India has 3 monthly contracts at a time, no yearly futures";
  }, fail("futIdx"));
}

/* ---------- global ---------- */
function renderGlobal() {
  jload("global").then((d) => {
    const items = d.items || [];
    const byN = (n) => items.filter((x) => x.name === n)[0];
    $("#globKpi").innerHTML = ["S&P 500", "Gold (COMEX)", "Crude Oil WTI", "USD-INR"]
      .map((n) => kpi(n, byN(n))).join("");
    $("#globBody").innerHTML = items.map((s) => {
      const hl = (s.high_52w && s.low_52w) ? nf2(s.high_52w) + " / " + nf2(s.low_52w) : "—";
      const c = s.chg_pct;
      return "<tr><td>" + esc(s.name) + "</td><td>" + nf2(s.price) + "</td><td>" +
        (c == null ? "—" : '<span class="' + pctCls(c) + '">' + sign(c) + "</span>") +
        '</td><td class="num">' + hl + "</td></tr>";
    }).join("");
    $("#globNote").textContent = "updated " + esc((d.updated || "").slice(0, 16)) + " UTC · refreshed every 6h · yfinance (free)";
  }, fail("globBody"));
}

/* ---------- news ---------- */
let newsTopic = "All";
function renderNews() {
  $("#newsBox").innerHTML = '<div class="loading">loading news…</div>';
  jload("news").then((d) => {
    const items = d.items || [];
    const topics = ["All"].concat(Array.from(new Set(items.map((x) => x.topic).filter(Boolean))));
    const draw = () => {
      const L = newsTopic === "All" ? items : items.filter((x) => x.topic === newsTopic);
      $("#newsChips").innerHTML = topics.map((t) =>
        '<button class="chip" data-t="' + esc(t) + '"' +
        (t === newsTopic ? ' style="border-color:var(--border2);color:var(--text);background:var(--glass2)"' : "") +
        ">" + esc(t) + ">" + "</button>").join("");
      $("#newsChips").querySelectorAll(".chip").forEach((b) =>
        b.onclick = () => { newsTopic = b.getAttribute("data-t"); draw(); });
      $("#newsBox").innerHTML = L.slice(0, 60).map((n) =>
        '<div class="card"><div style="display:flex;gap:8px;align-items:baseline;flex-wrap:wrap">' +
        '<span class="pill">' + esc(n.topic || "News") + "</span>" +
        '<span class="footer-note">' + esc((n.time || "").slice(0, 16)) + "</span></div>" +
        '<div style="margin:6px 0"><a href="' + esc(n.link || n.url || "#") + '" target="_blank" rel="noopener" style="color:var(--text);text-decoration:none;font-weight:600">' + esc(n.title) + "</a></div>" +
        '<div class="footer-note">' + esc(n.source || "") + "</div></div>").join("") ||
        '<div class="note">no items</div>';
    };
    draw();
  }, fail("newsBox"));
}

/* ---------- company cards ---------- */
let coIndex = null;
function coSearchDraw() {
  const q = $("#coSearch").value.trim().toUpperCase();
  const body = $("#coResults");
  if (!q) { body.innerHTML = '<div class="note">Type a stock name or symbol — tap a result to open its full company card.</div>'; return; }
  const keys = Object.keys(coIndex || {}).filter((k) => !k.startsWith("_"));
  const L = keys.filter((k) => k.includes(q) ||
    (coIndex[k].name || "").toUpperCase().includes(q)).slice(0, 15);
  body.innerHTML = L.map((k) => '<a class="co-res" href="#company/' + esc(k) + '"><b>' +
    esc(k) + "</b> · " + esc(coIndex[k].name) + '<span class="t-sb"> ' +
    esc(coIndex[k].sector || "") + "</span></a>").join("") || '<div class="note">no match</div>';
}
function coTbl(rows, last) {
  if (!rows || !rows.length) return '<div class="note">no data</div>';
  const R = rows.filter((r) => r.length > 1);
  if (!R.length) return '<div class="note">no data</div>';
  const trim = (r) => (r.length > last + 1 ? [r[0]].concat(r.slice(-last)) : r);
  const shown = R.map(trim);
  const width = shown[0].length;
  const hcells = shown[0].slice(1).map((x) => "<th>" + esc(x) + "</th>").join("");
  const bodyRows = shown.slice(1).filter((r) => r.length === width).map((r) =>
    "<tr><td class=\"lbl\">" + esc(r[0].replace(/\s*\+$/, "")) + "</td>" +
    r.slice(1).map((c) => "<td>" + esc(c) + "</td>").join("") + "</tr>").join("");
  return '<div class="tblwrap"><table><thead><tr><th></th>' + hcells + "</tr></thead><tbody>" +
    bodyRows + "</tbody></table></div>";
}
function drawCompany(d) {
  const box = $("#coBody");
  const p = d.profile || {};
  const top = d.top || {};
  const kpis = ["Market Cap", "Current Price", "Stock P/E", "ROCE", "ROE", "Dividend Yield", "Book Value", "High / Low"]
    .filter((k) => top[k]).map((k) =>
      '<div class="kpi"><div class="k-name">' + esc(k.toUpperCase()) + '</div><div class="k-val" style="font-size:14.5px">' + esc(top[k]) + "</div></div>").join("");
  const off = (p.officers || []).map((o) =>
    '<div class="statline"><span>' + esc(o.title) + '</span><b style="text-align:right">' +
    esc(o.name) + (o.age ? " · " + o.age : "") + "</b></div>").join("");
  box.innerHTML =
    '<div class="card"><div style="display:flex;gap:8px;align-items:baseline;flex-wrap:wrap">' +
    '<b style="font-size:16px">' + esc(d.name) + '</b><span class="badge-tier">' + esc(d.symbol) + "</span></div>" +
    '<div class="note" style="margin-top:4px">' + esc(p.sector || "") + " · " + esc(p.industry || "") +
    (p.employees ? " · " + Number(p.employees).toLocaleString("en-IN") + " employees" : "") + "</div>" +
    (p.website ? '<div class="note" style="margin-top:4px"><a href="' + esc(p.website) +
      '" target="_blank" rel="noopener">' + esc(p.website.replace(/^https?:\/\//, "")) + " ↗</a></div>" : "") + "</div>" +
    '<div class="grid g3" style="margin-top:10px">' + kpis + "</div>" +
    (p.summary ? '<div class="card"><div class="subhead">Company story</div><div class="note">' +
      esc(p.summary) + "</div></div>" : "") +
    (d.about ? '<div class="card"><div class="subhead">About</div><div class="note">' + esc(d.about) + "</div></div>" : "") +
    (d.key_points ? '<div class="card"><div class="subhead">Key points</div><details class="gl"><summary>show</summary><ul><li>' +
      esc(d.key_points) + "</li></ul></details></div>" : "") +
    (off ? '<div class="card"><div class="subhead">Management</div>' + off + "</div>" : "") +
    '<div class="card"><div class="subhead">Quarterly results (Rs Cr)</div>' + coTbl(d.quarters, 6) + "</div>" +
    '<div class="card"><div class="subhead">Profit and Loss — yearly (Rs Cr)</div>' + coTbl(d.profit_loss, 6) + "</div>" +
    '<div class="card"><div class="subhead">Shareholding (%)</div>' + coTbl(d.shareholding, 6) + "</div>" +
    '<div class="footer-note">source: <a href="' + esc(d.url) + '" target="_blank" rel="noopener">screener.in</a> + yfinance · updated ' +
    esc((d.updated || "").slice(0, 16)) + " · educational use only</div>";
}
function renderCompany(sym) {
  const res = $("#coResults"), body = $("#coBody");
  if (!sym) {
    body.innerHTML = "";
    if (!coIndex) {
      jload("company-index").then((d) => { coIndex = d; coSearchDraw(); },
        () => { coIndex = {}; coSearchDraw(); });
    } else coSearchDraw();
    return;
  }
  res.innerHTML = "";
  body.innerHTML = '<div class="loading">loading company card…</div>';
  jload("companies/" + sym.toUpperCase()).then(drawCompany, function () {
    body.innerHTML = '<div class="note">No company card for ' + esc(sym) +
      " yet — cards are being built for all Nifty 500 stocks (weekly). Try RELIANCE, TCS, HDFCBANK, INFY…</div>";
  });
}

/* ---------- app-style view router ---------- */
const loaders = {dash: renderDash, indices: renderIndices, screener: renderScreener,
  fundamentals: renderFundamentals, deepfund: renderDeepFund, futures: renderFutures, ipo: renderIPO, crypto: renderCrypto, global: renderGlobal, news: renderNews, ai: renderAI,
  filings: renderFilings, learn: renderLearn, studies: renderStudies, mynotes: renderNotes};
const loaded = new Set([]);
const views = document.querySelectorAll("section[id]");
function showView(id) {
  let found = false;
  views.forEach((s) => { const on = s.id === id; s.style.display = on ? "" : "none"; if (on) found = true; });
  if (!found) { views.forEach((s) => { s.style.display = s.id === "home" ? "" : "none"; }); id = "home"; }
  if (id !== "home" && !loaded.has(id) && loaders[id]) {
    loaded.add(id);
    try { loaders[id](); } catch (err) { console.error(err); }
  }
  window.scrollTo(0, 0);
}
function routeFromHash() {
  const h = (location.hash || "").replace("#/", "#");
  const parts = h.replace("#", "").split("/");
  const id = parts[0] || "home";
  showView(id);
  if (id === "company") renderCompany(parts[1] || "");
}
window.addEventListener("hashchange", routeFromHash);
$("#coSearch").addEventListener("input", () => { if (!location.hash || location.hash.indexOf("#company") === 0) coSearchDraw(); });
routeFromHash();
