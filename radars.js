/* radars.js - 8 RADAR cards (Economy-Pulse style: bada number + verdict + mini visual).
   #indices #fundamentals #mf #deepfund #filings #futures #gti #heatmap top pe mount hote hai.
   Data: existing daily JSONs (koi naya workflow nahi). Mobile-first, NO sticky, NO backdrop-filter. */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function fmt(n, d) { n = Number(n); if (!isFinite(n)) return "-"; return n.toFixed(d == null ? 2 : d); }
  function pcol(p) { p = Number(p) || 0; return p > 0.05 ? "var(--up)" : p < -0.05 ? "var(--down)" : "var(--dim)"; }
  function heatBg(p) {
    var a = Math.min(1, Math.abs(Number(p) || 0) / 2.5);
    var rgb = (Number(p) || 0) >= 0 ? "34,197,94" : "220,38,38";
    return "background:rgba(" + rgb + "," + (0.10 + a * 0.55).toFixed(2) + ")";
  }
  function badge(txt, bg, fg) {
    return "<span style='display:inline-block;font-family:var(--mono);font-size:10px;font-weight:800;padding:3px 8px;border-radius:6px;background:" + bg + ";color:" + fg + ";margin:2px 3px 2px 0;white-space:nowrap'>" + txt + "</span>";
  }
  function tile(name, val, pct) {
    return "<div class='kpi' style='text-align:center;min-width:0'>" +
      "<div class='k-name' style='white-space:normal'>" + name + "</div>" +
      "<div class='k-val' style='font-size:22px'>" + val + "</div>" +
      "<div class='k-chg' style='color:" + pcol(pct) + "'>" + (pct > 0 ? "+" : "") + fmt(pct) + "%</div></div>";
  }
  function mountCard(secId, id, title, sub) {
    var sec = document.querySelector("section#" + secId);
    if (!sec || document.getElementById(id)) return null;
    var c = document.createElement("details");
    c.className = "card"; c.id = id; c.style.marginTop = "14px";
    c.innerHTML = "<summary style='cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:var(--amber-dim);border:1px solid var(--amber);font-size:14.5px;text-align:center'><b style='color:var(--amber)'>" + title + "</b> <span style='font-size:11px;opacity:.65'>" + sub + "</span></summary>" +
      "<div class='note' style='margin-top:8px' id='" + id + "Body'>loading...</div>";
    var h2 = sec.querySelector("h2");
    if (h2 && h2.parentNode) sec.insertBefore(c, h2.nextSibling); else sec.appendChild(c);
    return document.getElementById(id + "Body");
  }
  function fj(p) { return fetch(p).then(function (r) { return r.json(); }); }
  function setB(id, html) { var b = document.getElementById(id); if (b) b.innerHTML = html; }

  /* 1) INDICES RADAR - breadth + gainers/losers + big tiles */
  function idxRadar() {
    var b = mountCard("indices", "mbIdxRadar", "📊 INDICES RADAR", "139 indices ka nichod");
    if (!b) return;
    fj("data/indices-all.json").then(function (d) {
      var arr = (d.indices || []).slice();
      var green = 0, red = 0;
      arr.forEach(function (i) { if ((i.change_pct || 0) > 0) green++; else if ((i.change_pct || 0) < 0) red++; });
      var maj = ["NIFTY 50", "NIFTY BANK", "SENSEX", "NIFTY NEXT 50"].map(function (n) {
        return arr.filter(function (i) { return i.index === n; })[0];
      }).filter(Boolean).slice(0, 3);
      var s = arr.slice().sort(function (a, c2) { return (c2.change_pct || 0) - (a.change_pct || 0); });
      var top = s.slice(0, 5), bot = s.slice(-5).reverse();
      var h = "<div class='grid g3' style='margin-top:6px'>";
      maj.forEach(function (m) { h += tile(m.index, fmt(m.price, 1), m.change_pct); });
      h += "</div>";
      h += "<div style='margin-top:10px;text-align:center'><b style='font-size:16px;font-weight:900;color:" + (green >= red ? "var(--up)" : "var(--down)") + "'>" + green + "/" + arr.length + " GREEN</b>" +
        "<div class='meter' style='background:var(--down-dim)'><i style='width:" + (arr.length ? (green * 100 / arr.length).toFixed(0) : 0) + "%'></i></div>" +
        "<div style='font-size:11px;opacity:.7'>" + red + " red &middot; " + (arr.length - green - red) + " flat &middot; " + esc((d.updated || "").slice(0, 10)) + "</div></div>";
      h += "<div class='subhead' style='margin-top:10px'>TOP GAINERS</div>";
      top.forEach(function (i) { h += badge(esc(i.index) + " +" + fmt(i.change_pct, 1) + "%", "var(--up-dim)", "var(--up)"); });
      h += "<div class='subhead' style='margin-top:6px'>TOP LOSERS</div>";
      bot.forEach(function (i) { h += badge(esc(i.index) + " " + fmt(i.change_pct, 1) + "%", "var(--down-dim)", "var(--down)"); });
      h += "<div class='footer-note'>Radar: breadth dikhta hai ki market andar se kaisa hai - sab green = healthy, sirf Nifty green = weak inside.</div>";
      setB("mbIdxRadarBody", h);
    }).catch(function () { setB("mbIdxRadarBody", "data load nahi hua - refresh karo"); });
  }

  /* 2) FUNDAMENTAL RADAR - valuation meter + quality counts */
  function fundRadar() {
    var b = mountCard("fundamentals", "mbFundRadar", "🏢 FUNDAMENTAL RADAR", "sasta ya mehga + quality");
    if (!b) return;
    Promise.all([fj("data/screener-fundamentals.json"), fj("data/indices-all.json")]).then(function (rr) {
      var st = rr[0].stocks || {}, npe = null;
      (rr[1].indices || []).forEach(function (i) { if (i.index === "NIFTY 50") npe = Number(i.pe); });
      var qv = 0, exp = 0, hy = 0, n = 0;
      Object.keys(st).forEach(function (k) {
        var s = st[k]; n++;
        var pe = Number(s["Stock P/E"]) || 0, roe = Number(s["ROE"]) || 0, dy = Number(s["Dividend Yield"]) || 0;
        if (pe > 0 && pe < 15 && roe > 15) qv++;
        if (pe > 50) exp++;
        if (dy >= 3) hy++;
      });
      var verdict = npe == null || !isFinite(npe) ? "?" : npe < 17 ? "SASTA" : npe <= 21 ? "FAIR" : "MEHGA";
      var vc = verdict === "SASTA" ? "var(--up)" : verdict === "FAIR" ? "var(--amber)" : "var(--down)";
      var w = npe == null ? 50 : Math.max(4, Math.min(96, (npe / 30) * 100));
      var h = "<div style='text-align:center;margin-top:6px'>" +
        "<div style='font-size:12px;opacity:.75'>NIFTY P/E <b style='font-size:20px;font-weight:900;color:" + vc + "'>" + (npe || "?") + "</b></div>" +
        "<div style='font-size:15px;font-weight:900;color:" + vc + ";margin-top:2px'>MARKET " + verdict + "</div>" +
        "<div class='fg-wrap'><div class='fg-bar'><div class='fg-marker' style='left:" + w.toFixed(0) + "%'></div></div>" +
        "<div class='fg-labels'><span>SASTA (<17)</span><span>FAIR</span><span>MEHGA (>21)</span></div></div></div>";
      h += "<div class='grid g3' style='margin-top:10px'>";
      h += "<div class='kpi' style='text-align:center'><div class='k-name'>VALUE+QUALITY<br>P/E<15, ROE>15</div><div class='k-val' style='font-size:24px;color:var(--up)'>" + qv + "</div></div>";
      h += "<div class='kpi' style='text-align:center'><div class='k-name'>MEHGE STOCKS<br>P/E>50</div><div class='k-val' style='font-size:24px;color:var(--down)'>" + exp + "</div></div>";
      h += "<div class='kpi' style='text-align:center'><div class='k-name'>YIELD &ge;3%<br>income stocks</div><div class='k-val' style='font-size:24px;color:var(--amber)'>" + hy + "</div></div>";
      h += "</div><div class='footer-note'>Radar: " + n + " Nifty-500 stocks se nikala. History me Nifty P/E 17-21 band fair raha hai - usse upar mehgi, neeche sasti market.</div>";
      setB("mbFundRadarBody", h);
    }).catch(function () { setB("mbFundRadarBody", "data load nahi hua - refresh karo"); });
  }

  /* 3) MF RADAR - top funds + best/worst */
  function mfRadar() {
    var b = mountCard("mf", "mbMfRadar", "📈 MF RADAR", "aaj ka category winner");
    if (!b) return;
    fj("data/mf-top.json").then(function (d) {
      var f = (d.funds || []).slice().sort(function (a, c2) { return (c2.r1 || 0) - (a.r1 || 0); });
      if (!f.length) { setB("mbMfRadarBody", "abhi koi fund data nahi"); return; }
      var best = f[0], worst = f[f.length - 1];
      var h = "<div style='text-align:center;margin-top:6px'>" +
        badge("WINNER 1Y: " + esc((best.n || "").split(" - ")[0]) + " +" + fmt(best.r1, 1) + "%", "var(--up-dim)", "var(--up)") +
        badge("LAGGARD: " + esc((worst.n || "").split(" - ")[0]) + " " + fmt(worst.r1, 1) + "%", "var(--down-dim)", "var(--down)") + "</div>";
      h += "<div class='tblwrap' style='margin-top:8px'><table style='min-width:440px'><thead><tr><th>Fund</th><th>1Y</th><th>3Y</th><th>5Y</th></tr></thead><tbody>";
      f.slice(0, 5).forEach(function (x) {
        h += "<tr><td>" + esc((x.n || "").split(" - ")[0]) + "<span class='cname'>" + esc(x.k || "") + "</span></td>" +
          "<td style='color:" + pcol(x.r1) + ";font-weight:800'>" + (x.r1 > 0 ? "+" : "") + fmt(x.r1, 1) + "%</td>" +
          "<td style='color:" + pcol(x.r3) + "'>" + (x.r3 > 0 ? "+" : "") + fmt(x.r3, 0) + "%</td>" +
          "<td style='color:" + pcol(x.r5) + "'>" + (x.r5 > 0 ? "+" : "") + fmt(x.r5, 0) + "%</td></tr>";
      });
      h += "</tbody></table></div>";
      var bm = d.bench || {};
      h += "<div style='margin-top:8px'>";
      Object.keys(bm).slice(0, 4).forEach(function (k) {
        var b1 = bm[k]; var r = b1 && b1.r1 != null ? b1.r1 : b1;
        if (r != null && isFinite(r)) h += badge(esc(k.toUpperCase()) + " 1Y: " + (r > 0 ? "+" : "") + fmt(r, 1) + "%", "var(--blue-dim)", "var(--blue)");
      });
      h += "</div><div class='footer-note'>Radar: returns total % hai (annual nahi). Winner-chasing mat karo - category dekho, 3-5Y dekho.</div>";
      setB("mbMfRadarBody", h);
    }).catch(function () { setB("mbMfRadarBody", "data load nahi hua - refresh karo"); });
  }

  /* 4) DEEP FUND RADAR - FD beaters + deep value */
  function dfRadar() {
    var b = mountCard("deepfund", "mbDfRadar", "🏦 DEEP FUND RADAR", "FD ko harane wale");
    if (!b) return;
    fj("data/screener-fundamentals.json").then(function (d) {
      var st = d.stocks || {};
      var list = [];
      Object.keys(st).forEach(function (k) {
        var s = st[k];
        var dy = Number(s["Dividend Yield"]) || 0, pe = Number(s["Stock P/E"]) || 0, roe = Number(s["ROE"]) || 0;
        if (dy > 0) list.push({ k: k, dy: dy, pe: pe, roe: roe });
      });
      list.sort(function (a, c2) { return c2.dy - a.dy; });
      var beaters = list.filter(function (x) { return x.dy >= 7; });
      var deepv = list.filter(function (x) { return x.pe > 0 && x.pe < 10 && x.roe > 10; });
      var h = "<div class='grid g2' style='margin-top:6px'>";
      h += "<div class='kpi' style='text-align:center'><div class='k-name'>FD BEATERS (YIELD &ge; 7%)</div><div class='k-val' style='font-size:26px;color:var(--up)'>" + beaters.length + "</div><div class='k-chg' style='color:var(--dim)'>FD ~7% ke against</div></div>";
      h += "<div class='kpi' style='text-align:center'><div class='k-name'>DEEP VALUE (P/E<10, ROE>10)</div><div class='k-val' style='font-size:26px;color:var(--amber)'>" + deepv.length + "</div><div class='k-chg' style='color:var(--dim)'>sasta + quality</div></div>";
      h += "</div>";
      h += "<div class='subhead' style='margin-top:10px'>TOP DIVIDEND YIELDS</div>";
      list.slice(0, 8).forEach(function (x) {
        h += badge(esc(x.k) + " " + fmt(x.dy, 1) + "%", x.dy >= 7 ? "var(--up-dim)" : "var(--amber-dim)", x.dy >= 7 ? "var(--up)" : "var(--amber)");
      });
      h += "<div class='footer-note'>Radar: yield trap bhi hota hai (price girne se yield chadhta hai) - pehle company ki halat dekho. Yield = salary, P/E = kitna bhugtan.</div>";
      setB("mbDfRadarBody", h);
    }).catch(function () { setB("mbDfRadarBody", "data load nahi hua - refresh karo"); });
  }

  /* 5) FILINGS RADAR - latest filings ticker */
  function filRadar() {
    var b = mountCard("filings", "mbFilRadar", "📋 FILINGS RADAR", "aaj ke sabse bade filings");
    if (!b) return;
    fj("data/filings.json").then(function (d) {
      var f = (d.filings || []).slice(0, 6);
      if (!f.length) { setB("mbFilRadarBody", "is hafte koi bada filing nahi"); return; }
      function catCol(cat) {
        cat = String(cat || "").toLowerCase();
        if (cat.indexOf("bulk") >= 0 || cat.indexOf("pledge") >= 0) return ["var(--down-dim)", "var(--down)"];
        if (cat.indexOf("insider") >= 0) return ["var(--amber-dim)", "var(--amber)"];
        if (cat.indexOf("buy") >= 0 || cat.indexOf("divid") >= 0 || cat.indexOf("bonus") >= 0) return ["var(--up-dim)", "var(--up)"];
        return ["var(--blue-dim)", "var(--blue)"];
      }
      var h = "<div style='margin-top:6px;text-align:center'>" +
        badge("TIER-1: " + (d.tier1_filings || 0) + " filings (" + (d.window_days || 7) + " din)", "var(--blue-dim)", "var(--blue)") +
        badge("TIER-2: " + (d.tier2_count || 0), "var(--glass)", "var(--dim)") + "</div>";
      h += "<div class='tblwrap' style='margin-top:8px'><table style='min-width:460px'><thead><tr><th>Co</th><th>Category</th><th>Date</th></tr></thead><tbody>";
      f.forEach(function (x) {
        var cc = catCol(x.category);
        h += "<tr><td><b>" + esc(x.symbol) + "</b><span class='cname'>" + esc((x.company || "").slice(0, 26)) + "</span></td>" +
          "<td>" + badge(esc(x.category), cc[0], cc[1]) + "</td>" +
          "<td style='font-family:var(--mono)'>" + esc(x.date) + "</td></tr>";
      });
      h += "</tbody></table></div><div class='footer-note'>Radar: bulk deal + insider pledge = 🐋 whale ka signal. Company khud apni stock kharid raha = bull sign.</div>";
      setB("mbFilRadarBody", h);
    }).catch(function () { setB("mbFilRadarBody", "data load nahi hua - refresh karo"); });
  }

  /* 6) FUTURES RADAR - basis + PCR + max pain */
  function futRadar() {
    var b = mountCard("futures", "mbFutRadar", "⏳ FUTURES RADAR", "premium/discount + PCR");
    if (!b) return;
    fj("data/futures.json").then(function (d) {
      var h = "<div class='grid g3' style='margin-top:6px'>";
      (d.indices || []).slice(0, 3).forEach(function (x) {
        var c = (x.contracts || [])[0];
        var basis = c && x.underlying ? ((c.close - x.underlying) / x.underlying) * 100 : null;
        var rollover = "n/a";
        if (c && x.contracts[1]) rollover = (x.contracts[1].oi / c.oi * 100).toFixed(0) + "%";
        h += "<div class='kpi' style='text-align:center'><div class='k-name'>" + esc(x.symbol) + "</div>" +
          "<div class='k-val' style='font-size:22px;color:" + (basis == null ? "var(--dim)" : basis >= 0 ? "var(--up)" : "var(--down)") + "'>" +
          (basis == null ? "-" : (basis >= 0 ? "+" : "") + fmt(basis, 2) + "%") + "</div>" +
          "<div class='k-chg' style='color:var(--dim)'>" + (basis >= 0 ? "PREMIUM" : "DISCOUNT") + " &middot; roll " + rollover + "</div></div>";
      });
      h += "</div>";
      var p = d.pcr || {};
      var pcr = Number(p.nifty_pcr_oi);
      var mood = !isFinite(pcr) ? "?" : pcr < 0.7 ? "BEARISH" : pcr <= 1.1 ? "NEUTRAL" : "BULLISH";
      var mc = mood === "BULLISH" ? "var(--up)" : mood === "BEARISH" ? "var(--down)" : "var(--amber)";
      h += "<div style='margin-top:10px;text-align:center'>" +
        badge("NIFTY PCR " + fmt(pcr, 2) + " &rarr; " + mood, mood === "BULLISH" ? "var(--up-dim)" : mood === "BEARISH" ? "var(--down-dim)" : "var(--amber-dim)", mc);
      if (p.nifty_max_pain && p.nifty_spot) {
        var d2 = ((p.nifty_max_pain - p.nifty_spot) / p.nifty_spot) * 100;
        h += badge("MAX PAIN " + p.nifty_max_pain + " (" + (d2 >= 0 ? "+" : "") + fmt(d2, 1) + "%)", "var(--blue-dim)", "var(--blue)");
      }
      h += "</div><div class='footer-note'>Radar: premium = bulls ka paisa, discount = dar. PCR >1.2 me ghabraavat (contrarian), <0.7 pe pagal bullish. Max pain expiry pe magnet hai.</div>";
      setB("mbFutRadarBody", h);
    }).catch(function () { setB("mbFutRadarBody", "data load nahi hua - refresh karo"); });
  }

  /* 7) GTI ZONES RADAR - current zone + compression */
  function gtiRadar() {
    var b = mountCard("gti", "mbGtiRadar", "🎯 GTI ZONES RADAR", "Nifty/Bank ab kis zone me");
    if (!b) return;
    fj("data/gti.json").then(function (d) {
      var syms = d.symbols || {};
      var keys = Object.keys(syms).slice(0, 2);
      if (!keys.length) { setB("mbGtiRadarBody", "GTI data nahi"); return; }
      var h = "";
      keys.forEach(function (k) {
        var s = syms[k];
        var near = s.nearest || ["?", 0];
        var dist = Number(near[1]) || 0;
        var comp = s.compression || {};
        var zc = dist > 0.5 ? "var(--down)" : dist < -0.5 ? "var(--up)" : "var(--amber)";
        h += "<div class='kpi' style='margin-top:6px'><div class='k-name'>" + esc(k) + " &middot; " + fmt(s.price, 0) + "</div>" +
          "<div style='font-size:17px;font-weight:900;color:" + zc + ";margin-top:2px'>NEAREST: " + esc(near[0]) + " (" + (dist >= 0 ? "+" : "") + fmt(dist, 2) + "%)</div>" +
          "<div style='margin-top:6px;font-family:var(--mono);font-size:11px;opacity:.85'>";
        var dz = s.day_zones || {};
        ["SD", "WD", "WS", "SS"].forEach(function (z) {
          if (dz[z]) h += z + " " + dz[z][0] + "-" + dz[z][1] + " &nbsp; ";
        });
        h += "</div><div style='margin-top:5px'>" +
          badge(comp.compressed ? "COMPRESSION ON (bada move aane wala)" : "COMPRESSION OFF", comp.compressed ? "var(--amber-dim)" : "var(--glass)", comp.compressed ? "var(--amber)" : "var(--dim)") +
          badge("GRID " + (s.grid ? s.grid.level : "?"), "var(--blue-dim)", "var(--blue)") + "</div></div>";
      });
      h += "<div class='footer-note'>Radar: SD = supply (upar bikta hai), SS = support (niche khareedte hai). Price SD ke paas = resistance, SS ke paas = support.</div>";
      setB("mbGtiRadarBody", h);
    }).catch(function () { setB("mbGtiRadarBody", "data load nahi hua - refresh karo"); });
  }

  /* 8) SECTOR MAP RADAR - heat grid */
  function secRadar() {
    var b = mountCard("heatmap", "mbSecRadar", "🗺 SECTOR MAP RADAR", "aaj ka rotation map");
    if (!b) return;
    fj("data/indices-all.json").then(function (d) {
      var want = ["NIFTY AUTO", "NIFTY BANK", "NIFTY IT", "NIFTY FMCG", "NIFTY METAL", "NIFTY PHARMA", "NIFTY REALTY", "NIFTY MEDIA", "NIFTY PSU BANK", "NIFTY PRIVATE BANK", "NIFTY FINANCIAL SERVICES", "NIFTY HEALTHCARE INDEX", "NIFTY CONSUMER DURABLES", "NIFTY MIDCAP 150", "NIFTY SMALLCAP 250", "NIFTY OIL & GAS"];
      var by = {};
      (d.indices || []).forEach(function (i) { by[i.index] = i; });
      var rows = want.map(function (w) { return by[w]; }).filter(Boolean);
      var green = rows.filter(function (r) { return (r.change_pct || 0) > 0; }).length;
      var h = "<div style='text-align:center;margin-top:4px'><b style='font-size:15px;font-weight:900;color:" + (green * 2 >= rows.length ? "var(--up)" : "var(--down)") + "'>" + green + "/" + rows.length + " SECTORS GREEN</b></div>";
      h += "<div style='display:grid;grid-template-columns:repeat(2,1fr);gap:7px;margin-top:8px'>";
      rows.forEach(function (r) {
        var nm = r.index.replace("NIFTY ", "");
        h += "<div style='" + heatBg(r.change_pct) + ";border:1px solid var(--border);border-radius:10px;padding:8px;text-align:center'>" +
          "<div style='font-size:11px;font-weight:800;opacity:.9;white-space:nowrap;overflow:hidden;text-overflow:ellipsis'>" + esc(nm) + "</div>" +
          "<div style='font-size:17px;font-weight:900;color:" + pcol(r.change_pct) + "'>" + (r.change_pct > 0 ? "+" : "") + fmt(r.change_pct, 2) + "%</div></div>";
      });
      h += "</div><div class='footer-note'>Radar: jahan gehra green = aaj paisa wahan. Kal ka colour badal jaye to rotation pakdo - paisa ghoom raha hai.</div>";
      setB("mbSecRadarBody", h);
    }).catch(function () { setB("mbSecRadarBody", "data load nahi hua - refresh karo"); });
  }

  function boot() {
    try { idxRadar(); } catch (e) {}
    try { fundRadar(); } catch (e) {}
    try { mfRadar(); } catch (e) {}
    try { dfRadar(); } catch (e) {}
    try { filRadar(); } catch (e) {}
    try { futRadar(); } catch (e) {}
    try { gtiRadar(); } catch (e) {}
    try { secRadar(); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot); else boot();
})();
