/* gti.js - GTI Zones card (Manish ka Ghost Trade Indicator math) - dedicated #gti section */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var DATA = null;
  function zoneRow(name, z, price) {
    if (!z) return "";
    var mid = Math.round((z[0] + z[1]) / 2);
    var d = price ? ((price - mid) / mid * 100).toFixed(1) : "";
    var col = name === "SD" || name === "WD" ? "#77f37b" : "#ff8b8b";
    return '<div class="note" style="display:flex;justify-content:space-between"><span style="color:' + col + '"><b>' + name + '</b> ' + esc(z[0]) + " - " + esc(z[1]) + '</span><span style="opacity:.7">' + d + "%</span></div>";
  }
  function symCard(sname) {
    var s = DATA.symbols[sname];
    var host = document.getElementById("gtiSymBox");
    if (!s) { host.innerHTML = '<div class="note">symbol nahi mila (36 me se hi hoga)</div>'; return; }
    var h = '<div class="note" style="margin-bottom:6px"><b style="font-size:15px">' + esc(sname) + '</b> - Rs ' + esc(s.price) +
      (s.nearest ? ' <span style="opacity:.75">(sabse paas: ' + esc(s.nearest[0]) + ", " + esc(s.nearest[1]) + "%)</span>" : "") + "</div>";
    if (s.day_zones) {
      h += '<div class="note" style="margin-top:6px"><b>Daily zones</b> (open ' + esc(s.day_open) + ' · POC ' + esc(s.day_poc) + ")</div>";
      var order = ["SD", "WD", "WS", "SS"];
      for (var i = 0; i < order.length; i++) h += zoneRow(order[i], s.day_zones[order[i]], s.price);
    }
    if (s.week_zones) {
      h += '<div class="note" style="margin-top:8px"><b>Weekly zones</b> (open ' + esc(s.week_open) + ' · POC ' + esc(s.week_poc) + ")</div>";
      for (var j = 0; j < order.length; j++) h += zoneRow(order[j], s.week_zones[order[j]], s.price);
    }
    if (s.compression && s.compression.compressed) {
      h += '<div class="note" style="margin-top:8px;background:rgba(255,165,0,.15);border:1px solid rgba(255,165,0,.4);border-radius:8px;padding:8px"><b style="color:#ffb84d">COMPRESSION</b> - day POC aur week POC bilkul paas hain. Zones kaam nahi karenge - levels par trade karo, blast expected (Nifty min 200-300 pts).</div>';
    }
    if (s.grid) {
      h += '<div class="note" style="margin-top:6px">300-pt grid: <b>' + esc(s.grid.level) + "</b> (" + esc(s.grid.dist_pct) + "% door) - bade players ka level</div>";
    }
    if (s.gann) {
      h += '<div class="note" style="margin-top:6px"><b>Gann/Fib levels</b> (aaj ka H ' + esc(s.gann.day_h) + " / L " + esc(s.gann.day_l) + "): 50% = <b>" + esc(s.gann.p50) + "</b> | 38.2% = " + esc(s.gann.fib382) + " | 61.8% = " + esc(s.gann.fib618) + "</div>";
    }
    h += '<div class="footer-note">SD/WD = demand (neeche support) · WS/SS = supply (upar resistance) · GTI: Manish ka zone math</div>';
    host.innerHTML = h;
  }
  function render() {
    var box = document.getElementById("gtiCard");
    if (!box) return;
    box.innerHTML =
      '<div class="subhead">GTI Zones - Manish ka Ghost Trade Indicator (36 symbols)</div>' +
      '<div class="note" style="margin:8px 0 4px">NIFTY 50 & BANKNIFTY ke live zones:</div>' +
      '<div id="gtiSymBox"></div>' +
      '<input id="gtiQ" placeholder="stock likho - RELIANCE, TCS, SBIN..." style="width:100%;box-sizing:border-box;padding:10px 12px;border-radius:10px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.05);color:inherit;font-size:14px;margin-top:8px">' +
      "        <div class=\"footer-note\" style=\"margin-top:6px\">SD/WD/WS/SS/POC matlab:</div>" +
        '<div class="note" style="font-size:12px;line-height:1.7">' +
        '<b style="color:#77f37b">SD</b> = Strong Demand (sabse neeche, tagda support - yahan se uthna best entry) · ' +
        '<b style="color:#77f37b">WD</b> = Weak Demand (halke wala support) · ' +
        '<b style="color:#ff8b8b">WS</b> = Weak Supply (halka resistance) · ' +
        '<b style="color:#ff8b8b">SS</b> = Strong Supply (sabse upar, tagda resistance) · ' +
        '<b style="color:#1E90FF">POC</b> = Point of Control (jahan sabse zyada business hua - magnet level, price wapas aana chahta hai). Manish ka rule: buying zone mein sirf BUY, selling zone mein sirf SELL, target = opposite zone.' +
        "</div>" +
      '<div class="footer-note">zones roz shaam update - Manish ka GTI math (podcast-verified)</div>';
    symCard("NIFTY 50");
    var q = document.getElementById("gtiQ");
    q.addEventListener("change", function () { symCard(q.value.trim().toUpperCase()); });
  }
  function mount() {
    var sec = document.querySelector("#gtiMount") || document.querySelector("section#global");
    if (!sec || document.getElementById("gtiCard")) return;
    var card = document.createElement("div");
    card.className = "card"; card.id = "gtiCard";
    card.innerHTML = '<div class="subhead">GTI Zones</div><div class="note">load ho raha hai...</div>';
    sec.appendChild(card);
    fetch("data/gti.json?t=" + Date.now()).then(function (r) { return r.json(); }).then(function (d) { DATA = d; render(); })
      .catch(function () {
        var b = document.getElementById("gtiCard");
        if (b) b.innerHTML = '<div class="subhead">GTI Zones</div><div class="note">data abhi nahi mila.</div>';
      });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
