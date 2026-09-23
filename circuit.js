/* circuit.js v4 - Circuit Scanner + stock search + NSE band change flash. #screener top */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var DATA = null, DAYS = [];

  function fmtCr(v) {
    if (v >= 100000) return "\u20B9" + (v / 100000).toFixed(2) + " L cr";
    if (v >= 100) return "\u20B9" + Math.round(v) + " cr";
    return "\u20B9" + v.toFixed(1) + " cr";
  }

  // 7-din UC/LC count trend
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
      tr.map(function (t) { return '<div style="flex:1;text-align:center;font-size:8.5px;opacity:.55">' + esc(t.d.split(" ")[0]) + '</div>'; }).join("") + '</div></div>';
    return h;
  }

  // per-stock 7-din daily % mini bars (list rows)
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
    return h + '</div>';
  }

  // ============ NSE BAND CHANGE FLASH ============
  function bandAlert(b) {
    if (!b || !b.ch) return "";
    var ch = b.ch;
    var h = '<div style="margin-top:10px;padding:10px 12px;border-radius:11px;background:rgba(255,139,139,.1);border:1.5px solid rgba(255,139,139,.55)">' +
      '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap"><b style="font-size:13.5px;color:#ff8b8b">\uD83D\uDEA8 NSE ne circuit band BADLE - ' + ch.length + ' stock' + (ch.length > 1 ? 's' : '') + '</b>' +
      '<span style="font-size:10px;opacity:.5">' + esc(b.updated) + ' \u00b7 surveillance decision, broker-only info</span></div>';
    ch.forEach(function (c) {
      var f = parseFloat(c.f), t = parseFloat(c.t);
      var tight = !isNaN(f) && !isNaN(t) && t < f;
      h += '<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:12.5px;flex-wrap:wrap">' +
        '<b style="min-width:86px">' + esc(c.s) + '</b>' +
        '<span style="min-width:44px;opacity:.6">' + esc(c.f) + '%</span>\u2192' +
        '<b style="min-width:44px;color:' + (tight ? "#ff8b8b" : "#77f37b") + '">' + esc(c.t) + '%</b>' +
        '<span style="font-size:10px;font-weight:700;color:' + (tight ? "#ff8b8b" : "#77f37b") + '">' + (tight ? "TIGHT (risk/monitoring)" : "LOOSE (zyada move possible)") + '</span>' +
        '<span style="margin-left:auto;font-size:10px;opacity:.45">' + esc(c.n) + '</span></div>';
    });
    h += '<div class="note" style="margin-top:5px;font-size:10.5px;opacity:.6">Band = din bhar max move limit. NSE/SEBI ye roz badalta hai - broker ko pata chalta hai, normal apps me nahi dikhta. Tight = stock par monitoring badhi.</div>';
    if (b.hist && b.hist.length > 1) {
      h += '<details style="margin-top:6px"><summary style="cursor:pointer;font-size:11.5px;opacity:.7">7-din ka band changes</summary><div>';
      b.hist.forEach(function (hd) {
        h += '<div style="padding:4px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:11.5px"><b>' + esc(hd.d) + '</b> \u00b7 ' + hd.n + ' change' + (hd.n > 1 ? 's' : '') +
          (hd.n ? ' \u2014 ' + hd.list.map(function (c) { return esc(c.s) + ' ' + esc(c.f) + '%\u2192' + esc(c.t) + '%'; }).join(', ') : ' (koi change nahi)') + '</div>';
      });
      h += '</div></details>';
    }
    h += '</div>';
    return h;
  }

  // ============ STOCK DETAIL (search/tap) ============
  // all[sym] = [d1..d7, flags, u, l, close, band]
  function detailHtml(sym) {
    var a = DATA.all[sym];
    if (!a) return "";
    var d7 = a.slice(0, 7), fl = String(a[7] || "0000000"), u = a[8] || 0, l = a[9] || 0, c = a[10], band = a[11] || "?";
    var vals = d7.filter(function (v) { return v != null; });
    var mx = 1;
    vals.forEach(function (v) { mx = Math.max(mx, Math.abs(v)); });
    var tot = 1;
    d7.forEach(function (v) { if (v != null) tot *= (1 + v / 100); });
    var net = (tot - 1) * 100;
    var h = '<div id="csDet" style="margin-top:8px;padding:10px;border-radius:11px;background:rgba(240,180,41,.08);border:1px solid rgba(240,180,41,.35)">' +
      '<div style="display:flex;align-items:baseline;gap:8px;flex-wrap:wrap"><b style="font-size:16px;color:rgba(240,180,41,.95)">' + esc(sym) + '</b>' +
      '<span style="font-size:13px;opacity:.85">\u20B9' + esc(c) + '</span>' +
      '<span style="font-size:12px;font-weight:700;color:' + (net >= 0 ? "#77f37b" : "#ff8b8b") + '">' + (net >= 0 ? "+" : "") + net.toFixed(1) + '% (7-din net)</span>' +
      '<span style="font-size:11px;padding:2px 8px;border-radius:8px;background:rgba(255,255,255,.08)">' + (band === "nb" ? "no band (F&O)" : band === "?" ? "" : "band " + esc(band) + "%") + '</span>' +
      '<span style="margin-left:auto;font-size:16px;cursor:pointer;opacity:.6" id="csDetX">\u2715</span></div>';
    h += '<div style="display:flex;align-items:stretch;gap:3px;height:64px;margin-top:10px">';
    d7.forEach(function (v, i) {
      var dl = DAYS[i] ? DAYS[i].split(" ")[0] : (i + 1);
      var chip = "";
      if (v != null && fl.charAt(i) === "1") chip = '<span style="font-size:8px;font-weight:800;color:#77f37b">UC</span>';
      else if (v != null && fl.charAt(i) === "2") chip = '<span style="font-size:8px;font-weight:800;color:#ff8b8b">LC</span>';
      if (v == null) {
        h += '<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center"><span style="font-size:8.5px;opacity:.3">-</span></div>';
        return;
      }
      var bh = Math.max(3, Math.round(22 * Math.abs(v) / mx));
      var up = v >= 0;
      h += '<div title="' + (DAYS[i] || "") + ': ' + (up ? "+" : "") + esc(v) + '%' + (chip ? " CIRCUIT" : "") + '" style="flex:1;display:flex;flex-direction:column;align-items:center">' +
        chip +
        '<div style="flex:1;width:100%;display:flex;flex-direction:column;justify-content:center">' +
        '<div style="flex:1"></div>' + (up ? '<div style="width:100%;height:' + bh + 'px;border-radius:2px 2px 0 0;background:rgba(119,243,123,.85)"></div>' : "") +
        '<div style="height:1px;background:rgba(255,255,255,.25)"></div>' +
        (up ? "" : '<div style="width:100%;height:' + bh + 'px;border-radius:0 0 2px 2px;background:rgba(255,139,139,.85)"></div>') + '<div style="flex:1"></div></div>' +
        '<span style="font-size:8.5px;font-weight:700;color:' + (up ? "#77f37b" : "#ff8b8b") + '">' + (up ? "+" : "") + esc(v) + '</span>' +
        '<span style="font-size:8px;opacity:.5">' + esc(dl) + '</span></div>';
    });
    h += '</div>';
    var ckt = "";
    if (u || l) ckt = '<span style="font-size:12px;font-weight:700;color:rgba(240,180,41,.95)">\u26A1 7 din me: ' + (u ? u + '\u00D7 UC' : "") + (u && l ? " + " : "") + (l ? l + '\u00D7 LC' : "") + ' circuit</span>';
    else ckt = '<span style="font-size:12px;opacity:.6">koi circuit nahi laga (7 din)</span>';
    h += '<div style="margin-top:8px;display:flex;align-items:center;gap:10px;flex-wrap:wrap">' + ckt + '<span style="font-size:10px;opacity:.5">(close = ' + esc(DATA.updated) + ')</span></div></div>';
    return h;
  }

  function showDetail(sym) {
    var box = document.getElementById("csDetail");
    var inp = document.getElementById("csSearch");
    if (!box || !DATA.all[sym]) return;
    if (inp) inp.value = sym;
    var res = document.getElementById("csResults");
    if (res) res.innerHTML = "";
    box.innerHTML = detailHtml(sym);
    var x = document.getElementById("csDetX");
    if (x) x.onclick = function () { box.innerHTML = ""; if (inp) inp.value = ""; };
  }

  function doSearch(q) {
    var res = document.getElementById("csResults");
    if (!res) return;
    if (!q || q.length < 2) { res.innerHTML = ""; return; }
    q = q.toUpperCase();
    var pre = [], sub = [];
    for (var sym in DATA.all) {
      if (sym.indexOf(q) === 0) pre.push(sym);
      else if (sym.indexOf(q) > 0) sub.push(sym);
      if (pre.length > 30) break;
    }
    var hits = pre.concat(sub).slice(0, 8);
    if (!hits.length) { res.innerHTML = '<div class="note" style="padding:4px 2px">"' + esc(q) + '" nahi mila - symbol check karo</div>'; return; }
    var h = "";
    hits.forEach(function (sym) {
      var a = DATA.all[sym], last = null;
      for (var i = 6; i >= 0; i--) { if (a[i] != null) { last = a[i]; break; } }
      var u = a[8] || 0, l = a[9] || 0;
      h += '<div data-sym="' + esc(sym) + '" style="display:flex;align-items:center;gap:8px;padding:6px 8px;margin-top:3px;border-radius:8px;background:rgba(255,255,255,.06);cursor:pointer;font-size:13px">' +
        '<b style="min-width:96px">' + esc(sym) + '</b>' +
        '<span style="opacity:.75">\u20B9' + esc(a[10]) + '</span>' +
        (last != null ? '<b style="min-width:44px;color:' + (last >= 0 ? "#77f37b" : "#ff8b8b") + '">' + (last > 0 ? "+" : "") + esc(last) + '%</b>' : "") +
        (u + l ? '<span style="font-size:10px;font-weight:700;color:rgba(240,180,41,.95)">\u26A1' + (u + l) + '/7</span>' : "") +
        '<span style="margin-left:auto;font-size:10px;opacity:.45">tap \u2192 detail</span></div>';
    });
    res.innerHTML = h;
    Array.prototype.forEach.call(res.querySelectorAll("div[data-sym]"), function (el) {
      el.onclick = function () { showDetail(el.getAttribute("data-sym")); };
    });
  }

  function bandRow(grp, isUp) {
    var h = '<details style="margin-top:6px"><summary style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:13.5px;flex-wrap:wrap">' +
      '<b style="min-width:56px;font-size:14px;color:' + (isUp ? "#77f37b" : "#ff8b8b") + '">' + grp.b + '%</b>' +
      '<span style="font-size:12.5px">' + (isUp ? "Upper" : "Lower") + ' Circuit</span>' +
      '<span style="margin-left:auto;font-size:11.5px;font-weight:700;color:rgba(240,180,41,.95)">' + grp.n + ' stocks</span></summary>' +
      '<div style="padding:2px 14px 8px 14px">';
    grp.top.forEach(function (x) {
      h += '<div data-sym="' + esc(x.s) + '" style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:12.5px;flex-wrap:wrap;cursor:pointer">' +
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
    DAYS = (d.tr || []).map(function (t) { return t.d; });
    var h = '<div class="note" style="margin-top:8px">' + esc(d.updated) + ' \u00b7 ' + d.n_uc + ' upper + ' + d.n_lc + ' lower circuit stocks. Stock pe tap = 7-din detail. (indicative, advice nahi)</div>';
    h += bandAlert(d.bands);
    h += '<div style="margin-top:10px;display:flex;gap:6px;align-items:center">' +
      '<input id="csSearch" type="text" placeholder="\uD83D\uDD0D stock likho - RELIANCE, TATA..." style="flex:1;padding:9px 12px;border-radius:10px;border:1px solid rgba(240,180,41,.5);background:rgba(255,255,255,.07);color:#fff;font-size:14px;outline:none" autocomplete="off" autocapitalize="characters">' +
      '<span style="font-size:11px;opacity:.5">' + (d.all ? Object.keys(d.all).length : 0) + ' stocks</span></div>' +
      '<div id="csResults"></div><div id="csDetail"></div>';
    h += trend(d.tr);
    h += '<div style="margin-top:8px;font-size:13px;font-weight:700;color:#77f37b">\uD83D\uDFE2 UPPER CIRCUIT (' + d.n_uc + ')</div>';
    (d.uc || []).forEach(function (g) { h += bandRow(g, true); });
    h += '<div style="margin-top:10px;font-size:13px;font-weight:700;color:#ff8b8b">\uD83D\uDD34 LOWER CIRCUIT (' + d.n_lc + ')</div>';
    (d.lc || []).forEach(function (g) { h += bandRow(g, false); });
    box.innerHTML = h;

    var inp = document.getElementById("csSearch");
    var tmr = null;
    if (inp) inp.addEventListener("input", function () {
      clearTimeout(tmr);
      var v = inp.value;
      tmr = setTimeout(function () { doSearch(v.trim()); }, 180);
    });
    Array.prototype.forEach.call(box.querySelectorAll("div[data-sym]"), function (el) {
      el.onclick = function () { showDetail(el.getAttribute("data-sym")); };
    });
  }

  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(240,180,41,.13);border:1px solid rgba(240,180,41,.5);font-size:14.5px;text-align:center"><b style="color:rgba(240,180,41,.95)">\u26A1 CIRCUIT SCANNER</b> <span style="font-size:11px;opacity:.65">upper \u00b7 lower \u00b7 band changes \u00b7 search</span></summary>' +
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
