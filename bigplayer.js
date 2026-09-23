/* bigplayer.js - BIG PLAYER RADAR: Whale (bulk/block deals) • Shark (futures/options OI) • Pig (most active). #screener */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var D = null;
  var KC = { "LONG BUILDUP": ["#77f37b", "\uD83E\uDD88 LONG BUILDUP \u2014 shark buying"], "SHORT BUILDUP": ["#ff8b8b", "\uD83E\uDD88 SHORT BUILDUP \u2014 shark shorting"], "SHORT COVER": ["#f5c542", "SHORT COVER \u2014 short wapas khareed"], "LONG UNWIND": ["#f5c542", "LONG UNWIND \u2014 long nikal rahe"] };

  function cr(n) { return "\u20B9" + (n >= 1000 ? (n / 1000).toFixed(1) + "k Cr" : n + " Cr"); }

  function render(box) {
    var h = '<div class="note" style="margin-top:8px">' + esc(D.updated) + ' \u2014 bade players ki footprint (Manish podcast framework). <b>Ye sirf signals hain, pakka proof nahi</b> \u2014 operator chhup bhi sakta hai. Advice nahi.</div>';
    h += '<div style="margin-top:10px;font-size:13.5px;font-weight:700">\uD83D\uDC33 WHALE \u2014 Bulk/Block Deals aaj (kis ne kitna khareeda-becha)</div>';
    [["bulk", "Bulk deals"], ["block", "Block deals"]].forEach(function (sec) {
      var rows = D[sec[0]] || [];
      if (!rows.length) return;
      h += '<div style="font-size:11px;opacity:.6;margin-top:5px">' + sec[1] + ':</div>';
      rows.slice(0, 12).forEach(function (r) {
        h += '<details style="margin-top:4px"><summary style="cursor:pointer;display:flex;gap:8px;align-items:center;padding:7px 10px;border-radius:9px;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.12);font-size:13px;flex-wrap:wrap">' +
          '<b>' + esc(r.s) + '</b><span style="font-size:11.5px;opacity:.75">' + cr(r.t) + ' \u00b7 ' + r.d + ' deals</span>' +
          '<span style="margin-left:auto;font-size:10.5px;font-weight:700;color:' + (r.bv >= r.sv ? "#77f37b" : "#ff8b8b") + '">B ' + cr(r.bv) + ' / S ' + cr(r.sv) + '</span></summary>' +
          '<div style="padding:4px 12px 8px;font-size:11.5px;opacity:.8">' + (r.c || []).map(function (c) { return "\uD83D\uDCB4 " + esc(c); }).join("<br>") + '<div class="note" style="margin-top:4px;opacity:.55">client names NSE disclosure se \u2014 tap se hide</div></div></details>';
      });
    });
    h += '<div style="margin-top:12px;font-size:13.5px;font-weight:700">\uD83E\uDD88 SHARK \u2014 Futures OI Buildup (bada OI + price = position bana rahe)</div>';
    (D.fut || []).slice(0, 15).forEach(function (r) {
      var k = KC[r.k] || KC["LONG UNWIND"];
      h += '<div style="display:flex;gap:8px;align-items:center;padding:6px 10px;margin-top:4px;border-radius:9px;background:rgba(255,255,255,.04);border:1px solid ' + k[0] + '33;font-size:13px;flex-wrap:wrap">' +
        '<b>' + esc(r.s) + '</b><span style="font-size:10.5px;font-weight:700;color:' + k[0] + '">' + r.k + '</span>' +
        '<span style="margin-left:auto;font-size:11px;opacity:.75">OI ' + (r.coi > 0 ? "+" : "") + (Math.abs(r.coi) / 100000).toFixed(1) + 'L \u00b7 ' + cr(r.v) + '</span>' +
        '<span style="font-size:11px;color:' + (r.p >= 0 ? "#77f37b" : "#ff8b8b") + '">' + (r.p > 0 ? "+" : "") + esc(r.p) + '%</span></div>';
    });
    if ((D.idxfut || []).length) {
      h += '<div style="font-size:11px;opacity:.6;margin-top:6px">Index futures:</div>';
      D.idxfut.slice(0, 4).forEach(function (r) {
        var k = KC[r.k] || KC["LONG UNWIND"];
        h += '<div style="display:flex;gap:8px;align-items:center;padding:5px 10px;margin-top:3px;border-radius:8px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);font-size:12px">' +
          '<b>' + esc(r.s) + '</b><span style="font-size:10px;font-weight:700;color:' + k[0] + '">' + r.k + '</span>' +
          '<span style="margin-left:auto;font-size:10.5px;opacity:.75">OI ' + (r.coi > 0 ? "+" : "") + (Math.abs(r.coi) / 100000).toFixed(1) + 'L</span>' +
          '<span style="font-size:10.5px;color:' + (r.p >= 0 ? "#77f37b" : "#ff8b8b") + '">' + (r.p > 0 ? "+" : "") + esc(r.p) + '%</span></div>';
      });
    }
    h += '<div style="margin-top:12px;font-size:13.5px;font-weight:700">\uD83E\uDCA1 OPTIONS \u2014 sabse bada OI change (kis strike pe paisa aa raha)</div>';
    (D.opts || []).forEach(function (r) {
      h += '<div style="display:flex;gap:8px;align-items:center;padding:5px 10px;margin-top:3px;border-radius:8px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.08);font-size:12px">' +
        '<b>' + esc(r.s) + '</b><span style="opacity:.7">' + esc(r.e) + ' \u00b7 ' + esc(r.k) + '</span>' +
        '<b style="color:' + (r.t === "CE" ? "#77f37b" : "#ff8b8b") + '">' + esc(r.t) + '</b>' +
        '<span style="margin-left:auto;font-size:10.5px;opacity:.75">OI ' + (r.coi > 0 ? "+" : "") + (Math.abs(r.coi) / 100000).toFixed(1) + 'L</span></div>';
    });
    if ((D.active || []).length) {
      h += '<div style="margin-top:12px;font-size:13.5px;font-weight:700">\uD83D\uDC37 PIG ZONE \u2014 aaj sabse zyada kheli gayi stocks (bheed yahan khelti hai)</div>';
      h += '<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px">';
      D.active.forEach(function (a) {
        h += '<span style="font-size:11.5px;padding:4px 8px;border-radius:8px;background:rgba(245,197,66,.08);border:1px solid rgba(245,197,66,.3)"><b>' + esc(a[0]) + '</b> \u20B9' + esc(a[1]) + 'Cr</span>';
      });
      h += '</div><div class="note" style="margin-top:4px;font-size:10.5px;opacity:.55">"Pigs get slaughtered" \u2014 yahan entry bhaag-daud me hoti hai, SL pakka rakhna</div>';
    }
    box.innerHTML = h;
  }

  function build(card) {
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(240,180,41,.13);border:1px solid rgba(240,180,41,.5);font-size:14.5px;text-align:center"><b style="color:rgba(240,180,41,.95)">\uD83D\uDC33 BIG PLAYER RADAR</b> <span style="font-size:11px;opacity:.65">Whale \u00b7 Shark \u00b7 Pig \u2014 aaj ki badi moves</span></summary>' +
      '<div id="bpBody" class="note" style="margin-top:8px">loading radar...</div>';
    fetch("data/bigplayer.json").then(function (r) { return r.json(); }).then(function (d) {
      D = d; render(document.getElementById("bpBody"));
    }).catch(function () {
      var b = document.getElementById("bpBody");
      if (b) b.innerHTML = "data load nahi hua \u2014 thodi der baad try karo";
    });
  }

  function mount() {
    var sec = document.querySelector("section#screener");
    if (!sec || document.getElementById("mbBP")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbBP"; c.style.marginTop = "14px";
    var anchor = document.getElementById("mbStage");
    if (anchor && anchor.nextSibling) anchor.parentNode.insertBefore(c, anchor.nextSibling);
    else if (anchor) anchor.parentNode.appendChild(c);
    else {
      var sc = document.getElementById("mbScoreCard");
      if (sc && sc.parentNode) sc.parentNode.insertBefore(c, sc); else sec.appendChild(c);
    }
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
