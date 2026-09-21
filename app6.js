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
let scrData = null, scrShown = 0, scrAI = false, aiBullish = null;
function filteredStocks() {
  const q = $("#scrSearch").value.trim().toLowerCase();
  const tier = + ("#scrTier").value, rsi = $("#scrRsi").value, ema = $("#scrEma").value;
  const sort = $("#scrSort").value;
  let L = (scrData.stocks || []).filter((s) =>
    (!q || s.symbol.toLowerCase().includes(q) || (s.company || "").toLowerCase().includes(q)) &&
    (!tier || s.tier === tier) &&
    (!ema || ema === "all" || (ema === "above" ? s.above_ema200 : !s.above_ema200)) &&
    (!scrAI || !aiBullish || aiBullish.has(s.symbol)));
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
    jload("timesfm_forecasts").then((tf) => {
      aiBullish = new Set((tf.forecasts || [])
        .filter((f) => f.direction === "up" && f.symbol.indexOf(".NS") !== -1)
        .map((f) => f.symbol.replace(".NS", "")));
    }, () => { aiBullish = new Set(); });
    const aiBtn = $("#scrAI");
    if (aiBtn) aiBtn.onclick = () => {
      scrAI = !scrAI;
      aiBtn.classList.toggle("on", scrAI);
      scrShown = 60;
      draw();
    };
  }, fail("scrBody"));
}

