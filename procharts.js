/* procharts.js v2 -- Chart Reading section me 3 pro features (Bloomberg-style, free data):
   1. MULTI-TIMEFRAME RADAR -- index ke 4 timeframes ek saath (15m / 1h / 4h / Daily)
      + trend confluence badge. candles.json (intraday) + CDN idx archive.
      CARD SECTION KE TOP PE HAI (price chart se pehle).
   2. PIVOT POINTS card -- Classic / Fibonacci / Camarilla / Woodie, Daily/Weekly/Monthly
      (daily chunks se, jo Chart Reading wala 5-saal archive hai)
   3. RENKO + POINT&FIGURE card -- noise-free charts (Renko bricks, P&F X/O columns)
   Sab self-contained, kisi aur file ko touch nahi karta. */
(function () {
  "use strict";
  var UP = "#77f37b", DN = "#ff8b8b", NEU = "#8fa3c8";
  var PCBASE = window.__PC_BASE || "/api/data?ref=data&p=data/";
  var CHUNKS = {}, SYML = null;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function n2(v) { return v == null ? "-" : Number(v).toLocaleString("en-IN", { maximumFractionDigits: 2 }); }

  function symbolsOnce() {
    if (SYML) return Promise.resolve(SYML);
    return fetch("data/symbols.json").then(function (r) { return r.json(); }).then(function (d) { SYML = d.syms || []; return SYML; });
  }
  function chunkFor(sym) {
    return symbolsOnce().then(function (L) {
      for (var i = 0; i < L.length; i++) if (L[i].s === sym) return L[i].c;
      return -1;
    });
  }
  function loadSymDaily(sym) {
    return chunkFor(sym).then(function (cid) {
      if (cid < 0) return null;
      if (CHUNKS[cid]) return CHUNKS[cid][sym] || null;
      return fetch(PCBASE + "daily-" + (cid < 10 ? "0" + cid : cid) + ".json")
        .then(function (r) { return r.json(); })
        .then(function (d) { CHUNKS[cid] = d.syms || {}; return CHUNKS[cid][sym] || null; });
    });
  }

  /* ================= PIVOT POINTS ================= */
  function pivotMethods(H, L, C) {
    var m = {};
    var P = (H + L + C) / 3, R = H - L;
    m["Classic"] = [["P3", P], ["R1", 2 * P - L], ["S1", 2 * P - H], ["R2", P + R], ["S2", P - R], ["R3", H + 2 * (P - L)], ["S3", L - 2 * (H - P)]];
    var PW = (H + L + 2 * C) / 4;
    m["Woodie"] = [["P3", PW], ["R1", 2 * PW - L], ["S1", 2 * PW - H], ["R2", PW + R], ["S2", PW - R], ["R3", H + 2 * (PW - L)], ["S3", L - 2 * (H - PW)]];
    m["Fibonacci"] = [["P3", P], ["R1", P + 0.382 * R], ["S1", P - 0.382 * R], ["R2", P + 0.618 * R], ["S2", P - 0.618 * R], ["R3", P + R], ["S3", P - R]];
    m["Camarilla"] = [["P3", C], ["R1", C + R * 1.1 / 12], ["S1", C - R * 1.1 / 12], ["R2", C + R * 1.1 / 6], ["S2", C - R * 1.1 / 6], ["R3", C + R * 1.1 / 4], ["S3", C - R * 1.1 / 4], ["R4", C + R * 1.1 / 2], ["S4", C - R * 1.1 / 2]];
    return m;
  }
  function periodBars(b, per) {
    /* completed pichla din / hafta / mahina */
    var t = b.t, n = t.length;
    if (per === "D") { var i = n - 1; return { H: b.h[i - 1], L: b.l[i - 1], C: b.c[i - 1], label: "kal (" + new Date(t[i - 1] * 1000).toLocaleDateString("en-IN", { day: "2-digit", month: "short" }) + ")" }; }
    var groups = {}, order = [];
    for (var i = 0; i < n; i++) {
      var d = new Date(t[i] * 1000), key;
      if (per === "W") { var dd = new Date(Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate())); var day = dd.getUTCDay() || 7; dd.setUTCDate(dd.getUTCDate() - day + 1); key = "W" + dd.getTime(); }
      else key = "M" + d.getUTCFullYear() + "-" + d.getUTCMonth();
      if (!groups[key]) { groups[key] = { h: b.h[i], l: b.l[i], c: b.c[i], t: t[i] }; order.push(key); }
      else { var g = groups[key]; g.h = Math.max(g.h, b.h[i]); g.l = Math.min(g.l, b.l[i]); g.c = b.c[i]; g.t = t[i]; }
    }
    var last = order[order.length - 1];
    var lg = groups[last];
    var lbl = per === "W" ? "pichla hafta" : "pichla mahina";
    return { H: lg.h, L: lg.l, C: lg.c, label: lbl };
  }
  var pvSym = "NIFTY", pvPer = "D";
  function renderPivots() {
    var box = document.getElementById("pcPivBox");
    box.innerHTML = '<div class="note">pivot data load ho raha...</div>';
    loadSymDaily(pvSym).then(function (b) {
      if (!b || !b.t || b.t.length < 5) { box.innerHTML = '<div class="note">is symbol ka daily archive nahi mila</div>'; return; }
      var pb = periodBars(b, pvPer);
      var price = b.c[b.c.length - 1];
      var m = pivotMethods(pb.H, pb.L, pb.C);
      var h = '<div class="note" style="margin-bottom:6px">' + esc(pvSym) + ' \u00b7 ' + pb.label + ' H ' + n2(pb.H) + ' \u00b7 L ' + n2(pb.L) + ' \u00b7 C ' + n2(pb.C) + ' \u00b7 abhi ' + n2(price) + '</div>';
      for (var mk in m) {
        h += '<div class="subhead" style="margin-top:8px">' + mk + '</div>';
        for (var i = 0; i < m[mk].length; i++) {
          var nm = m[mk][i][0] === "P3" ? "PIVOT" : m[mk][i][0], v = m[mk][i][1];
          var near = Math.abs(v - price) / price < 0.003;
          var col = nm.indexOf("R") === 0 ? DN : (nm.indexOf("S") === 0 ? UP : "#eab308");
          h += '<div class="note" style="display:flex;justify-content:space-between;margin:2px 0' + (near ? ';background:rgba(234,179,0,.12);border-radius:6px;padding:2px 6px' : '') + '">' +
            '<span style="color:' + col + '"><b>' + nm + '</b></span><span style="font-family:var(--mono,monospace)">' + n2(v) +
            ' <span style="opacity:.6;font-size:10.5px">' + (v > price ? "+" : "") + ((v - price) / price * 100).toFixed(2) + '%</span></span></div>';
        }
      }
      h += '<div class="note" style="margin-top:6px;opacity:.65">R = resistance (upar) \u00b7 S = support (neeche) \u00b7 piela = jahan price se sabse paas hai \u00b7 pivot ke upar = bulls, neeche = bears</div>';
      box.innerHTML = h;
    }, function () { box.innerHTML = '<div class="note">data nahi mila</div>'; });
  }

  /* ================= RENKO + P&F ================= */
  function toBars(d) { var o = []; for (var i = 0; i < d.t.length; i++) o.push({ c: d.c[i], h: d.h[i], l: d.l[i] }); return o; }
  function renkoBricks(bars, bs) {
    var out = [], base = bars[0].c;
    for (var i = 1; i < bars.length; i++) {
      var c = bars[i].c;
      while (c >= base + bs) { out.push({ d: 1, p: base + bs }); base += bs; }
      while (c <= base - bs) { out.push({ d: -1, p: base - bs }); base -= bs; }
    }
    return out;
  }
  function pnfColumns(bars, bs, rev) {
    var cols = [], cur = null, hi = bars[0].c, lo = hi, base = hi;
    function boxIdx(p) { return Math.round(p / bs); }
    for (var i = 1; i < bars.length; i++) {
      var c = bars[i].c;
      if (!cur) {
        if (c >= hi + bs) cur = { dir: 1, a: boxIdx(hi), b: boxIdx(c) };
        else if (c <= lo - bs) cur = { dir: -1, a: boxIdx(lo), b: boxIdx(c) };
        if (cur) { cols.push(cur); hi = c; lo = c; base = c; }
        continue;
      }
      if (cur.dir > 0) {
        if (c >= cur.b * bs + bs) { cur.b = boxIdx(c); hi = c; }
        else if (c <= (cur.b - rev) * bs) { cur = { dir: -1, a: cur.b - 1, b: boxIdx(c) }; cols.push(cur); lo = c; }
      } else {
        if (c <= cur.b * bs - bs) { cur.b = boxIdx(c); lo = c; }
        else if (c >= (cur.b + rev) * bs) { cur = { dir: 1, a: cur.b + 1, b: boxIdx(c) }; cols.push(cur); hi = c; }
      }
      hi = Math.max(hi, c); lo = Math.min(lo, c);
    }
    return cols;
  }
  var rkSym = "NIFTY", rkMode = "renko";
  function renderRenko() {
    var box = document.getElementById("pcRkBox");
    box.innerHTML = '<div class="note">load ho raha...</div>';
    loadSymDaily(rkSym).then(function (b) {
      if (!b || b.t.length < 30) { box.innerHTML = '<div class="note">archive nahi mila</div>'; return; }
      var bars = toBars(b).slice(-120);
      var price = bars[bars.length - 1].c;
      var atr = 0;
      for (var i = 1; i < bars.length; i++) atr += Math.max(bars[i].h, bars[i].c) - Math.min(bars[i].l, bars[i].c);
      atr /= (bars.length - 1);
      var bs = Math.max(Math.round(atr / 2), Math.round(price * 0.005 * 100) / 100 || 1);
      bs = Math.round(bs * 100) / 100;
      var W = 340, H = 220, h = "";
      if (rkMode === "renko") {
        var bricks = renkoBricks(bars, bs);
        var mx = Math.max.apply(null, bricks.map(function (x) { return x.p; })) + bs;
        var mn = Math.min.apply(null, bricks.map(function (x) { return x.p; })) - bs;
        var r = (mx - mn) || 1, bw = Math.min(14, Math.floor(W / Math.max(1, bricks.length)));
        h = '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" style="width:100%;height:220px;display:block">';
        for (var i = 0; i < bricks.length; i++) {
          var y = H - ((bricks[i].p - mn) / r) * (H - 8) - 4;
          h += '<rect x="' + (i * bw + 1) + '" y="' + y.toFixed(1) + '" width="' + Math.max(2, bw - 2) + '" height="' + Math.max(2, (bs / r) * (H - 8)).toFixed(1) + '" fill="' + (bricks[i].d > 0 ? "#2f7a44" : "#a34a4a") + '" stroke="rgba(255,255,255,.25)" stroke-width="0.5"/>';
        }
        h += '</svg><div class="note">brick size ' + bs + ' (ATR se auto) \u00b7 ' + bricks.length + ' bricks \u00b7 sirf movement, time nahi \u2014 trend saaf dikhta hai</div>';
      } else {
        var cols = pnfColumns(bars, bs, 3);
        var allA = [], allB = [];
        cols.forEach(function (c) { allA.push(c.a); allB.push(c.b); });
        var mx = Math.max.apply(null, allA.concat(allB)) + 1, mn = Math.min.apply(null, allA.concat(allB)) - 1;
        var r2 = (mx - mn) || 1, cw = Math.min(18, Math.floor(W / Math.max(1, cols.length))), bh = (H - 8) / r2;
        h = '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" style="width:100%;height:220px;display:block">';
        for (var i = 0; i < cols.length; i++) {
          var lo = Math.min(cols[i].a, cols[i].b), hi2 = Math.max(cols[i].a, cols[i].b);
          for (var k = lo; k <= hi2; k++) {
            var y = H - ((k - mn) / r2) * (H - 8) - 4;
            h += '<text x="' + (i * cw + cw / 2) + '" y="' + (y + 3) + '" text-anchor="middle" font-size="' + Math.min(11, cw - 1) + '" fill="' + (cols[i].dir > 0 ? "#77f37b" : "#ff8b8b") + '" font-family="monospace">' + (cols[i].dir > 0 ? "X" : "O") + '</text>';
          }
        }
        h += '</svg><div class="note">box ' + bs + ' \u00b7 reversal 3 boxes \u00b7 ' + cols.length + ' columns \u00b7 X = demand, O = supply \u2014 column jaisa lamba, trend utna tagda</div>';
      }
      box.innerHTML = h;
    }, function () { box.innerHTML = '<div class="note">data nahi mila</div>'; });
  }

  /* ================= MULTI-TIMEFRAME ================= */
  var mtSym = "NIFTY";
  function agg(d, k) {
    if (!d || !d.t) return null;
    var o = { t: [], c: [] }, i = 0;
    while (i < d.t.length) { var j = Math.min(i + k, d.t.length); o.t.push(d.t[j - 1]); o.c.push(d.c[j - 1]); i = j; }
    return o;
  }
  function trendOf(c) {
    if (!c || c.length < 8) return 0;
    var e = c[0], k = 2 / 21, ema = [];
    for (var i = 0; i < c.length; i++) { e = i ? c[i] * k + e * (1 - k) : c[0]; ema.push(e); }
    var last = c[c.length - 1];
    return last > ema[ema.length - 1] ? 1 : (last < ema[ema.length - 1] ? -1 : 0);
  }
  function miniLine(c, col, w, h2) {
    var mn = Math.min.apply(null, c), mx = Math.max.apply(null, c), r = (mx - mn) || 1;
    var pts = [];
    for (var i = 0; i < c.length; i++) pts.push((i / (c.length - 1) * w).toFixed(1) + "," + (h2 - 3 - (c[i] - mn) / r * (h2 - 6)).toFixed(1));
    return '<svg viewBox="0 0 ' + w + ' ' + h2 + '" preserveAspectRatio="none" style="width:100%;height:52px;display:block">' +
      '<polyline points="' + pts.join(" ") + '" fill="none" stroke="' + col + '" stroke-width="1.8"/></svg>';
  }
  var IDXN = { NIFTY: "NIFTY 50", BANKNIFTY: "BANKNIFTY", SENSEX: "SENSEX", MIDCPNIFTY: "MIDCPNIFTY", NIFTYIT: "NIFTY IT", FINNIFTY: "FINNIFTY" };
  function renderMTF() {
    var box = document.getElementById("pcMtfBox");
    box.innerHTML = '<div class="note">load ho raha...</div>';
    fetch("data/candles.json").then(function (r) { return r.json(); }).then(function (cd) {
      var av = (cd.syms || {})[mtSym];
      var five = av && (av["5m"] || av["15m"] || av["1h"]);
      if (!five) { box.innerHTML = '<div class="note">intraday data nahi mila</div>'; return; }
      /* best source per TF: seedha series ya aggregate (4h = multi-din 1h se) */
      var tf = {
        "15m": av["15m"] || agg(av["5m"], 3),
        "1h": av["1h"] || agg(av["5m"], 12),
        "4h": av["1h"] ? agg(av["1h"], 4) : agg(av["15m"], 16)
      };
      var idxSym = (mtSym === "NIFTY" ? "NIFTY" : mtSym);
      var dailyP = fetch(PCBASE + "idx-" + idxSym + ".json").then(function (r) { return r.json(); }).catch(function () { return null; });
      dailyP.then(function (dd) {
        var dly = null;
        if (dd && dd.c) { var n = Math.min(60, dd.c.length); dly = dd.c.slice(-n); }
        var defs = [["15m", tf["15m"] && tf["15m"].c], ["1h", tf["1h"] && tf["1h"].c], ["4h", tf["4h"] && tf["4h"].c], ["Daily", dly]];
        var up = 0, dn = 0, h = '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:4px">';
        for (var i = 0; i < defs.length; i++) {
          var nm = defs[i][0], c = defs[i][1];
          if (!c || c.length < 5) { h += '<div class="note" style="border:1px dashed rgba(255,255,255,.15);border-radius:8px;padding:6px">' + nm + ': data nahi</div>'; continue; }
          var t = trendOf(c);
          if (t > 0) up++; else if (t < 0) dn++;
          var col = t > 0 ? UP : (t < 0 ? DN : NEU);
          var rc = c.slice(-20); /* recent move: pichle ~20 bars */
          var chg = rc.length > 1 ? (rc[rc.length - 1] - rc[0]) / rc[0] * 100 : 0;
          h += '<div style="border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:6px;background:rgba(0,0,0,.15)">' +
            '<div style="display:flex;justify-content:space-between;font-size:11.5px"><b>' + nm + '</b>' +
            '<b style="color:' + col + '">' + (t > 0 ? "UP" : t < 0 ? "DOWN" : "FLAT") + ' ' + (chg >= 0 ? "+" : "") + chg.toFixed(2) + '%</b></div>' +
            miniLine(c, col, 160, 52) + '</div>';
        }
        h += '</div>';
        var conf = up === 4 ? ["\ud83d\ude80 SAB UP \u2014 full bullish confluence", UP] : (dn === 4 ? ["\ud83d\udca5 SAB DOWN \u2014 full bearish", DN] : (up >= 3 ? ["\ud83d\udfe2 ZYADA UP \u2014 trend upar", UP] : (dn >= 3 ? ["\ud83d\udfe5 ZYADA DOWN \u2014 trend neeche", DN] : ["\ud83d\udfe1 MIXED \u2014 range/confusion", "#eab308"])));
        h = '<div class="note" style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.12);border-radius:8px;padding:8px;margin-bottom:8px"><b style="color:' + conf[1] + '">' + esc(IDXN[mtSym] || mtSym) + ': ' + conf[0] + '</b> \u00b7 ' + up + ' up / ' + dn + ' down / ' + (4 - up - dn) + ' flat</div>' + h;
        h += '<div class="note" style="margin-top:6px;opacity:.65">15m/1h/4h aaj ke intraday se \u00b7 Daily 60-din archive \u00b7 EMA20 se trend \u00b7 jab charon ek disha me = strongest trade</div>';
        box.innerHTML = h;
      });
    }, function () { box.innerHTML = '<div class="note">candles data nahi mila</div>'; });
  }

  function chipRow(elId, items, cur, onPick) {
    var el = document.getElementById(elId);
    el.innerHTML = items.map(function (x) {
      return '<button class="chip' + (x === cur ? " on" : "") + '" data-v="' + esc(x) + '">' + esc(x) + '</button>';
    }).join("");
    el.querySelectorAll(".chip").forEach(function (b) {
      b.onclick = function () { onPick(b.getAttribute("data-v")); };
    });
  }

  /* ================= mount ================= */
  function mount() {
    var sec = document.getElementById("chartread");
    if (!sec) return false;
    if (document.getElementById("pcPivCard")) return true;

    var mk = function (id, sub, chipsId, boxId) {
      var c = document.createElement("div");
      c.className = "card"; c.id = id;
      c.innerHTML = '<div class="subhead">' + sub + '</div><div class="controls" style="margin:6px 0" id="' + chipsId + '"></div><div id="' + boxId + '"></div>';
      sec.appendChild(c);
      return c;
    };

    mk("pcMtfCard", "\ud83d\udd25 MULTI-TIMEFRAME RADAR \u2014 15m \u00b7 1h \u00b7 4h \u00b7 Daily", "pcMtfChips", "pcMtfBox");
    mk("pcPivCard", "\ud83d\udccd PIVOT POINTS \u2014 Classic \u00b7 Fibonacci \u00b7 Camarilla \u00b7 Woodie", "pcPivChips", "pcPivBox");
    mk("pcRkCard", "\ud83e\uddf1 RENKO \u00b7 POINT&FIGURE \u2014 noise-free charts", "pcRkChips", "pcRkBox");

    /* Dev (28 Sep): MULTI-TIMEFRAME RADAR sabse upar -- pehli card (price chart) se pehle, taaki turant dikhe */
    var mtfC = document.getElementById("pcMtfCard");
    var firstCard = sec.querySelector(".card");
    if (mtfC && firstCard && firstCard !== mtfC && firstCard.parentNode === sec) sec.insertBefore(mtfC, firstCard);

    /* MTF chips: sirf indices */
    chipRow("pcMtfChips", ["NIFTY", "BANKNIFTY", "SENSEX", "MIDCPNIFTY", "NIFTYIT", "FINNIFTY"], mtSym, function (v) { mtSym = v; renderMTF(); });
    renderMTF();

    /* pivot symbol input + period chips */
    document.getElementById("pcPivChips").innerHTML =
      '<input id="pcPivSym" placeholder="symbol likho (RELIANCE, TCS...)" style="width:100%;box-sizing:border-box;padding:8px 10px;border-radius:9px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.05);color:inherit;font-size:13px;margin-bottom:6px">' +
      '<div id="pcPivPer"></div>';
    chipRow("pcPivPer", ["D", "W", "M"], pvPer, function (v) { pvPer = v; renderPivots(); });
    document.getElementById("pcPivSym").addEventListener("change", function () {
      var v = this.value.trim().toUpperCase(); if (v) { pvSym = v; renderPivots(); }
    });
    renderPivots();

    chipRow("pcRkChips", ["renko", "p&f"], rkMode, function (v) { rkMode = v; renderRenko(); });
    var rkIn = document.createElement("input");
    rkIn.placeholder = "symbol badalna ho to likho (default NIFTY)";
    rkIn.style.cssText = "width:100%;box-sizing:border-box;padding:8px 10px;border-radius:9px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.05);color:inherit;font-size:13px;margin-top:6px";
    rkIn.addEventListener("change", function () { var v = this.value.trim().toUpperCase(); if (v) { rkSym = v; renderRenko(); } });
    document.getElementById("pcRkChips").appendChild(rkIn);
    renderRenko();
    return true;
  }

  var tries = 0;
  var t = setInterval(function () {
    tries++;
    if (mount()) clearInterval(t);
    if (tries > 240) clearInterval(t);
  }, 500);
})();
