/* aifix3.js - patch: TimesFM 3.0 AI view, grid half (categories, horizons, confidence). */
function renderAIGrid() {
  const F = aiF, extra = aiExtra;
    if (F.some((f) => f.cat)) {
      $("#aiGrid").className = "";
      $("#aiGrid").innerHTML = extra + ["index", "stock", "crypto", "global"].map((c) => {
        const L = F.filter((f) => f.cat === c);
        if (!L.length) return "";
        return '<div class="hgroup">' + (AI_CAT[c] || c) + " (" + L.length + ")</div>" +
          '<div class="grid g2">' + L.map(aiCard).join("") + "</div>";
      }).join("");
    } else {
      $("#aiGrid").innerHTML = F.map(aiCard).join("");
    }
}
