/* ict.js — ICT Terminal (GTI section): PDH/PDL · Weekly/Monthly H/L · Asia box
   · London/NY kill zones · Order Blocks · FVG · BOS/CHOCH — 100% free, client-side.
   Data: data/candles.json (Yahoo free) — 5m aaj, 15m 5 din, 1h 1 mahina.
   Asia box + NY KZ sirf 24h market (BTC) pe poore dikhte hain — NSE raat ko band.
   London KZ (12:30-15:30 IST) NSE me bhi dikhta hai. Read hai, tip nahi. */
(function () {
  "use strict";

  /* ---------------- helpers ---------------- */
  function esc(s) { if (s == null) { s = ""; } return String(s)
    .replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function n2(x) { return Number(x).toLocaleString("en-IN",
    { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function pct(x) { return (x >= 0 ? "+" : "\u2212") + Math.abs(x).toFixed(2) + "%"; }

  /* IST wall-clock (data Yahoo epoch sec; +5:30 offset se UTC getters = IST) */
  function istDate(t) { return new Date((t + 19800) * 1000); }
  function istKey(t) { var d = istDate(t);
    return d.getUTCFullYear() * 10000 + (d.getUTCMonth() + 1) * 100 + d.getUTCDate(); }
  function istMin(t) { var d = istDate(t); return d.getUTCHours() * 60 + d.getUTCMinutes(); }
  function weekKeyOfKey(k) { /* k = yyyymmdd -> us Monday ka key */
    var y = Math.floor(k / 10000), m = Math.floor(k / 100) % 100, d = k % 100;
    var ms = Date.UTC(y, m - 1, d), dow = new Date(ms).getUTCDay();
    var mon = new Date(ms - ((dow + 6) % 7) * 86400000);
    return mon.getUTCFullYear() * 10000 + (mon.getUTCMonth() + 1) * 100 + mon.getUTCDate();
  }
  function istStr(t) { var d = istDate(t); var M = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    return d.getUTCDate() + " " + M[d.getUTCMonth()] + " " +
      ("0" + d.getUTCHours()).slice(-2) + ":" + ("0" + d.getUTCMinutes()).slice(-2); }

  /* ---------------- HTF levels (1h bars se: prev day / prev week / month H-L) ---------------- */
  function htfLevels(d, now) {
    if (!d || !d.t || d.t.length < 2) return null;
    var todayK = istKey(now == null ? Math.floor(Date.now() / 1000) : now);
    var days = [], cur = null;
    for (var i = 0; i < d.t.length; i++) {
      var k = istKey(d.t[i]);
      if (cur && cur.k === k) { if (d.h[i] > cur.h) cur.h = d.h[i]; if (d.l[i] < cur.l) cur.l = d.l[i]; }
      else { cur = { k: k, h: d.h[i], l: d.l[i] }; days.push(cur); }
    }
    /* PDH/PDL = aakhri COMPLETE session (weekend/baad-e-close me wahi prev hai;
       live session chal rahi ho to usse pehle wala) */
    var lastD = days[days.length - 1];
    var lastComplete = lastD.k !== todayK || istMin(d.t[d.t.length - 1]) >= 15 * 60 + 25;
    var pd = lastComplete ? lastD : (days.length >= 2 ? days[days.length - 2] : null);
    var weeks = [], cw = null;
    for (var j = 0; j < days.length; j++) {
      var wk = weekKeyOfKey(days[j].k);
      if (cw && cw.k === wk) { if (days[j].h > cw.h) cw.h = days[j].h; if (days[j].l < cw.l) cw.l = days[j].l; }
      else { cw = { k: wk, h: days[j].h, l: days[j].l }; weeks.push(cw); }
    }
    var pw = weeks.length >= 2 ? weeks[weeks.length - 2] : null;
    var cw2 = weeks[weeks.length - 1];
    var months = [], cm = null;
    for (var q = 0; q < days.length; q++) {
      var mk = Math.floor(days[q].k / 100);
      if (cm && cm.k === mk) { if (days[q].h > cm.h) cm.h = days[q].h; if (days[q].l < cm.l) cm.l = days[q].l; }
      else { cm = { k: mk, h: days[q].h, l: days[q].l }; months.push(cm); }
    }
    var cmo = months[months.length - 1];
    return { pdh: pd && pd.h, pdl: pd && pd.l, pwh: pw && pw.h, pwl: pw && pw.l,
      wh: cw2 && cw2.h, wl: cw2 && cw2.l, mh: cmo && cmo.h, ml: cmo && cmo.l };
  }

  /* ---------------- sessions (displayed bars se) ---------------- */
  /* Asia: 21:15-06:30 IST (evening part aagle din ki session me count) */
  function asiaSessions(d) {
    var out = [], cur = null;
    for (var i = 0; i < d.t.length; i++) {
      var m = istMin(d.t[i]);
      var ok = m >= 1275 || m < 390;
      if (!ok) { cur = null; continue; }
      var k = istKey(d.t[i] + (m >= 1275 ? 86400 : 0));
      if (cur && cur.k === k) {
        if (d.h[i] > cur.h) cur.h = d.h[i];
        if (d.l[i] < cur.l) cur.l = d.l[i];
        cur.i1 = i;
      } else { cur = { k: k, i0: i, i1: i, h: d.h[i], l: d.l[i] }; out.push(cur); }
    }
    return out.filter(function (s) { return s.i1 > s.i0; });
  }
  /* Kill zones: LDN 12:30-15:30, NY 17:30-20:30 IST */
  function kzBands(d) {
    var out = [], cur = null;
    for (var i = 0; i < d.t.length; i++) {
      var m = istMin(d.t[i]), ty = 0;
      if (m >= 750 && m < 930) ty = 1;
      else if (m >= 1050 && m < 1230) ty = 2;
      if (!ty) { cur = null; continue; }
      var k = ty * 100000000 + istKey(d.t[i]);
      if (cur && cur.k === k) { cur.i1 = i; }
      else { cur = { k: k, ty: ty, i0: i, i1: i }; out.push(cur); }
    }
    return out;
  }

  /* ---------------- market structure (BOS / CHOCH) ---------------- */
  function detectStructure(d) {
    var n = d.t.length, k = 3, swings = [];
    for (var i = k; i < n - k; i++) {
      var isH = true, isL = true;
      for (var j = 1; j <= k; j++) {
        if (d.h[i] < d.h[i - j] || d.h[i] < d.h[i + j]) isH = false;
        if (d.l[i] > d.l[i - j] || d.l[i] > d.l[i + j]) isL = false;
      }
      if (isH) swings.push({ i: i, price: d.h[i], type: 1, ci: i + k });
      if (isL) swings.push({ i: i, price: d.l[i], type: -1, ci: i + k });
    }
    swings.sort(function (a, b) { return a.ci - b.ci; });
    var events = [], trend = 0, sh = null, sl = null, p = 0;
    for (var b = 0; b < n; b++) {
      while (p < swings.length && swings[p].ci <= b) {
        var s = swings[p++];
        if (s.type === 1) { if (!sh || s.i > sh.i) sh = s; }
        else { if (!sl || s.i > sl.i) sl = s; }
      }
      if (sh && d.c[b] > sh.price) {
        events.push({ i: b, t: d.t[b], type: trend === -1 ? "CHOCH" : "BOS", dir: 1, level: sh.price, si: sh.i });
        trend = 1; sh = null;
      }
      if (sl && d.c[b] < sl.price) {
        events.push({ i: b, t: d.t[b], type: trend === 1 ? "CHOCH" : "BOS", dir: -1, level: sl.price, si: sl.i });
        trend = -1; sl = null;
      }
    }
    return { events: events, trend: trend, sh: sh, sl: sl };
  }

  /* ---------------- fair value gaps ---------------- */
  function findFVG(d) {
    var out = [], n = d.t.length;
    for (var i = 2; i < n; i++) {
      var g = null;
      if (d.l[i] > d.h[i - 2]) g = { dir: 1, bot: d.h[i - 2], top: d.l[i] };
      else if (d.h[i] < d.l[i - 2]) g = { dir: -1, bot: d.h[i], top: d.l[i - 2] };
      if (!g) continue;
      g.i0 = i - 1; g.i1 = n - 1; g.open = true; g.touched = false;
      for (var j = i + 1; j < n; j++) {
        if (g.dir === 1) {
          if (d.l[j] <= g.bot) { g.open = false; g.i1 = j; break; }
          if (d.l[j] < g.top) g.touched = true;
        } else {
          if (d.h[j] >= g.top) { g.open = false; g.i1 = j; break; }
          if (d.h[j] > g.bot) g.touched = true;
        }
      }
      if (g.top > g.bot) out.push(g);
    }
    return out;
  }

  /* ---------------- order blocks (structure break ki leg se) ---------------- */
  function findOB(d, st) {
    var out = [], evs = st.events, n = d.t.length;
    for (var e = evs.length - 1; e >= 0 && out.length < 8; e--) {
      var ev = evs[e], m = -1;
      for (var i = ev.si; i <= ev.i; i++) {
        if (ev.dir === 1) { if (m < 0 || d.l[i] < d.l[m] || (d.l[i] === d.l[m] && d.c[i] < d.o[i])) m = i; }
        else { if (m < 0 || d.h[i] > d.h[m] || (d.h[i] === d.h[m] && d.c[i] > d.o[i])) m = i; }
      }
      if (m < 0) continue;
      var lo, hi;
      if (ev.dir === 1) { lo = d.l[m]; hi = Math.max(d.o[m], d.c[m]); }
      else { hi = d.h[m]; lo = Math.min(d.o[m], d.c[m]); }
      if (hi <= lo) continue;
      var ob = { dir: ev.dir, i0: m, i1: n - 1, lo: lo, hi: hi, active: true };
      for (var j = ev.i + 1; j < n; j++) {
        if (ev.dir === 1 && d.c[j] < lo) { ob.active = false; ob.i1 = j; break; }
        if (ev.dir === -1 && d.c[j] > hi) { ob.active = false; ob.i1 = j; break; }
      }
      out.push(ob);
    }
    return out;
  }

  /* node tests ke liye (browser me module undefined) */
  if (typeof module !== "undefined" && module.exports) {
    module.exports = { istMin: istMin, istKey: istKey, htfLevels: htfLevels,
      asiaSessions: asiaSessions, kzBands: kzBands, detectStructure: detectStructure,
      findFVG: findFVG, findOB: findOB, istStr: istStr };
    return;
  }

  /* ================= browser UI ================= */
  var DATA = null, cur = { sym: "NIFTY", iv: "15m" };
  var chart = null, ser = null, ov = null, octx = null, built = false, libOk = false, libTried = false;
  var curBars = null, curSt = null, curFvg = null, curOb = null, curAsia = null, curKz = null, curHtf = null;
  var TOG = { lvl: 1, wk: 1, mo: 1, ses: 1, ob: 1, fvg: 1, st: 1 };
  var IVS = ["5m", "15m", "1h"];
  var UP = "#34d399", DN = "#ff8b8b";

  try {
    var stt = JSON.parse(window.localStorage.getItem("ictog") || "");
    for (var q in stt) if (stt.hasOwnProperty(q) && q in TOG) TOG[q] = stt[q] ? 1 : 0;
  } catch (e) {}
  function saveTog() { try { window.localStorage.setItem("ictog", JSON.stringify(TOG)); } catch (e) {} }

  function loadLib(cb) {
    if (libOk || typeof window.LightweightCharts !== "undefined") { libOk = true; return cb(true); }
    if (libTried) return cb(false);
    libTried = true;
    var urls = [
      "https://unpkg.com/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js",
      "https://cdn.jsdelivr.net/npm/lightweight-charts@4.2.3/dist/lightweight-charts.standalone.production.js"
    ];
    (function tryUrl(k) {
      if (k >= urls.length) return cb(false);
      var s = document.createElement("script");
      s.src = urls[k];
      s.onload = function () { libOk = true; cb(true); };
      s.onerror = function () { tryUrl(k + 1); };
      document.head.appendChild(s);
    })(0);
  }

  function lineBox(l, r, cls) {
    return '<div class="note" style="display:flex;justify-content:space-between">' +
      '<span>' + l + '</span><b style="' + (cls ? "color:" + cls : "") + '">' + r + '</b></div>';
  }

  function panel() {
    var el = document.getElementById("ictRead");
    if (!el) return;
    var d = curBars, n = d.t.length, last = d.c[n - 1];
    var h = "";
    /* structure */
    var evs = curSt.events, lastEv = evs.length ? evs[evs.length - 1] : null;
    var tr = curSt.trend === 1 ? ["Bullish", UP] : curSt.trend === -1 ? ["Bearish", DN] : ["Range", "#d4af37"];
    h += lineBox("Structure (" + esc(cur.iv) + ")",
      esc(tr[0]) + (lastEv ? " \u2014 last " + esc(lastEv.type) +
        (lastEv.dir === 1 ? "\u2191" : "\u2193") + " " + n2(lastEv.level) +
        " (" + esc(istStr(lastEv.t)) + ")" : ""), tr[1]);
    /* HTF levels */
    var hf = curHtf;
    if (hf) {
      function dst(v) { return v ? pct((last - v) / v * 100) : "\u2014"; }
      if (hf.pdh) h += lineBox('<b style="color:#f87171">PDH</b> (pichla din H)', n2(hf.pdh) + " \u00b7 " + dst(hf.pdh), "#f87171");
      if (hf.pdl) h += lineBox('<b style="color:#60a5fa">PDL</b> (pichla din L)', n2(hf.pdl) + " \u00b7 " + dst(hf.pdl), "#60a5fa");
      if (hf.pwh) h += lineBox('<b style="color:#fbbf24">PWH / PWL</b>', n2(hf.pwh) + " / " + n2(hf.pwl), "#fbbf24");
      if (hf.wh) h += lineBox('<b style="color:#b8860b">WH / WL</b> (chalu hafta)', n2(hf.wh) + " / " + n2(hf.wl), "#b8860b");
      if (hf.mh) h += lineBox('<b style="color:#c084fc">MH / ML</b> (chalu mahina)', n2(hf.mh) + " / " + n2(hf.ml), "#c084fc");
    }
    /* FVG */
    var open = curFvg.filter(function (g) { return g.open; });
    var above = open.filter(function (g) { return g.bot > last; });
    var below = open.filter(function (g) { return g.top < last; });
    h += lineBox("Open FVGs", open.length + " (upar " + above.length + " \u00b7 neeche " + below.length + ")",
      open.length ? "#34d399" : null);
    var minA = null, maxB = null, iA = 0, iB = 0;
    for (var g2 = 0; g2 < open.length; g2++) {
      if (open[g2].bot > last && (minA == null || open[g2].bot < minA)) { minA = open[g2].bot; iA = g2; }
      if (open[g2].top < last && (maxB == null || open[g2].top > maxB)) { maxB = open[g2].top; iB = g2; }
    }
    if (minA != null) h += lineBox("\u00b7 nearest FVG upar", n2(open[iA].bot) + " \u2013 " + n2(open[iA].top), UP);
    if (maxB != null) h += lineBox("\u00b7 nearest FVG neeche", n2(open[iB].bot) + " \u2013 " + n2(open[iB].top), DN);
    /* OB */
    var act = curOb.filter(function (o) { return o.active; });
    var obA = act.filter(function (o) { return o.lo > last; });
    var obB = act.filter(function (o) { return o.hi < last; });
    h += lineBox("Active Order Blocks", act.length + (act.length ? " (bull " +
      act.filter(function (o) { return o.dir === 1; }).length + " \u00b7 bear " +
      act.filter(function (o) { return o.dir === -1; }).length + ")" : ""), act.length ? "#4da3ff" : null);
    var moA = null, moB = null, jA = 0, jB = 0;
    for (var o2 = 0; o2 < act.length; o2++) {
      if (act[o2].lo > last && (moA == null || act[o2].lo < moA)) { moA = act[o2].lo; jA = o2; }
      if (act[o2].hi < last && (moB == null || act[o2].hi > moB)) { moB = act[o2].hi; jB = o2; }
    }
    if (moA != null) h += lineBox("\u00b7 nearest OB upar", n2(act[jA].lo) + " \u2013 " + n2(act[jA].hi) +
      (act[jA].dir === 1 ? " (bull)" : " (bear)"), "#ff9f40");
    if (moB != null) h += lineBox("\u00b7 nearest OB neeche", n2(act[jB].lo) + " \u2013 " + n2(act[jB].hi) +
      (act[jB].dir === 1 ? " (bull)" : " (bear)"), "#4da3ff");
    /* asia */
    if (curAsia.length) {
      var a = curAsia[curAsia.length - 1];
      var brk = last > a.h ? "ab upar (bullish)" : last < a.l ? "ab neeche (bearish)" : "andar";
      h += lineBox('<b style="color:#60a5fa">ASIA box</b> (' + esc(istStr(d.t[a.i0])) + ")", n2(a.l) + " \u2013 " + n2(a.h) + " \u00b7 " + esc(brk), "#60a5fa");
    } else {
      h += lineBox("ASIA box", "is data me nahi (NSE raat ko band \u2014 BTC pe dikhega)", null);
    }
    el.innerHTML = h;
  }

  /* ---------------- chart + overlay ---------------- */
  function sizeCanvas() {
    var DPR = window.devicePixelRatio || 1;
    var w = ov.clientWidth, hh = ov.clientHeight;
    ov.width = Math.round(w * DPR); ov.height = Math.round(hh * DPR);
    octx.setTransform(DPR, 0, 0, DPR, 0, 0);
  }
  function draw() {
    if (!chart || !ser || !octx || !curBars) return;
    var w = ov.clientWidth, hh = ov.clientHeight, n = curBars.t.length;
    octx.clearRect(0, 0, w, hh);
    function X(i) {
      try {
        var vr = chart.timeScale().getVisibleLogicalRange();
        if (!vr) return null;
        var li = Math.max(Math.floor(vr.from), Math.min(Math.ceil(vr.to), i));
        return chart.timeScale().logicalToCoordinate(li);
      } catch (e) { return null; }
    }
    function Y(p) { try { return ser.priceToCoordinate(p); } catch (e) { return null; } }
    function rect(x1, y1, x2, y2, fill, stroke, label, lcol) {
      if (x1 == null || x2 == null || y1 == null || y2 == null) return;
      if (x2 < x1) { var t = x1; x1 = x2; x2 = t; }
      if (y2 < y1) { var t2 = y1; y1 = y2; y2 = t2; }
      if (x2 - x1 < 2) x2 = x1 + 2;
      octx.fillStyle = fill; octx.fillRect(x1, y1, x2 - x1, y2 - y1);
      octx.strokeStyle = stroke; octx.lineWidth = 1;
      octx.strokeRect(x1 + .5, y1 + .5, x2 - x1 - 1, y2 - y1 - 1);
      if (label) { octx.fillStyle = lcol || stroke;
        octx.font = "10px ui-monospace,Menlo,monospace"; octx.fillText(label, x1 + 4, y1 + 11); }
    }
    function dashLine(x1, y, x2, col) {
      if (y == null || x1 == null || x2 == null || x2 <= x1) return;
      octx.strokeStyle = col; octx.lineWidth = 1; octx.setLineDash([4, 3]);
      octx.beginPath(); octx.moveTo(x1, y + .5); octx.lineTo(x2, y + .5); octx.stroke();
      octx.setLineDash([]);
    }
    /* kill zone bands (poore height pe) */
    if (TOG.ses && curKz) {
      for (var i = 0; i < curKz.length; i++) {
        var b = curKz[i], x1 = X(b.i0), x2 = X(b.i1);
        if (x1 == null && x2 == null) continue;
        if (x1 == null) x1 = 0; if (x2 == null) x2 = w;
        if (x2 <= x1) continue;
        var kc = b.ty === 1 ? "rgba(52,211,153,.07)" : "rgba(255,184,77,.07)";
        var kl = b.ty === 1 ? "#34d399" : "#ffb84d";
        octx.fillStyle = kc; octx.fillRect(x1, 0, x2 - x1, hh);
        octx.fillStyle = kl; octx.font = "10px ui-monospace,Menlo,monospace";
        octx.fillText(b.ty === 1 ? "LDN KZ" : "NY KZ", x1 + 4, 12);
      }
    }
    /* asia boxes */
    if (TOG.ses && curAsia) {
      for (var a2 = Math.max(0, curAsia.length - 3); a2 < curAsia.length; a2++) {
        var s2 = curAsia[a2], ax1 = X(s2.i0), ax2 = X(s2.i1);
        var ay1 = Y(s2.h), ay2 = Y(s2.l);
        if (ay1 != null && ay2 != null) {
          if (ax1 == null) ax1 = 0;
          rect(ax1, ay1, ax2 == null ? w : ax2, ay2, "rgba(96,165,250,.10)", "rgba(96,165,250,.55)", "ASIA", "#60a5fa");
          /* session ke baad H/L project karo */
          var xr = X(n - 1);
          if (ax2 != null && xr != null && xr > ax2) {
            dashLine(ax2, ay1, xr, "rgba(96,165,250,.5)");
            dashLine(ax2, ay2, xr, "rgba(96,165,250,.5)");
          }
        }
      }
    }
    /* FVG */
    if (TOG.fvg && curFvg) {
      var shown = 0;
      for (var f = curFvg.length - 1; f >= 0 && shown < 8; f--) {
        var g = curFvg[f];
        if (!g.open) continue;
        shown++;
        var fy1 = Y(g.top), fy2 = Y(g.bot);
        rect(X(g.i0), fy1, X(Math.min(g.i1, n - 1)), fy2,
          g.dir === 1 ? "rgba(52,211,153,.13)" : "rgba(255,107,107,.13)",
          g.dir === 1 ? "rgba(52,211,153,.45)" : "rgba(255,107,107,.45)",
          g.dir === 1 ? "FVG\u2191" : "FVG\u2193",
          g.dir === 1 ? "#34d399" : "#ff6b6b");
      }
    }
    /* order blocks */
    if (TOG.ob && curOb) {
      for (var o = 0; o < curOb.length; o++) {
        var ob = curOb[o];
        var oy1 = Y(ob.hi), oy2 = Y(ob.lo);
        var fill = ob.dir === 1 ? (ob.active ? "rgba(77,163,255,.15)" : "rgba(77,163,255,.05)")
          : (ob.active ? "rgba(255,159,64,.15)" : "rgba(255,159,64,.05)");
        var stroke = ob.dir === 1 ? (ob.active ? "rgba(77,163,255,.6)" : "rgba(77,163,255,.2)")
          : (ob.active ? "rgba(255,159,64,.6)" : "rgba(255,159,64,.2)");
        rect(X(ob.i0), oy1, X(Math.min(ob.i1, n - 1)), oy2, fill, stroke,
          ob.dir === 1 ? "OB\u2191" : "OB\u2193", ob.dir === 1 ? "#4da3ff" : "#ff9f40");
      }
    }
  }

  function build() {
    var host = document.getElementById("ictChart");
    if (!host || !DATA || !DATA.syms) return;
    var av = DATA.syms[cur.sym];
    if (!av) { cur.sym = "NIFTY"; av = DATA.syms[cur.sym]; }
    if (!av) { host.innerHTML = '<div class="note">data nahi mila.</div>'; return; }
    var d = av[cur.iv] || av["15m"] || av["1h"] || av["5m"];
    if (!d || !d.t || !d.t.length) { host.innerHTML = '<div class="note">is symbol/interval ka data nahi.</div>'; return; }
    curBars = d;
    curSt = detectStructure(d);
    curFvg = findFVG(d);
    curOb = findOB(d, curSt);
    curAsia = asiaSessions(d);
    curKz = kzBands(d);
    curHtf = htfLevels(av["1h"] || d);

    loadLib(function (ok) {
      if (chart) { try { chart.remove(); } catch (e) {} chart = null; }
      host.innerHTML = "";
      if (!ok) { host.innerHTML = '<div class="note">chart lib load nahi hui \u2014 internet check karke dobara try karo.</div>'; return; }
      var light = document.documentElement.getAttribute("data-theme") === "light";
      var grid = light ? "rgba(0,0,0,.06)" : "rgba(255,255,255,.06)";
      var txt = light ? "#41506b" : "#8fa3c8";
      try {
        chart = LightweightCharts.createChart(host, {
          height: 420, layout: { background: { type: "solid", color: "transparent" },
            textColor: txt, fontSize: 10 },
          grid: { vertLines: { color: grid }, horzLines: { color: grid } },
          rightPriceScale: { borderVisible: false },
          timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
          localization: { locale: "en-IN" }
        });
        ser = chart.addCandlestickSeries({
          upColor: UP, downColor: DN, borderUpColor: UP, borderDownColor: DN,
          wickUpColor: UP, wickDownColor: DN, priceLineVisible: true
        });
        var bars = [];
        for (var i = 0; i < d.t.length; i++)
          bars.push({ time: d.t[i], open: d.o[i], high: d.h[i], low: d.l[i], close: d.c[i] });
        if (bars.length > 1 && bars[bars.length - 1].time <= bars[bars.length - 2].time) bars.pop();
        ser.setData(bars);
        /* BOS / CHOCH markers */
        if (TOG.st && curSt.events.length) {
          var mk = [], evs = curSt.events.slice(-20);
          for (var e2 = 0; e2 < evs.length; e2++) {
            var ev = evs[e2];
            mk.push({ time: ev.t, position: ev.dir === 1 ? "aboveBar" : "belowBar",
              color: ev.type === "CHOCH" ? "#ffd54d" : (ev.dir === 1 ? "#34d399" : "#ff8b8b"),
              shape: ev.dir === 1 ? "arrowUp" : "arrowDown",
              text: ev.type + (ev.dir === 1 ? "\u2191" : "\u2193"), size: 1 });
          }
          try { ser.setMarkers(mk); } catch (e3) {}
        }
        /* HTF price lines */
        var LINES = [
          { on: "lvl", p: curHtf && curHtf.pdh, t: "PDH", c: "#f87171", s: 0 },
          { on: "lvl", p: curHtf && curHtf.pdl, t: "PDL", c: "#60a5fa", s: 0 },
          { on: "wk", p: curHtf && curHtf.pwh, t: "PWH", c: "#fbbf24", s: 2 },
          { on: "wk", p: curHtf && curHtf.pwl, t: "PWL", c: "#fbbf24", s: 2 },
          { on: "wk", p: curHtf && curHtf.wh, t: "WH", c: "#b8860b", s: 4 },
          { on: "wk", p: curHtf && curHtf.wl, t: "WL", c: "#b8860b", s: 4 },
          { on: "mo", p: curHtf && curHtf.mh, t: "MH", c: "#c084fc", s: 1 },
          { on: "mo", p: curHtf && curHtf.ml, t: "ML", c: "#c084fc", s: 1 }
        ];
        for (var L = 0; L < LINES.length; L++) {
          var ln = LINES[L];
          if (!TOG[ln.on] || !ln.p) continue;
          try {
            ser.createPriceLine({ price: ln.p, color: ln.c, lineWidth: 1,
              lineStyle: ln.s, axisLabelVisible: true, title: ln.t });
          } catch (e4) {}
        }
        chart.timeScale().fitContent();
        try { chart.applyOptions({ width: host.clientWidth }); } catch (e5) {}
        /* overlay canvas */
        ov = document.createElement("canvas");
        ov.style.cssText = "position:absolute;inset:0;pointer-events:none;width:100%;height:100%";
        host.appendChild(ov);
        octx = ov.getContext("2d");
        sizeCanvas(); draw();
        try {
          chart.timeScale().subscribeVisibleLogicalRangeChange(function () { draw(); });
        } catch (e6) {}
        if (!build._rs) {
          build._rs = 1;
          window.addEventListener("resize", function () {
            if (chart && host) { try { chart.applyOptions({ width: host.clientWidth }); } catch (e) {} }
            if (ov) { sizeCanvas(); draw(); }
          });
        }
      } catch (e) { host.innerHTML = '<div class="note">chart render fail: ' + esc(e.message) + "</div>"; }
      panel();
    });
  }

  /* ---------------- chips ---------------- */
  function renderChips() {
    var sy = document.getElementById("ictSyms"), iv = document.getElementById("ictIvs"),
        tg = document.getElementById("ictTogs");
    if (!sy || !DATA || !DATA.syms) return;
    var keys = Object.keys(DATA.syms).sort();
    var h = "";
    for (var i = 0; i < keys.length; i++)
      h += '<button class="chip' + (keys[i] === cur.sym ? " on" : "") + '" data-ict-sym="' + esc(keys[i]) + '">' + esc(keys[i]) + "</button>";
    sy.innerHTML = h;
    var av = DATA.syms[cur.sym] || {};
    var h2 = "";
    for (var j = 0; j < IVS.length; j++)
      if (av[IVS[j]] && av[IVS[j]].t && av[IVS[j]].t.length)
        h2 += '<button class="chip' + (IVS[j] === cur.iv ? " on" : "") + '" data-ict-iv="' + IVS[j] + '">' + IVS[j] + "</button>";
    iv.innerHTML = h2 || '<span class="note" style="font-size:12px">data nahi</span>';
    var TOGD = [["lvl", "PDH/PDL"], ["wk", "W H/L"], ["mo", "M H/L"], ["ses", "Sessions/KZ"],
      ["ob", "Order Blocks"], ["fvg", "FVG"], ["st", "BOS/CHOCH"]];
    var h3 = "";
    for (var q = 0; q < TOGD.length; q++)
      h3 += '<button class="chip' + (TOG[TOGD[q][0]] ? " on" : "") + '" data-ict-tog="' + TOGD[q][0] + '">' + TOGD[q][1] + "</button>";
    tg.innerHTML = h3;
  }

  function onClick(e) {
    var t = e.target || e.srcElement;
    while (t && t !== document.body && !t.getAttribute) t = t.parentNode;
    if (!t || !t.getAttribute) return;
    var s = t.getAttribute("data-ict-sym"), iv = t.getAttribute("data-ict-iv"), tog = t.getAttribute("data-ict-tog");
    if (s && s !== cur.sym) { cur.sym = s; cur.iv = "15m"; renderChips(); build(); }
    else if (iv && iv !== cur.iv) { cur.iv = iv; renderChips(); build(); }
    else if (tog) { TOG[tog] = TOG[tog] ? 0 : 1; saveTog(); renderChips(); build(); }
  }

  function waitVisible() {
    if (built) return;
    var card = document.getElementById("ictCard");
    if (card && card.offsetParent !== null && DATA) { built = true; build(); return; }
    setTimeout(waitVisible, 700);
  }

  function mount() {
    var sec = document.querySelector("#gtiMount") || document.querySelector("section#gti");
    if (!sec || document.getElementById("ictCard")) return;
    var card = document.createElement("div");
    card.className = "card"; card.id = "ictCard";
    card.innerHTML =
      '<div class="subhead">ICT Terminal \u2014 PDH/PDL \u00b7 Weekly/Monthly H/L \u00b7 Asia box \u00b7 Kill zones \u00b7 Order Blocks \u00b7 FVG \u00b7 BOS/CHOCH</div>' +
      '<div class="note" style="margin:6px 0 4px">symbol chuno \u2014 15m = 5 din ka structure, 1h = 1 mahina:</div>' +
      '<div class="controls" id="ictSyms"></div>' +
      '<div class="controls" id="ictIvs"></div>' +
      '<div class="controls" id="ictTogs"></div>' +
      '<div id="ictChart" style="margin-top:10px;height:420px;position:relative"></div>' +
      '<div id="ictRead" style="margin-top:10px"></div>' +
      '<div class="note" style="font-size:12px;line-height:1.8;margin-top:10px">' +
      '<b style="color:#f87171">PDH</b>/<b style="color:#60a5fa">PDL</b> pichla din \u00b7 <b style="color:#fbbf24">PWH/PWL</b> pichla hafta \u00b7 <b style="color:#b8860b">WH/WL</b> chalu hafta \u00b7 <b style="color:#c084fc">MH/ML</b> chalu mahina \u00b7 ' +
      '<b style="color:#60a5fa">ASIA</b> 21:15\u201306:30 IST \u00b7 <b style="color:#34d399">LDN KZ</b> 12:30\u201315:30 \u00b7 <b style="color:#ffb84d">NY KZ</b> 17:30\u201320:30 \u00b7 ' +
      '<b style="color:#4da3ff">OB\u2191</b>/<b style="color:#ff9f40">OB\u2193</b> order block \u00b7 <b style="color:#34d399">FVG\u2191</b>/<b style="color:#ff6b6b">FVG\u2193</b> fair value gap \u00b7 ' +
      '<b style="color:#34d399">BOS</b> trend continuation \u00b7 <b style="color:#ffd54d">CHOCH</b> reversal</div>' +
      '<div class="footer-note">data: Yahoo free (5m aaj \u00b7 15m 5 din \u00b7 1h 1 mahina) \u00b7 Asia box + NY KZ sirf 24h market (BTC) pe poore \u2014 NSE raat ko band \u00b7 structure fractal-3 swings se \u00b7 read hai, tip nahi</div>';
    sec.insertBefore(card, sec.firstChild);
    fetch("data/candles.json?t=" + Date.now()).then(function (r) { return r.json(); }).then(function (dd) {
      DATA = dd;
      if (!DATA.syms[cur.sym]) cur.sym = Object.keys(DATA.syms)[0] || "NIFTY";
      renderChips();
      waitVisible();
    }).catch(function () {
      var el = document.getElementById("ictSyms");
      if (el) el.innerHTML = '<span class="note" style="font-size:12px">candles data nahi mila \u2014 thodi der baad try karo.</span>';
    });
    if (document.addEventListener) document.addEventListener("click", onClick, false);
    window.addEventListener("hashchange", waitVisible);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
