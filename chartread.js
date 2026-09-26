/* chartread.js — Chart Reading section: candles (Yahoo data) + pattern read + levels
   - lightweight-charts (TradingView OSS) se interactive chart, CDN fail ho to SVG fallback
   - patterns: Doji, Hammer, Shooting Star, Engulfing, Marubozu, Inside Bar
   - read: EMA20/50, VWAP, RSI, volume spike, trend
   - levels: prev close, open, H/L, VWAP, EMAs, swings
   - NEW 26 Sep: Volume Profile (POC · Value Area · HVN/LVN) + points in price header */
(function () {
  "use strict";

  var SYMS = ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "ICICIBANK",
              "INFY", "TCS", "SBIN", "TATASTEEL", "ITC"];
  var IVS = ["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"];
  var IVL = {"1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
             "1h": "1h", "4h": "4h", "1d": "1D·1Y"};
  var SRC = {"3m": "1m", "30m": "15m", "4h": "1h"};   /* derived intervals */
  var BUCKET = {"3m": 180, "30m": 1800, "4h": 14400};  /* bucket seconds */
  var REL = "https://github.com/devrajai/ArthaSaar/releases/download/candles/";
  var HDATA = {};   /* chunk cache: chunkId -> {SYMBOL: bars} */
  var SYMLIST = null;  /* data/symbols.json: {syms:[{s,n,c}], updated} */
  var UP = "#34d399", DN = "#ff8b8b";
  var DATA = null;
  var cur = { sym: "NIFTY", iv: "5m" };
  var chart = null, ser = null, vol = null, libOk = false, libTried = false;

  function esc(s) { if (s == null) { s = ""; } return String(s)
    .replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function n2(x) { return Number(x).toLocaleString("en-IN",
    { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }
  function pct(x) { return (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(2) + "%"; }

  /* ---------------- indicators ---------------- */
  function emaArr(a, n) {
    var k = 2 / (n + 1), out = [], e = a[0];
    for (var i = 0; i < a.length; i++) { e = a[i] * k + e * (1 - k); out.push(e); }
    return out;
  }
  function vwapArr(d) {
    var out = [], pv = 0, vv = 0, day = -1;
    for (var i = 0; i < d.t.length; i++) {
      var dt = new Date(d.t[i] * 1000);
      if (dt.getDate() !== day) { day = dt.getDate(); pv = 0; vv = 0; }
      var tp = (d.h[i] + d.l[i] + d.c[i]) / 3;
      pv += tp * (d.v[i] || 0); vv += (d.v[i] || 0);
      out.push(vv > 0 ? pv / vv : d.c[i]);
    }
    return out;
  }
  function rsiArr(c, n) {
    var out = [], g = 0, l = 0;
    for (var i = 1; i < c.length; i++) {
      var ch = c[i] - c[i - 1];
      if (i <= n) { g += Math.max(ch, 0); l += Math.max(-ch, 0);
        if (i === n) { g /= n; l /= n; out[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l); }
        continue; }
      g = (g * (n - 1) + Math.max(ch, 0)) / n;
      l = (l * (n - 1) + Math.max(-ch, 0)) / n;
      out[i] = l === 0 ? 100 : 100 - 100 / (1 + g / l);
    }
    return out;
  }

  /* ---------------- bar aggregation (3m/30m/4h) ---------------- */
  function aggBars(d, bucketSec) {
    var out = { t: [], o: [], h: [], l: [], c: [], v: [] }, cur2 = null;
    function flush() {
      if (cur2) { out.t.push(cur2.t); out.o.push(cur2.o); out.h.push(cur2.h);
        out.l.push(cur2.l); out.c.push(cur2.c); out.v.push(cur2.v); }
    }
    for (var i = 0; i < d.t.length; i++) {
      var b = Math.floor(d.t[i] / bucketSec);
      if (!cur2 || cur2.b !== b) { flush(); cur2 = { b: b, t: d.t[i], o: d.o[i], h: d.h[i], l: d.l[i], c: d.c[i], v: 0 }; }
      if (d.h[i] > cur2.h) cur2.h = d.h[i];
      if (d.l[i] < cur2.l) cur2.l = d.l[i];
      cur2.c = d.c[i]; cur2.v += (d.v[i] || 0);
    }
    flush();
    return out;
  }

  /* ---------------- daily archive (release assets) ---------------- */
  function loadSymbols() {
    if (SYMLIST) return Promise.resolve(SYMLIST);
    return fetch("data/symbols.json?t=" + Date.now()).then(function (r) { return r.json(); })
      .then(function (d) { SYMLIST = d; return d; });
  }
  function findChunk(sym) {
    if (SYMLIST && SYMLIST.syms) for (var i = 0; i < SYMLIST.syms.length; i++)
      if (SYMLIST.syms[i].s === sym) return SYMLIST.syms[i].c;
    return -1;
  }
  function loadDaily(sym) {
    var cid = findChunk(sym);
    if (cid < 0) return Promise.reject("no chunk");
    if (HDATA[cid]) return Promise.resolve(HDATA[cid][sym]);
    return fetch(REL + "daily-" + (cid < 10 ? "0" + cid : cid) + ".json")
      .then(function (r) { return r.json(); })
      .then(function (d) { HDATA[cid] = d.syms || {}; return HDATA[cid][sym]; });
  }

  /* ---------------- patterns ---------------- */
  function detect(d) {
    var n = d.t.length, res = [], seen = {};
    if (n < 3) return res;
    var start = Math.max(0, n - 7);
    function B(i) { return { o: d.o[i], h: d.h[i], l: d.l[i], c: d.c[i] }; }
    for (var i = start; i < n; i++) {
      var b = B(i), body = Math.abs(b.c - b.o), rng = (b.h - b.l) || 1e-9;
      var up = b.c >= b.o;
      var when = i === n - 1 ? "last candle" : (n - 1 - i) + " bar pehle";
      var lw = Math.min(b.o, b.c) - b.l, uw = b.h - Math.max(b.o, b.c);
      function add(s, bd, note) {
        if (seen[s]) return; seen[s] = 1;
        res.push({ s: s, b: bd, n: note + " (" + when + ")" });
      }
      if (body / rng < 0.08)
        add("Doji", "neutral", "Indecision — buyers/sellers barabar, next candle decide karega");
      if (body / rng > 0.9)
        add((up ? "Bullish" : "Bearish") + " Marubozu", up ? "bull" : "bear",
            up ? "Poora body, wick nahi — strong buying" : "Poora body niche — strong selling");
      if (body > 0 && lw >= 0.55 * rng && uw <= 0.2 * rng && body <= 0.35 * rng)
        add("Hammer", "bull", "Niche lamba wick — giraya toh wapas khareed diya");
      if (body > 0 && uw >= 0.55 * rng && lw <= 0.2 * rng && body <= 0.35 * rng)
        add("Shooting Star", "bear", "Upar lamba wick — rally pe bikwali");
      if (i > 0) {
        var p = B(i - 1), pb = Math.abs(p.c - p.o);
        if (!up && p.c >= p.o && b.c < p.o && b.o >= p.c && body > pb)
          add("Bearish Engulfing", "bear", "Laal candle ne kal ki hari poori nigal li — sellers ka control");
        if (up && p.c <= p.o && b.c > p.o && b.o <= p.c && body > pb)
          add("Bullish Engulfing", "bull", "Hari candle ne laal cover kar di — buyers wapas");
        if (b.h <= p.h && b.l >= p.l)
          add("Inside Bar", "neutral", "Pichli candle ke andar squeeze — breakout aane wala");
      }
    }
    return res;
  }

  /* swings: last 40 bars ke local highs/lows */
  function swings(d) {
    var n = d.t.length, hi = [], lo = [];
    for (var i = Math.max(1, n - 40); i < n - 1; i++) {
      if (d.h[i] >= d.h[i - 1] && d.h[i] >= d.h[i + 1]) hi.push(d.h[i]);
      if (d.l[i] <= d.l[i - 1] && d.l[i] <= d.l[i + 1]) lo.push(d.l[i]);
    }
    hi.sort(function (a, b) { return b - a; }); lo.sort(function (a, b) { return a - b; });
    return { r: hi.slice(0, 2), s: lo.slice(0, 2) };
  }

  /* ---------------- panels ---------------- */
  function lineBox(l, r, cls) {
    return '<div class="note" style="display:flex;justify-content:space-between">' +
      '<span>' + l + '</span><b style="' + (cls ? "color:" + cls : "") + '">' + r + '</b></div>';
  }
  function readPanel(name, d, pc) {
    var n = d.t.length; if (!n) return '<div class="note">data nahi.</div>';
    var c = d.c, last = c[n - 1];
    var e20 = emaArr(c, 20), e50 = emaArr(c, 50);
    var vw = vwapArr(d), r = rsiArr(c, 14);
    var avgv = 0, cnt = 0;
    for (var i = Math.max(0, n - 20); i < n; i++) { avgv += (d.v[i] || 0); cnt++; }
    avgv = cnt ? avgv / cnt : 0;
    var lastv = d.v[n - 1] || 0;
    var chg = pc ? (last - pc) / pc * 100 : 0;
    var h = "";
    var trend;
    if (last > e20[n - 1] && e20[n - 1] > e50[n - 1]) trend = ["Uptrend", UP];
    else if (last < e20[n - 1] && e20[n - 1] < e50[n - 1]) trend = ["Downtrend", DN];
    else if (last > e50[n - 1]) trend = ["Recovery try — EMA50 ke upar, EMA20 abhi paar nahi", "#d4af37"];
    else trend = ["Weak — EMAs ke neeche", "#d4af37"];
    h += lineBox("Trend (EMA20/50)", esc(trend[0]), trend[1]);
    h += lineBox("VWAP se", pct((last - vw[n - 1]) / vw[n - 1] * 100),
      last >= vw[n - 1] ? UP : DN);
    var rsi = r[n - 1];
    h += lineBox("RSI(14)", rsi == null ? "—" :
      rsi.toFixed(0) + (rsi > 70 ? " overbought" : rsi < 30 ? " oversold" : ""),
      rsi > 70 ? DN : rsi < 30 ? UP : null);
    h += lineBox("Volume (last vs 20-bar avg)", avgv ?
      (lastv / avgv).toFixed(1) + "×" + (lastv > 2 * avgv ? " 🔥 spike" : "") : "—",
      lastv > 2 * avgv ? "#d4af37" : null);
    var pats = detect(d);
    if (!pats.length) h += lineBox("Pattern", "koi major nahi", null);
    else {
      for (var k = 0; k < Math.min(pats.length, 4); k++) {
        var col = pats[k].b === "bull" ? UP : pats[k].b === "bear" ? DN : "#d4af37";
        h += '<div class="note" style="margin-top:6px"><b style="color:' + col + '">' +
          esc(pats[k].s) + '</b> — ' + esc(pats[k].n) + '</div>';
      }
    }
    h += lineBox("Aaj", esc(name) + " " + n2(last) + " (" + pct(chg) + " vs prev close)",
      chg >= 0 ? UP : DN);
    return h;
  }
  function levelsPanel(d, pc) {
    var n = d.t.length; if (!n) return "";
    var sw = swings(d);
    var hi = -1e18, lo = 1e18, op = d.o[n - 1];
    for (var i = n - 1; i >= 0; i--) {
      var dt = new Date(d.t[i] * 1000);
      if (hi < d.h[i]) hi = d.h[i]; if (lo > d.l[i]) lo = d.l[i];
    }
    var vw = vwapArr(d), e20 = emaArr(d.c, 20), e50 = emaArr(d.c, 50);
    var h = "";
    h += lineBox("Prev close (pivot)", pc ? n2(pc) : "—", "#d4af37");
    h += lineBox("Day high", n2(hi), DN);
    h += lineBox("Day low", n2(lo), UP);
    h += lineBox("VWAP", n2(vw[n - 1]), null);
    h += lineBox("EMA20", n2(e20[n - 1]), null);
    h += lineBox("EMA50", n2(e50[n - 1]), null);
    for (var s = 0; s < sw.r.length; s++) h += lineBox("Resistance " + (s + 1), n2(sw.r[s]), DN);
    for (var q = 0; q < sw.s.length; q++) h += lineBox("Support " + (q + 1), n2(sw.s[q]), UP);
    return h;
  }
  var GLOSS = [
    ["Doji", "open ≈ close — market soch raha hai"],
    ["Hammer", "niche wick 2× body — girane par kharidari aayi"],
    ["Engulfing", "aaj ki candle ne kal ki poori dhak li — control badla"],
    ["VWAP", "aaj ka average khareedna rate — uske upar = strong"],
    ["EMA20/50", "20 = short mood, 50 = trend; dono ke upar = uptrend"],
    ["POC", "point of control — sabse zyada volume wala level, price uski taraf khinchta hai"],
    ["Value Area", "70% volume ka band — price andar = balanced, bahar = trend"],
    ["HVN / LVN", "high volume node = magnet zone; low volume node = vacuum, wahan move tez hota hai"]
  ];
  function glossaryPanel() {
    var h = "";
    for (var i = 0; i < GLOSS.length; i++)
      h += '<div class="note" style="display:flex;justify-content:space-between"><span><b>' +
        GLOSS[i][0] + '</b></span><span style="opacity:.75">' + esc(GLOSS[i][1]) + '</span></div>';
    return h;
  }

  /* ---------------- chart ---------------- */
  function loadLib(cb) {
    if (libOk || typeof window.LightweightCharts !== "undefined") {
      libOk = true; return cb(true);
    }
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

  function svgFallback(d, name, chg) {
    var n = d.t.length, w = 640, h = 260;
    var lo = 1e18, hi = -1e18;
    for (var i = 0; i < n; i++) { lo = Math.min(lo, d.l[i]); hi = Math.max(hi, d.h[i]); }
    var span = (hi - lo) || 1;
    var parts = [];
    for (var j = 0; j < n; j++) {
      var x = Math.round(j * (w / n) + (w / n) / 2);
      var bw = Math.max(2, Math.floor(w / n) - 1);
      var Y = function (v) { return (h - 8) - (v - lo) / span * (h - 16); };
      var col = d.c[j] >= d.o[j] ? UP : DN;
      parts.push('<line x1="' + x + '" y1="' + Y(d.h[j]).toFixed(1) +
        '" x2="' + x + '" y2="' + Y(d.l[j]).toFixed(1) +
        '" stroke="' + col + '" stroke-width="1"/>');
      var yo = Y(d.o[j]), yc = Y(d.c[j]);
      parts.push('<rect x="' + (x - Math.floor(bw / 2)) + '" y="' +
        Math.min(yo, yc).toFixed(1) + '" width="' + bw + '" height="' +
        Math.max(1, Math.abs(yc - yo)).toFixed(1) + '" fill="' + col + '"/>');
    }
    return '<div style="border:1px solid rgba(255,255,255,.1);border-radius:12px;background:rgba(0,0,0,.15)">' +
      '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none" style="width:100%;height:260px;display:block">' +
      parts.join("") + '</svg></div>';
  }

  function drawChart(name, d, chg) {
    var host = document.getElementById("crChart");
    if (!host) return;
    var bars = [];
    for (var i = 0; i < d.t.length; i++) {
      bars.push({ time: d.t[i], open: d.o[i], high: d.h[i], low: d.l[i], close: d.c[i] });
    }
    if (bars.length > 1 && bars[bars.length - 1].time <= bars[bars.length - 2].time) bars.pop();
    loadLib(function (ok) {
      if (chart) { try { chart.remove(); } catch (e) {} chart = null; }
      host.innerHTML = "";
      if (!ok) {
        host.innerHTML = svgFallback(d, name, chg);
        return;
      }
      var light = document.documentElement.getAttribute("data-theme") === "light";
      var grid = light ? "rgba(0,0,0,.06)" : "rgba(255,255,255,.06)";
      var txt = light ? "#41506b" : "#8fa3c8";
      try {
        chart = LightweightCharts.createChart(host, {
          height: 300, layout: { background: { type: "solid", color: "transparent" },
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
        ser.setData(bars);
        vol = chart.addHistogramSeries({ priceScaleId: "vol", priceFormat: { type: "volume" } });
        var vbars = [];
        for (var k = 0; k < d.t.length; k++)
          vbars.push({ time: d.t[k], value: d.v[k] || 0,
            color: d.c[k] >= d.o[k] ? "rgba(52,211,153,.4)" : "rgba(255,139,139,.4)" });
        vol.setData(vbars);
        chart.priceScale("vol").applyOptions({ scaleMargins: { top: 0.82, bottom: 0 } });
        chart.timeScale().fitContent();
        try { chart.applyOptions({ width: host.clientWidth }); } catch (e) {}
        if (window.addEventListener) window.addEventListener("resize", function () {
          if (chart && host) try { chart.applyOptions({ width: host.clientWidth }); } catch (e2) {}
        });
      } catch (e) {
        host.innerHTML = svgFallback(d, name, chg);
      }
    });
  }

  /* ---------------- volume profile (POC · value area · HVN/LVN) ---------------- */
  function volProfile(d) {
    var n = d.t.length; if (n < 20) return null;
    var lo = Infinity, hi = -Infinity, tot = 0, tpo = false;
    for (var i = 0; i < n; i++) {
      var v = Number(d.v[i]);
      if (d.l[i] < lo) lo = d.l[i];
      if (d.h[i] > hi) hi = d.h[i];
      if (isFinite(v)) tot += v;
    }
    if (!tot || !isFinite(tot)) { tpo = true; tot = n; }
    if (hi <= lo) return null;
    var B = 48, w = (hi - lo) / B, prof = [], i2;
    for (i2 = 0; i2 < B; i2++) prof.push(0);
    for (i2 = 0; i2 < n; i2++) {
      var v2 = tpo ? 1 : Number(d.v[i2]);
      if (!isFinite(v2) || !v2) continue;
      var cl = d.l[i2], ch = d.h[i2];
      if (ch <= cl) { prof[Math.min(B - 1, Math.max(0, Math.floor((cl - lo) / w)))] += v2; continue; }
      var b1 = Math.max(0, Math.floor((cl - lo) / w)), b2 = Math.min(B - 1, Math.floor((ch - lo) / w)), sp = b2 - b1 + 1;
      for (var b3 = b1; b3 <= b2; b3++) prof[b3] += v2 / sp;
    }
    var poc = 0, k;
    for (k = 1; k < B; k++) if (prof[k] > prof[poc]) poc = k;
    var acc = prof[poc], a = poc, z = poc;
    while (acc < 0.7 * tot && (a > 0 || z < B - 1)) {
      var vl = a > 0 ? prof[a - 1] : -1, vr = z < B - 1 ? prof[z + 1] : -1;
      if (vr >= vl) { z++; acc += Math.max(vr, 0); } else { a--; acc += Math.max(vl, 0); }
    }
    var px = function (b) { return lo + (b + 0.5) * w; };
    var hvn = [], lvn = [];
    for (var q = 0; q < B; q++) {
      var mx = 0;
      for (var r2 = Math.max(0, q - 2); r2 <= Math.min(B - 1, q + 2); r2++) if (prof[r2] > mx) mx = prof[r2];
      if (q !== poc && prof[q] > 0.55 * prof[poc] && prof[q] === mx) hvn.push(px(q));
      if (q > 0 && q < B - 1 && prof[q] < 0.25 * prof[poc] && prof[q] <= prof[q - 1] && prof[q] <= prof[q + 1]) lvn.push(px(q));
    }
    return { poc: px(poc), val: px(a), vah: px(z), hvn: hvn.slice(0, 3), lvn: lvn.slice(0, 2), tpo: tpo };
  }
  function vpPanel(vp, last) {
    var h = "";
    var inVA = last >= vp.val && last <= vp.vah;
    h += lineBox(vp.tpo ? "POC — control (TPO)" : "POC — control level", n2(vp.poc), last >= vp.poc ? UP : DN);
    h += lineBox("Value Area (70% vol)", n2(vp.val) + " – " + n2(vp.vah), inVA ? "#d4af37" : null);
    h += lineBox("Price vs POC", pct((last - vp.poc) / vp.poc * 100), last >= vp.poc ? UP : DN);
    if (vp.hvn.length) h += lineBox("HVN — magnet zones", vp.hvn.map(function (x) { return n2(x); }).join(" · "), UP);
    if (vp.lvn.length) h += lineBox("LVN — vacuum, tez cross", vp.lvn.map(function (x) { return n2(x); }).join(" · "), DN);
    h += '<div class="note" style="margin-top:6px">' + (vp.tpo ? "index me volume nahi aata — TPO (kitni der price raha) se bana hai" : "heavy volume wale levels = jahan bade players beth gaye · halka area jaldi cross hota hai") + ' — read hai, tip nahi</div>';
    return h;
  }

  function render() {
    var symsEl = document.getElementById("crSyms");
    var ivsEl = document.getElementById("crIvs");
    var priceEl = document.getElementById("crPrice");
    if (!symsEl) return;
    if (!DATA || !DATA.syms) {
      priceEl.innerHTML = '<div class="note">candles data abhi nahi mila — thodi der baad try karo.</div>';
      return;
    }
    /* symbol chips */
    var h = "";
    for (var i = 0; i < SYMS.length; i++) {
      var s = SYMS[i];
      if (!DATA.syms[s]) continue;
      h += '<button class="chip' + (s === cur.sym ? " on" : "") + '" data-cr-sym="' + s + '">' + s + '</button>';
    }
    symsEl.innerHTML = h;
    /* interval chips (available only; derived/1d hamesha milenge) */
    var av = DATA.syms[cur.sym] || {};
    var h2 = "";
    for (var j = 0; j < IVS.length; j++) {
      var iv = IVS[j];
      var has = SRC[iv] ? !!av[SRC[iv]] : !!av[iv];
      if (iv === "1d") has = true; /* archive me sab hai */
      if (!has) continue;
      h2 += '<button class="chip' + (iv === cur.iv ? " on" : "") + '" data-cr-iv="' + iv + '">' + IVL[iv] + '</button>';
    }
    ivsEl.innerHTML = h2;
    if (cur.iv === "1d") { renderDaily(); return; }
    var d = av[cur.iv] || av["5m"] || av["15m"] || av["1h"];
    if (!d) {
      if (av["1h"] || av["15m"]) { d = null; } else { priceEl.innerHTML = '<div class="note">is symbol ka data nahi.</div>'; return; }
    }
    if (SRC[cur.iv] && av[SRC[cur.iv]]) d = aggBars(av[SRC[cur.iv]], BUCKET[cur.iv]);
    d = d || av["5m"] || av["15m"] || av["1h"];
    if (!d) { priceEl.innerHTML = '<div class="note">is symbol ka data nahi.</div>'; return; }
    var pc = av.pc;
    var last = d.c[d.c.length - 1];
    var chg = pc ? (last - pc) / pc * 100 : 0;
    priceEl.innerHTML = '<div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:6px">' +
      '<div class="subhead">' + esc(cur.sym) + ' · ' + esc(cur.iv) + '</div>' +
      '<div style="font-family:var(--mono);font-size:18px;font-weight:700">' + n2(last) +
      ' <span style="color:' + (chg >= 0 ? UP : DN) + ';font-size:13px">' + (pc ? ((last - pc >= 0 ? "+" : "−") + Math.abs(last - pc).toFixed(1) + " pts · ") : "") + pct(chg) + '</span></div></div>' +
      '<div class="note" style="margin:2px 0 8px">updated ' + esc(DATA.updated) + ' · Yahoo free EOD/intraday</div>';
    drawChart(cur.sym, d, chg);
    document.getElementById("crRead").innerHTML = readPanel(cur.sym, d, pc);
    document.getElementById("crLevels").innerHTML = levelsPanel(d, pc);
    var vp = volProfile(d);
    var vpEl = document.getElementById("crVP");
    if (vpEl) vpEl.innerHTML = vp ? vpPanel(vp, last) :
      '<div class="note">is symbol ka volume data nahi mila — VP sirf wahan hota hai jahan volume aata hai.</div>';
  }

  function renderDaily() {
    var priceEl = document.getElementById("crPrice");
    priceEl.innerHTML = '<div class="note">1-saal daily archive load ho raha...</div>';
    loadSymbols().then(function () {
      return loadDaily(cur.sym);
    }).then(function (bars) {
      if (!bars || !bars.t || !bars.t.length) {
        document.getElementById("crPrice").innerHTML = '<div class="note">is symbol ka archive nahi mila.</div>';
        return;
      }
      var d = bars;
      var pc = d.c.length > 1 ? d.c[d.c.length - 2] : 0;
      var last = d.c[d.c.length - 1];
      var chg = pc ? (last - pc) / pc * 100 : 0;
      document.getElementById("crPrice").innerHTML = '<div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:6px">' +
        '<div class="subhead">' + esc(cur.sym) + ' · 1D (1 saal)</div>' +
        '<div style="font-family:var(--mono);font-size:18px;font-weight:700">' + n2(last) +
        ' <span style="color:' + (chg >= 0 ? UP : DN) + ';font-size:13px">' + (pc ? ((last - pc >= 0 ? "+" : "\u2212") + Math.abs(last - pc).toFixed(1) + " pts · ") : "") + pct(chg) + '</span></div></div>' +
        '<div class="note" style="margin:2px 0 8px">' + (d.t.length) + ' din ka data · EOD archive · roz market close ke baad update</div>';
      drawChart(cur.sym, d, chg);
      document.getElementById("crRead").innerHTML = readPanel(cur.sym, d, pc);
      document.getElementById("crLevels").innerHTML = levelsPanel(d, pc);
      var vp = volProfile(d);
      var vpEl = document.getElementById("crVP");
      if (vpEl) vpEl.innerHTML = vp ? vpPanel(vp, last) :
        '<div class="note">is symbol ka volume data nahi mila.</div>';
    }, function () {
      document.getElementById("crPrice").innerHTML = '<div class="note">archive load nahi hua — thodi der baad try karo.</div>';
    });
  }

  function onClick(e) {
    var t = e.target || e.srcElement;
    while (t && t !== document.body && !t.getAttribute) t = t.parentNode;
    if (!t || !t.getAttribute) return;
    var s = t.getAttribute("data-cr-sym"), iv = t.getAttribute("data-cr-iv");
    if (s) { cur.sym = s;
      if (DATA && DATA.syms[s]) {
        if (cur.iv !== "1d" && !DATA.syms[s][cur.iv] &&
            !(SRC[cur.iv] && DATA.syms[s][SRC[cur.iv]])) cur.iv = "5m";
      } else { cur.iv = "1d"; }  /* non-core symbol -> archive daily */
      render(); }
    else if (iv) { cur.iv = iv; render(); }
  }

  function mount() {
    if (document.getElementById("chartread")) return;
    /* tile — GTI tile ke baad */
    try {
      var hg = document.querySelector("section#home .homegrid");
      var gtile = hg ? hg.querySelector('a[href="#gti"]') : null;
      var tile = document.createElement("a");
      tile.className = "tile";
      tile.href = "#chartread";
      tile.innerHTML = '<span class="t-ic">🕯️</span><span class="t-nm">Chart Reading</span><span class="t-sb">candles · patterns · levels</span>';
      if (gtile && gtile.nextSibling) hg.insertBefore(tile, gtile.nextSibling);
      else if (hg) hg.appendChild(tile);
    } catch (e) {}
    /* section — footer se pehle */
    var sec = document.createElement("section");
    sec.id = "chartread";
    sec.style.display = "none";
    sec.innerHTML =
      '<a class="backbtn" href="#home">⌂ Home</a>' +
      '<h2>Chart Reading — candles · patterns · levels</h2>' +
      '<div style="position:relative;margin:6px 0">' +
      '<input id="crSearch" type="text" placeholder="koi bhi NSE stock likho (TATAMOTORS, KPIT...) — 1 saal daily chart" ' +
      'autocomplete="off" style="width:100%;box-sizing:border-box;padding:8px 12px;border-radius:10px;border:1px solid rgba(125,180,255,.4);background:rgba(96,165,250,.08);color:inherit;font-size:13px">' +
      '<div id="crSugg" style="display:none;position:absolute;top:100%;left:0;right:0;z-index:60;max-height:220px;overflow-y:auto;background:#161b26;border:1px solid rgba(125,180,255,.35);border-radius:0 0 10px 10px;box-shadow:0 8px 24px rgba(0,0,0,.5)"></div>' +
      '</div>' +
      '<div class="controls" id="crSyms"></div>' +
      '<div class="controls" id="crIvs"></div>' +
      '<div class="card"><div id="crPrice"></div><div id="crChart"></div></div>' +
      '<div class="grid g2">' +
      '<div class="card"><div class="subhead">Aaj ka read</div><div id="crRead"></div></div>' +
      '<div class="card"><div class="subhead">Levels</div><div id="crLevels"></div></div>' +
      '</div>' +
      '<div class="card"><div class="subhead">Volume Profile — heavy volume zones</div><div id="crVP"></div></div>' +
      '<div class="card"><div class="subhead">Padho — pattern glossary</div><div id="crGloss"></div></div>' +
      '<div class="footer-note">data: Yahoo (free) · 1m/3m/5m = aaj, 15m/30m = 5 din, 1h/4h = 1 mahina, 1D = 1 saal (sab NSE stocks) · patterns sirf read hai, tip nahi</div>';
    var foot = document.querySelector("footer");
    if (foot && foot.parentNode) foot.parentNode.insertBefore(sec, foot);
    else document.body.appendChild(sec);
    document.getElementById("crGloss").innerHTML = glossaryPanel();
    /* lazy loader register (oldapp ke loaders map me) */
    try {
      if (typeof loaders !== "undefined") {
        loaders.chartread = function () {
          fetch("data/candles.json?t=" + Date.now())
            .then(function (r) { return r.json(); })
            .then(function (d) { DATA = d; render(); })
            .catch(function () {
              var p = document.getElementById("crPrice");
              if (p) p.innerHTML = '<div class="note">candles data abhi nahi mila.</div>';
            });
        };
      }
    } catch (e) {}
    /* agar loaders map mila hi nahi (ordering) to direct fetch karke ready rakh */
    fetch("data/candles.json?t=" + Date.now())
      .then(function (r) { return r.json(); })
      .then(function (d) { DATA = d; if (document.getElementById("crPrice")) render(); })
      .catch(function () {});
    /* symbol search */
    var inp = null;
    function bindSearch() {
      var el = document.getElementById("crSearch");
      if (!el) return;
      inp = el;
      el.addEventListener("input", function () {
        var q = el.value.trim().toUpperCase();
        var box = document.getElementById("crSugg");
        if (!q || q.length < 2 || !SYMLIST) { box.style.display = "none"; return; }
        var out = "", n = 0;
        for (var i = 0; i < SYMLIST.syms.length && n < 14; i++) {
          var it = SYMLIST.syms[i];
          if (it.s.indexOf(q) === 0 || (it.n || "").toUpperCase().indexOf(q) >= 0) {
            out += '<div data-cr-sym="' + esc(it.s) + '" style="padding:7px 12px;cursor:pointer;display:flex;justify-content:space-between;gap:8px;border-bottom:1px solid rgba(255,255,255,.05)">' +
              '<b style="font-size:12.5px">' + esc(it.s) + '</b><span class="note" style="font-size:11px;text-align:right">' + esc(it.n) + '</span></div>';
            n++;
          }
        }
        if (!out) out = '<div class="note" style="padding:8px 12px">kuch nahi mila</div>';
        box.innerHTML = out; box.style.display = "block";
      });
      el.addEventListener("keydown", function (e) {
        if (e.key === "Enter" && el.value.trim()) {
          var box = document.getElementById("crSugg");
          var first = box.querySelector("[data-cr-sym]");
          if (first) { pick(first.getAttribute("data-cr-sym")); return; }
        }
      });
    }
    function pick(sym2) {
      cur.sym = sym2; cur.iv = "1d";
      var box = document.getElementById("crSugg"); if (box) box.style.display = "none";
      if (inp) inp.value = "";
      render();
    }
    document.addEventListener("click", function (e) {
      var t = e.target || e.srcElement;
      while (t && t !== document.body && !t.getAttribute) t = t.parentNode;
      if (t && t.getAttribute && t.getAttribute("data-cr-sym")) return; /* onClick handle karega */
      var box = document.getElementById("crSugg");
      if (box && box.style.display === "block") box.style.display = "none";
    }, false);
    loadSymbols().then(bindSearch, function () {});
    document.addEventListener("click", onClick, false);
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();
