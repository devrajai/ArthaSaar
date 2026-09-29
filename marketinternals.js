/* marketinternals.js v1 -- MARKET INTERNALS section (Bloomberg-style breadth, free data):
   - Advance/Decline line (260 din) + aaj ka adv/dec
   - TRIN (Arms Index), McClellan Oscillator, New High/Low, Zweig Breadth Thrust
   - PCR history chart (roz collect hota hai)
   Data: arthasaar-data CDN pe internals.json (Actions roz banata hai) + pcr-history.json. */
(function () {
  "use strict";
  var UP = "#77f37b", DN = "#ff8b8b", NEU = "#eab308";
  var PCBASE = window.__PC_BASE || "https://cdn.jsdelivr.net/gh/devrajai/ArthaSaar@data/data/";

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }

  function line(vals, w, h, col, base) {
    if (!vals || vals.length < 2) return "";
    var mn = Math.min.apply(null, vals), mx = Math.max.apply(null, vals);
    if (base != null) { mn = Math.min(mn, base); mx = Math.max(mx, base); }
    var r = (mx - mn) || 1, pts = [];
    for (var i = 0; i < vals.length; i++) pts.push((i / (vals.length - 1) * w).toFixed(1) + "," + (h - 2 - (vals[i] - mn) / r * (h - 4)).toFixed(1));
    var bs = base != null ? '<line x1="0" y1="' + (h - 2 - (base - mn) / r * (h - 4)).toFixed(1) + '" x2="' + w + '" y2="' + (h - 2 - (base - mn) / r * (h - 4)).toFixed(1) + '" stroke="rgba(255,255,255,.25)" stroke-dasharray="4 4" stroke-width="1"/>' : "";
    return '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none" style="width:100%;height:' + h + 'px;display:block">' + bs +
      '<polyline points="' + pts.join(" ") + '" fill="none" stroke="' + col + '" stroke-width="1.8"/></svg>';
  }
  function bars(vals, w, h, base0) {
    var mx = Math.max.apply(null, vals.map(Math.abs)) || 1;
    var bw = w / vals.length, h2 = "";
    for (var i = 0; i < vals.length; i++) {
      var v = vals[i], bh = Math.abs(v) / mx * (h / 2 - 2);
      h2 += '<rect x="' + (i * bw + 0.5) + '" y="' + (v >= 0 ? h / 2 - bh : h / 2).toFixed(1) + '" width="' + Math.max(1, bw - 1) + '" height="' + Math.max(0.5, bh).toFixed(1) + '" fill="' + (v >= 0 ? "#2f7a44" : "#a34a4a") + '"/>';
    }
    return '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none" style="width:100%;height:' + h + 'px;display:block"><line x1="0" y1="' + h / 2 + '" x2="' + w + '" y2="' + h / 2 + '" stroke="rgba(255,255,255,.2)"/>' + h2 + '</svg>';
  }

  function draw() {
    var box = document.getElementById("miBox");
    if (!box) return;
    box.innerHTML = '<div class="note">internals load ho raha...</div>';
    fetch(PCBASE + "internals.json").then(function (r) { return r.json(); }).then(function (d) {
      var L = d.last || {}, n = d.days || (d.dates || []).length;
      var trim = function (a, k) { return (a || []).slice(-k); };
      var trin = L.trin, mcos = L.mcos;
      var trinTxt = trin == null ? "-" : (trin < 0.8 ? ["bullish \u2014 aalsi ab bhi bhid me hai", UP] : (trin > 1.2 ? ["bearish \u2014 bechne ka pressure zyada", DN] : ["neutral", NEU]));
      var mcTxt = mcos == null ? "-" : (mcos > 0 ? ["positive \u2014 breadth momentum upar", UP] : ["negative \u2014 breadth weak hai", DN]);
      var h = '<div class="card"><div class="subhead">\ud83e\udec0 Aaj ka snapshot \u2014 ' + esc((d.dates || [])[n - 1] || "") + '</div>' +
        '<div class="note" style="display:flex;justify-content:space-between"><span>Advances</span><b style="color:' + UP + '">' + (L.adv || 0) + '</b></div>' +
        '<div class="note" style="display:flex;justify-content:space-between"><span>Declines</span><b style="color:' + DN + '">' + (L.dec || 0) + '</b></div>' +
        '<div class="note" style="display:flex;justify-content:space-between"><span>TRIN (Arms)</span><b>' + (trin == null ? "-" : trin) + ' <span style="font-size:10.5px;color:' + trinTxt[1] + '">' + trinTxt[0] + '</span></b></div>' +
        '<div class="note" style="display:flex;justify-content:space-between"><span>McClellan Osc</span><b>' + (mcos == null ? "-" : mcos) + ' <span style="font-size:10.5px;color:' + mcTxt[1] + '">' + mcTxt[0] + '</span></b></div>' +
        '<div class="note" style="display:flex;justify-content:space-between"><span>52w Highs / Lows</span><b><span style="color:' + UP + '">' + (L.nh || 0) + '</span> / <span style="color:' + DN + '">' + (L.nl || 0) + '</span></b></div>' +
        '<div class="note" style="display:flex;justify-content:space-between"><span>Breadth Thrust</span><b style="color:' + (L.thrust_recent ? UP : NEU) + '">' + (L.thrust_recent ? "\u26a1 ACTIVE (30 din me)" : "nahi \u2014 normal") + '</b></div></div>';

      h += '<div class="card"><div class="subhead">\ud83d\udcc9 Advance-Decline Line \u2014 ' + n + ' din</div>' + line(d.ad || [], 340, 130, "#7db4ff") +
        '<div class="note" style="opacity:.65">cumulative (adv-dec) \u00b7 line girke Nifty uth raha ho to = divergence, warning</div></div>';
      h += '<div class="card"><div class="subhead">\ud83d\udcca McClellan Oscillator \u2014 pichle 60 din</div>' + bars(trim(d.mcos, 60), 340, 110) +
        '<div class="note" style="opacity:.65">0 ke upar = breadth strong \u00b7 neeche = weak \u00b7 zero cross = signal</div></div>';
      h += '<div class="card"><div class="subhead">\ud83c\udfc6 New 52w Highs (green) vs Lows (red) \u2014 60 din</div>' + bars(trim((d.nh || []).map(function (v, i) { return v - (d.nl || [])[i]; }), 60), 340, 90) +
        '<div class="note" style="opacity:.65">green lamba = strong trend \u00b7 red lamba = market ki jadd khali ho rahi hai</div></div>';

      box.innerHTML = h;
      drawPCR();
    }, function () {
      box.innerHTML = '<div class="note">internals data nahi mila \u2014 Actions job abhi bana raha hoga, thodi der baad try karo</div>';
    });
  }

  function drawPCR() {
    var el = document.getElementById("miPCR");
    if (!el) return;
    fetch("data/pcr-history.json").then(function (r) { return r.json(); }).then(function (d) {
      var h = (d.history || []);
      if (h.length < 2) { el.innerHTML = '<div class="note">PCR history collect ho rahi hai \u2014 kuch din me chart ban jayega (roz EOD ke baad auto)</div>'; return; }
      var vals = h.map(function (x) { return x.pcr; });
      el.innerHTML = line(vals, 340, 110, "#c084fc", 1) +
        '<div class="note" style="display:flex;justify-content:space-between"><span>aaj PCR</span><b>' + vals[vals.length - 1] + '</b></div>' +
        '<div class="note" style="opacity:.65">>1.3 = zyada puts (extreme fear, contrarian buy) \u00b7 <0.7 = zyada calls (greed, sambhal ke)</div>';
    }).catch(function () {
      el.innerHTML = '<div class="note">PCR history abhi shuru ho rahi hai</div>';
    });
  }

  function mount() {
    if (document.getElementById("internals")) { draw(); return true; }
    var sec = document.createElement("section");
    sec.id = "internals"; sec.style.display = "none";
    sec.innerHTML = '<a class="backbtn" href="#home">\u2302 Home</a><h2>Market Internals \u2014 breadth & smart internals</h2>' +
      '<div id="miBox"></div><div class="card"><div class="subhead">\ud83c\udfa7 Put/Call Ratio history</div><div id="miPCR"></div></div>' +
      '<div class="footer-note">~2200 NSE stocks se roz EOD pe calculate \u00b7 Actions auto \u00b7 100% free \u00b7 signal hai, guarantee nahi</div>';
    var ft = document.querySelector("footer");
    if (ft && ft.parentNode) ft.parentNode.insertBefore(sec, ft); else document.body.appendChild(sec);

    /* home tile: WATCH group me */
    try {
      var hg = document.querySelector("section#home .homegrid");
      var anchor = hg ? hg.querySelector('a[href="#portfolio"]') : null;
      var tile = document.createElement("a");
      tile.className = "tile";
      tile.href = "#internals";
      tile.innerHTML = '<span class="t-ic">\ud83e\udec0</span><span class="t-nm">Internals</span><span class="t-sb">A/D \u00b7 TRIN \u00b7 breadth</span>';
      if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(tile, anchor);
      else if (hg) hg.appendChild(tile);
    } catch (e) {}

    try { if (typeof loaders !== "undefined") loaders.internals = draw; } catch (e) {}
    draw();
    return true;
  }

  var tries = 0;
  var t = setInterval(function () {
    tries++;
    if (mount()) clearInterval(t);
    if (tries > 240) clearInterval(t);
  }, 500);
})();
