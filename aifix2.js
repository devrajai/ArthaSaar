/* aifix2.js - patch: TimesFM 3.0 AI view, header half (accuracy, rotation, movers). */
let aiF = [], aiExtra = "";
function renderAI() {
  jload("timesfm_forecasts").then((d) => { renderAIHead(d); renderAIGrid(); }, fail("aiGrid"));
}
function renderAIHead(d) {
    const F = d.forecasts || [];
    const up = F.filter((f) => f.direction === "up").length;
    const acc = d.accuracy || {};
    const accTxt = acc.rate != null ? acc.rate + "% (" + acc.hits + " of " + acc.tracked + " past forecasts)" : "building — needs ~1 month of daily runs";
    $("#aiHead").innerHTML = '<div class="kv"><span>Model</span><b>' + esc(d.model) +
      "</b><span>Coverage</span><b>" + F.length + " series — indices, top 50 stocks, crypto, global</b>" +
      "<span>Horizons</span><b>7d · 14d · 21d · 30d · 3 months (daily update)</b>" +
      "<span>Updated</span><b>" + esc((d.updated || "").slice(0, 10)) + "</b>" +
      '<span>Bias 21d</span><b>' + up + " up · " + (F.length - up) + " down / flat</b>" +
      "<span>Direction accuracy</span><b>" + accTxt + "</b></div>" +
      '<div class="note" style="margin-top:8px">' + esc(d.disclaimer) + "</div>";
    let extra = "";
    if ((d.rotation || []).length) {
      extra += '<div class="hgroup">SECTOR ROTATION — 30-day forecast ranked</div><div class="card">' +
        d.rotation.map((s, i) => '<div class="statline"><span>' + (i + 1) + ". " + esc(s.name) +
          '</span><b class="' + pctCls(s.chg30) + '">' + sign(s.chg30, 1) + " · conf " + s.conf + "%</b></div>").join("") +
        '<div class="footer-note">ranked by TimesFM 30-day median · top = strongest forecast · not advice</div></div>';
    }
    if ((d.movers || []).length) {
      extra += '<div class="hgroup">EXPECTED BIG MOVERS — widest 21-day bands</div><div class="card">' +
        d.movers.slice(0, 12).map((s) => '<div class="statline"><span>' + esc(s.name) +
          '</span><b>±' + (s.band / 2).toFixed(1) + '% band · median <span class="' + pctCls(s.median) + '">' + sign(s.median, 1) + "</span></b></div>").join("") +
        '<div class="footer-note">widest forecast bands = biggest expected swings (either direction)</div></div>';
    }
    aiF = F; aiExtra = extra;
}
