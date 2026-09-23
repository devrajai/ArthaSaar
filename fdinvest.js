/* fdinvest.js - FD vs Post Office vs best investment card. #learn */
(function () {
  var ASOF = "23 Sep 2026";
  var BANKS = [
    ["Suryoday SFB", "8.25%", "5 saal", "8.50%", 1],
    ["Utkarsh SFB", "8.10%", "666 din", "8.25%", 0],
    ["Unity SFB", "8.00%", "501 din", "8.50%", 1],
    ["Equitas SFB", "8.00%", "3 saal", "8.50%", 0],
    ["ESAF SFB", "8.00%", "800 din", "8.50%", 0],
    ["Jana SFB", "8.00%", "2-3 saal", "8.30%", 0],
    ["DCB Bank", "7.50%", "3 saal", "7.75%", 0],
    ["Bandhan Bank", "7.45%", "2-3 saal", "7.95%", 0],
    ["Bank of Baroda", "6.75%", "555 din", "7.25%", 0],
    ["Kotak Bank", "6.80%", "2-3 saal", "7.30%", 0],
    ["HDFC Bank", "6.50%", "3-4.5 saal", "7.00%", 0],
    ["ICICI Bank", "6.50%", "3-10 saal", "7.10%", 0],
    ["Axis Bank", "6.50%", "1.5-10 saal", "7.00%", 0],
    ["SBI", "6.45%", "444 din", "6.95%", 0]
  ];
  var PO = [
    ["Sukanya Samriddhi (SSY)", "8.20%", "beti ke liye, 100% tax-free", 1],
    ["Senior Citizen SCSS", "8.20%", "60+ ke liye, quarterly payout, 30L max", 1],
    ["NSC", "7.70%", "5 saal, 80C me", 0],
    ["KVP", "7.50%", "115 mahine me double", 0],
    ["5 Saal TD", "7.50%", "80C me, sovereign guarantee", 1],
    ["Monthly Income (MIS)", "7.40%", "har mahine payout", 0],
    ["PPF", "7.10%", "100% tax-free, 15 saal", 1],
    ["3 Saal TD", "7.10%", "", 0],
    ["2 Saal TD", "7.00%", "", 0],
    ["1 Saal TD", "6.90%", "", 0],
    ["RD (5 saal)", "6.70%", "", 0]
  ];
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function row(n, r, t, sr, hot) {
    return '<div style="display:flex;justify-content:space-between;align-items:baseline;padding:7px 10px;margin-top:6px;border-radius:8px;background:rgba(255,255,255,.04)' + (hot ? ';border-left:3px solid rgba(240,180,41,.85)' : ';border:1px solid rgba(255,255,255,.07)') + '">' +
      '<div style="font-size:13.5px"><b>' + esc(n) + '</b>' + (t ? '<div style="font-size:11.5px;opacity:.7">' + esc(t) + '</div>' : '') + '</div>' +
      '<div style="text-align:right"><b style="font-size:14px;color:#7ee787">' + esc(r) + '</b>' + (sr ? '<div style="font-size:11px;opacity:.65">senior ' + esc(sr) + '</div>' : '') + '</div></div>';
  }
  function block(title, items) {
    return '<details style="margin-top:8px"><summary style="cursor:pointer;padding:8px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:14px"><b>' + esc(title) + '</b></summary><div style="padding:4px 8px 6px 8px">' + items + '</div></details>';
  }
  function build(card) {
    var h = '<div class="note" style="margin-top:8px">Bank FD vs Post Office - kaunsa best kahan? Rates ' + esc(ASOF) + ' tak ke hain (general public, best tenure). Gold line = best picks.</div>';
    h += block("BANK FD RATES - Top Offers", BANKS.map(function (b) { return row(b[0], b[1], b[2], b[3], b[4]); }).join(""));
    h += block("POST OFFICE RATES (Jul-Sep 2026, 9 quarters se unchanged)", PO.map(function (p) { return row(p[0], p[1], p[2], "", p[3]); }).join(""));
    var V = [
      ["SHORT TERM (6 mahine - 1 saal)", "Unity SFB 7.50% ya Suryoday 7.25% (1 saal). Bade banks (SBI/HDFC/ICICI) sirf 6.25-6.50% - 1%+ ka farak!"],
      ["MEDIUM TERM (2-3 saal)", "Utkarsh 8.10% (666 din) sabse upar, uske baad Unity/Equitas/ESAF/Jana 8.00%."],
      ["LONG TERM (5 saal)", "Suryoday 8.25% (DICGC insured 5L tak) vs Post Office 5-saal TD 7.5% (sovereign guarantee - 100% safe). Zyada paisa + thoda risk = SFB. Full safety = PO."],
      ["BEST LONG-TERM DEAL (beti ke liye)", "SSY 8.2% + 100% TAX-FREE. India ka sabse achha risk-free return."],
      ["TAX KA PANGA", "FD ka interest POORA taxable hai - 30% slab me 8% FD ka real return sirf ~5.5%. PPF 7.1% aur SSY 8.2% tax-free - 30% slab me FD se aage. 5-saal TD + NSC = 80C saving."],
      ["SENIOR CITIZEN (60+)", "SCSS 8.2% - quarterly paisa seedha account me, 30L tak. Ya SFB FD 8.25-8.50%."],
      ["NPS (retirement)", "Extra 50,000 ka tax saving 80CCD(1B) me - 30% slab me ~15,000 bachat. Market-linked ~10-12% historical return. 60 saal tak lock. Job walo ke liye must."],
      ["APY - Atal Pension Yojana", "60 ki umar pe GUARANTEED pension 1,000 se 5,000/month. Age 18-40, bank se kholo. Chhoti kamai walo ke liye pension ka insurance."]
    ];
    V.forEach(function (v) {
      h += '<details style="margin-top:8px"><summary style="cursor:pointer;padding:8px 12px;border-radius:9px;background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);font-size:14px"><b>' + esc(v[0]) + '</b></summary><div class="note" style="padding:6px 14px 2px 14px">' + esc(v[1]) + '</div></details>';
    });
    h += '<div class="note" style="margin-top:10px;font-size:11.5px;opacity:.75">SFB = small finance bank, RBI regulated, DICGC insurance 5 lakh/bank - bada amount multiple banks me todo. Bank rates badalti rehti hain, booking se pehle bank site check kar lena. Post office rates har quarter (Jan/Apr/Jul/Oct) announce hote hain.</div>';
    card.innerHTML = '<summary style="cursor:pointer;margin:4px 2px;padding:10px 14px;border-radius:11px;background:rgba(240,180,41,.13);border:1px solid rgba(240,180,41,.5);font-size:14.5px;text-align:center"><b style="color:rgba(240,180,41,.95)">🏦 FD vs POST OFFICE</b> <span style="font-size:11px;opacity:.65">best rates \u00b7 Sep 2026</span></summary>' + h;
  }
  function mount() {
    var sec = document.querySelector("section#learn");
    if (!sec || document.getElementById("mbFdInvest")) return;
    var c = document.createElement("details");
    c.className = "card"; c.id = "mbFdInvest"; c.style.marginTop = "14px";
    sec.appendChild(c);
    try { build(c); } catch (e) {}
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
