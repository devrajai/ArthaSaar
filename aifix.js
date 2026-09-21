/* aifix.js — patch: TimesFM 3.0 multi-horizon AI view (accuracy, rotation, movers, confidence). Overrides renderAI; sparkline already in app.js. */
const AI_CAT = {index: "Indices", stock: "Top 50 stocks", crypto: "Crypto top 10", global: "Global and FX"};
function aiCard(f) {
      const H = f.horizons || {};
      const hrow = [["7", "7d"], ["14", "14d"], ["30", "30d"], ["3m", "3m"]].map(([k, lb]) =>
        H[k] ? '<span class="' + pctCls(H[k].p) + '" style="margin-right:8px">' + lb + " " + sign(H[k].p, 1) + "</span>" : "").join("");
      return '<div class="kpi"><div class="k-name">' + esc(f.name) +
        (f.confidence != null ? ' <span style="font-size:9px;color:var(--dim);border:1px solid var(--border);border-radius:99px;padding:1px 6px">conf ' + f.confidence + "%</span>" : "") + "</div>" +
        '<div class="k-val" style="font-size:15px">' + nf2(f.as_of_last_close) + " → " +
        nf2(f.median_end) + "</div>" +
        '<div class="k-chg ' + pctCls(f.median_chg_pct) + '">median 21d ' + sign(f.median_chg_pct) +
        ' · band <span class="neg">' + sign(f.low10_chg_pct, 1) + "</span> … <span class=\"pos\">" +
        sign(f.high90_chg_pct, 1) + "</span></div>" +
        '<div style="font-size:10px;margin-top:2px">' + hrow + "</div>" +
        sparkline(f.median_path) + "</div>";
}
