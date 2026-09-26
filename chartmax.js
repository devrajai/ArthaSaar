/* chartmax.js — Chart Reading me "1D·MAX" (listing se full history) — bina bade
   download ke default 5y fast rehta hai; MAX toggle daily-XX fetch ko full-XX
   pe redirect karta hai (chartread ka code untouched). User request: "past all data". */
(function () {
  var ON = false;
  try { ON = window.sessionStorage.getItem("crmax") === "1"; } catch (e) { ON = false; }
  var RELRE = /releases\/download\/candles\/daily-/;
  var realFetch = window.fetch;
  if (typeof realFetch === "function") {
    window.fetch = function (u, o) {
      if (ON && typeof u === "string" && RELRE.test(u)) {
        var fu = u.replace("/daily-", "/full-");
        return realFetch.call(window, fu, o).catch(function () {
          return realFetch.call(window, u, o);
        });
      }
      return realFetch.call(window, u, o);
    };
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return "&#" + c.charCodeAt(0) + ";";
    });
  }

  function addToggle(ivs) {
    if (!ivs || document.getElementById("crMaxBtn")) return;
    var b = document.createElement("button");
    b.id = "crMaxBtn";
    b.className = "chip" + (ON ? " on" : "");
    b.setAttribute("data-crmax", "1");
    b.style.cssText = "border-style:dashed";
    b.textContent = ON ? "1D·MAX \u2713" : "1D·MAX";
    b.title = "listing se full history (thoda bada download)";
    ivs.appendChild(b);
  }

  function relabel() {
    /* 1D chip ka label + header patch jab MAX on ho */
    if (!ON) return;
    var chip = document.querySelector('[data-cr-iv="1d"]');
    if (chip && chip.textContent.indexOf("MAX") < 0) {
      chip.textContent = "1D·MAX";
    }
    var h = document.querySelector("#crPrice .subhead");
    if (h && h.textContent.indexOf("1D (5 saal)") >= 0) {
      h.textContent = h.textContent.replace("1D (5 saal)", "1D (listing se)");
    }
  }

  function mount() {
    var ivs = document.getElementById("crIvs");
    if (!ivs) return;
    addToggle(ivs);
    try {
      new MutationObserver(function () { addToggle(ivs); relabel(); })
        .observe(ivs, { childList: true, subtree: true });
    } catch (e) { /* observe fail ho to interval */ }
    setInterval(relabel, 700);
    document.addEventListener("click", function (e) {
      var t = e.target || e.srcElement;
      while (t && t !== document.body && !t.getAttribute) t = t.parentNode;
      if (!t || !t.getAttribute) return;
      if (t.getAttribute("data-crmax")) {
        try {
          if (ON) { window.sessionStorage.removeItem("crmax"); }
          else { window.sessionStorage.setItem("crmax", "1"); }
        } catch (e2) {}
        window.location.reload();
      }
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else { mount(); }
})();
