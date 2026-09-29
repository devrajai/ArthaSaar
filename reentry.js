/* reentry.js — purane terminal ke poore features, naye look website ke andar.
   Kya karta hai: naye UI me ek full-screen "TERMINAL" view add karta hai jisme
   index-old.html (poora purana app) load hota hai — Trading Tools, Chart Reading,
   ICT, Watchlist+Journal, Smart Brain, Calculators, Market X-Ray, Learn/Arthabodh,
   GTI zones... sab wapas.
   - Hash routing: #t/<old-section>  (jaise #t/tools, #t/chartread, #t/journal)
   - Theme sync: naya as-theme -> purana as-theme5 (same a-e letters, har kholne par)
   - Gate: terminal pehle kholne par purana password poochega, 6 ghante yaad rakhta hai
   - Home pe tile-grid + More menu me poora TERMINAL group bhi add hota hai
   Naya UI ka apna code/khud ka data bilkul untouched rehta hai. */
(function () {
  "use strict";
  if (window.__AS_REENTRY) return;
  window.__AS_REENTRY = 1;

  var MAP = [
    ["home", "Full Terminal", "poora purana terminal — saare features"],
    ["dash", "Market X-Ray", "pre-open · movers · F&O radar · stress"],
    ["tools", "Trading Tools", "GTT · power pack · tax · peers · notes"],
    ["chartread", "Chart Reading", "candles · patterns · indicators · pivots"],
    ["gti", "GTI + ICT", "zones · option OI · ICT terminal"],
    ["journal", "Watchlist + Journal", "watchlist · trades · R-multiple stats"],
    ["calc", "Calculators", "position size · R:R · SIP · EMI · charges"],
    ["smart", "Smart Brain", "kal ka guess · confluence · radars"],
    ["arthabodh", "Learn · Studies · Notes", "course · strategies · heatmap · notes"]
  ];
  var HOME_TILES = [
    ["tools", "Trading Tools", "GTT · power pack · tax · peers"],
    ["chartread", "Chart Reading", "candles · patterns · pivots"],
    ["journal", "Watchlist · Journal", "trades · R-stats"],
    ["smart", "Smart Brain", "guess · confluence"],
    ["calc", "Calculators", "size · R:R · SIP · EMI"],
    ["home", "Full Terminal", "saare purane features"]
  ];

  var term = null, frame = null, lastTarget = "home", booted = false;

  function syncTheme() {
    try { localStorage.setItem("as-theme5", localStorage.getItem("as-theme") || "a"); } catch (e) {}
  }

  function tryNav(w, t) {
    if (!w) return;
    try { w.location.hash = "#" + t; } catch (e) {}
    if (w.showView) { try { w.showView(t.indexOf("/") === -1 ? t : t.split("/")[0]); } catch (e) {} }
  }

  function navInside(t) {
    lastTarget = t = t || "home";
    if (!frame) return;
    var w = null;
    try { w = frame.contentWindow; } catch (e) {}
    tryNav(w, t);
    /* late-mount sections (journal/calc/etc app.js ke modules bad me lagate hain) — ek retry */
    setTimeout(function () {
      try { tryNav(frame.contentWindow, t); } catch (e) {}
    }, 1500);
  }

  function buildTerm() {
    if (term) return;
    var host = document.querySelector("main") || document.body;
    term = document.createElement("section");
    term.className = "view";
    term.id = "v-terminal";
    term.innerHTML =
      '<div id="asTB">' +
      '<button id="asBack" type="button">← BACK</button>' +
      '<b>AS · TERMINAL</b>' +
      '<span class="asSub" id="asTitle">poore purane features</span>' +
      '<span class="asSp"></span>' +
      '<a id="asOpen" href="index-old.html" target="_blank" rel="noopener">OPEN ↗</a>' +
      '</div>' +
      '<iframe id="asFrame" title="ArthaSaar Terminal"></iframe>';
    host.appendChild(term);
    frame = term.querySelector("#asFrame");
    term.querySelector("#asBack").addEventListener("click", function () { location.hash = "#home"; });
    frame.addEventListener("load", function () { booted = true; navInside(lastTarget); });
  }

  function showTerm(target) {
    buildTerm();
    document.querySelectorAll(".view").forEach(function (v) { v.classList.toggle("on", v.id === "v-terminal"); });
    var b;
    ["dHome", "dLearn", "dPort"].forEach(function (id) { b = document.getElementById(id); if (b) b.classList.remove("on"); });
    b = document.getElementById("dGrid"); if (b) b.classList.add("on");
    document.querySelectorAll(".nav button").forEach(function (n) { n.classList.remove("active"); });
    var m = null;
    for (var i = 0; i < MAP.length; i++) if (MAP[i][0] === target) m = MAP[i];
    var ttl = document.getElementById("asTitle");
    if (ttl) ttl.textContent = m ? m[2] : target;
    window.scrollTo(0, 0);
    syncTheme();
    if (!booted) frame.src = "index-old.html";
    else navInside(target);
  }

  function myRoute() {
    var h = (location.hash || "").replace(/^#/, "");
    if (h === "terminal") { history.replaceState(null, "", "#t/home"); showTerm("home"); return; }
    if (h.indexOf("t/") === 0) showTerm(h.slice(2) || "home");
  }

  function buildMenu() {
    var sheet = document.querySelector("#moreOv .sheet");
    if (!sheet || sheet.querySelector(".asTermGroup")) return;
    var g = document.createElement("div");
    g.className = "asTermGroup";
    g.innerHTML =
      '<div class="ovh" style="border-top:1px solid var(--border)"><span>TERMINAL · PURANE FEATURES</span></div><div class="mlist"></div>';
    var box = g.querySelector(".mlist"), h = "";
    MAP.forEach(function (x) { h += '<button class="mli" data-t="' + x[0] + '"><b>' + x[1] + '</b><small>' + x[2] + '</small></button>'; });
    box.innerHTML = h;
    sheet.appendChild(g);
    var ov = document.getElementById("moreOv");
    box.addEventListener("click", function (e) {
      var t = e.target && e.target.closest ? e.target.closest("[data-t]") : null;
      if (!t) return;
      if (ov) ov.classList.remove("open");
      location.hash = "#t/" + t.getAttribute("data-t");
    });
  }

  function buildHome() {
    var home = document.getElementById("v-home");
    if (!home || home.querySelector(".asTermHome")) return;
    var sect = document.createElement("div");
    sect.className = "sect asTermHome";
    sect.textContent = "TERMINAL — PURANE FEATURES · FULL";
    var g = document.createElement("div");
    g.className = "grid3";
    g.style.marginTop = "2px";
    var h = "";
    HOME_TILES.forEach(function (p) {
      h += '<a class="card asTile" href="#t/' + p[0] + '" style="text-decoration:none;color:inherit">' +
           '<div class="sh2">' + p[1] + '</div>' +
           '<div style="padding:10px 14px;font:500 10.5px var(--mono);color:var(--dim)">' + p[2] + '</div></a>';
    });
    g.innerHTML = h;
    home.appendChild(sect);
    home.appendChild(g);
  }

  function css() {
    var st = document.createElement("style");
    st.textContent =
      "#v-terminal.on{display:flex;flex-direction:column;position:fixed;inset:0;z-index:70;max-width:none;margin:0}" +
      "#asTB{display:flex;align-items:center;gap:10px;padding:10px 12px;border-bottom:var(--bw,1px) solid var(--border);background:var(--surface);flex:0 0 auto}" +
      "#asTB b{font:600 11px var(--mono);letter-spacing:.12em;color:var(--text)}" +
      "#asTB .asSub{font:500 10px var(--mono);color:var(--dim);letter-spacing:.02em}" +
      "#asTB .asSp{flex:1}" +
      "#asTB button,#asTB a{font:600 10px var(--mono);letter-spacing:.08em;padding:6px 12px;border-radius:999px;border:var(--bw,1px) solid var(--border2);background:var(--surface2);color:var(--text);text-decoration:none;cursor:pointer}" +
      "#asTB button:hover,#asTB a:hover{border-color:var(--accent)}" +
      "#asFrame{flex:1 1 auto;width:100%;border:0;display:block;background:#070c17}" +
      ".asTile:hover{border-color:var(--accent)!important}";
    document.head.appendChild(st);
  }

  /* boot */
  css();
  buildHome();
  buildMenu();
  var tb = document.getElementById("themeBtn");
  if (tb) tb.addEventListener("click", function () {
    syncTheme();
    if (term && term.classList.contains("on")) { booted = false; frame.src = "index-old.html"; }
  });
  addEventListener("hashchange", myRoute);
  myRoute();
})();
