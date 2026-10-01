/* treemap.js v1 -- Sector Map section me Mcap Treemap card (Bloomberg style).
   Box size = market cap (screener-fundamentals), color = aaj ka % change (brain-screener).
   Top 140 stocks, squarified layout, 100% free data. */
(function () {
  "use strict";
  var N = 140;

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }

  function squarify(items, x, y, w, h, out) {
    if (!items.length) return;
    if (items.length === 1) { out.push([items[0], x, y, w, h]); return; }
    var total = items.reduce(function (a, b) { return a + b.v; }, 0);
    /* split items into two halves with ~half the value, along the longer side */
    var half = total / 2, acc = 0, k = 0;
    for (var i = 0; i < items.length; i++) { acc += items[i].v; k = i + 1; if (acc >= half) break; }
    if (k >= items.length) k = items.length - 1;
    var A = items.slice(0, k), B = items.slice(k);
    var va = A.reduce(function (a, b) { return a + b.v; }, 0);
    if (w >= h) {
      var wa = va / total * w;
      squarify(A, x, y, wa, h, out);
      squarify(B, x + wa, y, w - wa, h, out);
    } else {
      var ha = va / total * h;
      squarify(A, x, y, w, ha, out);
      squarify(B, x, y + ha, w, h - ha, out);
    }
  }

  function chgColor(p) {
    if (p == null) return "rgba(255,255,255,.08)";
    var t = Math.min(1, Math.abs(p) / 3);
    return p >= 0 ? "rgba(47,122,68," + (0.25 + 0.75 * t).toFixed(2) + ")" : "rgba(163,74,74," + (0.25 + 0.75 * t).toFixed(2) + ")";
  }

  function draw() {
    var host = document.getElementById("tmBox");
    if (!host) return;
    host.innerHTML = '<div class="note">treemap load ho raha...</div>';
    Promise.all([
      fetch("data/screener-fundamentals.json").then(function (r) { return r.json(); }),
      fetch("data/brain-screener.json").then(function (r) { return r.json(); })
    ]).then(function (res) {
      var f = res[0].stocks || {}, s = res[1].stocks || [];
      var byChg = {};
      s.forEach(function (x) { byChg[x.symbol] = x.change_pct; });
      var items = [];
      for (var sym in f) {
        var mc = f[sym] && f[sym]["Market Cap"];
        if (!mc) continue;
        items.push({ s: sym, v: mc, p: byChg[sym] });
      }
      items.sort(function (a, b) { return b.v - a.v; });
      items = items.slice(0, N);
      var W = 360, H = 470, rects = [];
      squarify(items, 0, 0, W, H, rects);
      var h = '<svg viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="xMidYMid meet" style="width:100%;height:auto;display:block;border-radius:10px">';
      for (var i = 0; i < rects.length; i++) {
        var it = rects[i][0], x = rects[i][1], y = rects[i][2], w = rects[i][3], hh = rects[i][4];
        if (w < 2 || hh < 2) continue;
        h += '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + Math.max(1, w - 1).toFixed(1) + '" height="' + Math.max(1, hh - 1).toFixed(1) + '" rx="2" fill="' + chgColor(it.p) + '" stroke="rgba(255,255,255,.18)" stroke-width="0.5"><title>' + esc(it.s) + ' \u00b7 mcap ' + Math.round(it.v) + ' Cr \u00b7 ' + (it.p == null ? "?" : (it.p >= 0 ? "+" : "") + it.p + "%") + '</title></rect>';
        if (w > it.s.length * 6 + 6 && hh > 16) { /* symbol fit ho tabhi label */
          var fs = Math.min(11, Math.max(6.5, (w - 6) / it.s.length));
          h += '<text x="' + (x + 3).toFixed(1) + '" y="' + (y + Math.min(13, hh / 2 + 4)).toFixed(1) + '" font-size="' + fs.toFixed(1) + '" fill="#fff" font-family="monospace" font-weight="600">' + esc(it.s) + '</text>';
          if (hh > 32 && it.p != null) h += '<text x="' + (x + 3).toFixed(1) + '" y="' + (y + Math.min(13, hh / 2 + 4) + 11).toFixed(1) + '" font-size="' + Math.max(7, fs - 2).toFixed(1) + '" fill="rgba(255,255,255,.85)" font-family="monospace">' + (it.p >= 0 ? "+" : "") + it.p.toFixed(1) + '%</text>';
        }
      }
      h += '</svg><div class="note" style="opacity:.65">box size = market cap \u00b7 rang = aaj ka change (hara = upar, laal = neeche) \u00b7 top ' + items.length + ' stocks \u00b7 box par tap = details</div>';
      host.innerHTML = h;
    }).catch(function () {
      host.innerHTML = '<div class="note">treemap data nahi mila</div>';
    });
  }

  function mount() {
    var sec = document.getElementById("heatmap");
    if (!sec) return false;
    if (document.getElementById("tmCard")) { return true; }
    var card = document.createElement("div");
    card.className = "card";
    card.id = "tmCard";
    card.innerHTML = '<div class="subhead">\ud83d\uddfa\ufe0f MCAP TREEMAP \u2014 Bloomberg style \u00b7 size = market cap</div><div id="tmBox"></div>';
    var body = document.getElementById("hmBody");
    if (body && body.parentNode === sec) sec.insertBefore(card, body);
    else sec.appendChild(card);
    draw();
    return true;
  }

  if (typeof document !== 'undefined') {
    var tries = 0;
    var t = setInterval(function () {
      tries++;
      if (mount()) clearInterval(t);
      if (tries > 240) clearInterval(t);
    }, 500);
  }

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = { squarify };
  }
})();
