/* circuit.js v2 - Circuit Scanner: NSE upper/lower circuit stocks (1-20% bands) + 7-day history (daily % bars, circuit hits, UC/LC trend). #screener top */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var DATA = null;

  function fmtCr(v) {
    if (v >= 100000) return "\u20B9" + (v / 100000).toFixed(2) + " L cr";
    if (v >= 100) return "\u20B9" + Math.round(v) + " cr";
    return "\u20B9" + v.toFixed(1) + " cr";
  }

  // 7-din UC/LC count trend: green up bars (UC) + red down bars (LC)
  function trend(tr) {
    if (!tr || !tr.length) return "";
    var mx = 1;
    tr.forEach(function (t) { mx = Math.max(mx, t.uc, t.lc); });
    var h = '<div style="margin-top:10px"><div style="font-size:12px;font-weight:700;opacity:.85">7-din circuit trend</div>' +
      '<div style="display:flex;align-items:stretch;gap:4px;height:44px;margin-top:4px">';
    tr.forEach(function (t) {
      var ub = Math.max(2, Math.round(18 * t.uc / mx));
      var db = Math.max(2, Math.round(18 * t.lc / mx));
      h += '<div title="' + esc(t.d) + ': ' + t.uc + ' UC / ' + t.lc + ' LC" style="flex:1;display:flex;flex-direction:column">' +
        '<div style="flex:1;display:flex;align-items:flex-end"><div style="width:100%;height:' + ub + 'px;border-radius:2px 2px 0 0;background:#77f37b"></div></div>' +
        '<div style="height:1px;background:rgba(255,255,255,.3)"></div>' +
        '<div style="flex:1"><div style="width:100%;height:' + db + 'px;border-radius:0 0 2px 2px;background:#ff8b8b"></div></div></div>';
    });
    h += '</div><div style="display:flex;gap:4px;margin-top:2px">' +
      tr.map(function (t) { return '<div style="flex:1;text-align:center;font-size:8.5px;opacity:.55">' + esc(t.d.split(" ")[0]) + '</div>'; }).join("") + '</div>' +
      '<div class="note" style="margin-top:3px;font-size:10.5px;opacity:.6">har din kitne stocks UC (upar green) / LC (neeche red) pe band hue - tap karke exact number</div></div>';
    return h;
  }

  // per-stock 7-din daily % mini bars
  function d7bars(d7) {
    if (!d7 || !d7.length) return "";
    var vals = d7.filter(function (v) { return v != null; });
    if (!vals.length) return "";
    var mx = 1;
    vals.forEach(function (v) { mx = Math.max(mx, Math.abs(v)); });
    var h = '<div style="display:flex;align-items:stretch;gap:1px;height:20px;min-width:76px">';
    d7.forEach(function (v) {
      if (v == null) {
        h += '<div style="flex:1;display:flex;align-items:center;justify-content:center"><div style="width:60%;height:1px;background:rgba(255,255,255,.15)"></div></div>';
        return;
      }
      var bh = Math.max(2, Math.round(9 * Math.abs(v) / mx));
      var up = v >= 0;
      h += '<div title="' + (up ? "+" : "") + esc(v) + '%" style="flex:1;display:flex;flex-direction:column">' +
        '<div style="flex:1;display:flex;align-items:flex-end">' + (up ? '<div style="width:100%;height:' + bh + 'px;background:rgba(119,243,123,.75)"></div>' : '<div style="flex:1"></div>') + '</div>' +
        '<div style="height:1px;background:rgba(255,255,255,.2)"></div>' +
        '<div style="flex:1">' + (up ? '<div style="flex:1"></div>' : '<div style="width:100%;height:' + bh + 'px;background:rgba(255,139,139,.75)"></div>') + '</div></div>';
    });
    h += '</div>';
    return h;
  }

  function bandRow(grp, isUp) {
    var h = '<details style="margin-top:6px"><summary style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:13.5px;flex-wrap:wrap">' +
      '<b style="min-width:56px;font-size:14px;color:' + (isUp ? "#77f37b" : "#ff8b8b") + '">' + grp.b + '%</b>' +
      '<span style="font-size:12.5px">' + (isUp ? "Upper" : "Lower") + ' Circuit</span>' +
      '<span style="margin-left:auto;font-size:11.5px;font-weight:700;color:rgba(240,180,41,.95)">' + grp.n + ' stocks</span></summary>' +
      '<div style="padding:2px 14px 8px 14px">';
    grp.top.forEach(function (x) {
      h += '<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:12.5px;flex-wrap:wrap">' +
        '<div style="display:flex;align-items:center;gap:8px;min-width:170px"><b style="min-width:92px">' + esc(x.s) + '</b>' + d7bars(x.d7) + '</div>' +
        '<span style="min-width:58px;opacity:.8">\u20B9' + esc(x.c) + '</span>' +
        '<b style="min-width:50px;color:' + (x.p >= 0 ? "#77f37b" : "#ff8b8b") + '">' + (x.p > 0 ? "+" : "") + esc(x.p) + '%</b>' +
        (x.h && x.h >= 2 ? '<span style="font-size:10px;font-weight:700;color:rgba(240,180,41,.95)">\u26A1' + x.h + '/7</span>' : "") +
        '<span style="margin-left:auto;opacity:.55;font-size:11px">' + fmtCr(x.v) + '</span></div>';
    });
    if (grp.n > grp.top.length) h += '<div class="note" style="margin-top:4px">...aur ' + (grp.n - grp.top.length) + ' stocks (value ke hisaab se top ' + grp.top.length + ' dikhe)</div>';
    h += '</div></details>';
    return h;
  }

  function render(box) {
    var d = DATA;
    var h = '<div class="note" style="margin-top:8px">' + esc(d.updated) + ' \u00b7 ' + d.n_uc + ' upper + ' + d.n_lc + ' lower circuit stocks. Upper = sellers khatam (buyer ka raj), lower = buyers khatam. Stock ke saath uske 7-din ka daily % (bars) + \u26A1n/7 = 7 din me kitni baar circuit laga. Band % tap karke list dekho. (indicative, advice nahi)</div>';
    h += trend(d.tr);
    h += '<div style="margin-top:8px;font-size:13px;font-weight:700;color:#77f37b">\uD83D\uDFE2 UPPER CIRCUIT (' + d.n_uc + ')</div>';
    (d.uc || []).forEach(function (g) { h += bandRow(g, true); });
    h += '<div style="margin-top:10px;font-size:13px;font-weight:700;color:#ff8b8b">\uD83D\uDD34 LOWER CIRCUIT (' + d.n_lc + ')</div>';
    (d.lc || []).forEach(function (g) { h += bandRow(g, false); });
    box.innerHTML = h;
  }

  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(240,180,41,.13);border:1px solid rgba(240,180,41,.5);font-size:14.5px;text-align:center"><b style="color:rgba(240,180,41,.95)">\u26A1 CIRCUIT SCANNER</b> <span style="font-size:11px;opacity:.65">upper \u00b7 lower \u00b7 1-20% \u00b7 7-din history</span></summary>' +
      '<div id="csBody" class="note" style="margin-top:8px">loading circuits...</div>';
    fetch("data/circuits.json").then(function (r) { return r.json(); }).then(function (d) {
      DATA = d; render(document.getElementById("csBody"));
    }).catch(function () {
      var b = document.getElementById("csBody");
      if (b) b.innerHTML = "data load nahi hua - thodi der baad try karo";
    });
  }

  function mount() {
    var sec = document.querySelector("section#screener");
    if (!sec || document.getElementById("mbCircuits")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbCircuits"; c.style.marginTop = "14px";
    var ref = document.getElementById("mbScoreCard") || sec.querySelector("h2");
    if (ref && ref.parentNode) ref.parentNode.insertBefore(c, ref); else sec.appendChild(c);
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
