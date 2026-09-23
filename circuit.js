/* circuit.js - Circuit Scanner: NSE upper/lower circuit stocks (1-20% bands), daily bhavcopy. #screener top */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var DATA = null;

  function fmtCr(v) {
    if (v >= 100000) return "\u20B9" + (v / 100000).toFixed(2) + " L cr";
    if (v >= 100) return "\u20B9" + Math.round(v) + " cr";
    return "\u20B9" + v.toFixed(1) + " cr";
  }

  function bandRow(grp, isUp) {
    var h = '<details style="margin-top:6px"><summary style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:13.5px;flex-wrap:wrap">' +
      '<b style="min-width:56px;font-size:14px;color:' + (isUp ? "#77f37b" : "#ff8b8b") + '">' + grp.b + '%</b>' +
      '<span style="font-size:12.5px">' + (isUp ? "Upper" : "Lower") + ' Circuit</span>' +
      '<span style="margin-left:auto;font-size:11.5px;font-weight:700;color:rgba(240,180,41,.95)">' + grp.n + ' stocks</span></summary>' +
      '<div style="padding:2px 14px 8px 14px">';
    grp.top.forEach(function (x) {
      h += '<div style="display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:12.5px">' +
        '<b style="min-width:92px">' + esc(x.s) + '</b>' +
        '<span style="min-width:64px;opacity:.8">\u20B9' + esc(x.c) + '</span>' +
        '<b style="min-width:56px;color:' + (x.p >= 0 ? "#77f37b" : "#ff8b8b") + '">' + (x.p > 0 ? "+" : "") + esc(x.p) + '%</b>' +
        '<span style="margin-left:auto;opacity:.55;font-size:11px">' + fmtCr(x.v) + '</span></div>';
    });
    if (grp.n > grp.top.length) h += '<div class="note" style="margin-top:4px">...aur ' + (grp.n - grp.top.length) + ' stocks (value ke hisaab se top ' + grp.top.length + ' dikhe)</div>';
    h += '</div></details>';
    return h;
  }

  function render(box) {
    var d = DATA;
    var h = '<div class="note" style="margin-top:8px">' + esc(d.updated) + ' \u00b7 ' + d.n_uc + ' upper + ' + d.n_lc + ' lower circuit stocks. Upper = sellers khatam (buyer ka raj), lower = buyers khatam. Band % tap karke list dekho. Tip: UC + volume = strong demand; LC + volume = panic. Band 2/5/10/20 NSE ka standard hai. (indicative, advice nahi)</div>';
    h += '<div style="margin-top:8px;font-size:13px;font-weight:700;color:#77f37b">\uD83D\uDFE2 UPPER CIRCUIT (' + d.n_uc + ')</div>';
    (d.uc || []).forEach(function (g) { h += bandRow(g, true); });
    h += '<div style="margin-top:10px;font-size:13px;font-weight:700;color:#ff8b8b">\uD83D\uDD34 LOWER CIRCUIT (' + d.n_lc + ')</div>';
    (d.lc || []).forEach(function (g) { h += bandRow(g, false); });
    box.innerHTML = h;
  }

  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(240,180,41,.13);border:1px solid rgba(240,180,41,.5);font-size:14.5px;text-align:center"><b style="color:rgba(240,180,41,.95)">\u26A1 CIRCUIT SCANNER</b> <span style="font-size:11px;opacity:.65">upper \u00b7 lower \u00b7 1-20% \u00b7 NSE</span></summary>' +
      '<div id="csBody" class="note" style="margin-top:8px">loading circuits...</div>';
    fetch("data/circuits.json").then(function (r) { return r.json(); }).then(function (d) {
      DATA = d; render(document.getElementById("csBody"));
    }).catch(function () {
      var b = document.getElementById("csBody");
      if (b) b.innerHTML = "data load nahi hua - thodi der baad try karo";
    });
  }

  function mount() {
    var sec = document.querySelector("section#screener");
    if (!sec || document.getElementById("mbCircuits")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbCircuits"; c.style.marginTop = "14px";
    var ref = document.getElementById("mbScoreCard") || sec.querySelector("h2");
    if (ref && ref.parentNode) ref.parentNode.insertBefore(c, ref); else sec.appendChild(c);
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
