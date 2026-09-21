/* scrfix.js — patch: screener EMA-fix + AI bullish chip (TimesFM). Loads after app.js, overrides its functions. */
let scrAI = false, aiBullish = null;  /* patch state; scrData/scrShown declared in app.js */
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
