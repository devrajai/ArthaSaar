/* smart.js — Smart Brain section: kal ka guess, confluence signals,
   result radar, 52W/RS radar + portfolio night report. Data: data/smart-brain.json */
(function () {
  var t = document.querySelector('a.tile[href="#tools"]');
  if (t) t.insertAdjacentHTML("afterend",
    '<a class="tile" href="#smart"><span class="t-ic">🧠</span><span class="t-nm">Smart Brain</span><span class="t-sb">signals · radar</span></a>');
  var sec = document.createElement("section");
  sec.id = "smart"; sec.style.display = "none";
  sec.innerHTML = '<a class="backbtn" href="#home">⌂ Home</a><h2>Smart Brain</h2>' +
    '<div class="card" id="sbGuess"></div>' +
    '<div class="card" id="sbConf"></div>' +
    '<div class="card" id="sbRes"></div>' +
    '<div class="card" id="sbHl"></div>' +
    '<div class="note" style="margin:6px 2px 0">auto-analysis free EOD data par — trading advice nahi, apna dimaag lagao.</div>';
  var ft = document.querySelector("footer");
  if (ft) ft.parentNode.insertBefore(sec, ft); else document.body.appendChild(sec);

  function tbl() { return ""; }
  var pc = function (v) { return '<span class="' + (v >= 0 ? "pos" : "neg") + '">' + (v >= 0 ? "+" : "") + (v == null ? "—" : v) + "%</span>"; };
  var esc2 = function (s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) { return "\x26" + "#x" + c.charCodeAt(0).toString(16) + ";"; }); };

  loaders.smart = function () {
    jload("smart-brain").then(function (d) {
      var g = d.guess || {};
      $("#sbGuess").innerHTML = '<div class="subhead">Kal ka Guess — market regime</div>' +
        '<div style="display:flex;align-items:center;gap:12px;margin:4px 0 8px">' +
        '<div style="font-size:34px;font-weight:700" class="' + (g.score >= 55 ? "pos" : g.score <= 45 ? "neg" : "neu") + '">' + (g.score || 0) + "/100</div>" +
        '<div><b>' + esc2(g.verdict || "—") + "</b>" +
        '<div class="note" style="margin-top:2px">breadth + FII/DII + TimesFM se auto-calculated</div></div></div>' +
        '<div class="meter"><i style="width:' + Math.max(3, g.score || 0) + '%"></i></div>' +
        '<div class="note" style="margin-top:8px">' + (g.points || []).map(function (p) { return "· " + esc2(p); }).join("<br>") + "</div>";

      var cRow = function (c) { return "<tr><td class='sym'><a href='#company/" + encodeURIComponent(c.symbol) + "'>" + esc2(c.symbol) + "</a></td><td>" + c.price + "</td><td>" + pc(c.chg) + "</td><td><b class='" + (c.score >= 0 ? "pos" : "neg") + "'>" + c.score + "</b></td><td class='note'>" + esc2(c.why || "") + "</td></tr>"; };
      $("#sbConf").innerHTML = '<div class="subhead">Confluence — top signals (score −100…+100)</div>' +
        "<div class='subhead' style='margin-top:6px'>🐂 Bull side</div>" +
        '<div class="tblwrap"><table><thead><tr><th>Stock</th><th>₹</th><th>Day%</th><th>Score</th><th>Why</th></tr></thead><tbody>' +
        (d.bull || []).map(cRow).join("") + "</tbody></table></div>" +
        "<div class='subhead' style='margin-top:10px'>🐻 Bear side</div>" +
        '<div class="tblwrap"><table><thead><tr><th>Stock</th><th>₹</th><th>Day%</th><th>Score</th><th>Why</th></tr></thead><tbody>' +
        (d.bear || []).map(cRow).join("") + "</tbody></table></div>";

      var rRow = function (r) { return "<tr><td class='sym'>" + esc2(r.symbol) + "</td><td class='note'>" + esc2(r.company) + "</td><td>" + esc2(r.date) + "</td><td class='note'>" + esc2(r.note) + "</td><td>" + pc(r.chg) + "</td></tr>"; };
      $("#sbRes").innerHTML = '<div class="subhead">Result Radar — results / board meetings (tier-1 filings)</div>' +
        ((d.results || []).length
          ? '<div class="tblwrap"><table><thead><tr><th>Stock</th><th>Company</th><th>Date</th><th>Event</th><th>Day%</th></tr></thead><tbody>' + (d.results || []).map(rRow).join("") + "</tbody></table></div>"
          : "<div class='note'>is hafte koi bada event nahi</div>");

      var hRow = function (x) { return "<tr><td class='sym'><a href='#company/" + encodeURIComponent(x.symbol) + "'>" + esc2(x.symbol) + "</a></td><td class='note'>" + esc2(x.company) + "</td><td>" + x.price + "</td><td>" + pc(x.chg) + "</td></tr>"; };
      var rsRow = function (x) { return "<tr><td class='sym'><a href='#company/" + encodeURIComponent(x.symbol) + "'>" + esc2(x.symbol) + "</a></td><td class='note'>" + esc2(x.company) + "</td><td>" + pc(x.chg) + "</td><td><b class='" + (x.rs >= 0 ? "pos" : "neg") + "'>" + (x.rs >= 0 ? "+" : "") + x.rs + "</b></td></tr>"; };
      $("#sbHl").innerHTML = '<div class="subhead">52-Week Radar + Relative Strength (Nifty ke mukable)</div>' +
        "<div class='subhead' style='margin-top:6px'>🚀 naye 52w High</div>" +
        '<div class="tblwrap"><table><thead><tr><th>Stock</th><th>Company</th><th>₹</th><th>Day%</th></tr></thead><tbody>' + (d.highs || []).map(hRow).join("") + "</tbody></table></div>" +
        "<div class='subhead' style='margin-top:10px'>🕳️ naye 52w Low</div>" +
        '<div class="tblwrap"><table><thead><tr><th>Stock</th><th>Company</th><th>₹</th><th>Day%</th></tr></thead><tbody>' + (d.lows || []).map(hRow).join("") + "</tbody></table></div>" +
        "<div class='subhead' style='margin-top:10px'>💪 sabse tez (RS)</div>" +
        '<div class="tblwrap"><table><thead><tr><th>Stock</th><th>Company</th><th>Day%</th><th>vs Market</th></tr></thead><tbody>' + (d.rs || []).map(rsRow).join("") + "</tbody></table></div>";
    }).catch(function () {
      $("#sbGuess").innerHTML = "<div class='note'>smart-brain data load nahi hua — thodi der baad try karo</div>";
    });
  };

  /* ---- portfolio night report (day P&L + value history) ---- */
  function pfReport() {
    var pf = mbTool.nload("mb-pf");
    if (!pf.length) return;
    jload("brain-screener").then(function (d) {
      var by = {};
      (d.stocks || []).forEach(function (s) { by[s.symbol] = s; });
      var val = 0, day = 0, contrib = [];
      pf.forEach(function (h) {
        var s = by[h.sym] || {}, p = s.price != null ? s.price : h.buy;
        val += p * h.qty;
        if (s.change_pct != null) {
          var c = p * h.qty * s.change_pct / 100;
          day += c; contrib.push([h.sym, c]);
        }
      });
      contrib.sort(function (a, b) { return b[1] - a[1]; });
      var hist = mbTool.nload("mb-pf-hist"), today = new Date().toISOString().slice(0, 10);
      hist = hist.filter(function (x) { return x.d !== today; });
      hist.push({ d: today, v: Math.round(val) });
      if (hist.length > 90) hist = hist.slice(-90);
      mbTool.nsave("mb-pf-hist", hist);
      var box = $("#pfNight");
      if (!box) {
        var card = document.createElement("div");
        card.className = "card";
        card.id = "pfNight";
        var secP = document.querySelector("section#portfolio");
        if (!secP) return;
        secP.insertBefore(card, secP.firstChild);
        box = card;
      }
      var best = contrib[0], worst = contrib[contrib.length - 1];
      box.innerHTML = '<div class="subhead">Aaj ka Portfolio Report</div>' +
        '<div style="display:flex;gap:14px;flex-wrap:wrap;align-items:center">' +
        '<div><div class="note">aaj ka P&L</div><div style="font-size:24px;font-weight:700" class="' + (day >= 0 ? "pos" : "neg") + '">' + (day >= 0 ? "+" : "−") + "₹" + Math.abs(day).toFixed(0) + "</div></div>" +
        '<div><div class="note">value</div><div style="font-size:24px;font-weight:700">₹' + Math.round(val).toLocaleString("en-IN") + "</div></div></div>" +
        (best ? '<div class="note" style="margin-top:6px">sabse zyada diya: <b class="pos">' + esc2(best[0]) + " ₹" + best[1].toFixed(0) + "</b>" +
          (worst && worst[1] < 0 ? " · sabse zyada liya: <b class='neg'>" + esc2(worst[0]) + " ₹" + Math.abs(worst[1]).toFixed(0) + "</b>" : "") + "</div>" : "") +
        (hist.length > 2 ? '<div class="note" style="margin-top:6px">' + sparkline(hist.map(function (x) { return x.v; })) + "</div>" : "");
    });
  }
  if (typeof loaders !== "undefined" && typeof loaders.portfolio === "function") {
    var op = loaders.portfolio;
    loaders.portfolio = function () { op(); setTimeout(pfReport, 800); };
  }
})();
