/* tools.js — Trade Tools section part 1: skeleton + router + notes engine */
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
    nsave: function (k, x) { try { localStorage.setItem(k, JSON.stringify(x)); } catch (e) {} },
    drawNoteCard: function (opts) {
      var a = mbTool.nload(opts.key);
      var bysym = window.__mbBySym || {};
      var rows = a.map(function (n, i) {
        var s = bysym[n.sym] || {}, cur = s.price != null ? s.price : null;
        var dist = cur && n.lvl ? (cur - n.lvl) / n.lvl * 100 : null;
        return '<tr><td class="sym"><a href="#company/' + esc(n.sym) + '">' + esc(n.sym) + '</a></td>' +
          '<td>' + esc(n.type || "") + '</td><td>' + nf2(n.lvl) + '</td>' +
          '<td>' + (cur != null ? nf2(cur) : "—") + '</td>' +
          '<td class="' + pctCls(dist) + '">' + (dist != null ? sign(dist) : "—") + '</td>' +
          '<td>' + (n.qty > n.qty : "—") + '</td><td>' + esc(n.note || "") + '</td>' +
          '<td><button class="chip" data-nd="' + i + '" style="padding:2px 8px">✕</button></td></tr>';
      }).join("") || '<tr><td colspan="8" class="loading">' + opts.empty + '</td></tr>';
      $(opts.card).innerHTML = '<div class="subhead">' + opts.head + '</div>' +
        '<div class="controls">' +
        '<input id="' + opts.id + 'S" placeholder="' + opts.symPh + '">' +
        '<select id="' + opts.id + 'T">' + opts.types.map(function (t) { return '<option>' + t + '</option>'; }).join("") + '</select>' +
        '<input id="' + opts.id + 'L" type="number" placeholder="level ₹">' +
        '<input id="' + opts.id + 'Q" type="number" placeholder="qty (opt)">' +
        '<button class="chip" id="' + opts.id + 'A">+ Add</button></div>' +
        '<div class="controls"><input id="' + opts.id + 'N" placeholder="' + opts.notePh + '"></div>' +
        '<div class="tblwrap"><table><thead><tr><th>Symbol</th><th>Type</th><th>Level</th><th>Now</th><th>Dist%</th><th>Qty</th><th>Note</th><th></th></tr></thead><tbody>' +
        rows + '</tbody></table></div>' + opts.foot;
      $(opts.card).querySelectorAll("[data-nd]").forEach(function (b) {
        b.onclick = function () { var p = mbTool.nload(opts.key); p.splice(+b.getAttribute("data-nd"), 1); mbTool.nsave(opts.key, p); opts.draw(); };
      });
      $("#" + opts.id + "A").onclick = function () {
        var sym = $("#" + opts.id + "S").value.trim().toUpperCase(), lvl = parseFloat($("#" + opts.id + "L").value);
        if (!sym || !lvl) { $("#" + opts.id + "N").value = ""; $("#" + opts.id + "N").placeholder = "fill symbol and level first"; return; }
        var p = mbTool.nload(opts.key);
        p.push({sym: sym, lvl: lvl, type: $("#" + opts.id + "T").value, qty: parseFloat($("#" + opts.id + "Q").value) || 0, note: $("#" + opts.id + "N").value.trim()});
        mbTool.nsave(opts.key, p); opts.draw();
      };
    }
  };
})();
