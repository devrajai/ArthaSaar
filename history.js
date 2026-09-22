/* history.js - Muhurat Trading + Budget History + Market Astro cards. #tools mein mount */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }

  /* 1. MUHURAT TRADING */
  function buildMuhurat(card) {
    var hist = [["2024", "+0.42%"], ["2023", "+0.55%"], ["2022", "+0.88%"], ["2021", "+0.49%"], ["2020", "+0.45%"], ["2019", "+0.49%"], ["2018", "+0.70%"], ["2017", "-0.60%"], ["2016", "-0.04%"], ["2015", "+0.48%"]];
    var now = new Date();
    var mu = new Date(2026, 10, 8); // 8 Nov 2026 Diwali
    var daysTo = Math.ceil((mu - now) / 86400000);
    var h = '<div class="note" style="margin-top:8px;background:rgba(255,165,0,.12);border:1px solid rgba(255,165,0,.35);border-radius:8px;padding:10px">' +
      '<b style="color:#ffb84d">Muhurat Trading 2026: Sun, 8 Nov</b> (Diwali Laxmi Pujan, shaam ki special session - time NSE circular se aayega)' +
      (daysTo > 0 && daysTo < 120 ? '<br><b>' + daysTo + ' din baade hain</b>' : '') + '</div>';
    h += '<div class="note" style="margin-top:10px"><b>Sensex ka muhurat scorecard (2015-2024):</b> 10 me se <b style="color:#77f37b">8 baar GREEN</b> - average +0.39%</div>';
    hist.forEach(function (r0) {
      h += '<div class="note" style="display:flex;justify-content:space-between"><span>' + r0[0] + '</span><span style="color:' + (r0[1].indexOf("-") < 0 ? "#77f37b" : "#ff8b8b") + '">' + r0[1] + '</span></div>';
    });
    h += '<div class="note" style="margin-top:10px"><b>Rules:</b> delivery buying shubh mani jati hai (F&O gambling nahi), chhoti qty se naya saal shuru karo, family ke saath - paisa nahi sanskar. Source: exchange reports.</div>';
    card.innerHTML = '<div class="subhead">Muhurat Trading (Diwali special session)</div>' + h;
  }

  /* 2. BUDGET HISTORY */
  function buildBudget(card) {
    var rows = [
      ["Feb 2025", "+0.01%", "No tax till 12L income - consumption boost, capex 11.21L cr, FD target 4.4%"],
      ["Jul 2024", "-0.09%", "LTCG 10% to 12.5%, STCG 15% to 20%, STT options 0.1% - din me 1200 pt girr"],
      ["Feb 2024 (interim)", "-0.15%", "Capex 11.11L cr (3.4% GDP), angel tax khatam"],
      ["Feb 2023", "+0.27%", "Capex 10L cr, insurance tax changes - first mega capex budget"],
      ["Feb 2022", "+1.46%", "Capex 35% badha, digital rupee announce"],
      ["Feb 2021", "+5.0%", "BEST in 20 yrs - capex 34.5% jump, PSU bank recap"],
      ["Feb 2020", "-2.43%", "WORST - DDT khatam but corona panic start"],
      ["Jul 2019", "-0.98%", "FPI surcharge - market naraz"],
      ["Feb 2019", "+0.59%", "Interim, sarkar wapas aa rahi thi"]
    ];
    var h = '<div class="note" style="margin-top:8px"><b>Sensex budget-day reaction:</b> average ~+0.5% - budget day trend follow karne se zyada pre-budget positioning matter karti hai</div>';
    rows.forEach(function (r0) {
      h += '<div class="note"><b>' + r0[0] + '</b> <span style="color:' + (r0[1].indexOf("-") < 0 ? "#77f37b" : "#ff8b8b") + '">' + r0[1] + '</span><br><span style="opacity:.75;font-size:12px">' + esc(r0[2]) + '</span></div>';
    });
    h += '<div class="footer-note">Source: exchange data / financial press compilations</div>';
    card.innerHTML = '<div class="subhead">Union Budget History (market reaction)</div>' + h;
  }

  /* 3. MARKET ASTRO */
  function buildAstro(card) {
    var h = '<div class="note" style="margin-top:8px"><b>Shubh timing for SIP start:</b></div>' +
      '<div class="note">- <b>Panchak</b> me SIP mat start karo (Panchak card mein live dates hain)<br>' +
      '- Amavasya se bache<br>- <b>Purnima, Ekadashi, Guru Pushya</b> acche din maane jaate hain<br>- Akshaya Tritiya / Diwali / New Year - traditional shubh investment days</div>' +
      '<div class="note" style="margin-top:10px"><b>Planetary cycles (fun fact):</b></div>' +
      '<div class="note">Jupiter (Guru) 1 saal me 1 rashi mein rehta hai - traditional belief: Jupiter banks/finance me aane par banking sector me bull run aata hai. Saturn (Shani) ka 2.5 saal ka cycle - bear phase ke liye famous hai.</div>' +
      '<div class="note" style="margin-top:10px"><b>Weekly days:</b><br>- Monday (Som) - Moon ka din, volatility<br>- Thursday (Guru) - Jupiter ka din - shubh maana jata hai<br>- Saturday (Shani) - choppy / sideways</div>' +
      '<div class="footer-note">Ye traditional beliefs hain, trading decisions ka basis nahi - sirf shaukeen ke liye</div>';
    card.innerHTML = '<div class="subhead">Market Astro (Shubh Muhurat + Planetary Cycles)</div>' + h;
  }

  function mount() {
    var sec = document.querySelector("section#tools");
    if (!sec || document.getElementById("mbMuhurat")) return;
    [["mbMuhurat", buildMuhurat], ["mbBudget", buildBudget], ["mbAstro", buildAstro]].forEach(function (d0) {
      var c = document.createElement("div");
      c.className = "card"; c.id = d0[0]; c.style.marginTop = "14px";
      sec.appendChild(c);
      try { d0[1](c); } catch (e) { c.innerHTML = '<div class="subhead">' + d0[0] + '</div>'; }
    });
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
