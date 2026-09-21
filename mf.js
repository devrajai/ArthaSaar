/* mf.js — MF Tracker: AMFI se saare funds ka daily NAV + search + fund detail
   (mfapi.in history, 1Y/3Y returns) + SIP/lumpsum calculator + My MF holdings. */
(function () {
  var t = document.querySelector('a.tile[href="#fundamentals"]');
  if (t) t.insertAdjacentHTML("afterend",
    '<a class="tile" href="#mf"><span class="t-ic">📊</span><span class="t-nm">MF Tracker</span><span class="t-sb">nav · sip · my funds</span></a>');
  var sec = document.createElement("section");
  sec.id = "mf"; sec.style.display = "none";
  sec.innerHTML = '<a class="backbtn" href="#home">⌂ Home</a><h2>MF Tracker</h2>' +
    '<div class="card"><div class="subhead">Fund dhoondo — naam ya code</div>' +
    '<input id="mfQ" placeholder="e.g. bluechip / hdfc / 120502" style="width:100%;box-sizing:border-box;padding:10px 12px;border-radius:10px;border:1px solid var(--border2,var(--border,rgba(255,255,255,.12)));background:var(--glass2,rgba(255,255,255,.05));color:inherit;font-size:14px">' +
    '<div id="mfRes" style="margin-top:8px"></div></div>' +
    '<div class="card" id="mfCard"></div>' +
    '<div class="card" id="mfSip"></div>' +
    '<div class="card" id="mfPf"></div>' +
    '<div class="note" style="margin:6px 2px 0">Source: AMFI (free, daily). Fund-manager ki personal history free mein nahi milti — house + category dikhta hai. Advice nahi.</div>';
  var ft = document.querySelector("footer");
  if (ft) ft.parentNode.insertBefore(sec, ft); else document.body.appendChild(sec);

  var esc2 = function (s) { return String(s == null ? "" : s).replace(/[&<>]/g, function (c) { return "\x26#x" + c.charCodeAt(0).toString(16) + ";"; }); };
  var pc = function (v) { return v == null ? "—" : '<span class="' + (v >= 0 ? "pos" : "neg") + '">' + (v >= 0 ? "+" : "") + v + "%</span>"; };
  var nf2 = function (v) { return "\u20B9" + (Math.round(v * 100) / 100).toLocaleString("en-IN"); };
  var FUNDS = [];

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
      '<div class="note">invested ' + nf2(tc) + " · value " + nf2(tv) + " · P&L <b class='" + (tp >= 0 ? "pos" : "neg") + "'>" + (tp >= 0 ? "+" : "−") + nf2(Math.abs(tp)).slice(0) + "</b></div>";
    box.querySelectorAll("[data-mdel]").forEach(function (b) {
      b.onclick = function () { var p = mbTool.nload("mb-pf"); p.splice(+b.getAttribute("data-mdel"), 1); mbTool.nsave("mb-pf", p); renderPf(); };
    });
  }

  function returnsFrom(hist) {
    if (!hist || hist.length < 30) return "";
    var navs = hist.map(function (x) { return +x.nav; });
    var last = navs[0], oneY = null, threeY = null;
    hist.forEach(function (x, i) {
      var d = new Date(x.date.split("-").reverse().join("-"));
      var days = (Date.now() - d.getTime()) / 864e5;
      if (oneY === null && days >= 365 && days < 400) oneY = navs[i];
      if (threeY === null && days >= 1095 && days < 1130) threeY = navs[i];
    });
    var out = [];
    if (oneY) out.push("1Y <b class='pos'>" + ((last / oneY - 1) * 100).toFixed(1) + "%</b>");
    if (threeY) out.push("3Y <b class='pos'>" + ((last / threeY - 1) * 100).toFixed(1) + "%</b>");
    return out.length ? '<div class="note" style="margin-top:6px">returns: ' + out.join(" · ") + "</div>" : "";
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
      if (!hist.length) { box.textContent = "chart data nahi mili"; return; }
      var lastN = hist.slice(0, 365).reverse().map(function (x) { return +x.nav; });
      var m = (d.meta || {});
      box.innerHTML = (lastN.length > 30 ? sparkline(lastN) : "") + returnsFrom(hist) +
        '<div class="note" style="margin-top:4px">' + esc2(m.fund_house || f.h || "") + (m.scheme_category ? " · " + esc2(m.scheme_category) : "") + "</div>";
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
    jload("mf").then(function (d) {
      FUNDS = (d.funds || []).filter(function (f) { return f.v; });
      $("#mfRes").innerHTML = "<div class='note'>" + (d.count || FUNDS.length).toLocaleString("en-IN") + " funds ready — naam likho upar</div>";
    }).catch(function () {
      $("#mfRes").innerHTML = "<div class='note'>MF data load nahi hua — thodi der baad try karo</div>";
    });
    renderPf();
    sipCard();
    var q = null;
    $("#mfQ").addEventListener("input", function () {
      clearTimeout(q); q = setTimeout(function () { search($("#mfQ").value); }, 300);
    });
  };
})();
