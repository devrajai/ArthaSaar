/* MARKET BRAIN part 3 — view router tail. Loaded after app.js and app2.js. */
const loaders = {dash: renderDash, indices: renderIndices, heatmap: renderHeatmap, screener: renderScreener, events: renderEvents,
  charts: renderCharts, portfolio: renderPortfolio,
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
/* refresh should always open clean at home — no pre-selected section */
(function () {
  const h = location.hash || "";
  if (h && h.indexOf("#company") !== 0 && h !== "#lock") {
    try { history.replaceState(null, "", location.pathname + location.search); } catch (e) {}
  }
})();
$("#coSearch").addEventListener("input", () => { if (!location.hash || location.hash.indexOf("#company") === 0) coSearchDraw(); });
routeFromHash();
