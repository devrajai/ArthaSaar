/* bank.js - BANK HEALTH SCANNER: notebook rules se bank stock selection checklist. #screener */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var DATA = null, R = {};

  function chip(label, val, state, want) {
    var col = state === "ok" ? "#77f37b" : (state === "avg" ? "#f5c542" : "#ff8b8b");
    var ttl = esc(label) + ": " + esc(val) + " (rule: " + esc(want) + ")";
    return '<span title="' + ttl + '" style="font-size:10px;font-weight:700;padding:2px 6px;border-radius:7px;border:1px solid ' + col + ';color:' + col + '">' + esc(label) + ' ' + esc(val) + '</span>';
  }

  function bankRow(b) {
    var npa = b.npa, roe = b.roe, roa = b.roa, casa = b.casa, car = b.car;
    var st = {
      npa: npa <= R.npa_max ? "ok" : "bad",
      roe: (roe >= R.roe_min && roe <= R.roe_max) ? "ok" : "bad",
      casa: casa >= R.casa_good ? "ok" : (casa >= R.casa_avg ? "avg" : "bad"),
      car: car >= R.car_min ? "ok" : "bad",
      roa: roa >= R.roa_min ? "ok" : "bad"
    };
    var score = 0;
    ["npa", "roe", "casa", "car", "roa"].forEach(function (k) { if (st[k] === "ok") score++; });
    var scoreCol = score >= 4 ? "#77f37b" : (score >= 3 ? "#f5c542" : "#ff8b8b");
    var chg = b.chg;
    var h = '<details style="margin-top:6px"><summary style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:13.5px;flex-wrap:wrap">' +
      '<b style="min-width:128px">' + esc(b.n) + '</b>' +
      (b.p != null ? '<span style="opacity:.75;font-size:12.5px">\u20B9' + esc(b.p) + (chg != null ? ' <span style="font-weight:700;color:' + (chg >= 0 ? "#77f37b" : "#ff8b8b") + '">' + (chg > 0 ? "+" : "") + esc(chg) + '%</span>' : '') + '</span>' : "") +
      '<span style="margin-left:auto;font-size:12px;font-weight:800;color:' + scoreCol + '">' + score + '/5</span></summary>' +
      '<div style="padding:6px 14px 10px 14px">' +
      '<div style="display:flex;gap:5px;flex-wrap:wrap;margin-top:4px">' +
      chip("NPA", npa + "%", st.npa, "\u22641.5%") +
      chip("ROE", roe + "%", st.roe, "15-35%") +
      chip("CASA", casa + "%", st.casa, "40+ (30 avg)") +
      chip("CAR", car + "%", st.car, "\u22659%") +
      chip("ROA", roa + "%", st.roa, "\u22651.5%") +
      '</div>' +
      '<div class="note" style="margin-top:6px;font-size:10.5px;opacity:.55">' + esc(DATA.asof) + ' results. NPA = loan default risk (kam = better). ROE = paisa kamne ki taakat. CASA = sasta deposits jitna zyada utna fayda. CAR = crisis jhelne ka buffer. ROA = efficiency.</div>' +
      '</div></details>';
    return h;
  }

  function render(box) {
    var h = '<div class="note" style="margin-top:8px">' + esc(DATA.asof) + ' quarterly data \u00b7 price ' + esc(DATA.updated) + ' se. Ye <b>personal notebook ke rules</b> ka checklist hai - har bank 5 me se kitne rule pass karti hai. (checklist hai, advice nahi)</div>';
    h += '<div style="margin-top:8px;padding:8px 12px;border-radius:10px;background:rgba(240,180,41,.08);border:1px solid rgba(240,180,41,.35);font-size:12px">' +
      '\uD83D\uDCD3 <b>NOTEBOOK RULES:</b> Net NPA \u2264 1.5% \u00b7 ROE 15-35% \u00b7 CASA 40%+ (30 avg) \u00b7 CAR 9%+ \u00b7 ROA 1.5%+ <span style="opacity:.6">(notebook me 5% likha tha - India ke top banks bhi ~2.5% pe aate hain, isliye 1.5%+ = strong)</span></div>';
    function score(b) {
      var n = 0;
      if (b.npa <= R.npa_max) n++;
      if (b.roe >= R.roe_min && b.roe <= R.roe_max) n++;
      if (b.casa >= R.casa_good) n++;
      if (b.car >= R.car_min) n++;
      if (b.roa >= R.roa_min) n++;
      return n;
    }
    var sorted = (DATA.banks || []).slice().sort(function (a, b) { return score(b) - score(a); });
    h += '<div style="margin-top:8px;font-size:13px;font-weight:700;opacity:.85">Banks (score ke hisaab se):</div>';
    sorted.forEach(function (b) { h += bankRow(b); });
    box.innerHTML = h;
  }

  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(240,180,41,.13);border:1px solid rgba(240,180,41,.5);font-size:14.5px;text-align:center"><b style="color:rgba(240,180,41,.95)">\uD83C\uDFDA BANK SCANNER</b> <span style="font-size:11px;opacity:.65">notebook rules \u00b7 5-point checklist</span></summary>' +
      '<div id="bsBody" class="note" style="margin-top:8px">loading banks...</div>';
    fetch("data/banks.json").then(function (r) { return r.json(); }).then(function (d) {
      DATA = d; R = d.rules || {};
      render(document.getElementById("bsBody"));
    }).catch(function () {
      var b = document.getElementById("bsBody");
      if (b) b.innerHTML = "data load nahi hua - thodi der baad try karo";
    });
  }

  function mount() {
    var sec = document.querySelector("section#screener");
    if (!sec || document.getElementById("mbBank")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbBank"; c.style.marginTop = "14px";
    var ref = document.getElementById("mbCircuits");
    var anchor = null;
    if (ref && ref.parentNode) {
      // circuit ke baad
      if (ref.nextSibling) anchor = ref.nextSibling; else { ref.parentNode.appendChild(c); anchor = null; }
    }
    if (anchor && anchor.parentNode) anchor.parentNode.insertBefore(c, anchor);
    else if (!ref) {
      var sc = document.getElementById("mbScoreCard") || sec.querySelector("h2");
      if (sc && sc.parentNode) sc.parentNode.insertBefore(c, sc); else sec.appendChild(c);
    }
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
