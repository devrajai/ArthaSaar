/* mbscore.js - ArthaSaar Score (TM): 100-point combo (fundamentals + technicals + sentiment + trend AI) + Smart Money + red flags. #screener top */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var DATA = null;

  function bar(label, v, col) {
    var pct = Math.round(4 * v);
    return '<div style="flex:1;min-width:52px;text-align:center">' +
      '<div style="height:5px;border-radius:3px;background:rgba(255,255,255,.12);margin:0 4px"><div style="width:' + pct + '%;max-width:100%;height:5px;border-radius:3px;background:' + col + '"></div></div>' +
      '<div style="font-size:9.5px;opacity:.6;margin-top:2px">' + label + " " + v + "</div></div>";
  }

  function row(sym, e) {
    var sc = e.s, col = sc >= 75 ? "#77f37b" : sc >= 60 ? "rgba(240,180,41,.95)" : sc >= 45 ? "var(--dim)" : "#ff8b8b";
    var smCol = e.sm >= 7 ? "#77f37b" : e.sm >= 4 ? "rgba(240,180,41,.95)" : "#ff8b8b";
    var flagHtml = e.fl ? '<div class="note" style="margin-top:5px;color:#ff8b8b">🚩 ' + esc(e.fl) + "</div>" : "";
    var newsTag = e.nw ? "" : '<span style="font-size:9px;opacity:.45"> (news n/a)</span>';
    return '<details style="margin-top:6px"><summary style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:13.5px;flex-wrap:wrap">' +
      '<b style="min-width:86px">' + esc(sym) + "</b>" +
      '<span style="font-size:11px;opacity:.6;min-width:70px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:110px">' + esc(e.n) + "</span>" +
      '<b style="margin-left:auto;font-size:16px;color:' + col + '">' + sc + "</b><span style='font-size:9px;opacity:.5'>/100</span>" +
      '<span style="font-size:11px;font-weight:700;color:' + smCol + '">💰' + e.sm + "/10</span></summary>" +
      '<div style="padding:6px 14px 10px 14px">' +
      '<div style="display:flex;gap:2px;margin-top:4px">' +
      bar("Funda", e.f, "rgba(126,231,135,.8)") + bar("Tech", e.t, "rgba(88,166,255,.8)") +
      bar("News", e.se, "rgba(240,180,41,.8)") + bar("TrendAI", e.ai, "rgba(255,123,114,.8)") + "</div>" + newsTag + flagHtml +
      '<div class="note" style="margin-top:5px;opacity:.55">Price ₹' + esc(e.p == null ? "-" : e.p) + " · Smart Money " + e.sm + "/10 (FII/DII/promoter/pledge)</div>" +
      "</div></details>";
  }

  function render(box, q) {
    if (!DATA) return;
    q = (q || "").toLowerCase().trim();
    var st = DATA.stocks || {}, syms;
    if (q) syms = Object.keys(st).filter(function (s) { return (s + " " + st[s].n).toLowerCase().indexOf(q) >= 0; }).sort(function (a, b) { return st[b].s - st[a].s; });
    else syms = DATA.top || [];
    var h = "";
    if (!q) h += '<div class="note" style="margin-top:8px">Har stock ko 100-point combo score: <b>Fundamental 25</b> (PE/ROE/growth) + <b>Technical 25</b> (EMA200/52w/RSI) + <b>News Sentiment 25</b> (41 Nifty stocks live) + <b>Trend AI 25</b> (MACD/volume machine signals). 💰 Smart Money 0-10. Tap = breakdown. Neeche red flags bhi. (indicative, advice nahi)</div>';
    if (!syms.length) h += '<div class="note" style="margin-top:10px">koi match nahi mila</div>';
    syms.slice(0, 60).forEach(function (s) { h += row(s, st[s]); });
    if (!q && (DATA.flags || []).length) {
      h += '<div style="font-size:12px;letter-spacing:.6px;opacity:.75;margin-top:16px;font-weight:600;border-left:3px solid #ff8b8b;padding-left:8px">🚩 RED FLAGS (pledge / low promoter)</div>';
      DATA.flags.forEach(function (f) {
        if (!st[f.sym]) return;
        h += '<div class="note" style="margin-top:5px"><b>' + esc(f.sym) + "</b> — " + esc(f.flags.join(", ")) + " · Smart Money " + f.sm + "/10</div>";
      });
    }
    box.innerHTML = h;
  }

  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(240,180,41,.13);border:1px solid rgba(240,180,41,.5);font-size:14.5px;text-align:center"><b style="color:rgba(240,180,41,.95)">\uD83E\uDDE0 ARTHASAAR SCORE\u2122</b> <span style="font-size:11px;opacity:.65">100-point combo · smart money · red flags</span></summary>' +
      '<div style="margin-top:10px"><input id="mbQ" placeholder="stock search... (RELIANCE, TATASTEEL)" style="width:100%;box-sizing:border-box;padding:9px 12px;border-radius:9px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.15);color:inherit;font-size:13px;outline:none"></div>' +
      '<div id="mbBody" class="note" style="margin-top:8px">loading scores...</div>';
    var inp = document.getElementById("mbQ");
    inp.addEventListener("input", function () { render(document.getElementById("mbBody"), inp.value); });
    fetch("data/mb-score.json").then(function (r) { return r.json(); }).then(function (d) {
      DATA = d;
      render(document.getElementById("mbBody"), "");
      var b = document.getElementById("mbBody");
      if (b && d.updated) b.insertAdjacentHTML("afterbegin", '<div class="note" style="margin-bottom:6px">' + esc(d.updated) + " \u00b7 " + d.count + " stocks</div>");
    }).catch(function () {
      var b = document.getElementById("mbBody");
      if (b) b.innerHTML = "data load nahi hua - thodi der baad try karo";
    });
  }

  function mount() {
    var sec = document.querySelector("section#screener");
    if (!sec || document.getElementById("mbScoreCard")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbScoreCard"; c.style.marginTop = "14px";
    var h2 = sec.querySelector("h2");
    if (h2 && h2.parentNode) sec.insertBefore(c, h2.nextSibling); else sec.appendChild(c);
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
