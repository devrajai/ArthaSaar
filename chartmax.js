/* chartmax.js v3 — data layer + 1D·MAX toggle.
   GitHub Release assets pe CORS nahi hota (site "archive load nahi hua" dikha
   raha tha), isliye candle chunks ab arthasaar-data repo se jsDelivr CDN pe
   aate hain: https://cdn.jsdelivr.net/gh/devrajai/ArthaSaar@data/data/
   + MAX toggle: ON hone par daily-XX full-XX ho jaata hai (listing se history).
   + toggle ke baad reload par wapas Chart Reading pe hi aate hain (landing nahi). */
(function () {
  var CDN = "/api/data?ref=data&p=data/";
  var RELRE = /https:\/\/github\.com\/devrajai\/ArthaSaar\/releases\/download\/candles\//;
  var ON = false;
  try { ON = window.sessionStorage.getItem("crmax") === "1"; } catch (e) { ON = false; }

  var realFetch = window.fetch;
  if (typeof realFetch === "function") {
    window.fetch = function (u, o) {
      if (typeof u === "string" && RELRE.test(u)) {
        var fu = u.replace(RELRE, CDN);
        if (ON && fu.indexOf("/daily-") >= 0) { fu = fu.replace("/daily-", "/full-"); }
        return realFetch.call(window, fu, o);
      }
      return realFetch.call(window, u, o);
    };
  }

  function addToggle(ivs) {
    if (!ivs || document.getElementById("crMaxBtn")) return;
    var b = document.createElement("button");
    b.id = "crMaxBtn";
    b.className = "chip" + (ON ? " on" : "");
    b.setAttribute("data-crmax", "1");
    b.style.cssText = "border-style:dashed";
    b.textContent = ON ? "1D\u00b7MAX \u2713" : "1D\u00b7MAX";
    b.title = "listing se full history on/off (thoda bada download)";
    ivs.appendChild(b);
  }

  function relabel() {
    /* sirf header patch — chip ka label untouched (duplicate confusion nahi) */
    if (!ON) return;
    var h = document.querySelector("#crPrice .subhead");
    if (h && h.textContent.indexOf("1D (5 saal)") >= 0) {
      h.textContent = h.textContent.replace("1D (5 saal)", "1D (listing se)");
    }
  }

  /* toggle ke baad reload -> wapas chartread pe auto-return + 1D auto-load */
  function autoReturn() {
    var go = false;
    try { go = window.sessionStorage.getItem("crgo") === "1"; } catch (e) { go = false; }
    if (!go) return;
    try { window.sessionStorage.removeItem("crgo"); } catch (e) {}
    var tries = 0;
    var t = setInterval(function () {
      tries++;
      var sec = document.getElementById("chartread");
      if (sec && !document.querySelector("section.on") && location.hash.indexOf("chartread") < 0) {
        location.hash = "#chartread";
      }
      var chip = document.querySelector('[data-cr-iv="1d"]');
      if (chip) {
        clearInterval(t);
        chip.click();
        return;
      }
      if (tries > 40) clearInterval(t);
    }, 500);
  }

  function mount() {
    var ivs = document.getElementById("crIvs");
    if (!ivs) return;
    addToggle(ivs);
    try {
      new MutationObserver(function () { addToggle(ivs); relabel(); })
        .observe(ivs, { childList: true, subtree: true });
    } catch (e) {}
    setInterval(relabel, 700);
    document.addEventListener("click", function (e) {
      var t = e.target || e.srcElement;
      while (t && t !== document.body && !t.getAttribute) t = t.parentNode;
      if (!t || !t.getAttribute) return;
      if (t.getAttribute("data-crmax")) {
        try {
          if (ON) {
            window.sessionStorage.removeItem("crmax");
          } else {
            window.sessionStorage.setItem("crmax", "1");
            window.sessionStorage.setItem("crgo", "1");
          }
        } catch (e2) {}
        window.location.reload();
      }
    });
    autoReturn();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", mount);
  } else { mount(); }
})();
