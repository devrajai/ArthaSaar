/* tools.js — Trade Tools part 1: tile + section + router + storage */
(function () {
  var ai = document.querySelector('a.tile[href="#ai"]');
  if (ai) ai.insertAdjacentHTML("afterend",
    '<a class="tile" href="#tools"><span class="t-ic">🧮</span><span class="t-nm">Trade Tools</span><span class="t-sb">GTT · levels · scans</span></a>');
  var sec = document.createElement("section");
  sec.id = "tools"; sec.style.display = "none";
  sec.innerHTML = '<a class="backbtn" href="#home">⌂ Home</a><h2>Trade Tools</h2>' +
    '<div class="card" id="gttCard"></div>' +
    '<div class="card" id="trendCard"></div>' +
    '<div class="card" id="scanCard"></div>';
  var ft = document.querySelector("footer");
  if (ft) ft.parentNode.insertBefore(sec, ft); else document.body.appendChild(sec);

  window.showView = function (id) {
    var all = document.querySelectorAll("section[id]"), found = false;
    all.forEach(function (s) { var on = s.id === id; s.style.display = on ? "" : "none"; if (on) found = true; });
    if (!found) { all.forEach(function (s) { s.style.display = s.id === "home" ? "" : "none"; }); id = "home"; }
    if (id !== "home" && !loaded.has(id) && loaders[id]) {
      loaded.add(id);
      try { loaders[id](); } catch (err) { console.error(err); }
    }
    window.scrollTo(0, 0);
  };

  window.mbTool = {
    nload: function (k) { try { return JSON.parse(localStorage.getItem(k) || "[]"); } catch (e) { return []; } },
    nsave: function (k, x) { try { localStorage.setItem(k, JSON.stringify(x)); } catch (e) {} }
  };
})();
