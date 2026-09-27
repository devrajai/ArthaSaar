/* rangefc.js v1 -- "Kal ka range" card (chart reading section ke andar).
   data/rangeforecast.json: kal ka projected range (close +/- ATR14) +
   30-din ka accuracy history. honest math, koi AI nahi. */
(function () {
  "use strict";
  var UP = "#34d399", DN = "#ff8b8b";

  function esc(s) {
    if (s == null) s = "";
    return String(s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; });
  }
  function n2(x) { return isFinite(x) ? Number(x).toLocaleString("en-IN", { maximumFractionDigits: 2 }) : "--"; }

  function render(d) {
    var host = document.getElementById("crFC");
    if (!host) return;
    var fc = d.fc || [];
    var hist = d.hist || [];
    if (!fc.length) {
      host.innerHTML = '<div class="note">forecast data abhi nahi mila \u2014 shaam ko archive update ke baad aayega.</div>';
      return;
    }
    var h = "";
    h += '<div class="note" style="opacity:.75;margin-bottom:8px">' + esc(d.note || "") + ' \u00b7 updated ' + esc(d.updated || "") + '</div>';
    for (var i = 0; i < fc.length; i++) {
      var x = fc[i];
      h += '<div class="note" style="display:flex;justify-content:space-between;gap:8px;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.06)">' +
        '<b style="font-size:12.5px">' + esc(x.s) + '</b>' +
        '<span style="font-family:var(--mono);font-size:12.5px">' + n2(x.lo) +
        ' \u2013 <b style="color:' + UP + '">' + n2(x.hi) + '</b>' +
        ' <span style="opacity:.65">(' + n2(x.c) + ' \u00b1 ' + n2(x.atr) + ')</span></span></div>';
    }
    if (hist.length) {
      var hits = 0, of = 0;
      for (var j = 0; j < hist.length; j++) { hits += hist[j].h; of += hist[j].n; }
      h += '<div style="margin-top:10px" class="subhead">Accuracy \u2014 last ' + hist.length + ' din</div>';
      h += '<div class="note" style="display:flex;justify-content:space-between;margin:4px 0">' +
        '<span>actual high+low dono range ke andar:</span><b style="color:' + (of && hits / of >= 0.5 ? UP : "#d4af37") + '">' +
        (of ? (100 * hits / of).toFixed(0) : "--") + '% (' + hits + '/' + of + ')</b></div>';
      var last = hist.slice(-12), dots = "";
      for (var k = 0; k < last.length; k++) {
        dots += '<span title="' + esc(last[k].d) + '" style="display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:4px;background:' +
          (last[k].h >= last[k].n / 2 ? UP : DN) + ';opacity:.85"></span>';
      }
      h += '<div style="margin:6px 0">' + dots + '<span class="note" style="opacity:.6;font-size:11px"> \u00b7 green = us din projection me fit (last ' + last.length + ' din)</span></div>';
      h += '<div class="note" style="opacity:.65;margin-top:4px">ye 1-sigma type band hai \u2014 100% kabhi nahi hota. bahar jana = strong trend din.</div>';
    } else {
      h += '<div class="note" style="opacity:.65;margin-top:6px">accuracy kal se track hona shuru hoga (aaj ka forecast, kal check hoga).</div>';
    }
    host.innerHTML = h;
  }

  function load() {
    fetch("data/rangeforecast.json?t=" + Date.now())
      .then(function (r) { return r.json(); })
      .then(render)
      .catch(function () {
        var host = document.getElementById("crFC");
        if (host) host.innerHTML = '<div class="note">forecast abhi available nahi.</div>';
      });
  }

  /* card chartread section me daalna (crVP card ke baad) */
  function mount() {
    var sec = document.getElementById("chartread");
    if (!sec) { setTimeout(mount, 800); return; }
    if (!document.getElementById("crFC")) {
      var card = document.createElement("div");
      card.className = "card";
      card.innerHTML = '<div class="subhead">Kal ka range \u2014 honest math (ATR14)</div><div id="crFC"></div>';
      var vp = sec.querySelector("#crVP");
      if (vp && vp.parentNode) vp.parentNode.insertBefore(card, vp.nextSibling);
      else sec.appendChild(card);
    }
    load();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();