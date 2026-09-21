/* mft.js — MF Tracker (static tile version): AMFI daily NAV + full fund detail
   (year-by-year returns, vs Nifty + Gold, SIP backtest with custom amount) + Top Performers + SIP calc + My MF + guide. */
(function () {
  if (window.__MB_MF) return; window.__MB_MF = 1;
  if (!document.querySelector('a.tile[href="#mf"]')) {
    var t = document.querySelector('a.tile[href="#fundamentals"]');
    if (t) t.insertAdjacentHTML("afterend",
      '<a class="tile" href="#mf"><span class="t-ic">📊</span><span class="t-nm">MF Tracker</span><span class="t-sb">nav · sip · my funds</span></a>');
  }
  var sec = document.getElementById("mf");
  if (sec) sec.style.display = "none";
  if (!sec) {
    sec = document.createElement("section");
    sec.id = "mf"; sec.style.display = "none";
  sec.innerHTML = '<a class="backbtn" href="#home">⌂ Home</a><h2>MF Tracker</h2>' +
    '<div class="card"><div class="subhead">Fund dhoondo — naam ya code</div>' +
    '<input id="mfQ" placeholder="e.g. bluechip / hdfc / 120502" style="width:100%;box-sizing:border-box;padding:10px 12px;border-radius:10px;border:1px solid var(--border2,var(--border,rgba(255,255,255,.12)));background:var(--glass2,rgba(255,255,255,.05));color:inherit;font-size:14px">' +
    '<div id="mfRes" style="margin-top:8px"></div></div>' +
    '<div class="card" id="mfCard"></div>' +
    '<div class="card" id="mfTop"></div>' +
    '<div class="card" id="mfSip"></div>' +
    '<div class="card" id="mfPf"></div>' +
    '<div class="card" id="mfGuide"></div>';
  var ft = document.querySelector("footer");
  if (ft) ft.parentNode.insertBefore(sec, ft); else document.body.appendChild(sec);
  }

  var esc2 = function (s) { return String(s == null ? "" : s).replace(/[&<>]/g, function (c) { return "\x26#x" + c.charCodeAt(0).toString(16) + ";"; }); };
  var pc = function (v) { return v == null ? "—" : '<span class="' + (v >= 0 ? "pos" : "neg") + '">' + (v >= 0 ? "+" : "") + v + "%</span>"; };
  var pc2 = function (v) { return v == null ? "—" : '<b class="' + (v >= 0 ? "pos" : "neg") + '">' + (v >= 0 ? "+" : "") + v + "%</b>"; };
  var nf2 = function (v) { return "\u20B9" + Math.round(v).toLocaleString("en-IN"); };
  var FUNDS = [], NIFTY_Y = null, MFTOP = null, CUR_HIST = null;

  function niftyYearly() {
    if (NIFTY_Y) return NIFTY_Y;
    jload("index-history").then(function (d) {
      var row = (d.indices || []).filter(function (x) { return x.key === "nifty"; })[0];
      if (!row) return;
      var out = {};
      Object.keys(row.years || {}).forEach(function (y) {
        var r = 1, c = 0;
        Object.keys(row.years[y]).forEach(function (m) { r *= 1 + (row.years[y][m] || 0) / 100; c++; });
        out[y] = c ? (r - 1) * 100 : null;
      });
      NIFTY_Y = out;
    }).catch(function () {});
  }

  function yearRows(hist) {
    var byY = {};
    for (var i = hist.length - 1; i >= 0; i--) {
      var p = (hist[i].date || "").split("-");
      if (p.length === 3) byY[p[2]] = +hist[i].nav;
    }
    var ys = Object.keys(byY).sort();
    var rows = [];
    for (var j = 1; j < ys.length; j++) rows.push({ y: ys[j], r: (byY[ys[j]] / byY[ys[j - 1]] - 1) * 100 });
    return rows.slice(-8);
  }

  function sipBacktest(hist, amt, years) {
    var months = [];
    for (var i = hist.length - 1; i >= 0; i--) {   // oldest -> newest
      var p = (hist[i].date || "").split("-");
      if (p.length !== 3) continue;
      var key = p[2] + "-" + p[1];
      if (!months.length || months[months.length - 1].key !== key) months.push({ key: key, nav: +hist[i].nav, y: +p[2], m: +p[1] });
    }
    if (months.length < years * 12 + 1) return null;
    months = months.slice(-(years * 12 + 1), months.length - 1); // buy months
    var units = 0, inv = 0;
    months.forEach(function (mm) { units += amt / mm.nav; inv += amt; });
    var val = units * (+hist[0].nav);
    return { inv: inv, val: val, pct: (val / inv - 1) * 100 };
  }

  function trailHtml(hist) {
    function ret(days) {
      var now = +hist[0].nav, cut = new Date(hist[0].date.split("-").reverse().join("-")).getTime() - days * 864e5, last = null;
      for (var i = hist.length - 1; i >= 0; i--) {
        var d = new Date(hist[i].date.split("-").reverse().join("-")).getTime();
        if (d <= cut) last = +hist[i].nav; else break;
      }
      return last ? (now / last - 1) * 100 : null;
    }
    var parts = [];
    [["1Y", 365], ["3Y", 1095], ["5Y", 1825], ["10Y", 3650]].forEach(function (p) {
      var v = ret(p[1]);
      if (v != null) parts.push(p[0] + " " + pc2(v.toFixed(1)));
    });
    return parts.length ? '<div class="note" style="margin-top:6px">returns: ' + parts.join(" · ") + "</div>" : "";
  }

  function showFund(code) {
    var f = null;
    FUNDS.forEach(function (x) { if (x.c === code) f = x; });
    if (!f) return;
    $("#mfCard").innerHTML = '<div class="subhead">' + esc2(f.n) + "</div>" +
      '<div style="display:flex;gap:14px;flex-wrap:wrap;align-items:center;margin:4px 0">' +
      '<div><div class="note">NAV</div><div style="font-size:24px;font-weight:700">\u20B9' + f.v + "</div></div>" +
      '<div><div class="note">aaj</div><div style="font-size:24px;font-weight:700">' + pc(f.p) + "</div></div></div>" +
      '<div class="note">' + esc2(f.h || "—") + " · " + esc2(f.k || "—") + "</div>" +
      '<div class="note" style="margin-top:8px">units: <input id="mfU" type="number" placeholder="units" style="width:90px;padding:6px 8px;border-radius:8px;border:1px solid var(--border2,rgba(255,255,255,.12));background:var(--glass2,rgba(255,255,255,.05));color:inherit"> ' +
      '<button class="chip on" id="mfAddBtn">add to My MF</button></div>' +
      '<div id="mfHist" class="note" style="margin-top:8px">history load ho rahi…</div>';
    var box = $("#mfHist");
    fetch("https://api.mfapi.in/mf/" + code).then(function (r) { return r.json(); }).then(function (d) {
      var hist = (d && d.data) || [];
      CUR_HIST = hist;
      if (hist.length < 30) { box.textContent = "chart data nahi mili"; return; }
      var lastN = hist.slice(0, 365).reverse().map(function (x) { return +x.nav; });
      var yr = yearRows(hist), nY = NIFTY_Y || {};
      var bars = yr.map(function (r) {
        var w = Math.min(100, Math.abs(r.r) * 2.2);
        var cls = r.r >= 0 ? "pos" : "neg";
        var bg = r.r >= 0 ? "linear-gradient(90deg,#22c55e,#4ade80)" : "linear-gradient(90deg,#ef4444,#f87171)";
        var gy = (MFTOP && MFTOP.bench && MFTOP.bench.gold && MFTOP.bench.gold.y && MFTOP.bench.gold.y[r.y] != null) ? MFTOP.bench.gold.y[r.y] : null;
        var nv = (nY[r.y] != null || gy != null) ? ' <span style="opacity:.55">' +
          (nY[r.y] != null ? "Nifty " + (nY[r.y] >= 0 ? "+" : "") + nY[r.y].toFixed(0) + "%" : "") +
          (nY[r.y] != null && gy != null ? " · " : "") +
          (gy != null ? "Gold " + (gy >= 0 ? "+" : "") + gy.toFixed(0) + "%" : "") + "</span>" : "";
        return '<div style="display:flex;align-items:center;gap:8px;margin:3px 0">' +
          '<span style="width:38px;font-size:11px;opacity:.8">' + r.y + "</span>" +
          '<span style="flex:1;height:10px;border-radius:5px;background:rgba(255,255,255,.07);overflow:hidden"><i style="display:block;width:' + w.toFixed(0) + '%;height:100%;border-radius:5px;background:' + bg + '"></i></span>' +
          '<span class="' + cls + '" style="width:56px;text-align:right;font-size:12px">' + (r.r >= 0 ? "+" : "") + r.r.toFixed(1) + "%</span></div>" +
          '<div class="note" style="margin:-1px 0 2px 46px;font-size:10px">' + nv + "</div>";
      }).join("");
      var m = (d.meta || {});
      var bn = (MFTOP && MFTOP.bench) || {};
      var bnNote = (bn.gold && bn.gold.r3 != null) || (bn.silver && bn.silver.r3 != null) ?
        '<div class="note" style="margin-top:4px">usi samay: Gold 3Y ' + (bn.gold && bn.gold.r3 != null ? pc2(bn.gold.r3.toFixed(1)) : "—") +
        " · Silver 3Y " + (bn.silver && bn.silver.r3 != null ? pc2(bn.silver.r3.toFixed(1)) : "—") + "</div>" : "";
      var sipDef = sipBacktest(hist, 5000, 3);
      box.innerHTML = (lastN.length > 30 ? sparkline(lastN) : "") + trailHtml(hist) + bnNote +
        (yr.length ? '<div class="subhead" style="margin-top:10px">Year-by-Year</div>' + bars : "") +
        '<div class="subhead" style="margin-top:10px">SIP test — apna amount daalo</div>' +
        '<div class="note" style="margin:6px 0">\u20B9/mahina <input id="mfSAmt" type="number" value="5000" min="100" step="100" style="width:90px;padding:6px 8px;border-radius:8px;border:1px solid var(--border2,rgba(255,255,255,.12));background:var(--glass2,rgba(255,255,255,.05));color:inherit"> ' +
        'saal <select id="mfSYrs" style="padding:6px 8px;border-radius:8px;border:1px solid var(--border2,rgba(255,255,255,.12));background:var(--glass2,rgba(255,255,255,.05));color:inherit"><option>3</option><option>5</option><option>10</option></select> ' +
        '<button class="chip on" id="mfSGo">batao</button></div>' +
        '<div id="mfSOut" class="note">' + (sipDef ? "invested <b>" + nf2(sipDef.inv) + "</b> \u2192 value <b class='pos'>" + nf2(sipDef.val) + "</b> (" + (sipDef.pct >= 0 ? "+" : "") + sipDef.pct.toFixed(0) + "%)" : "itni history nahi hai") + "</div>" +
        (sipDef ? '<div class="note" style="margin-top:4px">\u20B9100/month wale mini-SIP ke liye bhi same % return milega — amount badal ke dekho</div>' : "") +
        '<div class="note" style="margin-top:8px">' + esc2(m.fund_house || f.h || "") + (m.scheme_category ? " · " + esc2(m.scheme_category) : "") + "</div>" +
        '<div class="note" style="margin-top:6px">AUM / expense ratio / holdings / fund manager — free data mein nahi milte, <a style="color:var(--blue,#5aa7ff)" target="_blank" rel="noopener" href="https://www.google.com/search?q=' + encodeURIComponent((f.n || "").split(" \u00b7 ")[0] + " mutual fund AUM expense ratio portfolio holdings") + '">yahan dekho \u2192</a></div>';
      var goBtn = document.querySelector("#mfSGo");
      if (goBtn) goBtn.onclick = function () {
        var amt = Math.max(100, +document.querySelector("#mfSAmt").value || 100);
        var yr2 = +document.querySelector("#mfSYrs").value || 3;
        var r2 = sipBacktest(CUR_HIST, amt, yr2);
        var o2 = document.querySelector("#mfSOut");
        if (o2) o2.innerHTML = r2 ? "invested <b>" + nf2(r2.inv) + "</b> \u2192 value <b class='" + (r2.pct >= 0 ? "pos" : "neg") + "'>" + nf2(r2.val) + "</b> (" + (r2.pct >= 0 ? "+" : "") + r2.pct.toFixed(0) + "%)" : "itni history nahi hai";
      };
    }).catch(function () { box.textContent = "history offline — NAV upar wala pakka hai"; });
    $("#mfAddBtn").onclick = function () {
      var u = parseFloat($("#mfU").value);
      if (!u || u <= 0) { box.textContent = "units daalo pehle"; return; }
      var p = mbTool.nload("mb-pf");
      p.push({ c: f.c, n: f.n, u: u, nav: f.v });
      mbTool.nsave("mb-pf", p);
      $("#mfU").value = "";
      renderPf();
      box.textContent = "added to My MF ✓";
    };
  }

  function renderTop() {
    jload("mf-top").then(function (d) {
      MFTOP = d;
      var nf = (d.nifty || {}), rows = d.funds || [];
      if (!rows.length) { $("#mfTop").innerHTML = '<div class="subhead">\uD83C\uDFC6 Top Performers</div><div class="note">data aaj raat banega — kal subah se dikhega</div>'; return; }
      $("#mfTop").innerHTML = '<div class="subhead">\uD83C\uDFC6 Top Performers — popular Direct-Growth funds (3Y return se sorted)</div>' +
        '<div class="tblwrap"><table><thead><tr><th>Fund</th><th>1Y</th><th>3Y</th><th>5Y</th><th>vs Nifty</th></tr></thead><tbody>' +
        rows.map(function (r) {
          var beat = (r.r3 != null && nf.r3 != null) ? r.r3 - nf.r3 : null;
          return '<tr data-mc="' + esc2(r.c) + '"><td class="note">' + esc2(r.n).slice(0, 40) + "</td><td>" + pc(r.r1) + "</td><td><b>" + pc(r.r3) + "</b></td><td>" + pc(r.r5) + "</td>" +
            '<td>' + (beat == null ? "—" : '<b class="' + (beat >= 0 ? "pos" : "neg") + '">' + (beat >= 0 ? "✓ +" : "✗ ") + beat.toFixed(0) + "</b>") + "</td></tr>";
        }).join("") + "</tbody></table></div>" +
        '<div class="note" style="margin-top:6px">Nifty 3Y: ' + (nf.r3 != null ? "+" + nf.r3 + "%" : "—") +
        ((d.bench || {}).gold ? " · Gold 3Y: +" + (d.bench.gold.r3 != null ? d.bench.gold.r3 : "—") + "%" : "") +
        ((d.bench || {}).silver ? " · Silver 3Y: +" + (d.bench.silver.r3 != null ? d.bench.silver.r3 : "—") + "%" : "") +
        " · roz raat update · ye 34 popular funds hain, poora market nahi</div>";
      $("#mfTop").querySelectorAll("[data-mc]").forEach(function (tr) {
        tr.onclick = function () { showFund(tr.getAttribute("data-mc")); window.scrollTo(0, 0); };
      });
    }).catch(function () { $("#mfTop").innerHTML = ""; });
  }

  function renderGuide() {
    $("#mfGuide").innerHTML = '<div class="subhead">\uD83E\uDDED Best MF kaise chunein?</div>' +
      '<div class="note" style="margin-top:6px">· <b>Category pehle decide karo</b> — Large Cap (sthair), Flexi (all-round), Mid/Small (tez but risky), Index (sasta, Nifty-jaisa), Gold (safety).<br>' +
      "· <b>3-5 saal ka record dekho</b> — 1 saal ka top fund luck bhi ho sakta hai. Top Performers table mein 3Y dekho, Nifty se kitna aage (vs Nifty column).<br>" +
      "· <b>Direct Plan + Growth</b> lo — Regular plan ka commission ~1% har saal katata hai.<br>" +
      "· <b>Index fund vs active</b> — agar fund 3-5 saal se Nifty ko beat nahi kar raha to sasta Index fund hi better hai.<br>" +
      "· <b>SIP best hai beginners ke liye</b> — timing ka tension khatam, roz/fixed date auto-invest.<br>" +
      "· Ek hi category ke 10 fund mat le — 2-3 achhe fund kaafi hain.</div>" +
      '<div class="subhead" style="margin-top:12px">MF vs ETF — kya lena hai?</div>' +
      '<div class="note" style="margin-top:6px">· <b>Index MF</b>: SIP auto, NAV ek rate (no spread), demat account nahi chahiye. Best for SIP.<br>' +
      "· <b>ETF</b>: exchange par stock ki tarah kharido — intraday price, sasta expense, but liquidity kam aur demat chahiye. Best for lumpsum + bade amounts.<br>" +
      "· Simple rule: <b>SIP karoge → Index MF. Lumpsum ho → bade ETF (Nifty BeES jaise)</b>.</div>" +
      '<div class="note" style="margin-top:10px"><b>Honest note:</b> AUM, expense ratio, portfolio holdings (sector/stocks %) aur fund manager ki details free data mein available nahi hain — wo fund ke page ya AMC site par dekhna (fund card mein link hai). Ye terminal sirf free data dikhata hai — invest karne se pehle khud verify karo.</div>';
  }

  function renderPf() {
    var pf = mbTool.nload("mb-pf");
    var box = $("#mfPf");
    if (!pf.length) {
      box.innerHTML = '<div class="subhead">My MF Holdings</div><div class="note">koi fund select karke "add to My MF" dabao — units aur avg NAV daalo, daily value dikhega.</div>';
      return;
    }
    var by = {}; FUNDS.forEach(function (f) { by[f.c] = f; });
    var tv = 0, tc = 0, rows = "";
    pf.forEach(function (h, i) {
      var f = by[h.c] || {}, v = (f.v || h.nav) * h.u, cost = h.nav * h.u;
      tv += v; tc += cost;
      rows += "<tr><td class='note'>" + esc2(h.n).slice(0, 34) + "</td><td>" + h.u + "</td><td>" + h.nav + "</td><td>" + (f.v || "—") + "</td><td>" + (f.v ? pc(f.p) : "—") + "</td><td>" + nf2(v) + "</td>" +
        '<td><button class="chip" data-mdel="' + i + '" style="padding:2px 8px">✕</button></td></tr>';
    });
    var tp = tv - tc;
    box.innerHTML = '<div class="subhead">My MF Holdings</div><div class="tblwrap"><table><thead><tr><th>Fund</th><th>Units</th><th>Avg ₹</th><th>NAV ₹</th><th>Day</th><th>Value</th><th></th></tr></thead><tbody>' + rows +
      '<tr><td colspan="5"><b>TOTAL</b></td><td><b>' + nf2(tv) + '</b></td><td></td></tr></tbody></table></div>' +
      '<div class="note">invested ' + nf2(tc) + " · value " + nf2(tv) + " · P&L <b class='" + (tp >= 0 ? "pos" : "neg") + "'>" + (tp >= 0 ? "+" : "\u2212") + nf2(Math.abs(tp)) + "</b></div>";
    box.querySelectorAll("[data-mdel]").forEach(function (b) {
      b.onclick = function () { var p = mbTool.nload("mb-pf"); p.splice(+b.getAttribute("data-mdel"), 1); mbTool.nsave("mb-pf", p); renderPf(); };
    });
  }

  function search(q) {
    q = q.trim().toLowerCase();
    var box = $("#mfRes");
    if (q.length < 2) { box.innerHTML = ""; return; }
    var hits = [];
    FUNDS.forEach(function (f) {
      if (hits.length >= 25) return;
      if (f.n.toLowerCase().indexOf(q) !== -1 || f.c === q) hits.push(f);
    });
    if (!hits.length) { box.innerHTML = "<div class='note'>kuch nahi mila</div>"; return; }
    box.innerHTML = '<div class="tblwrap"><table><thead><tr><th>Fund</th><th>NAV ₹</th><th>Day%</th></tr></thead><tbody>' +
      hits.map(function (f) {
        return '<tr data-mc="' + f.c + '"><td class="note">' + esc2(f.n).slice(0, 44) + "</td><td>" + f.v + "</td><td>" + pc(f.p) + "</td></tr>";
      }).join("") + "</tbody></table></div>" +
      (hits.length >= 25 ? '<div class="note">…25 tak dikhaya</div>' : "");
    box.querySelectorAll("[data-mc]").forEach(function (tr) {
      tr.onclick = function () { showFund(tr.getAttribute("data-mc")); window.scrollTo(0, 300); };
    });
  }

  function sipCard() {
    $("#mfSip").innerHTML = '<div class="subhead">SIP Calculator</div>' +
      '<div class="note" style="margin:6px 0">har mahine ₹ <input id="sipM" type="number" value="5000" style="width:80px;padding:6px 8px;border-radius:8px;border:1px solid var(--border2,rgba(255,255,255,.12));background:var(--glass2,rgba(255,255,255,.05));color:inherit"> ' +
      'saal <input id="sipY" type="number" value="10" style="width:60px;padding:6px 8px;border-radius:8px;border:1px solid var(--border2,rgba(255,255,255,.12));background:var(--glass2,rgba(255,255,255,.05));color:inherit"> ' +
      'return % <input id="sipR" type="number" value="12" style="width:60px;padding:6px 8px;border-radius:8px;border:1px solid var(--border2,rgba(255,255,255,.12));background:var(--glass2,rgba(255,255,255,.05));color:inherit"> ' +
      '<button class="chip on" id="sipGo">batao</button></div><div id="sipOut" class="note"></div>';
    $("#sipGo").onclick = function () {
      var m = +$("#sipM").value || 0, y = +$("#sipY").value || 0, r = +$("#sipR").value || 0;
      if (!m || !y) return;
      var i = r / 1200, n = y * 12, inv = m * n;
      var val = i === 0 ? inv : m * ((Math.pow(1 + i, n) - 1) / i) * (1 + i);
      $("#sipOut").innerHTML = "invested <b>" + nf2(inv) + "</b> · value <b class='pos'>" + nf2(val) + "</b> · gain <b class='pos'>+" + nf2(val - inv) + "</b> (" + ((val / inv - 1) * 100).toFixed(0) + "%)";
    };
  }

  loaders.mf = function () {
    niftyYearly();
    jload("mf").then(function (d) {
      FUNDS = (d.funds || []).filter(function (f) { return f.v; });
      $("#mfRes").innerHTML = "<div class='note'>" + (d.count || FUNDS.length).toLocaleString("en-IN") + " funds ready — naam likho upar</div>";
    }).catch(function () {
      $("#mfRes").innerHTML = "<div class='note'>MF data load nahi hua — thodi der baad try karo</div>";
    });
    renderTop();
    renderGuide();
    renderPf();
    sipCard();
    var q = null;
    $("#mfQ").addEventListener("input", function () {
      clearTimeout(q); q = setTimeout(function () { search($("#mfQ").value); }, 300);
    });
  };
})();
