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
  P.push(Promise.all([jload("indices-all"), jload("futures")]).then(([ix, f]) => {
    fresh.push("PCR " + esc(f.date || ""));
    const vix = idxByName(ix.indices || [], "INDIA VIX");
    const pcr = f.pcr || {};
    const row = (label, val, cls) => '<div class="statline"><span>' + label + "</span><b" +
      (cls ? ' class="' + cls + '"' : "") + ' style="text-align:right">' + val + "</b></div>";
    $("#vixBox").innerHTML =
      row("India VIX", vix ? nf2(vix.price) + " (" + sign(vix.change_pct) + ")" : "—",
        vix ? pctCls(vix.change_pct) : "") +
      row("Nifty PCR (OI)", pcr.nifty_pcr_oi != null ? pcr.nifty_pcr_oi : "—") +
      row("Nifty PCR (volume)", pcr.nifty_pcr_vol != null ? pcr.nifty_pcr_vol : "—") +
      row("Nifty max pain", pcr.nifty_max_pain != null ? nf2(pcr.nifty_max_pain) : "—") +
      '<div class="note" style="margin-top:6px">PCR > 1.2: heavy put buying (fear) · PCR < 0.7: heavy call buying (greed). Max pain = strike where option writers lose least on ' +
      esc(pcr.nifty_expiry || "expiry") + ".</div>";
  }, fail("vixBox")));
  Promise.allSettled(P).then(() => {
    $("#dataFresh").textContent = "data: " + fresh.join(" · ");
  });
}

