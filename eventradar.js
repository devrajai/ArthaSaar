/* eventradar.js v1 -- Events section ke top pe "Market Open-Close Radar" card.
   GTI zone card jaisa: har row = market session, right side live status.
   - NSE pre-open/live/post, GIFT Nifty, Europe, US, MCX, Crypto
   - LIVE sessions green + band hone ka countdown
   - closed = khulne ka countdown (weekend + midnight cross handled)
   - US/Europe ka DST (summer/winter) auto detect
   Times sab IST me. Har 30 sec refresh. */
(function () {
  "use strict";

  function p2(n) { return (n < 10 ? "0" : "") + n; }

  /* US/Europe DST approx: March ka 2nd Sunday -> Nov ka 1st Sunday */
  function isDST(d) {
    var y = d.getFullYear(), m = d.getMonth(), day = d.getDate();
    if (m < 2 || m > 10) return false;
    if (m > 2 && m < 10) return true;
    if (m === 2) {
      var dow = new Date(y, 2, 1).getDay();
      return day >= 1 + ((7 - dow) % 7) + 7;
    }
    var dowN = new Date(y, 10, 1).getDay();
    return day < 1 + ((7 - dowN) % 7);
  }

  /* [name, startMin, endMin, note] -- minutes of day IST; end > 1440 = raat cross */
  function sessions(now) {
    var dst = isDST(now);
    return [
      ["NSE PRE-OPEN", 540, 555, "bidding window"],
      ["NSE LIVE", 555, 930, "India equity"],
      ["NSE POST", 940, 960, "closing collection"],
      ["GIFT NIFTY", 405, 945, "Singapore Nifty"],
      ["EUROPE (DAX/FTSE)", dst ? 750 : 810, dst ? 1260 : 1320, "Frankfurt/London"],
      ["US (DOW/NASDAQ)", dst ? 1140 : 1200, dst ? 1530 : 1590, "America"],
      ["MCX COMMODITY", 540, 1410, "gold \u00b7 silver \u00b7 crude"],
      ["CRYPTO", 0, 1440, "24x7 \u00b7 hamesha open"]
    ];
  }

  function fmtT(min) {
    min = ((min % 1440) + 1440) % 1440;
    return p2(Math.floor(min / 60)) + ":" + p2(min % 60);
  }

  function fmtDur(ms) {
    var m = Math.round(ms / 60000);
    if (m < 1) return "abhi";
    var h = Math.floor(m / 60), mm = m % 60;
    if (h === 0) return mm + "m";
    return h + "h " + mm + "m";
  }

  function nextDayLabel(d) {
    return ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"][d.getDay()];
  }

  function prevDayWeekday(d) {
    var pd = new Date(d.getTime() - 86400000);
    var w = pd.getDay();
    return w !== 0 && w !== 6;
  }

  function nextStart(now, startMin) {
    var d = new Date(now);
    d.setHours(Math.floor(startMin / 60), startMin % 60, 0, 0);
    var tries = 0;
    while (d <= now && tries < 9) { d.setDate(d.getDate() + 1); tries++; }
    while (d.getDay() === 0 || d.getDay() === 6) { d.setDate(d.getDate() + 1); }
    return d;
  }

  function draw() {
    var box = document.getElementById("evRadarBox");
    if (!box) return;
    var now = new Date();
    var nowMin = now.getHours() * 60 + now.getMinutes() + now.getSeconds() / 60;
    var dow = now.getDay();
    var isWk = dow !== 0 && dow !== 6;
    var h = "";
    var indiaOpen = false;

    var S = sessions(now);
    for (var i = 0; i < S.length; i++) {
      var nm = S[i][0], s0 = S[i][1], s1 = S[i][2], note = S[i][3];
      var live;
      if (nm === "CRYPTO") live = true;
      else if ((isWk && nowMin >= s0 && nowMin < s1)) live = true;
      else if (s1 > 1440 && nowMin < s1 - 1440 && prevDayWeekday(now)) live = true; /* Friday raat wali US session */
      else live = false;
      if (nm === "NSE LIVE" && live) indiaOpen = true;

      var col = live ? "#77f37b" : "#8fa3c8";
      var right = "";
      var rng = fmtT(s0) + " - " + fmtT(s1);
      if (nm === "CRYPTO") {
        right = '<span style="color:#77f37b">OPEN</span>';
      } else if (live) {
        var endMs = (s1 - nowMin) * 60000;
        right = '<b style="color:#77f37b">LIVE</b> \u00b7 band ' + fmtDur(endMs) + " me";
      } else {
        var ns = nextStart(now, s0);
        var opens = fmtDur(ns - now);
        if (ns.getDate() !== now.getDate() || ns.getMonth() !== now.getMonth())
          opens = nextDayLabel(ns) + " " + opens;
        right = '<span style="opacity:.75">khulega ' + opens + " me</span>";
      }
      h += '<div class="note" style="display:flex;justify-content:space-between;gap:8px">' +
        '<span><b style="color:' + col + '">' + nm + '</b> ' + rng +
        (note ? ' <span style="opacity:.5">\u00b7 ' + note + "</span>" : "") + "</span>" +
        '<span style="white-space:nowrap;font-family:var(--mono,monospace);font-size:10.5px">' + right + "</span></div>";
    }

    var badge = indiaOpen
      ? '<div class="note" style="background:rgba(119,243,123,.12);border:1px solid rgba(119,243,123,.35);border-radius:8px;padding:8px;margin-bottom:8px"><b style="color:#77f37b">INDIA MARKET LIVE</b> \u2014 15:30 pe band</div>'
      : '<div class="note" style="background:rgba(255,139,139,.1);border:1px solid rgba(255,139,139,.3);border-radius:8px;padding:8px;margin-bottom:8px"><b style="color:#ff8b8b">INDIA MARKET CLOSED</b> \u2014 ' + nextOpenTxt(now, isWk) + "</div>";
    box.innerHTML = badge + h;
  }

  function nextOpenTxt(now, isWk) {
    if (!isWk) return "Monday 09:15 pe khulega";
    return "khulega " + fmtDur(nextStart(now, 555) - now) + " me";
  }

  function mount() {
    var sec = document.getElementById("events");
    if (!sec) return;
    if (document.getElementById("evRadarCard")) { draw(); return; }
    var chips = sec.querySelector("#evChips");
    var card = document.createElement("div");
    card.className = "card";
    card.id = "evRadarCard";
    card.innerHTML =
      '<div class="subhead">MARKET OPEN-CLOSE RADAR \u2014 aaj ke sessions</div>' +
      '<div id="evRadarBox"></div>' +
      '<div class="footer-note" style="margin-top:6px">sab times IST \u00b7 sat-sun India band \u00b7 US/Europe ka summer-winter shift auto</div>';
    if (chips && chips.parentNode === sec) sec.insertBefore(card, chips);
    else sec.appendChild(card);
    draw();
    setInterval(draw, 30000);
  }

  var tries = 0;
  var t = setInterval(function () {
    tries++;
    if (document.getElementById("events")) { clearInterval(t); mount(); }
    if (tries > 120) clearInterval(t);
  }, 500);
})();