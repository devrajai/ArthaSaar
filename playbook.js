/* playbook.js - EVENT PLAYBOOKS: War / AI Boom / Crash — sector impact maps (Learn section). */
(function () {
  var PLAY = [
    {
      t: "\u2694\uFE0F WAR PLAYBOOK", c: "#ff8b8b",
      body: [
        ["\uD83D\uDEE1\uFE0F Fayda uthane wale", "Defence (HAL, BEL, BDL, Mazagon) \u2014 order pipeline badhta hai \u00b7 Oil PSUs / ONGC-type upstream \u2014 crude spike me fayda \u00b7 Gold / Gold funds \u2014 safe-haven"],
        ["\uD83D\uDCA5 Nuksan wale", "Airlines / cement / margin wale cos \u2014 fuel mehnga \u00b7 Import-dependent (electronics) \u00b7 IT \u2014 sirf tab jab war global demand tod de"],
        ["\uD83D\uDD0D Kaise pakde signal", "Crude +10% gaya? \u2192 India ka CAD kharab, inflation up \u2192 RBI rate cut delay \u2192 market pressure. Pehle gold + defence chale, phir correction. Global Radar + Correlation Engine dekho \u2014 Nasdaq girega to NIFTY next day avg -0.2% (data-backed)"],
        ["\u26A0\uFE0F Sach", "War ke waqt pehle VIX, phir gold, phir defence chalti hai \u2014 lekin exact timing koi nahi jaanta. Satellite weight hi rakho."]
      ]
    },
    {
      t: "\uD83E\uDD16 AI BOOM PLAYBOOK", c: "#77f37b",
      body: [
        ["\uD83D\uDCC8 Direct fayda", "IT giants (TCS, INFY, HCLTech) \u2014 AI deals \u00b7 Data centers \u2014 land + power demand \u00b7 Power cos \u2014 AI ke data centers bijli kite hain"],
        ["\uD83D\uDCA1 2nd order soch", "Semiconductor supply chain \u00b7 Cooling/power infra \u00b7 Telecom fiber \u2014 AI ka data kahin to travel karta hai"],
        ["\u26A0\uFE0F Risk side", "AI bubble jaisa 2000-dotcom ban sakta hai \u2014 valuation pagal ho to Stage Detector dekho (Stage 4 me mat kharido). Entry 40-SMA 'dancing area' me, breakout confirmation ke saath (notebook rule)"],
        ["\uD83D\uDD0D Live tracking", "Nasdaq + Nifty IT correlation engine me dekho \u2014 AI sacha boom ho to Nifty IT, Nasdaq se strong dikhega. Fake boom me sirf Nasdaq chalega, India IT nahi."]
      ]
    },
    {
      t: "\uD83E\uDEE7 CRASH PLAYBOOK (2008 / 2020)", c: "#ffd54f",
      body: [
        ["\uD83D\uDCC9 2008 (Global Debt Crisis)", "NIFTY -60%, wapsi ~5 saal. Pehle subprime news, phir banks gaye. Signal: credit bhi tight + VIX 40+"],
        ["\uD83E\uDDA0 2020 (COVID Crash)", "NIFTY -38% sirf 6 hafte me, wapsi ~6 mahine (FII ne tez kharida). Signal: VIX 60+, sab ek saath gira \u2014 panic bottom aksar VIX peak ke paas"],
        ["\uD83D\uDCCC Tumhara escape plan", "1. Stress Meter >= 55 \u2192 position size 50% karo \u00b7 2. >= 75 \u2192 sirf quality stocks, trading band \u00b7 3. Recovery me Stage-2 stocks (40-SMA ke upar) pehle chalti hai \u2014 Stage Detector use karo"],
        ["\u26A0\uFE0F Sabse bada sach", "Crash ke baad sabse zyada paisa wahi banata hai jo crash me girta kharidta hai \u2014 lekin zaroorat ka paisa kabhi crash me mat rakho. Dividend/fundamental wale stocks hi 2008 me sabse pehle wapas aaye."]
      ]
    }
  ];
  function build(sec) {
    PLAY.forEach(function (p, i) {
      var d = document.createElement("details");
      d.className = "card";
      d.id = "mbPlay" + i;
      d.style.marginTop = "14px";
      d.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:' + p.c + '22;border:1px solid ' + p.c + ';font-size:14.5px;text-align:center;font-weight:700;color:' + p.c + '">' + p.t + '</summary>' +
        '<div class="note" style="margin-top:8px">' + p.body.map(function (r) {
          return "<div style='margin-top:8px'><b style='font-size:12px'>" + r[0] + "</b><div style='font-size:12px;opacity:.85;margin-top:2px'>" + r[1] + "</div></div>";
        }).join("") + "<div style='font-size:10.5px;opacity:.55;margin-top:8px'>Educational playbook hai \u2014 investment decision apne risk par.</div></div>";
      sec.appendChild(d);
    });
  }
  function mount() {
    var sec = document.querySelector("section#learn");
    if (!sec || document.getElementById("mbPlay0")) return;
    try { build(sec); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
