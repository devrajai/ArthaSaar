/* movement.js - "Why is the market moving?" narrative card. #dash top */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function chip(txt, good, neutral) {
    var col = neutral ? "#9fb0c4" : (good ? "#77f37b" : "#ff8b8b");
    var bg = neutral ? "rgba(255,255,255,.06)" : (good ? "rgba(119,243,123,.1)" : "rgba(255,139,139,.1)");
    var bd = neutral ? "rgba(255,255,255,.15)" : (good ? "rgba(119,243,123,.35)" : "rgba(255,139,139,.35)");
    return '<span style="padding:5px 10px;border-radius:9px;border:1px solid ' + bd + ';background:' + bg + ';color:' + col + ';font-size:12px">' + txt + '</span>';
  }
  function build(card) {
    card.innerHTML = '<div class="subhead">Market Movement Analysis (aaj kyun aisa chal raha hai?)</div><div class="note">load ho raha hai...</div>';
    Promise.all([
      fetch("data/indices-all.json?t=" + Date.now()).then(function (r) { return r.json(); }),
      fetch("data/fii-dii.json?t=" + Date.now()).then(function (r) { return r.json(); }).catch(function () { return {}; }),
      fetch("data/global.json?t=" + Date.now()).then(function (r) { return r.json(); }).catch(function () { return {}; }),
      fetch("data/gti.json?t=" + Date.now()).then(function (r) { return r.json(); }).catch(function () { return {}; }),
      fetch("data/news.json?t=" + Date.now()).then(function (r) { return r.json(); }).catch(function () { return {}; })
    ]).then(function (R) {
      var ind = R[0].indices || [], fii = R[1], glo = R[2], gti = R[3], news = R[4];
      function get(name) {
        for (var i = 0; i < ind.length; i++) if (ind[i].index === name || ind[i].symbol === name) return ind[i];
        return null;
      }
      var nifty = get("NIFTY 50") || get("NIFTY 50 INDEX") || (ind[0] || {});
      var bank = get("NIFTY BANK") || get("BANKNIFTY");
      var skip = ["NIFTY 50", "NIFTY BANK", "BANKNIFTY", "NIFTY NEXT 50", "INDIA VIX"];
      var secs = ind.filter(function (x) {
        var n = String(x.index || "");
        return n.indexOf("NIFTY") >= 0 && skip.indexOf(n) < 0 && n.split(" ").length <= 3;
      });
      secs.sort(function (a, b) { return (a.change_pct || 0) - (b.change_pct || 0); });
      var drags = secs.slice(0, 2), sups = secs.slice(-2).reverse();
      var fiiNet = ((fii.categories || {})["FII/FPI"] || {}).net_cr;
      var diiNet = ((fii.categories || {})["DII"] || {}).net_cr;
      var g50 = (glo.items || []).filter(function (x) { return ["S&P 500", "Nasdaq Composite", "Dow Jones", "Hang Seng", "Nikkei 225"].indexOf(x.name) >= 0; }).slice(0, 2);
      var nzone = ((gti.symbols || {})["NIFTY 50"] || {}).zone;
      var newsN = (news.items || []).length;
      var pct = nifty.change_pct || 0;
      var h = '<div class="note" style="margin-top:8px"><b>' + esc(nifty.index || "NIFTY") + ' ' + (pct >= 0 ? "+" : "") + pct + '%</b> - kyun? (aaj ka story)</div>';
      h += '<div class="note" style="display:flex;flex-wrap:wrap;gap:6px;margin-top:10px">';
      if (bank) h += chip("Bank Nifty " + (bank.change_pct >= 0 ? "+" : "") + bank.change_pct + "%", bank.change_pct >= 0);
      drags.forEach(function (s) { h += chip(esc((s.index || "").replace("NIFTY ", "")) + " " + s.change_pct + "% (pressure)", false); });
      sups.forEach(function (s) { if ((s.change_pct || 0) > 0) h += chip(esc((s.index || "").replace("NIFTY ", "")) + " +" + s.change_pct + "% (support)", true); });
      if (fiiNet != null) h += chip("FII net " + Math.round(fiiNet) + " Cr", fiiNet >= 0);
      if (diiNet != null) h += chip("DII net " + Math.round(diiNet) + " Cr", diiNet >= 0);
      g50.forEach(function (g0) { h += chip(esc(g0.name) + " " + (g0.chg_pct >= 0 ? "+" : "") + g0.chg_pct + "% (global)", g0.chg_pct >= 0, g0.chg_pct > -0.3 && g0.chg_pct < 0.3); });
      if (nzone) h += chip("GTI zone: " + esc(String(nzone).toUpperCase()), String(nzone).toUpperCase().indexOf("SD") >= 0, String(nzone).toUpperCase().indexOf("S") < 0);
      if (newsN) h += chip(newsN + " news detected", true, true);
      h += '</div>';
      var story = [];
      if (drags.length) story.push(drags[0].index.replace("NIFTY ", "") + (drags.length > 1 ? " + " + drags[1].index.replace("NIFTY ", "") : "") + " daba raha hai");
      if (sups.length && (sups[0].change_pct || 0) > 0) story.push(sups[0].index.replace("NIFTY ", "") + " support de raha hai");
      if (fiiNet != null) story.push(fiiNet < 0 ? "FII bech rahe hain" + (diiNet > 0 ? " (DII kharid rahe)" : "") : "FII kharid rahe hain");
      if (bank && (bank.change_pct || 0) < -0.5) story.push("Banking pressure heavy");
      h += '<div class="note" style="margin-top:12px;border-left:3px solid rgba(240,180,41,.7);padding:8px 12px;background:rgba(240,180,41,.07);border-radius:0 8px 8px 0"><b>Insight:</b> ' + (story.join(", ") || "mixed signals - ek direction nahi") + '. Kal subah digest Telegram pe aayega.</div>';
      card.innerHTML = '<div class="subhead">Market Movement Analysis (aaj kyun aisa chal raha hai?)</div>' + h;
    }).catch(function () { card.innerHTML = '<div class="subhead">Market Movement Analysis</div><div class="note">data nahi mila.</div>'; });
  }
  function mount() {
    var sec = document.querySelector("section#dash");
    if (!sec || document.getElementById("mbMove")) return;
    var c = document.createElement("div");
    c.className = "card"; c.id = "mbMove"; c.style.marginTop = "14px";
    var first = sec.querySelector(".card");
    if (first) sec.insertBefore(c, first); else sec.appendChild(c);
    try { build(c); } catch (e) { c.innerHTML = '<div class="subhead">Market Movement Analysis</div><div class="note">error</div>'; }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
