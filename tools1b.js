/* tools1b.js — Trade Tools part 2: shared notes-table engine */
(function () {
  mbTool.drawNoteCard = function (opts) {
    var a = mbTool.nload(opts.key);
    var bysym = window.__mbBySym || {};
    var rows = a.map(function (n, i) {
      var s = bysym[n.sym] || {}, cur = s.price != null ? s.price : null;
      var dist = cur && n.lvl ? (cur - n.lvl) / n.lvl * 100 : null;
      return '<tr><td class="sym"><a href="#company/' + esc(n.sym) + '">' + esc(n.sym) + '</a></td>' +
        '<td>' + esc(n.type || "") + '</td><td>' + nf2(n.lvl) + '</td>' +
        '<td>' + (cur != null ? nf2(cur) : "—") + '</td>' +
        '<td class="' + pctCls(dist) + '">' + (dist != null ? sign(dist) : "—") + '</td>' +
        '<td>' + (n.qty ? n.qty : "—") + '</td><td>' + esc(n.note || "") + '</td>' +
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
  };
})();
