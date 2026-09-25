/* stage.js - STOCK STAGE DETECTOR: 4-Stage (notebook rules). #screener */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var DATA = null;
  var ST = {
    1: ["S1 \u00b7 BASE", "#f5c542", "Neeche se theek ho raha hai \u2014 base bana raha hai (taiyari). Swing traders dhyan dein, breakout ka wait karo."],
    2: ["S2 \u00b7 UP", "#77f37b", "UPTREND! 4W MA > 8W MA aur price 40W MA ke upar \u2014 notebook ka \u2018dancing area\u2019 buy stage. Trend follow karo."],
    3: ["S3 \u00b7 TOP", "#ff8b8b", "TOPPING! Price abhi upar hai lekin short MA neeche gir raha hai \u2014 profit book karna socho (trailing SL)."],
    4: ["S4 \u00b7 DOWN", "#ff5c5c", "DOWNTREND \u2014 40W MA ke neeche, MA bhi gir raha. Falling knife mat pakdo, stage 1 ka wait karo."]
  };

  function detail(sym) {
    var st = DATA.all[sym];
    var box = document.getElementById("stgDetail");
    if (!st) { box.innerHTML = "<div class='note'>nahi mila \u2014 symbol check karo</div>"; return; }
    var wk = DATA.w[sym] || [];
    var lo = Infinity, hi = -Infinity;
    wk.forEach(function (v) { if (v != null) { if (v < lo) lo = v; if (v > hi) hi = v; } });
    var bars = "";
    wk.forEach(function (v) {
      if (v == null) return;
      var h = Math.max(8, Math.round(44 * (v - lo) / Math.max(0.01, hi - lo)));
      bars += '<div title="' + esc(v) + '" style="width:7px;height:' + h + 'px;background:' + (st[0] === 2 ? "#77f37b" : st[0] === 4 ? "#ff5c5c" : "#f5c542") + ';border-radius:2px;opacity:.85"></div>';
    });
    var s = ST[st[0]] || ST[1];
    box.innerHTML = '<div style="padding:8px 12px;border:1px solid ' + s[1] + ';border-radius:10px;background:rgba(255,255,255,.04)">' +
      '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><b style="font-size:15px">' + esc(sym) + '</b>' +
      '<span style="font-weight:800;color:' + s[1] + '">' + s[0] + '</span>' +
      '<span style="margin-left:auto;font-size:11.5px;opacity:.7">\u20B9' + esc(wk.length ? wk[wk.length - 1] : "?") + ' \u00b7 52W high se ' + esc(st[1]) + '%</span></div>' +
      '<div style="display:flex;align-items:flex-end;gap:2px;height:52px;margin-top:8px">' + bars + '</div>' +
      '<div style="font-size:11px;opacity:.6;margin-top:4px">\u2190 ' + (DATA.wl && DATA.wl[0] ? esc(DATA.wl[0]) : "") + ' se ab tak weekly closes</div>' +
      '<div class="note" style="margin-top:6px">' + s[2] + '</div></div>';
  }

  function render(box) {
    var c = DATA.counts || {};
    var h = '<div class="note" style="margin-top:8px"><b>Har stock kis stage me hai</b> (weekly chart pe notebook rules se): ' +
      '<span style="color:#f5c542">\u26A0 S1 ' + (c[1] || 0) + '</span> \u00b7 <span style="color:#77f37b">\u2191 S2 ' + (c[2] || 0) + '</span> \u00b7 <span style="color:#ff8b8b">\u26A0 S3 ' + (c[3] || 0) + '</span> \u00b7 <span style="color:#ff5c5c">\u2193 S4 ' + (c[4] || 0) + '</span> (S2 = uptrend, long-term wealth focus). Data: ' + esc(DATA.updated) + ' \u00b7 ' + (DATA.wl ? DATA.wl.length : "?") + ' hafte.</div>';
    h += '<input id="stgQ" placeholder="\uD83D\uDD0D stock naam likho (e.g. RELIANCE)" style="width:100%;box-sizing:border-box;margin-top:8px;padding:8px 10px;border-radius:9px;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.07);color:#fff;font-size:13px">';
    h += '<div id="stgDetail" style="margin-top:8px"></div>';
    h += '<div style="margin-top:10px;font-size:13px;font-weight:700;opacity:.85">\u2B50 Top Stage-2 stocks (52W high ke sabse paas \u2014 sabse strong):</div>';
    (DATA.top2 || []).forEach(function (t, i) {
      h += '<div data-sym="' + esc(t[0]) + '" class="stgRow" style="display:flex;gap:8px;align-items:center;padding:7px 10px;margin-top:5px;border-radius:9px;background:rgba(119,243,123,.07);border:1px solid rgba(119,243,123,.25);cursor:pointer;font-size:13px">' +
        '<span style="opacity:.5;width:20px">' + (i + 1) + '</span><b>' + esc(t[0]) + '</b>' +
        '<span style="opacity:.75">\u20B9' + esc(t[1]) + '</span>' +
        '<span style="margin-left:auto;font-size:11.5px;color:' + (t[2] > -5 ? "#77f37b" : t[2] > -15 ? "#f5c542" : "#ff8b8b") + '">52WH se ' + esc(t[2]) + '%</span></div>';
    });
    box.innerHTML = h;
    var q = document.getElementById("stgQ");
    q.addEventListener("input", function () {
      var v = this.value.trim().toUpperCase();
      if (!v) return;
      var hits = Object.keys(DATA.all).filter(function (k) { return k.indexOf(v) === 0 || k.indexOf(v) > -1; }).slice(0, 6);
      if (hits.length === 1 || (hits.length && hits[0] === v)) detail(hits[0]);
    });
    Array.prototype.forEach.call(box.querySelectorAll(".stgRow"), function (r) {
      r.addEventListener("click", function () { detail(this.getAttribute("data-sym")); });
    });
  }

  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(240,180,41,.13);border:1px solid rgba(240,180,41,.5);font-size:14.5px;text-align:center"><b style="color:rgba(240,180,41,.95)">\uD83D\uDCC8 STAGE DETECTOR</b> <span style="font-size:11px;opacity:.65">4-Stage \u00b7 notebook rules \u00b7 long-term</span></summary>' +
      '<div id="stgBody" class="note" style="margin-top:8px">loading stages...</div>';
    fetch("data/stages.json").then(function (r) { return r.json(); }).then(function (d) {
      DATA = d; render(document.getElementById("stgBody"));
    }).catch(function () {
      var b = document.getElementById("stgBody");
      if (b) b.innerHTML = "data load nahi hua \u2014 thodi der baad try karo";
    });
  }

  function mount() {
    var sec = document.querySelector("section#screener");
    if (!sec || document.getElementById("mbStage")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbStage"; c.style.marginTop = "14px";
    var anchor = document.getElementById("mbBank");
    if (anchor && anchor.nextSibling) anchor.parentNode.insertBefore(c, anchor.nextSibling);
    else if (anchor) anchor.parentNode.appendChild(c);
    else {
      var sc = document.getElementById("mbScoreCard");
      if (sc && sc.parentNode) sc.parentNode.insertBefore(c, sc); else sec.appendChild(c);
    }
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
