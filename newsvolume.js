/* newsvolume.js - News Volume Tracker: 7-day Google News article count per stock, spike + headline sentiment. #news */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  var DATA = null, ALL = [];

  function bars(d7) {
    var mx = Math.max.apply(null, d7.concat([1]));
    var h = '<div style="display:flex;align-items:flex-end;gap:2px;height:18px">';
    d7.forEach(function (v, i) {
      var bh = Math.max(2, Math.round(18 * v / mx));
      var last = i === 6;
      h += '<div style="width:5px;height:' + bh + 'px;border-radius:2px;background:' + (last ? "rgba(240,180,41,.95)" : "rgba(255,255,255,.22)") + '"></div>';
    });
    return h + "</div>";
  }

  function row(c) {
    var spikeTxt = c.spike >= 1.5 ? c.spike + "x" : "";
    var spikeCol = c.spike >= 2 ? "#ff8b8b" : (c.spike >= 1.5 ? "rgba(240,180,41,.95)" : "");
    var sentEmoji = c.tag === "positive" ? "\uD83D\uDCC8" : (c.tag === "negative" ? "\uD83D\uDCC9" : "\u25B8");
    var sentCol = c.tag === "positive" ? "#77f37b" : (c.tag === "negative" ? "#ff8b8b" : "var(--dim)");
    var h = '<details style="margin-top:6px"><summary style="cursor:pointer;display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:13.5px;flex-wrap:wrap">' +
      '<b style="min-width:86px">' + esc(c.sym) + "</b>" + bars(c.d7) +
      '<span style="font-size:11px;opacity:.65">' + c.total7 + " art / 7d</span>" +
      (spikeTxt ? '<span style="font-size:11px;font-weight:700;color:' + spikeCol + '">' + spikeTxt + " spike</span>" : "") +
      '<span style="font-size:12px;color:' + sentCol + ';margin-left:auto">' + sentEmoji + " " + c.sent + "</span></summary>" +
      '<div style="padding:4px 14px 8px 14px">';
    (c.hl || []).forEach(function (x) {
      h += '<div style="font-size:12px;line-height:1.45;margin-top:5px;opacity:.85"><span style="opacity:.5">' + esc(x.d) + " \u00b7 " + esc(x.s) + "</span> \u2014 " + esc(x.t) + "</div>";
    });
    if (!c.hl || !c.hl.length) h += '<div class="note">koi headline nahi mili</div>';
    h += "</div></details>";
    return h;
  }

  function render(box, q) {
    q = (q || "").toLowerCase().trim();
    var list = ALL.filter(function (c) {
      if (!q) return c.total7 > 0;
      return (c.sym + " " + c.q).toLowerCase().indexOf(q) >= 0;
    });
    var h = "";
    if (!q) h += '<div class="note" style="margin-top:8px">Spike = aaj ke articles vs pichle 6 din ka avg (1.5x+ = dhyan do). Bars = 7 din ka volume, last bar aaj. Sentiment headline keywords se (indicative, advice nahi). Tap = top headlines. Guide upar tap karke padho.</div>';
    if (!list.length) h += '<div class="note" style="margin-top:10px">koi match nahi mila</div>';
    list.forEach(function (c) { h += row(c); });
    box.innerHTML = h;
  }

  function build(card) {
    var guide = '<details style="margin-top:8px"><summary style="cursor:pointer;padding:8px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:13px"><b>\u2753 SPIKE GUIDE</b> <span style="font-size:11px;opacity:.6">kaise padhein \u00b7 buy/sell/hold</span></summary>' +
      '<div class="note" style="padding:6px 14px 10px 14px;line-height:1.7">' +
      '<b style="color:rgba(240,180,41,.9)">Spike</b> = aaj ke articles vs pichle 6 din ka avg. Spike khud neutral hai - direction <b>sentiment</b> batata hai:' +
      '<div style="margin-top:6px;padding:7px 10px;border-radius:8px;background:rgba(119,243,123,.08);border:1px solid rgba(119,243,123,.3)">📈 <b>Spike 2x+ positive</b> (upgrade, order win, record profit): achhi khabar - short-term momentum (1-3 din swing / BTST) ka chance. Par gap-up me chase mat karo, price pe entry dekho. Holders: hold.</div>' +
      '<div style="margin-top:6px;padding:7px 10px;border-radius:8px;background:rgba(255,139,139,.08);border:1px solid rgba(255,139,139,.3)">📉 <b>Spike 2x+ negative</b> (probe, fraud, crash, downgrade): buri khabar - exit/avoid. F&O trader short dekh sakta hai (risky). Holders: headline padho, SL strict.</div>' +
      '<div style="margin-top:6px;padding:7px 10px;border-radius:8px;background:rgba(159,176,196,.08);border:1px solid rgba(159,176,196,.3)">▸ <b>Spike 2x+ neutral</b>: kuch bada aa raha (result, order, policy) - wait & watch. 1.5-2x = medium, <1.5x = normal.</div>' +
      '<div style="margin-top:8px"><b style="color:rgba(240,180,41,.9)">Sentiment score</b> (-100 se +100): +50 se upar = strong positive, -50 se neeche = strong negative, beech me = mixed/neutral. Headline keywords se - indicative, guarantee nahi.</div>' +
      '<div style="margin-top:8px"><b style="color:rgba(240,180,41,.9)">Timeframe:</b> spike ka asar mostly 1-3 din (BTST/swing). Positional/long-term ke liye sentiment kam, <b>Market Brain Score</b> (Screener) zyada matter karta hai. Intraday ke liye news akela kaafi nahi - price action + volume + OI chahiye.</div>' +
      '<div style="margin-top:8px;opacity:.6">Rule: news aane tak price me baat ban chuki hoti hai - entry SL ke saath, sirf spike pe blind trade nahi.</div></div></details>';
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(240,180,41,.13);border:1px solid rgba(240,180,41,.5);font-size:14.5px;text-align:center"><b style="color:rgba(240,180,41,.95)">\uD83D\uDCCA NEWS VOLUME</b> <span style="font-size:11px;opacity:.65">7-day spike \u00b7 sentiment \u00b7 Nifty 40</span></summary>' +
      guide +
      '<div id="nvSearch" style="margin-top:10px"><input id="nvQ" placeholder="company search... (RELIANCE, TCS)" style="width:100%;box-sizing:border-box;padding:9px 12px;border-radius:9px;background:rgba(255,255,255,.07);border:1px solid rgba(255,255,255,.15);color:inherit;font-size:13px;outline:none"></div>' +
      '<div id="nvBody" class="note" style="margin-top:8px">loading news volume...</div>';
    var inp = document.getElementById("nvQ");
    inp.addEventListener("input", function () { render(document.getElementById("nvBody"), inp.value); });
    fetch("data/news-volume.json").then(function (r) { return r.json(); }).then(function (d) {
      DATA = d; ALL = d.companies || [];
      render(document.getElementById("nvBody"), "");
      var s = document.getElementById("nvSearch");
      if (s) s.insertAdjacentHTML("afterbegin", '<div class="note" style="margin-bottom:6px">' + esc(d.updated || "") + " \u00b7 " + (ALL.length) + " stocks</div>");
    }).catch(function () {
      var b = document.getElementById("nvBody");
      if (b) b.innerHTML = "data load nahi hua - thodi der baad try karo";
    });
  }

  function mount() {
    var sec = document.querySelector("section#news");
    if (!sec || document.getElementById("mbNewsVol")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbNewsVol"; c.style.marginTop = "14px";
    var nb = document.getElementById("newsBox");
    if (nb) sec.insertBefore(c, nb); else sec.appendChild(c);
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
