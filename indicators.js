/* indicators.js — ArthaSaar Phase 1 indicator engine (100% free, pure client-side math).
   chartread.js ko bilkul touch nahi karta — LightweightCharts ko wrap karke
   chart/series capture karta hai, phir apni overlay series add karta hai.

   Overlays  : SuperTrend(10,3) · EMA Ribbon(5/10/20/50/200) · Hull MA(9) · Donchian(20) · Ichimoku(9/26/52)
   Sub-panel : MACD(12/26/9) · Stoch RSI(14/14/3/3) · Awesome Oscillator(5/34)
   UI        : #crIvs ke niche chips row, state localStorage ("crind") me save.
   Rules     : max 3 overlays + 1 panel — warna chart gadbad ho jata hai. */
(function () {
  "use strict";
  if (window.__ASIND__) return;
  window.__ASIND__ = 1;

  var UP = "#34d399", DN = "#f87171";

  var chart = null, ser = null;         /* main chart + candle series (captured) */
  var mySeries = [];                    /* hamari overlay series refs */
  var subChart = null, subSeries = []; /* panel chart + uski series */
  var syncing = false;

  var OVERLAYS = [
    { id: "supertrend", name: "SuperTrend" },
    { id: "emaribbon", name: "EMA Ribbon" },
    { id: "hma", name: "Hull MA" },
    { id: "donchian", name: "Donchian" },
    { id: "ichimoku", name: "Ichimoku" }
  ];
  var PANELS = [
    { id: "macd", name: "MACD" },
    { id: "stochrsi", name: "Stoch RSI" },
    { id: "ao", name: "Awesome Osc" }
  ];

  /* ---------- active state (persisted) ---------- */
  var ACTIVE = { overlays: [], panel: "" };
  try {
    var sv = JSON.parse(localStorage.getItem("crind") || "null");
    if (sv && typeof sv === "object") {
      if (Array.isArray(sv.overlays))
        ACTIVE.overlays = sv.overlays.filter(function (x) { return OVERLAYS.some(function (o) { return o.id === x; }); });
      if (PANELS.some(function (p) { return p.id === sv.panel; })) ACTIVE.panel = sv.panel;
    }
  } catch (e) {}
  function save() { try { localStorage.setItem("crind", JSON.stringify(ACTIVE)); } catch (e) {} }

  /* ================= math (null-tolerant arrays) ================= */
  function compact(a) {
    var idx = [], val = [];
    for (var i = 0; i < a.length; i++)
      if (a[i] != null && isFinite(a[i])) { idx.push(i); val.push(a[i]); }
    return { idx: idx, val: val };
  }
  function scatter(len, idx, val) {
    var out = new Array(len).fill(null);
    for (var k = 0; k < idx.length; k++) out[idx[k]] = val[k];
    return out;
  }
  function smaC(a, n) { /* compact input par */
    var out = new Array(a.length).fill(null), s = 0;
    for (var i = 0; i < a.length; i++) {
      s += a[i];
      if (i >= n) s -= a[i - n];
      if (i >= n - 1) out[i] = s / n;
    }
    return out;
  }
  function emaC(a, n) {
    var out = new Array(a.length).fill(null), k = 2 / (n + 1), prev = null, sum = 0;
    for (var i = 0; i < a.length; i++) {
      if (prev == null) {
        sum += a[i];
        if (i === n - 1) { prev = sum / n; out[i] = prev; }
      } else { prev = a[i] * k + prev * (1 - k); out[i] = prev; }
    }
    return out;
  }
  function wmaC(a, n) {
    var out = new Array(a.length).fill(null), den = n * (n + 1) / 2;
    for (var i = n - 1; i < a.length; i++) {
      var s = 0;
      for (var j = 0; j < n; j++) s += a[i - j] * (n - j);
      out[i] = s / den;
    }
    return out;
  }
  function hmaC(a, n) {
    var w1 = wmaC(a, n), w2 = wmaC(a, Math.max(1, Math.floor(n / 2)));
    var raw = new Array(a.length).fill(null);
    for (var i = 0; i < a.length; i++) if (w1[i] != null && w2[i] != null) raw[i] = 2 * w2[i] - w1[i];
    var c = compact(raw); /* sirf leading nulls hote hain — alignment safe */
    return scatter(raw.length, c.idx, wmaC(c.val, Math.max(1, Math.round(Math.sqrt(n)))));
  }
  function scatterInto(raw, compactVals) {
    var c = compact(raw), out = new Array(raw.length).fill(null);
    for (var k = 0; k < c.idx.length && k < compactVals.length; k++) out[c.idx[k]] = compactVals[k];
    return out;
  }
  function atrArr(h, l, c, n) {
    var tr = [h[0] - l[0]];
    for (var i = 1; i < c.length; i++)
      tr.push(Math.max(h[i] - l[i], Math.abs(h[i] - c[i - 1]), Math.abs(l[i] - c[i - 1])));
    return scatter(tr.length, tr.map(function (_, k) { return k; }), emaC(tr, n));
  }
  function rsiC(c, n) {
    var out = new Array(c.length).fill(null), g = 0, l = 0;
    for (var i = 1; i < c.length; i++) {
      var d = c[i] - c[i - 1];
      if (i <= n) {
        g += Math.max(d, 0); l += Math.max(-d, 0);
        if (i === n) { g /= n; l /= n; out[i] = 100 - 100 / (1 + (l === 0 ? 100 : g / l)); }
      } else {
        g = (g * (n - 1) + Math.max(d, 0)) / n;
        l = (l * (n - 1) + Math.max(-d, 0)) / n;
        out[i] = 100 - 100 / (1 + (l === 0 ? 100 : g / l));
      }
    }
    return out;
  }

  /* ================= overlays ================= */
  function superTrend(t, h, l, c, n, mult) {
    var a = atrArr(h, l, c, n);
    var up = new Array(c.length).fill(null), dn = new Array(c.length).fill(null);
    var fu = null, fl = null, dir = 1;
    for (var i = 0; i < c.length; i++) {
      if (a[i] == null) continue;
      var hl2 = (h[i] + l[i]) / 2, bu = hl2 + mult * a[i], bl = hl2 - mult * a[i];
      if (fu === null) { fu = bu; fl = bl; dir = 1; }
      else {
        fu = (bu < fu || c[i - 1] > fu) ? bu : fu;
        fl = (bl > fl || c[i - 1] < fl) ? bl : fl;
        if (dir === 1 && c[i] < fl) dir = -1;
        else if (dir === -1 && c[i] > fu) dir = 1;
      }
      if (dir === 1) up[i] = fl; else dn[i] = fu;
    }
    return { up: up, dn: dn };
  }
  function rollingHL(h, l, n) { /* mid donchian / ichimoku helper */
    var out = new Array(h.length).fill(null);
    for (var i = n - 1; i < h.length; i++) {
      var mx = -Infinity, mn = Infinity;
      for (var j = i - n + 1; j <= i; j++) { if (h[j] > mx) mx = h[j]; if (l[j] < mn) mn = l[j]; }
      out[i] = (mx + mn) / 2;
    }
    return out;
  }

  function toLine(t, arr) {
    var d = [];
    for (var i = 0; i < t.length; i++)
      if (arr[i] != null && isFinite(arr[i])) d.push({ time: t[i], value: arr[i] });
    return d;
  }

  /* ================= series helpers ================= */
  function addLine(data, color, width, style, title) {
    if (!data.length || !chart) return;
    try {
      var s = chart.addLineSeries({
        color: color, lineWidth: width || 1, lineStyle: style || 0,
        priceLineVisible: false, lastValueVisible: false, crosshairMarkerVisible: false, title: title || ""
      });
      s.setData(data); mySeries.push(s);
    } catch (e) {}
  }

  /* ================= sub-panel (MACD / StochRSI / AO) ================= */
  function ensureSub() {
    if (subChart) return subChart;
    var host = document.getElementById("crSub");
    if (!host || typeof window.LightweightCharts === "undefined") return null;
    var light = document.documentElement.getAttribute("data-theme") === "light";
    var grid = light ? "rgba(0,0,0,.06)" : "rgba(255,255,255,.06)";
    var txt = light ? "#41506b" : "#8fa3c8";
    try {
      subChart = window.LightweightCharts.createChart(host, {
        height: 130, layout: { background: { type: "solid", color: "transparent" }, textColor: txt, fontSize: 10 },
        grid: { vertLines: { color: grid }, horzLines: { color: grid } },
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false, timeVisible: true, secondsVisible: false },
        localization: { locale: "en-IN" }
      });
      var sync = function (from, to) {
        if (syncing || !from || !to) return;
        syncing = true;
        try { var r = from.timeScale().getVisibleLogicalRange(); if (r) to.timeScale().setVisibleLogicalRange(r); } catch (e) {}
        syncing = false;
      };
      if (chart) chart.timeScale().subscribeVisibleLogicalRangeChange(function () { sync(chart, subChart); });
      subChart.timeScale().subscribeVisibleLogicalRangeChange(function () { sync(subChart, chart); });
      if (window.addEventListener) window.addEventListener("resize", function () {
        if (subChart && host && host.style.display !== "none")
          try { subChart.applyOptions({ width: host.clientWidth }); } catch (e) {}
      });
    } catch (e) { subChart = null; }
    return subChart;
  }
  function subLine(data, color, width) {
    var s = subChart.addLineSeries({
      color: color, lineWidth: width || 1, priceLineVisible: false,
      lastValueVisible: false, crosshairMarkerVisible: false
    });
    s.setData(data); subSeries.push(s); return s;
  }
  function subHist(data) {
    var s = subChart.addHistogramSeries({ priceFormat: { type: "price", precision: 2, minMove: 0.01 } });
    s.setData(data); subSeries.push(s); return s;
  }
  function applyPanel(t, h, l, c) {
    var host = document.getElementById("crSub");
    if (!ACTIVE.panel || !host || typeof window.LightweightCharts === "undefined") {
      if (host) host.style.display = "none";
      if (subChart) { subSeries.forEach(function (s) { try { s.remove(); } catch (e) {} }); subSeries = []; }
      return;
    }
    var sc = ensureSub();
    if (!sc) return;
    host.style.display = "block";
    try { sc.applyOptions({ width: host.clientWidth }); } catch (e) {}
    subSeries.forEach(function (s) { try { s.remove(); } catch (e) {} }); subSeries = [];

    if (ACTIVE.panel === "macd") {
      var cc = compact(c);
      var e12 = emaC(cc.val, 12), e26 = emaC(cc.val, 26);
      var ml = new Array(cc.val.length).fill(null);
      for (var i = 0; i < cc.val.length; i++)
        if (e12[i] != null && e26[i] != null) ml[i] = e12[i] - e26[i];
      var mc = compact(ml);
      var sig = scatterInto(ml, emaC(mc.val, 9));
      var hist = [];
      for (var k = 0; k < t.length; k++)
        if (ml[k] != null && sig[k] != null)
          hist.push({ time: t[k], value: ml[k] - sig[k], color: (ml[k] - sig[k]) >= 0 ? "rgba(52,211,153,.55)" : "rgba(248,113,113,.55)" });
      subHist(hist);
      subLine(toLine(t, scatter(t.length, cc.idx, ml)), "#60a5fa", 2);
      subLine(toLine(t, sig), "#f59e0b", 1);
    } else if (ACTIVE.panel === "stochrsi") {
      var rc = compact(c);
      var rr = rsiC(rc.val, 14);
      var st = new Array(rr.length).fill(null);
      for (var i2 = 0; i2 < rr.length; i2++) {
        if (rr[i2] == null) continue;
        var mn = Infinity, mx = -Infinity;
        for (var j2 = Math.max(0, i2 - 13); j2 <= i2; j2++) { if (rr[j2] == null) continue; if (rr[j2] < mn) mn = rr[j2]; if (rr[j2] > mx) mx = rr[j2]; }
        if (mx > mn) st[i2] = (rr[i2] - mn) / (mx - mn) * 100;
      }
      var kS = smaC(st.map(function (v) { return v == null ? 0 : v; }), 3); /* leading nulls ~0 — visual fine */
      var dS = smaC(kS, 3);
      /* scatter wapas full timeline par */
      var kL = [], dL = [];
      for (var q2 = 0; q2 < rc.idx.length; q2++) {
        var ti = t[rc.idx[q2]];
        if (kS[q2] != null) kL.push({ time: ti, value: kS[q2] });
        if (dS[q2] != null) dL.push({ time: ti, value: dS[q2] });
      }
      var kSer = subLine(kL, "#60a5fa", 2);
      subLine(dL, "#f59e0b", 1);
      try {
        kSer.createPriceLine({ price: 80, color: "rgba(248,113,113,.5)", lineWidth: 1, lineStyle: 3, axisLabelVisible: true, title: "80" });
        kSer.createPriceLine({ price: 20, color: "rgba(52,211,153,.5)", lineWidth: 1, lineStyle: 3, axisLabelVisible: true, title: "20" });
      } catch (e) {}
    } else if (ACTIVE.panel === "ao") {
      var hl2 = [];
      for (var i3 = 0; i3 < c.length; i3++) hl2.push((h[i3] + l[i3]) / 2);
      var hc = compact(hl2);
      var f5 = scatter(t.length, hc.idx, smaC(hc.val, 5));
      var s34 = scatter(t.length, hc.idx, smaC(hc.val, 34));
      var aoH = [];
      for (var i4 = 0; i4 < t.length; i4++)
        if (f5[i4] != null && s34[i4] != null)
          aoH.push({ time: t[i4], value: f5[i4] - s34[i4], color: (f5[i4] - s34[i4]) >= 0 ? "rgba(52,211,153,.55)" : "rgba(248,113,113,.55)" });
      subHist(aoH);
    }
    try { sc.timeScale().fitContent(); } catch (e) {}
    try {
      if (chart) { var r = chart.timeScale().getVisibleLogicalRange(); if (r) sc.timeScale().setVisibleLogicalRange(r); }
    } catch (e) {}
  }

  /* ================= main apply ================= */
  function applyIndicators() {
    buildUI();
    mySeries.forEach(function (s) { try { s.remove(); } catch (e) {} }); mySeries = [];
    if (!chart || !ser) return;
    var bars;
    try { bars = ser.data(); } catch (e) { return; }
    if (!bars || bars.length < 30) return;

    var t = [], o = [], h = [], l = [], c = [];
    for (var i = 0; i < bars.length; i++) {
      t.push(bars[i].time); o.push(bars[i].open); h.push(bars[i].high); l.push(bars[i].low); c.push(bars[i].close);
    }

    for (var oi = 0; oi < ACTIVE.overlays.length; oi++) {
      var id = ACTIVE.overlays[oi];
      try {
        if (id === "supertrend") {
          var stt = superTrend(t, h, l, c, 10, 3);
          addLine(toLine(t, stt.up), UP, 2, 0, "ST");
          addLine(toLine(t, stt.dn), DN, 2, 0, "ST");
        } else if (id === "emaribbon") {
          var cc = compact(c), lens = [5, 10, 20, 50, 200];
          var cols = ["#38bdf8", "#22d3ee", "#4ade80", "#f59e0b", "#c084fc"];
          for (var e = 0; e < lens.length; e++) {
            var arr = scatter(t.length, cc.idx, emaC(cc.val, lens[e]));
            addLine(toLine(t, arr), cols[e], 1, 0, "EMA" + lens[e]);
          }
        } else if (id === "hma") {
          var cc2 = compact(c);
          var hma = scatter(t.length, cc2.idx, hmaC(cc2.val, 9));
          addLine(toLine(t, hma), "#fb923c", 2, 0, "HMA9");
        } else if (id === "donchian") {
          var upA = new Array(t.length).fill(null), loA = new Array(t.length).fill(null), midA = new Array(t.length).fill(null);
          for (var d2 = 19; d2 < t.length; d2++) {
            var mx = -Infinity, mn = Infinity;
            for (var d3 = d2 - 19; d3 <= d2; d3++) { if (h[d3] > mx) mx = h[d3]; if (l[d3] < mn) mn = l[d3]; }
            upA[d2] = mx; loA[d2] = mn; midA[d2] = (mx + mn) / 2;
          }
          addLine(toLine(t, upA), "#34d399", 1, 0, "DC+");
          addLine(toLine(t, loA), "#f87171", 1, 0, "DC-");
          addLine(toLine(t, midA), "#d4af37", 1, 2, "DC=");
        } else if (id === "ichimoku") {
          var ten = rollingHL(h, l, 9), kij = rollingHL(h, l, 26), spb = rollingHL(h, l, 52);
          var spA = new Array(t.length).fill(null);
          for (var q = 0; q < t.length; q++) if (ten[q] != null && kij[q] != null) spA[q] = (ten[q] + kij[q]) / 2;
          addLine(toLine(t, ten), "#38bdf8", 1, 0, "Tenkan");
          addLine(toLine(t, kij), "#f472b6", 1, 0, "Kijun");
          addLine(toLine(t, spA), "rgba(52,211,153,.75)", 1, 0, "SpanA");
          addLine(toLine(t, spb), "rgba(248,113,113,.75)", 1, 0, "SpanB");
          var chik = [];
          for (var q3 = 26; q3 < t.length; q3++) chik.push({ time: t[q3 - 26], value: c[q3] });
          addLine(chik, "#a78bfa", 1, 2, "Chikou");
        }
      } catch (e) { /* ek indicator fail ho to baaki chalte rahen */ }
    }
    applyPanel(t, h, l, c);
  }

  /* ================= UI ================= */
  function buildUI() {
    var ivs = document.getElementById("crIvs");
    if (!ivs || document.getElementById("crInd")) return;
    var wrap = document.createElement("div");
    wrap.className = "controls";
    wrap.id = "crInd";
    wrap.style.cssText = "margin-top:2px";
    var html = '<span style="font-size:11px;opacity:.75;margin-right:4px">📊 Indicators</span>';
    OVERLAYS.forEach(function (x) {
      html += '<button class="chip' + (ACTIVE.overlays.indexOf(x.id) >= 0 ? " on" : "") + '" data-asind="' + x.id + '">' + x.name + '</button>';
    });
    html += '<span style="font-size:11px;opacity:.75;margin:0 4px">Panel</span>';
    PANELS.forEach(function (x) {
      html += '<button class="chip' + (ACTIVE.panel === x.id ? " on" : "") + '" data-aspan="' + x.id + '">' + x.name + '</button>';
    });
    wrap.innerHTML = html;
    ivs.parentNode.insertBefore(wrap, ivs.nextSibling);

    wrap.addEventListener("click", function (e) {
      var btn = e.target && e.target.closest ? e.target.closest("button") : null;
      if (!btn) return;
      if (btn.hasAttribute("data-asind")) {
        var id = btn.getAttribute("data-asind"), pos = ACTIVE.overlays.indexOf(id);
        if (pos >= 0) { ACTIVE.overlays.splice(pos, 1); btn.classList.remove("on"); }
        else {
          if (ACTIVE.overlays.length >= 3) { /* oldest hatao — chart saaf rakho */
            var old = ACTIVE.overlays.shift();
            var ob = wrap.querySelector('[data-asind="' + old + '"]');
            if (ob) ob.classList.remove("on");
          }
          ACTIVE.overlays.push(id); btn.classList.add("on");
        }
      } else {
        var pid = btn.getAttribute("data-aspan");
        if (ACTIVE.panel === pid) { ACTIVE.panel = ""; btn.classList.remove("on"); }
        else {
          ACTIVE.panel = pid;
          wrap.querySelectorAll("[data-aspan]").forEach(function (b) { b.classList.remove("on"); });
          btn.classList.add("on");
        }
      }
      save();
      applyIndicators();
    });
  }
  function injectSubDiv() {
    var ch = document.getElementById("crChart");
    if (!ch || document.getElementById("crSub")) return;
    var d = document.createElement("div");
    d.id = "crSub";
    d.style.cssText = "display:none;margin-top:4px";
    ch.parentNode.insertBefore(d, ch.nextSibling);
  }

  /* ================= LightweightCharts hook ================= */
  function wrapLib(L) {
    if (!L || L.__asind) return L;
    try {
      var oc = L.createChart;
      L.createChart = function () {
        var ch = oc.apply(L, arguments);
        var isMain = false;
        try { isMain = arguments.length > 0 && arguments[0] === document.getElementById("crChart"); } catch (e) {}
        if (isMain) chart = ch;
        var oacs = ch.addCandlestickSeries;
        ch.addCandlestickSeries = function () {
          var s = oacs.apply(ch, arguments);
          if (isMain) {
            ser = s;
            var osd = s.setData;
            s.setData = function () {
              var r = osd.apply(s, arguments);
              setTimeout(applyIndicators, 0);
              return r;
            };
          }
          return s;
        };
        return ch;
      };
      try { Object.defineProperty(L, "__asind", { value: 1 }); } catch (e) { L.__asind = 1; }
    } catch (e) {}
    return L;
  }
  if (typeof window.LightweightCharts !== "undefined") {
    wrapLib(window.LightweightCharts);
  } else {
    try {
      var _v;
      Object.defineProperty(window, "LightweightCharts", {
        configurable: true,
        get: function () { return _v; },
        set: function (nv) { _v = wrapLib(nv); }
      });
    } catch (e) {}
    var _n = 0;
    var _iv = setInterval(function () {
      if (window.LightweightCharts) {
        if (!window.LightweightCharts.__asind) wrapLib(window.LightweightCharts);
        else { clearInterval(_iv); return; }
      }
      if (++_n > 200) clearInterval(_iv);
    }, 300);
  }

  /* mount: chartread ke section banne ke baad UI inject */
  function start() {
    var tryn = 0;
    var wait = setInterval(function () {
      if (document.getElementById("crIvs")) { clearInterval(wait); injectSubDiv(); buildUI(); applyIndicators(); return; }
      if (++tryn > 120) clearInterval(wait);
    }, 500);
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
