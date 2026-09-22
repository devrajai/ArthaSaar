/* bullish.js - Bullish Scanner: week/month/year/long-term scores (fundamentals + technicals). #fundamentals section top */
(function () {
  var TAB = "week";
  var DATA = null, GTI = null;
  var LBL = { week: "This Week (technical: delivery + momentum + zones)",
    month: "This Month (50% technical + 50% fundamentals)",
    year: "This Year (70% fundamentals + 30% trend)",
    decade: "Long-Term Quality (ROE/ROCE/growth - 5-10 saal wale)" };
  var IDX = ["NIFTY 50", "BANKNIFTY", "FINNIFTY", "SENSEX", "MIDCPNIFTY", "NIFTY NEXT 50"];

  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }

  function row(x) {
    var pct = Math.round(x[TAB === "week" ? "w" : TAB === "month" ? "m" : TAB === "year" ? "y" : "d"]);
    var col = x.c;
    return '<div class="note" style="display:flex;align-items:center;gap:8px;margin-top:6px">' +
      '<span style="min-width:86px"><b>' + esc(x.s) + '</b></span>' +
      '<span style="flex:1;height:8px;border-radius:4px;background:rgba(255,255,255,.08);overflow:hidden">' +
      '<span style="display:block;height:100%;width:' + pct + '%;background:' + col + ';border-radius:4px"></span></span>' +
      '<span style="min-width:36px;text-align:right;color:' + col + '"><b>' + pct + '</b></span>' +
      '<span style="min-width:96px;text-align:right;font-size:11px;opacity:.75">F ' + x.f + ' · T ' + x.t + '</span></div>';
  }

  function render(card) {
    var list = DATA[TAB] || [];
    var h = '<div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px">';
    ["week", "month", "year", "decade"].forEach(function (t) {
      h += '<button data-t="' + t + '" style="flex:1;min-width:70px;padding:8px 4px;border-radius:9px;border:1px solid ' +
        (t === TAB ? "rgba(240,180,41,.6)" : "rgba(255,255,255,.12)") + ';background:' +
        (t === TAB ? "rgba(240,180,41,.15)" : "rgba(255,255,255,.04)") + ';color:inherit;font-size:12px;cursor:pointer">' +
        (t === "week" ? "Week" : t === "month" ? "Month" : t === "year" ? "Year" : "Long-term") + '</button>';
    });
    h += '</div><div class="note" style="margin-top:8px;font-size:12px;opacity:.8">' + LBL[TAB] + '</div>';
    var n = TAB === "decade" ? 12 : 10;
    list.slice(0, n).forEach(function (x) { h += row(x); });
    if (TAB === "week" && DATA.bearish && DATA.bearish.length) {
      h += '<div class="note" style="margin-top:12px"><b style="color:#ff8b8b">BEARISH side (mat lena):</b></div>';
      DATA.bearish.slice(0, 4).forEach(function (x) {
        h += '<div class="note" style="display:flex;justify-content:space-between"><span>' + esc(x.s) + '</span><span style="color:#ff8b8b">score ' + x.m + '</span></div>';
      });
    }
    h += '<div class="footer-note">' + esc(DATA.note) + '</div>';
    var body = card.querySelector(".bsInner");
    if (body) body.innerHTML = h;
    card.querySelectorAll("button[data-t]").forEach(function (b) {
      b.onclick = function () { TAB = b.getAttribute("data-t"); render(card); };
    });
  }

  function build(card) {
    card.innerHTML = '<div class="subhead">Bullish Scanner (fundamentals + technicals = ek score)</div><div class="bsBody"><div class="note">load ho raha hai...</div></div>';
    Promise.all([
      fetch("data/bullish.json?t=" + Date.now()).then(function (r) { return r.json(); }),
      fetch("data/gti.json?t=" + Date.now()).then(function (r) { return r.json(); }).catch(function () { return {}; })
    ]).then(function (res) {
      DATA = res[0]; GTI = res[1] || {};
      var bias = DATA.bias || "neutral";
      var h = '<div class="note" style="display:flex;flex-wrap:wrap;gap:6px;margin-top:8px">' +
        '<span style="padding:4px 10px;border-radius:8px;background:rgba(30,144,255,.12);border:1px solid rgba(30,144,255,.3)">FII/DII bias: <b>' + esc(bias) + '</b></span>';
      (DATA.indices || IDX).forEach(function (name) {
        var g = (GTI.symbols || {})[name];
        if (!g) return;
        var z = String((g.nearest || ["?"])[0]).toUpperCase();
        var bull = z.indexOf("SD") >= 0, bear = z.indexOf("SS") >= 0;
        h += '<span style="padding:4px 10px;border-radius:8px;border:1px solid ' +
          (bull ? "rgba(119,243,123,.4);background:rgba(119,243,123,.1)" : bear ? "rgba(255,139,139,.4);background:rgba(255,139,139,.1)" : "rgba(255,255,255,.12)") +
          '">' + esc(name.replace(" 50", "")) + ': <b>' + z + '</b></span>';
      });
      h += '</div>';
      var bd = card.querySelector(".bsBody");
      bd.innerHTML = h + '<div class="bsInner"></div>';
      render(card);
    }).catch(function () {
      card.innerHTML = '<div class="subhead">Bullish Scanner</div><div class="note">data nahi mila.</div>';
    });
  }

  function mount() {
    var sec = document.querySelector("section#fundamentals");
    if (!sec || document.getElementById("mbBullish")) return;
    var c = document.createElement("div");
    c.className = "card"; c.id = "mbBullish"; c.style.marginTop = "14px";
    var first = sec.querySelector(".card");
    if (first) sec.insertBefore(c, first); else sec.appendChild(c);
    try { build(c); } catch (e) { c.innerHTML = '<div class="subhead">Bullish Scanner</div><div class="note">error</div>'; }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
