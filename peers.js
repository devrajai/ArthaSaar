/* peers.js - Peer Comparison: same industry stocks side-by-side (PE/ROE/ROCE/growth). #tools */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var IDX = null, FUND = null;

  function cell(txt, col, bold) {
    return '<span style="flex:1;min-width:52px;text-align:right;color:' + (col || "inherit") + (bold ? ";font-weight:600" : "") + '">' + txt + "</span>";
  }

  function render(sym) {
    var st = (FUND.stocks || {})[sym.toUpperCase()];
    var o = document.getElementById("prOut");
    if (!st) { o.innerHTML = '<div class="note">' + esc(sym) + ' 500-list me nahi - spelling check karo</div>'; return; }
    var me = sym.toUpperCase();
    var meta = (IDX[me] || {});
    var industry = meta.industry, sector = meta.sector;
    if (!industry && !sector) { o.innerHTML = '<div class="note">' + esc(sym) + ' ka industry data nahi mila</div>'; return; }
    var peers = [];
    Object.keys(IDX).forEach(function (s) {
      if (s[0] === "_") return;
      if (!(FUND.stocks || {})[s]) return;
      var m = IDX[s];
      if (industry && m.industry === industry) peers.push(s);
    });
    var level = "industry";
    if (peers.length < 3 && sector) {
      peers = [];
      Object.keys(IDX).forEach(function (s) {
        if (s[0] === "_") return;
        if (!(FUND.stocks || {})[s]) return;
        if (IDX[s].sector === sector) peers.push(s);
      });
      level = "sector";
    }
    if (peers.length < 2) { o.innerHTML = '<div class="note">Iske peers 500-list me nahi mile</div>'; return; }
    peers.sort(function (a, b) { return ((FUND.stocks[b] || {})["Market Cap"] || 0) - ((FUND.stocks[a] || {})["Market Cap"] || 0); });
    var rows = peers.map(function (s) {
      var x = FUND.stocks[s];
      return { s: s, cap: x["Market Cap"] || 0, pe: x["Stock P/E"] || 0, roe: x.ROE || 0, roce: x.ROCE || 0, py: x["Net Profit_yoy"] || 0, pr: x.promoters_pct || 0 };
    });
    var best = {
      pe: Math.min.apply(null, rows.filter(function (r) { return r.pe > 0; }).map(function (r) { return r.pe; })),
      roe: Math.max.apply(null, rows.map(function (r) { return r.roe; })),
      roce: Math.max.apply(null, rows.map(function (r) { return r.roce; })),
      py: Math.max.apply(null, rows.map(function (r) { return r.py; })),
      pr: Math.max.apply(null, rows.map(function (r) { return r.pr; }))
    };
    var h = '<div class="note" style="margin-top:8px"><b>' + esc(industry || sector) + "</b> - " + peers.length + " peers (" + level + " level, market cap order)</div>";
    h += '<div class="note" style="display:flex;gap:4px;font-size:11px;opacity:.6;margin-top:8px"><span style="min-width:60px">SYMBOL</span>' + cell("MCap", "", false) + cell("P/E", "", false) + cell("ROE", "", false) + cell("ROCE", "", false) + cell("P-YoY", "", false) + cell("PROM", "", false) + "</div>";
    rows.forEach(function (r) {
      var hl = r.s === me;
      h += '<div style="display:flex;gap:4px;align-items:center;margin-top:5px;padding:6px 8px;border-radius:8px;' +
        (hl ? "border:1px solid rgba(240,180,41,.6);background:rgba(240,180,41,.08)" : "background:rgba(255,255,255,.03)") + '">' +
        '<span style="min-width:60px;font-weight:' + (hl ? "700" : "400") + '">' + esc(r.s) + "</span>" +
        cell(Math.round(r.cap / 1000) + "k", "", hl) +
        cell(r.pe || "-", r.pe > 0 && r.pe === best.pe ? "#77f37b" : (r.pe > 60 ? "#ff8b8b" : ""), hl) +
        cell(r.roe || "-", r.roe === best.roe ? "#77f37b" : (r.roe < 10 ? "#ff8b8b" : ""), hl) +
        cell(r.roce || "-", r.roce === best.roce ? "#77f37b" : "", hl) +
        cell(r.py + "%", r.py === best.py ? "#77f37b" : (r.py < 0 ? "#ff8b8b" : ""), hl) +
        cell(Math.round(r.pr) + "%", r.pr === best.pr ? "#77f37b" : "", hl) +
        "</div>";
    });
    var quality = rows.filter(function (r) { return r.roe >= 15 && r.pe > 0; });
    var cheap = quality.length ? quality.sort(function (a, b) { return a.pe - b.pe; })[0] : null;
    var dear = rows.filter(function (r) { return r.pe > 0; }).sort(function (a, b) { return b.pe - a.pe; })[0];
    h += '<div class="note" style="margin-top:12px;border-left:3px solid rgba(240,180,41,.7);padding:8px 12px;background:rgba(240,180,41,.07)"><b>Verdict:</b> ' +
      (cheap ? esc(cheap.s) + " sabse value-for-money (PE " + cheap.pe + " with ROE " + cheap.roe + "%)" : "quality-me-sasta koi nahi mila") +
      (dear ? " | sabse mehnga: " + esc(dear.s) + " (PE " + dear.pe + ")" : "") + "</div>";
    o.innerHTML = h;
  }

  function build(card) {
    card.innerHTML = '<div class="subhead">Peer Comparison (industry ke saathi se compare)</div>' +
      '<input id="prSym" placeholder="Symbol daalo (RELIANCE, TCS...)" style="width:100%;box-sizing:border-box;padding:9px 12px;border-radius:9px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.05);color:inherit;font-size:14px;margin-top:8px">' +
      '<div id="prOut" class="note" style="margin-top:10px">symbol daalo - same industry ke sab stocks ek table me: PE, ROE, ROCE, growth - best green, worst red</div>';
    document.getElementById("prSym").addEventListener("input", function () {
      var s = this.value.trim().toUpperCase();
      if (s.length < 3) return;
      function go() { render(s); }
      if (IDX && FUND) { go(); return; }
      Promise.all([
        fetch("data/company-index.json").then(function (r) { return r.json(); }),
        fetch("data/screener-fundamentals.json").then(function (r) { return r.json(); })
      ]).then(function (R) { IDX = R[0]; FUND = R[1]; render(s); });
    });
  }

  function mount() {
    var t = document.querySelector("section#tools");
    if (!t || document.getElementById("mbPeers")) return;
    var c = document.createElement("div");
    c.className = "card"; c.id = "mbPeers"; c.style.marginTop = "14px";
    t.appendChild(c);
    try { build(c); } catch (e) { c.innerHTML = '<div class="subhead">Peer Comparison</div><div class="note">error</div>'; }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
