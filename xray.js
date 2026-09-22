/* xray.js - Market X-Ray: evening auto-analysis card (like YouTube market-xray videos). #dash */
(function () {
  var COL = { g: "#77f37b", r: "#ff8b8b", n: "#9fb0c4" };
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }

  function build(card) {
    card.innerHTML = '<div class="subhead">Market X-Ray (Evening Analysis - auto 6 PM)</div>' +
      '<div id="xrBody" class="note" style="margin-top:8px">loading aaj ka x-ray...</div>';
    fetch("data/xray.json").then(function (r) { return r.json(); }).then(function (d) {
      var h = '<div style="font-size:16px;font-weight:600;margin:6px 0">' + esc(d.headline || "") + '</div>';
      (d.points || []).forEach(function (p) {
        var blood = p.blood ? '<div style="margin-top:6px;padding:7px 10px;border-radius:8px;border:1px dashed rgba(255,139,139,.55);background:rgba(255,139,139,.08);font-size:13px"><b style="color:#ff8b8b">Blood Bath Level: ' + p.blood + '</b> - ye break hua to giregi kharidar</div>' : "";
        h += '<div style="margin-top:9px;padding:8px 12px;border-radius:9px;background:rgba(255,255,255,.03);border-left:3px solid ' + (COL[p.c] || COL.n) + '">' +
          '<div style="font-size:11px;letter-spacing:.4px;opacity:.6">' + esc(p.h) + "</div>" +
          '<div style="font-size:13.5px;margin-top:3px;line-height:1.5">' + esc(p.t) + "</div>" + blood + "</div>";
      });
      h += '<div style="margin-top:12px;padding:10px 14px;border-radius:10px;background:' + (d.vc || "rgba(240,180,41,.1)") + '22;border:1px solid ' + (d.vc || "rgba(240,180,41,.5)") + ';font-size:14px;font-weight:600">' + esc(d.verdict || "") + "</div>";
      if (d.note) h += '<div class="note" style="margin-top:8px;font-size:11.5px;opacity:.55">' + esc(d.note) + "</div>";
      document.getElementById("xrBody").innerHTML = h;
    }).catch(function () {
      document.getElementById("xrBody").innerHTML = "x-ray data load nahi hua - thodi der baad try karo";
    });
  }

  function mount() {
    var t = document.querySelector("section#dash");
    if (!t || document.getElementById("mbXray")) return;
    var c = document.createElement("div");
    c.className = "card"; c.id = "mbXray"; c.style.marginTop = "14px";
    var ref = document.getElementById("mbMovement");
    if (ref && ref.nextSibling) t.insertBefore(c, ref.nextSibling); else t.appendChild(c);
    try { build(c); } catch (e) { c.innerHTML = '<div class="subhead">Market X-Ray</div><div class="note">error</div>'; }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
