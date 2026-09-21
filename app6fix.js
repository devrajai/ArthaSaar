/* app6fix.js — hotfix: correct filteredStocks (tier NaN bug) */
function filteredStocks() {
  const q = $("#scrSearch").value.trim().toLowerCase();
  const tier = +$("#scrTier").value, rsi = $("#scrRsi").value, ema = $("#scrEma").value;
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
