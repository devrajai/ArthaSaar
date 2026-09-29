/* Arthasaar livedata.js — demo UI + REAL data
   Sources: data/*.json + ipo/data.json (bots in auto-update karte hain)
   UI markup/classes demo jaisi hi — sirf numbers real. */
(function () {
  "use strict";

  /* ---------- helpers ---------- */
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&" + "amp;", "<": "&" + "lt;", ">": "&" + "gt;", '"': "&" + "quot;" }[c];
    });
  }
  function num(n, d) {
    if (n == null || isNaN(n)) return "—";
    return Number(n).toLocaleString("en-IN", { minimumFractionDigits: d == null ? 2 : d, maximumFractionDigits: d == null ? 2 : d });
  }
  function pctS(n) { if (n == null || isNaN(n)) return "—"; return (n >= 0 ? "+" : "−") + Math.abs(n).toFixed(2) + "%"; }
  function cl(n) { return n >= 0 ? "up" : "dn"; }
  function sp(n) { return "<span class='" + cl(n) + "'>" + pctS(n) + "</span>"; }
  function ar(n) { return n >= 0 ? "▲" : "▼"; }
  function ago(iso) {
    try {
      var t = new Date(iso).getTime();
      if (!t || isNaN(t)) return "";
      var m = Math.round((Date.now() - t) / 60000);
      if (m < 1) return "abhi";
      if (m < 60) return m + " min ago";
      var h = Math.round(m / 60);
      if (h < 24) return h + " hr ago";
      return Math.round(h / 24) + " d ago";
    } catch (e) { return ""; }
  }
  /* data seedha GitHub se (hamesha fresh — deploy ka wait nahi), fail ho to local */
  var RAW = "https://raw.githubusercontent.com/devrajai/ArthaSaar/main/";
  function fj(p) {
    var t = Date.now();
    return fetch(RAW + p + "?t=" + t).then(function (r) {
      if (!r.ok) throw new Error("raw " + r.status);
      return r.json();
    }).catch(function () {
      return fetch(p + "?t=" + t).then(function (r) { return r.json(); });
    });
  }
  function sec(id) { return document.getElementById(id); }

  var PM = {};      /* symbol -> {price, chg, ...} brain-screener */
  var NAME = {};    /* symbol -> company */
  var FUND = {};    /* symbol -> fundamentals */

  /* ---------- 1) HOME KPIs + sparkline + breadth + FII ---------- */
  function renderHome() {
    fj("data/indices-all.json").then(function (d) {
      var by = {};
      (d.indices || []).forEach(function (x) { by[(x.index || "").toUpperCase()] = x; });
      var pick = function (k) {
        return by["NIFTY 50"] && k === "NIFTY 50" ? by[k] : (by[k] || {});
      };
      var n = by["NIFTY 50"] || {}, se = by["SENSEX"] || {}, bn = by["BANK NIFTY"] || by["BANKNIFTY"] || {}, vx = by["INDIA VIX"] || {};
      var k = sec("v-home") ? $(".kpis", sec("v-home")) : null;
      if (k) {
        k.innerHTML =
          kpi("NIFTY 50", num(n.price), n.change_pct, n.change) +
          kpi("SENSEX", num(se.price), se.change_pct, se.change) +
          kpi("BANK NIFTY", num(bn.price), bn.change_pct, bn.change) +
          kpi("INDIA VIX", num(vx.price), vx.change_pct);
      }
      /* nifty 1D card title */
      var g2 = sec("v-home") ? $(".grid2 .card .sh2", sec("v-home")) : null;
      if (g2 && n.price != null) {
        g2.innerHTML = "NIFTY 50 · 1D " + sp(n.change_pct) +
          '<span class="fr">52wH ' + num(n.year_high, 0) + " · 52wL " + num(n.year_low, 0) + "</span>";
      }
    }).catch(function () {});
    /* FII / DII 5 days */
    fj("data/fii-history.json").then(function (h) {
      var c = sec("v-home");
      if (!c) return;
      var card = null;
      $$(".card", c).forEach(function (x) {
        if (!card && $(".sh2", x) && /FII \/ DII/.test($(".sh2", x).textContent)) card = x;
      });
      if (!card) return;
      var h2 = "";
      (h.slice(0, 5) || []).forEach(function (r) {
        h2 += '<div class="zrow"><span>' + esc((r.date || "").split("-").slice(0, 2).join("-")) + "</span><span>" +
          '<b class="' + (r.fii >= 0 ? "up" : "dn") + '">' + (r.fii >= 0 ? "+" : "−") + num(Math.abs(r.fii), 0) + '</b> <small class="mono">FII</small> · ' +
          '<b class="' + (r.dii >= 0 ? "up" : "dn") + '">' + (r.dii >= 0 ? "+" : "−") + num(Math.abs(r.dii), 0) + '</b> <small class="mono">DII</small></span></div>';
      });
      var body = $("div[style]", card);
      if (body && h2) body.innerHTML = h2;
    }).catch(function () {});
  }
  function kpi(lbl, numTxt, chg, pts) {
    var c = chg == null ? "" : cl(chg);
    var t = chg == null ? "" : ar(chg) + " " + pctS(chg) + (pts != null && !isNaN(pts) ? " · " + (pts >= 0 ? "+" : "−") + num(Math.abs(pts), 0) : "");
    return '<div class="card kpi"><div class="lbl">' + esc(lbl) + '</div><div class="num">' + numTxt + '</div><div class="chg ' + c + '">' + t + "</div></div>";
  }

  /* ---------- 2) SCREENER data load (price map) + home modules + breadth ---------- */
  function loadScreenerData(cb) {
    fj("data/brain-screener.json").then(function (d) {
      var st = d.stocks || [];
      st.forEach(function (x) {
        PM[x.symbol] = x;
        NAME[x.symbol] = x.company || x.symbol;
      });
      fj("data/screener-fundamentals.json").then(function (f) {
        var ss = f.stocks || {};
        Object.keys(ss).forEach(function (k) { FUND[k] = ss[k]; });
      }).catch(function () {});
      /* indices table */
      renderIndicesTable();
      /* screener table */
      renderScreenerTable(st);
      /* heatmap */
      renderHeatmap();
      /* home modules + breadth */
      renderHomeModules(st);
      /* portfolio (prices ready) */
      renderPortfolio();
      /* company card ready */
      wireCompany(st);
    }).catch(function () {});
  }

  function renderHomeModules(st) {
    var c = sec("v-home");
    if (!c) return;
    var up = st.slice().sort(function (a, b) { return (b.change_pct || 0) - (a.change_pct || 0); });
    var dn = st.slice().sort(function (a, b) { return (a.change_pct || 0) - (b.change_pct || 0); });
    var adv = 0, dec = 0, unch = 0, tierSum = { 1: [0, 0], 2: [0, 0], 3: [0, 0] };
    st.forEach(function (x) {
      var cp = x.change_pct || 0;
      if (cp > 0) adv++; else if (cp < 0) dec++; else unch++;
      var t = x.tier || 3;
      if (tierSum[t]) { tierSum[t][0] += cp; tierSum[t][1]++; }
    });
    /* breadth card */
    $$(".card", c).forEach(function (x) {
      var sh = $(".sh2", x);
      if (sh && /Market Breadth/.test(sh.textContent)) {
        var b = $(".breadth i", x);
        if (b && adv + dec + unch) b.style.width = Math.round(adv / (adv + dec + unch) * 100) + "%";
        var m = $(".mono.s11", x);
        if (m) m.innerHTML = "<b>" + num(adv, 0) + "</b> adv · <b>" + num(unch, 0) + "</b> unch · <b>" + num(dec, 0) + "</b> dec";
        var z = $$(".zrow", x);
        if (z[0]) z[0].innerHTML = "<span>Large Cap</span><b class='" + (tierSum[1][0] >= 0 ? "up" : "dn") + "'>" + pctS(tierSum[1][1] ? tierSum[1][0] / tierSum[1][1] : 0) + "</b>";
        if (z[1]) z[1].innerHTML = "<span>Mid Cap</span><b class='" + (tierSum[2][0] >= 0 ? "up" : "dn") + "'>" + pctS(tierSum[2][1] ? tierSum[2][0] / tierSum[2][1] : 0) + "</b>";
        if (z[2]) z[2].innerHTML = "<span>Small Cap</span><b class='" + (tierSum[3][0] >= 0 ? "up" : "dn") + "'>" + pctS(tierSum[3][1] ? tierSum[3][0] / tierSum[3][1] : 0) + "</b>";
      }
    });
    /* modules minirow */
    var mr = $(".minirow", c);
    if (mr && up.length) {
      var vol = st.slice().sort(function (a, b) { return (b.rsi14 || 0) - (a.rsi14 || 0); })[0] || {};
      fj("data/breadth.json").then(function (b) {
        var h =
          '<div class="card kpi"><div class="lbl">TOP GAINER</div><div class="num up">' + esc(up[0].symbol) + '</div><div class="chg up">' + pctS(up[0].change_pct) + "</div></div>" +
          '<div class="card kpi"><div class="lbl">TOP LOSER</div><div class="num dn">' + esc(dn[0].symbol) + '</div><div class="chg dn">' + pctS(dn[0].change_pct) + "</div></div>" +
          '<div class="card kpi"><div class="lbl">VOLUME SHOCKER</div><div class="num">' + num(b.volume_spike_2x, 0) + '</div><div class="chg">stocks 2× volume</div></div>' +
          '<div class="card kpi"><div class="lbl">52W MOVERS</div><div class="num">' + num(b.near_52w_high, 0) + '</div><div class="chg">near 52w high</div></div>';
        mr.innerHTML = h;
      }).catch(function () {});
    }
    /* internals view KPIs */
    var iv = sec("v-internals");
    if (iv) {
      var ks = $(".kpis", iv);
      if (ks) {
        fj("data/futures.json").then(function (f) {
          var pcr = f.pcr || {};
          ks.innerHTML =
            '<div class="card kpi"><div class="lbl">ADVANCES</div><div class="num">' + num(adv, 0) + '</div><div class="chg up">aaj ke winner</div></div>' +
            '<div class="card kpi"><div class="lbl">DECLINES</div><div class="num">' + num(dec, 0) + '</div><div class="chg dn">aaj ke loser</div></div>' +
            '<div class="card kpi"><div class="lbl">PCR (OI)</div><div class="num">' + (pcr.nifty_pcr_oi != null ? pcr.nifty_pcr_oi : "—") + '</div><div class="chg hold">' + (pcr.nifty_pcr_oi > 1.3 ? "fear high" : pcr.nifty_pcr_oi < 0.7 ? "greed" : "neutral zone") + "</div></div>" +
            '<div class="card kpi"><div class="lbl">RSI SPLIT</div><div class="num">—</div><div class="chg hold">breadth split</div></div>';
          fj("data/breadth.json").then(function (b) {
            var el = ks.children[3];
            if (el) el.innerHTML = '<div class="lbl">RSI SPLIT</div><div class="num">' + num(b.rsi_above_60, 0) + " / " + num(b.rsi_below_40, 0) + '</div><div class="chg hold">above 60 / below 40</div>';
          }).catch(function () {});
          var pcrCard = $$(".grid3 .card", iv)[2];
          if (pcrCard) {
            var h2 = $(".sh2", pcrCard);
            if (h2) h2.innerHTML = "PCR — aaj " + (pcr.nifty_pcr_oi != null ? pcr.nifty_pcr_oi : "—");
            var zr = $$("div[style]", pcrCard);
            var rows = [["Aaj", (pcr.nifty_pcr_oi != null ? pcr.nifty_pcr_oi + " — " + (pcr.nifty_pcr_oi > 1.3 ? "extreme fear" : pcr.nifty_pcr_oi < 0.7 ? "greed zone" : "neutral zone") : "—")]];
            var inner = $("div[style]", pcrCard);
            if (inner && pcr.nifty_max_pain) {
              inner.innerHTML = '<div class="zrow"><span>Max pain</span><b class="">' + num(pcr.nifty_max_pain, 0) + '</b></div><div class="zrow"><span>Expiry</span><b class="">' + esc(pcr.nifty_expiry || "—") + "</b></div>" +
                '<div class="zrow"><span>PCR vol</span><b class="">' + (pcr.nifty_pcr_vol != null ? pcr.nifty_pcr_vol : "—") + "</b></div>";
            }
          }
        }).catch(function () {});
    }
    }
  }

  /* ---------- 3) indices table ---------- */
  function renderIndicesTable() {
    var b = sec("idxBody");
    if (!b) return;
    fj("data/indices-all.json").then(function (d) {
      var ix = d.indices || [];
      var h2 = sec("v-indices") ? $("h2", sec("v-indices")) : null;
      if (h2) h2.textContent = "Indices — " + num(ix.length, 0) + " tracked";
      var h = "";
      ix.forEach(function (x) {
        var pos = "—";
        try {
          if (x.year_high && x.year_low && x.price) pos = Math.max(0, Math.min(100, Math.round((x.price - x.year_low) / (x.year_high - x.year_low) * 100))) + "%";
        } catch (e) {}
        h += "<tr><td>" + esc(x.index || x.symbol) + "</td><td>" + num(x.price) + "</td><td>" + sp(x.change_pct) + "</td><td>" + pos + "</td><td>" + (x.pe || "—") + "</td><td>" + (x.pb || "—") + "</td></tr>";
      });
      b.innerHTML = h;
    }).catch(function () {});
  }

  /* ---------- 4) screener table ---------- */
  var SCRSIG = {};
  function renderScreenerTable(st) {
    var b = sec("scrBody");
    if (!b) return;
    var h2 = sec("v-screener") ? $("h2", sec("v-screener")) : null;
    if (h2) h2.textContent = "Screener — " + num(st.length, 0) + " stocks";
    fj("data/stock-scores.json").then(function (sc) {
      (sc.top || []).forEach(function (x) { SCRSIG[x.sym] = x; });
    }).catch(function () {}).then(function () {
      var rows = st.slice().sort(function (a, b2) { return (b2.change_pct || 0) - (a.change_pct || 0); });
      var mixed = rows.slice(0, 15).concat(rows.slice(-15));
      var h = "";
      mixed.forEach(function (x) {
        var f = FUND[x.symbol] || {};
        var sig = sigFor(x);
        var mc = f["Market Cap"] != null ? mcap(f["Market Cap"]) : "—";
        h += "<tr><td>" + esc(x.symbol) + "</td><td>" + num(x.price) + "</td><td>" + sp(x.change_pct) + "</td><td>" + mc + "</td><td>" + (f["Stock P/E"] != null ? f["Stock P/E"] : "—") + "</td><td>" + (f.ROE != null ? f.ROE + "%" : (f.ROCE != null ? f.ROCE + "%" : "—")) + "</td><td>" + sig + "</td></tr>";
      });
      b.innerHTML = h;
      renderFundamentalsTable();
    });
  }
  function sigFor(x) {
    var s = SCRSIG[x.symbol];
    if (s && s.total != null) {
      if (s.total >= 8) return "<span class='b buy'>BUY</span>";
      if (s.total >= 6) return "<span class='b hold'>HOLD</span>";
      return "<span class='b dn'>REDUCE</span>";
    }
    if ((x.change_pct || 0) > 1 && x.above_ema200) return "<span class='b buy'>BUY</span>";
    if ((x.change_pct || 0) < -1) return "<span class='b dn'>REDUCE</span>";
    return "<span class='b hold'>HOLD</span>";
  }
  function mcap(cr) {
    if (cr == null) return "—";
    if (cr >= 100000) return (cr / 100000).toFixed(1) + "T";
    return num(Math.round(cr), 0) + "Cr";
  }

  /* ---------- 5) fundamentals table ---------- */
  function renderFundamentalsTable() {
    var v = sec("v-fundamentals");
    if (!v) return;
    var tb = $("tbody", v);
    if (!tb) return;
    var ks = Object.keys(FUND).sort(function (a, b2) { return (FUND[b2]["Market Cap"] || 0) - (FUND[a]["Market Cap"] || 0); });
    var h = "";
    ks.slice(0, 20).forEach(function (sym) {
      var f = FUND[sym] || {};
      var pr = f["Current Price"], bv = f["Book Value"];
      var pb = pr && bv ? (pr / bv).toFixed(1) : "—";
      h += "<tr><td>" + esc(NAME[sym] || sym) + "</td><td>" + mcap(f["Market Cap"]) + "</td><td>" + (f["Stock P/E"] != null ? f["Stock P/E"] : "—") + "</td><td>" + pb + "</td><td>" + (f.ROE != null ? f.ROE + "%" : "—") + "</td><td>" + (f.ROCE != null ? f.ROCE + "%" : "—") + "</td><td>" + (f["D/E"] != null ? f["D/E"] : "—") + "</td><td>" + (f["Dividend Yield"] != null ? f["Dividend Yield"] + "%" : "—") + "</td></tr>";
    });
    if (h) tb.innerHTML = h;
  }

  /* ---------- 6) heatmap ---------- */
  function renderHeatmap() {
    var v = sec("v-heatmap");
    if (!v) return;
    var heat = $(".heat", v);
    if (!heat) return;
    fj("data/constituents.json").then(function (c) {
      var secs = c.sectors || {};
      var names = Object.keys(secs);
      var h = "";
      names.forEach(function (sn) {
        var sum = 0, cnt = 0;
        (secs[sn] || []).forEach(function (m) {
          var p = PM[m.symbol];
          if (p && p.change_pct != null) { sum += p.change_pct; cnt++; }
        });
        if (!cnt) return;
        var av = sum / cnt;
        h += '<div class="hc" style="background:color-mix(in srgb,var(' + (av >= 0 ? "up" : "dn") + ') ' + Math.min(20, 4 + Math.abs(av) * 6).toFixed(0) + '%,var(--surface))"><b>' + esc(sn.toUpperCase().slice(0, 8)) + "</b><span class='" + cl(av) + "'>" + pctS(av) + "</span></div>";
      });
      if (h) heat.innerHTML = h;
    }).catch(function () {});
  }

  /* ---------- 7) IPO terminal (home + v-ipo) ---------- */
  function renderIPO() {
    fj("ipo/data.json").then(function (d) {
      var ipos = d.ipos || [];
      var gmpMap = {};
      fj("ipo/data/gmp.json").then(function (g) {
        (g.data || []).forEach(function (x) { gmpMap[x.name] = x; });
      }).catch(function () {}).then(function () {
        var open = ipos.filter(function (x) { return /^(open|closing|live|subscribed)/i.test(x.status || ""); });
        var up = ipos.filter(function (x) { return /^upcoming/i.test(x.status || ""); });
        var cl = ipos.filter(function (x) { return /^closed/i.test(x.status || ""); });
        function ni(x) {
          var g = x.gmp || (gmpMap[x.company] && gmpMap[x.company].gmp) || "";
          var s = [x.priceBand || (x.issueSizeCr ? "₹" + x.issueSizeCr + "Cr" : ""), x.subscription || "", g ? "GMP " + g : "", x.listingDate ? "list " + x.listingDate : ""].filter(Boolean).join(" · ");
          return '<div class="ni"><b>' + esc(x.company) + "</b><small>" + esc(s) + "</small></div>";
        }
        function col(list, n) {
          var h = "";
          list.slice(0, n).forEach(function (x) { h += ni(x); });
          return h || '<div class="ni"><b>—</b><small>kuch nahi</small></div>';
        }
        [sec("v-home"), sec("v-ipo")].forEach(function (root) {
          if (!root) return;
          $$(".grid3 .card", root).forEach(function (card) {
            var sh = $(".sh2", card);
            if (!sh) return;
            var t = sh.textContent;
            if (/OPEN/.test(t)) card.innerHTML = '<div class="sh2">OPEN <span class="b buy">LIVE</span></div>' + col(open, 4);
            else if (/UPCOMING/.test(t)) card.innerHTML = '<div class="sh2">UPCOMING</div>' + col(up, 4);
            else if (/CLOSED/.test(t)) card.innerHTML = '<div class="sh2">CLOSED</div>' + col(cl, 4);
          });
        });
      });
    }).catch(function () {});
  }

  /* ---------- 8) news (home + v-news) ---------- */
  function renderNews() {
    fj("data/news.json").then(function (d) {
      var items = (d.items || []).slice();
      var mk = function (title, re, card) {
        var list = items.filter(function (x) { return re.test((x.topic || "") + " " + (x.title || "")); });
        if (!list.length) list = items.slice(0, 3);
        var h = '<div class="sh2">' + title + "</div>";
        list.slice(0, 3).forEach(function (x) {
          h += '<div class="ni"><b>' + esc(x.title) + "</b><small>" + esc(x.topic || "") + " · " + ago(x.published) + "</small></div>";
        });
        card.innerHTML = h;
      };
      [sec("v-home"), sec("v-news")].forEach(function (root) {
        if (!root) return;
        $$(".grid3 .card", root).forEach(function (card) {
          var sh = $(".sh2", card);
          if (!sh) return;
          var t = sh.textContent;
          if (/Market News/.test(t)) mk("Market News", /market|nifty|sensex|stock|index|fii|crash|rate/i, card);
          else if (/IPO News/.test(t)) mk("IPO News", /ipo|listing|allotment|drhp|gmp/i, card);
          else if (/Company News/.test(t)) mk("Company News", /compan|result|earning|corporate|profit|order-book|deal/i, card);
        });
      });
    }).catch(function () {});
  }

  /* ---------- 9) global + crypto + events + filings + futures + mf ---------- */
  function renderGlobal() {
    var v = sec("v-global");
    if (!v) return;
    fj("data/global.json").then(function (d) {
      var h = "";
      (d.items || []).forEach(function (x) {
        h += "<tr><td>" + esc(x.name) + "</td><td>" + num(x.price) + "</td><td>" + sp(x.chg_pct) + "</td></tr>";
      });
      var tb = $("tbody", v);
      if (tb && h) tb.innerHTML = h;
    }).catch(function () {});
  }
  function renderCrypto() {
    var v = sec("v-crypto");
    if (!v) return;
    fj("data/crypto.json").then(function (d) {
      var h = "";
      (d.top || []).slice(0, 12).forEach(function (x) {
        var mc = x.market_cap;
        var mcS = mc == null ? "—" : (mc >= 1e12 ? "$" + (mc / 1e12).toFixed(2) + "T" : "$" + Math.round(mc / 1e9) + "B");
        h += "<tr><td>" + esc(x.symbol) + "</td><td>$" + num(x.price_usd) + "</td><td>" + sp(x.chg_24h_pct) + "</td><td>" + sp(x.chg_7d_pct) + "</td><td>" + mcS + "</td></tr>";
      });
      var tb = $("tbody", v);
      if (tb && h) tb.innerHTML = h;
    }).catch(function () {});
  }
  function renderEvents() {
    var v = sec("v-events");
    if (!v) return;
    fj("data/events.json").then(function (d) {
      var h = "";
      (d.key_dates || []).forEach(function (x) {
        var dt = (x.date || "").slice(5).replace("-", " ");
        var imp = /^(high)$/i.test(x.impact || "") ? "<span class='b dn'>HIGH</span>" : "<span class='b hold'>" + esc((x.impact || "MED").toUpperCase()) + "</span>";
        h += "<tr><td>" + esc(dt) + "</td><td>" + esc((x.title || "").slice(0, 70)) + "</td><td>" + esc(x.country || "") + "</td><td>" + imp + "</td></tr>";
      });
      var tb = $("tbody", v);
      if (tb && h) tb.innerHTML = h;
    }).catch(function () {});
  }
  function renderFilings() {
    var v = sec("v-filings");
    if (!v) return;
    fj("data/filings.json").then(function (d) {
      var h = "";
      (d.filings || []).slice(0, 12).forEach(function (x) {
        h += "<tr><td>" + esc(x.company || x.symbol) + "</td><td>" + esc((x.nse_desc || x.subject || "").slice(0, 60)) + "</td><td>" + esc((x.date || "").slice(5)) + "</td></tr>";
      });
      var tb = $("tbody", v);
      if (tb && h) tb.innerHTML = h;
    }).catch(function () {});
  }
  function renderFutures() {
    var v = sec("v-futures");
    if (!v) return;
    fj("data/futures.json").then(function (d) {
      var h = "";
      (d.indices || []).forEach(function (ix) {
        (ix.contracts || []).slice(0, 2).forEach(function (c) {
          var chg = ix.underlying ? (c.close - ix.underlying) / ix.underlying * 100 : null;
          var oiC = c.oi != null ? (c.oi >= 1e7 ? (c.oi / 1e7).toFixed(2) + "Cr" : (c.oi / 1e5).toFixed(1) + "L") : "—";
          var oc = c.oi && c.oi_chg != null && (c.oi - c.oi_chg) ? (c.oi_chg / (c.oi - c.oi_chg) * 100) : null;
          var bs = ix.underlying ? Math.round(c.close - ix.underlying) + " pts" : "—";
          h += "<tr><td>" + esc(ix.symbol) + " " + esc((c.expiry || "").slice(5)) + "</td><td>" + num(c.close) + "</td><td>" + sp(chg) + "</td><td>" + oiC + "</td><td>" + sp(oc) + "</td><td>" + bs + "</td></tr>";
        });
      });
      (d.stocks || []).slice(0, 6).forEach(function (s) {
        var oiC = s.oi != null ? (s.oi >= 1e7 ? (s.oi / 1e7).toFixed(2) + "Cr" : (s.oi / 1e5).toFixed(1) + "L") : "—";
        h += "<tr><td>" + esc(s.symbol) + " " + esc((s.expiry || "").slice(5)) + "</td><td>" + num(s.close) + "</td><td>" + (s.basis_pct != null ? sp(s.basis_pct) : "—") + "</td><td>" + oiC + "</td><td>—</td><td>" + (s.basis_pct != null ? (Math.abs(s.close * s.basis_pct / 100)).toFixed(2) : "—") + "</td></tr>";
      });
      var tb = $("tbody", v);
      if (tb && h) tb.innerHTML = h;
    }).catch(function () {});
  }
  function renderMF() {
    var v = sec("v-mf");
    if (!v) return;
    fj("data/mf-top.json").then(function (d) {
      var th = $("thead", v);
      if (th) th.innerHTML = "<tr><th>Fund</th><th>Category</th><th>1Y%</th><th>3Y%</th><th>5Y%</th></tr>";
      var tb = $("tbody", v);
      if (!tb) return;
      var h = "";
      (d.funds || []).slice(0, 10).forEach(function (f) {
        h += "<tr><td>" + esc((f.n || "").split("·")[0].trim()) + "</td><td>" + esc(f.k || "—") + "</td><td>" + sp(f.r1) + "</td><td>" + sp(f.r3) + "</td><td>" + sp(f.r5) + "</td></tr>";
      });
      if (h) tb.innerHTML = h;
    }).catch(function () {});
  }

  /* ---------- 10) GTI zones + AI forecast ---------- */
  function renderGTI() {
    var v = sec("v-gtizones");
    if (!v) return;
    fj("data/gti.json").then(function (d) {
      var syms = d.symbols || {};
      var want = ["NIFTY 50", "BANKNIFTY", "RELIANCE"];
      var g = "";
      want.forEach(function (w) {
        var x = syms[w];
        if (!x || !x.day_zones) return;
        var z = x.day_zones;
        var sd = z.SD || z.WD || [], ss = z.SS || z.WS || [];
        g += '<div class="card"><div class="sh2">' + esc(w) + ' — Zones</div><div style="padding:6px 14px 10px">' +
          '<div class="zrow"><span>Demand</span><b class="up">' + (sd.length ? num(sd[0], 0) + " – " + num(sd[1], 0) : "—") + "</b></div>" +
          '<div class="zrow"><span>Supply</span><b class="dn">' + (ss.length ? num(ss[0], 0) + " – " + num(ss[1], 0) : "—") + "</b></div>" +
          '<div class="zrow"><span>POC day</span><b class="">' + (x.day_poc != null ? num(x.day_poc, 0) : "—") + "</b></div></div></div>";
      });
      var g3 = $(".grid3", v);
      if (g3 && g) g3.innerHTML = g;
    }).catch(function () {});
  }
  function renderForecast() {
    var v = sec("v-gtiai");
    if (!v) return;
    fj("data/timesfm_forecasts.json").then(function (d) {
      var fc2 = d.forecasts || [];
      var f = fc2.filter(function (x) { return /\^nsei|nifty 50/i.test((x.symbol || "") + " " + (x.name || "")); })[0] ||
        fc2.filter(function (x) { return /nifty|sensex/i.test((x.symbol || "") + " " + (x.name || "")); })[0] ||
        fc2.filter(function (x) { return /index/i.test(x.cat || ""); })[0];
      if (!f) return;
      var ks = $(".kpis", v);
      if (ks) {
        ks.innerHTML =
          '<div class="card kpi"><div class="lbl">NIFTY — ' + f.horizon_days + 'D TARGET</div><div class="num">' + num(f.median_end, 0) + '</div><div class="chg ' + cl(f.median_chg_pct) + '">' + pctS(f.median_chg_pct) + " expected</div></div>" +
          '<div class="card kpi"><div class="lbl">CONFIDENCE</div><div class="num">' + (f.confidence != null ? f.confidence + "%" : "—") + '</div><div class="chg hold">model agreement</div></div>' +
          '<div class="card kpi"><div class="lbl">TREND</div><div class="num ' + cl(f.median_chg_pct) + '">' + ((f.direction || "") || (f.median_chg_pct >= 0 ? "UP" : "DOWN")).toUpperCase() + '</div><div class="chg hold">median path</div></div>' +
          '<div class="card kpi"><div class="lbl">RANGE 10-90</div><div class="num" style="font-size:15px">' + num(f.low10_end, 0) + "–" + num(f.high90_end, 0) + '</div><div class="chg hold">10% – 90% band</div></div>';
      }
      var mv = $$(".card", v).filter(function (x) { return /Model View/.test($(".sh2", x) ? $(".sh2", x).textContent : ""); })[0];
      if (mv) {
        var body = $("div[style]", mv);
        if (body) body.textContent = (f.name || f.symbol) + ": " + f.horizon_days + "-din ka median target " + num(f.median_end, 0) + " (" + pctS(f.median_chg_pct) + "). Model band " + num(f.low10_end, 0) + " se " + num(f.high90_end, 0) + " tak. Base case " + (f.median_chg_pct >= 0 ? "upar" : "neeche") + " — range ke andar trade karo, band ke bahar nahi.";
      }
    }).catch(function () {});
  }

  /* ---------- 11) deepfund (stock scores) ---------- */
  function renderDeep() {
    var v = sec("v-deepfund");
    if (!v) return;
    fj("data/stock-scores.json").then(function (d) {
      var top = (d.top || []).slice(0, 4);
      var ks = $(".kpis", v);
      if (ks && top.length) {
        var h = "";
        top.forEach(function (x) {
          h += '<div class="card kpi"><div class="lbl">' + esc(x.sym) + ' — Score</div><div class="num">' + (x.total != null ? x.total + " / 10" : "—") + '</div><div class="chg ' + ((x.t || 0) >= 6 ? "up" : "hold") + '">' + esc(((x.r || [])[0]) || "") + "</div></div>";
        });
        ks.innerHTML = h;
      }
      var cards = $$(".card", v);
      var fc = cards.filter(function (x) { return /Piotroski|F-Score|Signals/i.test($(".sh2", x) ? $(".sh2", x).textContent : ""); })[0] || cards[cards.length - 1];
      if (fc && top.length) {
        var sh = $(".sh2", fc);
        if (sh) sh.textContent = "Signal drill — " + top[0].sym;
        var body = $("div[style]", fc);
        if (body) {
          var h = "";
          (top[0].r || []).slice(0, 6).forEach(function (r) { h += '<div class="zrow"><span>' + esc(r) + '</span><b class="up">✓</b></div>'; });
          if (h) body.innerHTML = h;
        }
      }
    }).catch(function () {});
  }

  /* ---------- 12) company card ---------- */
  function wireCompany(st) {
    var v = sec("v-company");
    if (!v) return;
    var inp = $("input[type=search]", v);
    if (!inp) return;
    function show(sym) {
      sym = (sym || "").trim().toUpperCase();
      var x = PM[sym];
      if (!x) return false;
      var f = FUND[sym] || {};
      var ks = $(".kpis", v);
      var pos = 100 + (x.from_52w_high_pct || 0);
      if (ks) {
        ks.innerHTML =
          kpi(sym, "₹" + num(x.price), x.change_pct) +
          '<div class="card kpi"><div class="lbl">Market Cap</div><div class="num">' + mcap(f["Market Cap"]) + '</div><div class="chg hold">' + esc((x.industry || (f.k || "")).slice(0, 24) || "—") + "</div></div>" +
          '<div class="card kpi"><div class="lbl">P/E · P/B</div><div class="num">' + (f["Stock P/E"] != null ? f["Stock P/E"] : "—") + " · " + (f["Book Value"] && x.price ? (x.price / f["Book Value"]).toFixed(1) : "—") + '</div><div class="chg hold">sector data</div></div>' +
          '<div class="card kpi"><div class="lbl">52W Range</div><div class="num" style="font-size:16px">' + num(x.low_52w, 0) + " – " + num(x.high_52w, 0) + '</div><div class="chg ' + (pos > 70 ? "up" : "hold") + '">' + Math.max(0, Math.round(pos)) + "% of high</div></div>";
      }
      var cards = $$(".grid2 .card", v);
      if (cards[0]) {
        var sh = $(".sh2", cards[0]);
        var body = $("div[style]", cards[0]);
        if (sh) sh.textContent = "Snapshot — " + (NAME[sym] || sym);
        if (body) body.textContent = (NAME[sym] || sym) + " — price ₹" + num(x.price) + " (" + pctS(x.change_pct) + "). RSI(14) " + (x.rsi14 != null ? x.rsi14.toFixed(1) : "—") + ", EMA200 " + (x.above_ema200 ? "ke upar" : "ke neeche") + ", MACD hist " + (x.macd_hist != null ? x.macd_hist.toFixed(2) : "—") + ". 52w high se " + pctS(x.from_52w_high_pct) + " door.";
      }
      if (cards[1]) {
        var sh2 = $(".sh2", cards[1]);
        var body2 = $("div[style]", cards[1]);
        if (sh2) sh2.textContent = "Technical position — " + sym;
        if (body2) {
          var b = $(".breadth i", cards[1]);
          if (b) b.style.width = Math.max(2, Math.min(100, pos)) + "%";
          var m = $(".mono.s11", cards[1]);
          if (m) m.innerHTML = "RSI <b>" + (x.rsi14 != null ? x.rsi14.toFixed(0) : "—") + "</b> · 200DMA pos <b>" + Math.max(0, Math.round(pos)) + "%</b> · tier <b>" + (x.tier || "—") + "</b>";
        }
      }
      return true;
    }
    if (!inp.__ld) {
      inp.__ld = 1;
      inp.placeholder = "Search any stock — RELIANCE, TCS, INFY…";
      var t;
      inp.addEventListener("input", function () {
        clearTimeout(t);
        t = setTimeout(function () { show(inp.value); }, 250);
      });
    }
  }

  /* ---------- 13) portfolio (localStorage mbPortfolio — same as old app) ---------- */
  function renderPortfolio() {
    var v = sec("v-portfolio");
    if (!v) return;
    var rows = [];
    try { rows = JSON.parse(localStorage.getItem("mbPortfolio") || "[]") || []; } catch (e) { rows = []; }
    var ks = $(".kpis", v);
    var tb = $("tbody", v);
    if (!rows.length) {
      if (ks) ks.innerHTML =
        '<div class="card kpi"><div class="lbl">PORTFOLIO</div><div class="num" style="font-size:15px">Khali hai</div><div class="chg hold">0 holdings</div></div>' +
        '<div class="card kpi"><div class="lbl">TIP</div><div class="num" style="font-size:14px">Trades add karo</div><div class="chg hold">old app wala data aayega</div></div>';
      if (tb) tb.innerHTML = "<tr><td colspan='7' style='padding:14px;color:var(--dim)'>Abhi holdings nahi hain — pehle wale app (index-old.html) se add kiye the to yahan dikhen ge, same browser mein.</td></tr>";
      return;
    }
    var inv = 0, cur = 0, today = 0;
    var h = "";
    rows.forEach(function (r0) {
      var p = PM[r0.sym] ? PM[r0.sym].price : r0.avg;
      var chg = PM[r0.sym] ? PM[r0.sym].change_pct : 0;
      var pl = (p - r0.avg) * r0.qty, plp = r0.avg ? (p - r0.avg) / r0.avg * 100 : 0;
      var td = p - p / (1 + (chg || 0) / 100);
      inv += r0.avg * r0.qty; cur += p * r0.qty; today += td * r0.qty;
      h += "<tr><td>" + esc(r0.sym) + "</td><td>" + num(r0.qty, 0) + "</td><td>" + num(r0.avg, 0) + "</td><td>" + num(p) + "</td><td><span class='" + (pl >= 0 ? "up" : "dn") + "'>" + (pl >= 0 ? "+" : "−") + "₹" + num(Math.abs(pl), 0) + "</span></td><td><span class='" + (plp >= 0 ? "up" : "dn") + "'>" + pctS(plp) + "</span></td><td>" + sigFor(PM[r0.sym] || { change_pct: 0 }) + "</td></tr>";
    });
    var tot = cur - inv;
    if (ks) {
      ks.innerHTML =
        '<div class="card kpi"><div class="lbl">INVESTED</div><div class="num">₹' + num(inv, 0) + '</div><div class="chg hold">' + num(rows.length, 0) + " holdings</div></div>" +
        '<div class="card kpi"><div class="lbl">CURRENT</div><div class="num">₹' + num(cur, 0) + '</div><div class="chg ' + (tot >= 0 ? "up" : "dn") + '">' + ar(tot) + "</div></div>" +
        '<div class="card kpi"><div class="lbl">UNREALIZED P/L</div><div class="num ' + (tot >= 0 ? "up" : "dn") + '">' + (tot >= 0 ? "+" : "−") + "₹" + num(Math.abs(tot), 0) + '</div><div class="chg ' + (inv ? cl(tot / inv * 100) : "") + '">' + (inv ? pctS(tot / inv * 100) : "—") + "</div></div>" +
        '<div class="card kpi"><div class="lbl">TODAY</div><div class="num ' + (today >= 0 ? "up" : "dn") + '">' + (today >= 0 ? "+" : "−") + "₹" + num(Math.abs(today), 0) + '</div><div class="chg hold">' + num(rows.length, 0) + " holdings</div></div>";
    }
    if (tb) tb.innerHTML = h;
  }

  /* ---------- 14) AI brain ---------- */
  function renderAIBrain() {
    var v = sec("v-aibrain");
    if (!v) return;
    Promise.all([fj("data/mood.json"), fj("data/indices-all.json"), fj("data/futures.json"), fj("data/crypto.json")].map(function (p) { return p.catch(function () { return null; }); })).then(function (rs) {
      var mood = rs[0] || {}, idx = rs[1] || {}, fut = rs[2] || {}, cry = rs[3] || {};
      var vx = null;
      ((idx.indices || [])).forEach(function (x) { if (/vix/i.test(x.index || x.symbol || "")) vx = x; });
      var pcr = (fut.pcr || {}).nifty_pcr_oi;
      var fg = (cry.fear_greed || {}).value;
      var ov = mood.overall != null ? mood.overall : null;
      var tag = mood.tag || "—";
      var lean = /bull/i.test(tag) ? "BULLISH LEAN" : /bear/i.test(tag) ? "BEARISH LEAN" : "NEUTRAL LEAN";
      var cards = $$(".grid2 > .card", v);
      if (cards[0]) {
        var body = $("div[style]", cards[0]);
        if (body) {
          var nn = $(".num", body), br = $(".breadth i", body), mm = $(".mono.s11", body);
          if (nn) { nn.textContent = lean; nn.className = "num " + (/bull/i.test(tag) ? "up" : /bear/i.test(tag) ? "dn" : "hold"); nn.style.fontSize = "24px"; }
          if (br) br.style.width = Math.max(2, Math.min(100, ov != null ? ov : 50)) + "%";
          if (mm) mm.textContent = "news mood " + (ov != null ? ov + "/100" : "—") + " · " + (mood.counted || 0) + " headlines scanned · " + tag;
        }
      }
      if (cards[1]) {
        var body2 = $("div[style]", cards[1]);
        if (body2) {
          var kk = $$(".kpi", body2);
          if (kk[0]) kk[0].innerHTML = '<div class="lbl">VIX</div><div class="num" style="font-size:17px">' + (vx ? num(vx.price) : "—") + "</div>";
          if (kk[1]) kk[1].innerHTML = '<div class="lbl">PCR</div><div class="num" style="font-size:17px">' + (pcr != null ? pcr : "—") + "</div>";
          if (kk[2]) kk[2].innerHTML = '<div class="lbl">RISK</div><div class="num ' + (ov != null && ov < 35 ? "dn" : "hold") + '" style="font-size:17px">' + (ov != null ? (ov < 35 ? "HIGH" : ov > 65 ? "LOW" : "MED") : "—") + "</div>";
        }
      }
      var rot = $$(".card", v).filter(function (x) { return /Rotation|Report/i.test($(".sh2", x) ? $(".sh2", x).textContent : ""); })[0];
      if (rot) {
        var body3 = $("div[style]", rot);
        if (body3) {
          var pos = (mood.pos || []).slice(0, 2).map(function (x) { return x.t || ""; }).join(" ");
          var neg = (mood.neg || []).slice(0, 2).map(function (x) { return x.t || ""; }).join(" ");
          body3.textContent = "Mood " + tag + " (" + (ov != null ? ov + "/100" : "—") + "). " +
            (pos ? "Positive: " + pos + ". " : "") + (neg ? "Negative: " + neg + ". " : "") +
            "Fear/Greed index " + (fg != null ? fg : "—") + ". Report daily update hota hai.";
        }
      }
    });
  }

  /* ---------- boot ---------- */
  function boot() {
    try { renderHome(); } catch (e) {}
    try { loadScreenerData(); } catch (e) {}
    try { renderIPO(); } catch (e) {}
    try { renderNews(); } catch (e) {}
    try { renderGlobal(); } catch (e) {}
    try { renderCrypto(); } catch (e) {}
    try { renderEvents(); } catch (e) {}
    try { renderFilings(); } catch (e) {}
    try { renderFutures(); } catch (e) {}
    try { renderMF(); } catch (e) {}
    try { renderGTI(); } catch (e) {}
    try { renderForecast(); } catch (e) {}
    try { renderDeep(); } catch (e) {}
    try { renderAIBrain(); } catch (e) {}
  }
  if (document.readyState === "loading") addEventListener("DOMContentLoaded", boot);
  else boot();

  /* har 5 min refresh — bots data update karte rehte hain */
  setInterval(function () {
    try { renderHome(); } catch (e) {}
    try { loadScreenerData(); } catch (e) {}
    try { renderIPO(); } catch (e) {}
    try { renderNews(); } catch (e) {}
    try { renderGlobal(); } catch (e) {}
    try { renderCrypto(); } catch (e) {}
    try { renderAIBrain(); } catch (e) {}
  }, 5 * 60 * 1000);
})();
