/* Arthasaar livedata.js — demo UI + REAL data
   Sources: data/*.json + ipo/data.json (bots in auto-update karte hain)
   UI markup/classes demo jaisi hi — sirf numbers real. */
(function () {
  "use strict";

  /* ---------- helpers ---------- */
  function $(s, r) { return (r || document).querySelector(s); }
  function $$(s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); }
  function q1(s, r) { var L = (r || document).querySelectorAll(s); return L && L.length ? L[0] : null; }
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
  /* repo private hai: data cdnfix.js ke through /api/data proxy se aata hai */
  function fj(p) {
    return fetch(p + "?t=" + Date.now()).then(function (r) {
      if (!r.ok) throw new Error("data " + r.status + " " + p);
      return r.json();
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
      var n = by["NIFTY 50"] || {}, se = by["SENSEX"] || by["BSE SENSEX"] || null, bn = by["BANK NIFTY"] || by["BANKNIFTY"] || by["NIFTY BANK"] || {}, vx = by["INDIA VIX"] || {};
      var k = sec("v-home") ? $(".kpis", sec("v-home")) : null;
      var draw = function (seX) {
        if (k) {
          k.innerHTML =
            kpi("NIFTY 50", num(n.price), n.change_pct, n.change) +
            kpi("SENSEX", num(seX.price), seX.change_pct, seX.change) +
            kpi("BANK NIFTY", num(bn.price), bn.change_pct, bn.change) +
            kpi("INDIA VIX", num(vx.price), vx.change_pct);
        }
      };
      if (se) { draw({ price: se.price, change_pct: se.change_pct, change: se.change }); }
      else {
        /* SENSEX indices-all mein nahi — candles se */
        draw({ price: null, change_pct: null });
        fj("data/candles.json").then(function (c) {
          var s = ((c || {}).syms || {})["SENSEX"];
          if (!s) return;
          var m = s["1m"] || s["5m"] || s["15m"] || s["1h"];
          if (!m || !m.c || !m.c.length) return;
          var last = m.c[m.c.length - 1];
          var pc2 = s.pc != null ? s.pc : m.c[0];
          var chg = last - pc2;
          draw({ price: last, change_pct: pc2 ? chg / pc2 * 100 : null, change: chg });
        }).catch(function () {});
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
  function parseBrainCsv(csv) {
    var lines = String(csv || "").split(/\r?\n/).filter(function (x) { return x.trim(); });
    if (!lines.length) return { stocks: [] };
    var head = lines[0].split(",");
    function row(s) {
      var out = [], cur = "", q = false;
      for (var i = 0; i < s.length; i++) {
        var ch = s[i];
        if (ch === '"') { if (q && s[i + 1] === '"') { cur += '"'; i++; } else q = !q; }
        else if (ch === "," && !q) { out.push(cur); cur = ""; }
        else cur += ch;
      }
      out.push(cur);
      var o = {};
      head.forEach(function (k, i) { o[k] = out[i] == null ? "" : out[i]; });
      ["tier","price","change_pct","high_52w","low_52w","high_200d","low_200d","from_52w_high_pct","ema20","ema200","rsi14","macd","macd_signal","macd_hist","vol_vs_avg20","consec_days","history_days"].forEach(function (k) {
        if (o[k] !== "") { var z = Number(o[k]); if (!isNaN(z)) o[k] = z; }
      });
      ["above_ema200"].forEach(function (k) { if (o[k] !== "") o[k] = String(o[k]).toLowerCase() === "true"; });
      return o;
    }
    return { stocks: lines.slice(1).map(row).filter(function (x) { return x.symbol; }) };
  }
  function loadScreenerData(cb) {
    fj("data/brain-screener.json").then(function (d) {
      var st = d.stocks || [];
      if (st.length) return st;
      throw new Error("brain-screener.json empty");
    }).catch(function () {
      return fj("data/brain-screener.csv").then(function (csv) {
        return parseBrainCsv(csv).stocks;
      });
    }).then(function (st) {
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
  var SCR_CHIP = "all", VOLSET = null;
  function applyScr() {
    var v = sec("v-screener");
    if (!v) return;
    var qi = document.getElementById("qScr");
    var q = (qi && qi.value || "").toLowerCase();
    $$("#scrBody tr").forEach(function (r) {
      var ok = true;
      if (SCR_CHIP.indexOf("large") > -1) ok = r.getAttribute("data-tier") === "1";
      else if (SCR_CHIP.indexOf("mid") > -1) ok = r.getAttribute("data-tier") === "2";
      else if (SCR_CHIP.indexOf("52w") > -1) ok = parseFloat(r.getAttribute("data-f52") || "0") >= -3;
      else if (SCR_CHIP.indexOf("volume") > -1) ok = r.getAttribute("data-vol") === "1";
      if (ok && q) ok = r.textContent.toLowerCase().indexOf(q) > -1;
      r.style.display = ok ? "" : "none";
    });
  }
  function wireScreenerChips() {
    var v = sec("v-screener");
    if (!v) return;
    var chips = $(".chips", v);
    if (chips && !chips.__ldc) {
      chips.__ldc = 1;
      chips.addEventListener("click", function (e) {
        var t = e.target.closest(".fch");
        if (!t) return;
        $$("span", chips).forEach(function (x) { x.classList.toggle("on", x === t); });
        SCR_CHIP = t.textContent.trim().toLowerCase();
        applyScr();
      });
    }
    if (VOLSET === null) {
      VOLSET = {};
      fj("data/radar.json").then(function (r) {
        (((r || {}).volume_blast) || []).forEach(function (x) { VOLSET[x.sym] = 1; });
      }).catch(function () {});
    }
    var qi = document.getElementById("qScr");
    if (qi && !qi.__ldscr) {
      qi.__ldscr = 1;
      qi.addEventListener("input", function () { setTimeout(applyScr, 0); });
    }
  }
  function renderScreenerTable(st) {
    var b = sec("scrBody");
    if (!b) return;
    var h2 = sec("v-screener") ? $("h2", sec("v-screener")) : null;
    if (h2) h2.textContent = "Screener — " + num(st.length, 0) + " stocks";
    fj("data/stock-scores.json").then(function (sc) {
      (sc.top || []).forEach(function (x) { SCRSIG[x.sym] = x; });
    }).catch(function () {}).then(function () {
      var rows = st.slice().sort(function (a, b2) { return Math.abs(b2.change_pct || 0) - Math.abs(a.change_pct || 0); }).slice(0, 100);
      var vols = VOLSET || {};
      var h = "";
      rows.forEach(function (x) {
        var f = FUND[x.symbol] || {};
        var sig = sigFor(x);
        var mc = f["Market Cap"] != null ? mcap(f["Market Cap"]) : "—";
        h += "<tr data-tier=\"" + (x.tier || 3) + "\" data-f52=\"" + (x.from_52w_high_pct != null ? x.from_52w_high_pct : 0) + "\" data-vol=\"" + (vols[x.symbol] ? 1 : 0) + "\"><td>" + esc(x.symbol) + "</td><td>" + num(x.price) + "</td><td>" + sp(x.change_pct) + "</td><td>" + mc + "</td><td>" + (f["Stock P/E"] != null ? f["Stock P/E"] : "—") + "</td><td>" + (f.ROE != null ? f.ROE + "%" : (f.ROCE != null ? f.ROCE + "%" : "—")) + "</td><td>" + sig + "</td></tr>";
      });
      b.innerHTML = h;
      applyScr();
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
      h += "<tr><td>" + esc(NAME[sym] || sym) + " <small>( " + esc(sym) + " )</small></td><td>" + mcap(f["Market Cap"]) + "</td><td>" + (f["Stock P/E"] != null ? f["Stock P/E"] : "—") + "</td><td>" + pb + "</td><td>" + (f.ROE != null ? f.ROE + "%" : "—") + "</td><td>" + (f.ROCE != null ? f.ROCE + "%" : "—") + "</td><td>" + (f["D/E"] != null ? f["D/E"] : "—") + "</td><td>" + (f["Dividend Yield"] != null ? f["Dividend Yield"] + "%" : "—") + "</td></tr>";
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
      var mv = v.querySelector(".card");
      var sh2s = v.querySelectorAll(".card .sh2");
      for (var ci = 0; ci < sh2s.length; ci++) { var sh2 = sh2s[ci]; if (/Model View/i.test(sh2.textContent)) { mv = sh2.closest(".card"); break; } }
      if (mv) {
        var body = mv.querySelector("div[style]");
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
    function findSym(q) {
      q = (q || "").trim().toUpperCase();
      if (!q) return null;
      if (PM[q]) return q;
      var ks = Object.keys(PM);
      var i;
      for (i = 0; i < ks.length; i++) if (ks[i].indexOf(q) === 0) return ks[i];
      for (i = 0; i < ks.length; i++) if (String(NAME[ks[i]] || "").toUpperCase().indexOf(q) > -1) return ks[i];
      return null;
    }
    function show(sym) {
      sym = findSym(sym);
      var x = sym ? PM[sym] : null;
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
        var sh = q1(".sh2", cards[0]);
        var body = q1("div[style]", cards[0]);
        if (sh) sh.textContent = "Snapshot — " + (NAME[sym] || sym);
        if (body) body.textContent = (NAME[sym] || sym) + " — price ₹" + num(x.price) + " (" + pctS(x.change_pct) + "). RSI(14) " + (x.rsi14 != null ? x.rsi14.toFixed(1) : "—") + ", EMA200 " + (x.above_ema200 ? "ke upar" : "ke neeche") + ", MACD hist " + (x.macd_hist != null ? x.macd_hist.toFixed(2) : "—") + ". 52w high se " + pctS(x.from_52w_high_pct) + " door." + (function () { try { var f2 = fcFind(sym); if (f2 && f2.median_end != null) return " AI 21-din forecast: \u20b9" + num(f2.median_end, 0) + " (" + pctS(f2.median_chg_pct) + ")."; } catch (e) {} return ""; })();
      }
      if (cards[1]) {
        var sh2 = q1(".sh2", cards[1]);
        var body2 = q1("div[style]", cards[1]);
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


  /* ---------- 15) real charts (candles.json se) ---------- */
  var CH = { sym: "NIFTY" };
  var CH_TFS = [["1D\u00b75m", "5m", 75], ["3D\u00b715m", "15m", 75], ["1W\u00b71h", "1h", 30], ["2M\u00b71h", "1h", 0], ["1D\u00b71m", "1m", 0]];
  var CH_TF = "1D\u00b75m";
  function chPath(c) {
    var n = c.length;
    if (!n) return "";
    var mn = Math.min.apply(null, c), mx = Math.max.apply(null, c);
    if (mx === mn) { mx += 1; mn -= 1; }
    var pts = [];
    for (var i = 0; i < n; i++) {
      var x = (i / (n - 1 || 1)) * 800;
      var y = 150 - ((c[i] - mn) / (mx - mn)) * 130;
      pts.push(x.toFixed(1) + "," + y.toFixed(1));
    }
    return "M" + pts.join("L");
  }
  function chDraw(v, syms, sym, tfLabel) {
    var def = CH_TFS.filter(function (t) { return t[0] === tfLabel; })[0] || CH_TFS[0];
    var s = syms[sym];
    var m = s && (s[def[1]] || s["5m"] || s["15m"] || s["1h"] || s["1m"]);
    var card = $(".card", v);
    if (!m || !card) return;
    var c = m.c.slice(def[2] ? -def[2] : 0);
    var h = m.h.slice(def[2] ? -def[2] : 0);
    var l = m.l.slice(def[2] ? -def[2] : 0);
    var up = c[c.length - 1] >= c[0];
    var col = up ? "var(--up)" : "var(--dn)";
    var chg = (c[c.length - 1] - c[0]) / c[0] * 100;
    var sh = $(".sh2", card);
    if (sh) {
      sh.innerHTML = esc(sym) + " \u00b7 " + esc(tfLabel) + " " +
        "<span class=\"" + (up ? "up" : "dn") + "\">" + pctS(chg) + "</span>" +
        '<span class="fr">H ' + num(Math.max.apply(null, h), 0) + " \u00b7 L " + num(Math.min.apply(null, l), 0) + "</span>";
    }
    var svg = $("svg", card);
    if (svg) {
      var p = chPath(c);
      svg.innerHTML = '<path d="M0 30H800M0 85H800M0 140H800" class="gl"/>' +
        '<path d="' + p + 'V170H0Z" fill="' + col + '" opacity=".12"/>' +
        '<path d="' + p + '" fill="none" stroke="' + col + '" stroke-width="2.5"/>';
    }
  }
  function renderCharts() {
    var v = sec("v-gticharts");
    if (!v) return;
    fj("data/candles.json").then(function (d) {
      var syms = (d && d.syms) || {};
      var names = Object.keys(syms);
      if (!names.length) return;
      var chips = $(".chips", v);
      if (!chips) return;
      /* symbol chips row — demo style hi */
      if (!v.__symRow) {
        var sr = document.createElement("div");
        sr.className = "chips";
        sr.style.margin = "6px 0 0";
        v.insertBefore(sr, chips);
        v.__symRow = sr;
      }
      v.__symRow.innerHTML = names.map(function (s) {
        return '<span class="fch' + (s === CH.sym ? " on" : "") + '" data-sym="' + esc(s) + '">' + esc(s) + "</span>";
      }).join("");
      v.__symRow.onclick = function (e) {
        var t = e.target.closest("[data-sym]");
        if (!t) return;
        CH.sym = t.getAttribute("data-sym");
        $$("span", v.__symRow).forEach(function (x) { x.classList.toggle("on", x === t); });
        chDraw(v, syms, CH.sym, CH_TF);
      };
      /* TF chips */
      chips.innerHTML = CH_TFS.map(function (t) {
        return '<span class="fch' + (t[0] === CH_TF ? " on" : "") + '" data-tf="' + t[0] + '">' + t[0] + "</span>";
      }).join("");
      chips.onclick = function (e) {
        var t = e.target.closest("[data-tf]");
        if (!t) return;
        CH_TF = t.getAttribute("data-tf");
        $$("span", chips).forEach(function (x) { x.classList.toggle("on", x === t); });
        chDraw(v, syms, CH.sym, CH_TF);
      };
      chDraw(v, syms, CH.sym, CH_TF);
      /* placeholder hataya — BANKNIFTY second chart */
      var ph = null;
      $$(".sect", v).forEach(function (s) { if (/REPO VERSION|TradingView/i.test(s.textContent)) ph = s; });
      if (ph) {
        var card2 = document.createElement("div");
        card2.className = "card";
        card2.style.marginTop = "10px";
        card2.innerHTML = '<div class="sh2">BANKNIFTY \u00b7 1D</div><div style="padding:10px 12px"><svg viewBox="0 0 800 170" preserveAspectRatio="none" style="width:100%;height:160px"></svg></div>';
        v.replaceChild(card2, ph);
        var s2 = syms["BANKNIFTY"] || syms[names[1]] || syms[names[0]];
        if (s2) {
          var m2 = s2["5m"] || s2["15m"] || s2["1h"];
          var c2 = m2.c.slice(-75), h2 = m2.h.slice(-75), l2 = m2.l.slice(-75);
          var up2 = c2[c2.length - 1] >= c2[0];
          var col2 = up2 ? "var(--up)" : "var(--dn)";
          var chg2 = (c2[c2.length - 1] - c2[0]) / c2[0] * 100;
          var sh2 = $(".sh2", card2);
          if (sh2) sh2.innerHTML = "BANKNIFTY \u00b7 1D <span class=\"" + (up2 ? "up" : "dn") + "\">" + pctS(chg2) + "</span>" +
            '<span class="fr">H ' + num(Math.max.apply(null, h2), 0) + " \u00b7 L " + num(Math.min.apply(null, l2), 0) + "</span>";
          var svg2 = $("svg", card2);
          var p2 = chPath(c2);
          if (svg2) svg2.innerHTML = '<path d="M0 30H800M0 85H800M0 140H800" class="gl"/>' +
            '<path d="' + p2 + 'V170H0Z" fill="' + col2 + '" opacity=".12"/>' +
            '<path d="' + p2 + '" fill="none" stroke="' + col2 + '" stroke-width="2.5"/>';
        }
      }
    }).catch(function () {});
  }

  /* ---------- 16) generic search filters (fundamentals + MF + crypto + filings) ---------- */
  function wireFilters() {
    [["v-fundamentals", "tbody"], ["v-mf", "tbody"], ["v-crypto", "tbody"], ["v-events", "tbody"], ["v-filings", "tbody"]].forEach(function (p) {
      var v = sec(p[0]);
      if (!v) return;
      var inp = $("input[type=search]", v);
      var tb = $(p[1], v);
      if (!inp || !tb || inp.__ldf) return;
      inp.__ldf = 1;
      inp.addEventListener("input", function () {
        var q = inp.value.toLowerCase();
        $$("tr", tb).forEach(function (r) { r.style.display = !q || r.textContent.toLowerCase().indexOf(q) > -1 ? "" : "none"; });
      });
    });
  }

  /* ---------- 17) Learn studies heatmap (index-history se real monthly returns) ---------- */
  function renderLearn() {
    var v = sec("v-learn");
    if (!v) return;
    var heat = null;
    $$(".heat", v).forEach(function (h2) { if (!heat && /STUDIES/.test((h2.previousElementSibling || {}).textContent || "")) heat = h2; });
    if (!heat) heat = $$(".heat", v)[0];
    if (!heat) return;
    fj("data/index-history.json").then(function (d) {
      var ix = (d.indices || []).filter(function (x) { return /nifty/i.test(x.key) && !/bank/i.test(x.key); })[0] || (d.indices || [])[0];
      if (!ix) return;
      var out = [];
      Object.keys(ix.years).sort().forEach(function (y) {
        Object.keys(ix.years[y]).sort().forEach(function (m) { out.push([y, m, ix.years[y][m]]); });
      });
      var last12 = out.slice(-12);
      var MN = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
      var h = "";
      last12.forEach(function (r2) {
        var vv = r2[2];
        h += '<div class="hc" style="background:color-mix(in srgb,var(' + (vv >= 0 ? "up" : "dn") + ') ' + Math.min(20, 4 + Math.abs(vv) * 2).toFixed(0) + '%,var(--surface))"><b>' + MN[parseInt(r2[1], 10) - 1] + " '" + r2[0].slice(2) + "</b><span class='" + cl(vv) + "'>" + pctS(vv) + "</span></div>";
      });
      if (h) heat.innerHTML = h;
    }).catch(function () {});
  }


  /* ---------- 18) fundamentals DEEP search - company summary card ---------- */
  var CIDX = null;
  function plRow(rows, label) {
    for (var i = 0; i < rows.length; i++) {
      if (String(rows[i][0] || "").replace(/\+$/, "").trim().toLowerCase() === label) return rows[i];
    }
    return null;
  }
  function lookupCompany(q, card) {
    if (!q || q.length < 2 || !CIDX) { card.style.display = "none"; return; }
    var sym = null;
    if (CIDX[q.toUpperCase()]) sym = q.toUpperCase();
    else {
      var ks = Object.keys(CIDX);
      for (var i = 0; i < ks.length; i++) {
        if (String(CIDX[ks[i]].name || "").toLowerCase().indexOf(q) > -1) { sym = ks[i]; break; }
      }
    }
    if (!sym) { card.style.display = "none"; return; }
    fj("data/companies/" + sym + ".json").then(function (c) {
      if (!c || !c.name) { card.style.display = "none"; return; }
      var top = c.top || {}, pr = c.profile || {};
      var h = '<div class="sh2">' + esc(c.name) + " <small>(" + esc(c.symbol) + ')</small><span class="fr">' + esc(pr.sector || "") + " \u00b7 " + esc(pr.industry || "") + "</span></div>";
      h += '<div style="padding:10px 14px 4px;font-size:12px;line-height:1.7;color:var(--dim)">' + esc((c.about || "").slice(0, 420)) + "\u2026</div>";
      var kv = [["Market Cap", top["Market Cap"]], ["Price", "\u20b9" + (top["Current Price"] || "\u2014")], ["P/E", top["Stock P/E"]], ["ROCE", top["ROCE"]], ["ROE", top["ROE"]], ["Div Yield", top["Dividend Yield"]], ["52w H/L", top["High / Low"]], ["Book Value", "\u20b9" + (top["Book Value"] || "\u2014")]];
      h += '<div class="kpis" style="margin-top:8px">';
      kv.forEach(function (x) {
        h += '<div class="card kpi"><div class="lbl">' + esc(x[0]) + '</div><div class="num" style="font-size:15px">' + esc(String(x[1] != null ? x[1] : "\u2014")) + "</div></div>";
      });
      h += "</div>";
      var PL = c.profit_loss || [], RT = c.ratios || [];
      var yrs = PL[0] || [];
      var cols = [];
      for (var ci = Math.max(1, yrs.length - 5); ci < yrs.length; ci++) cols.push(ci);
      var defs = [[PL, "sales", "Sales"], [PL, "operating profit", "Op Profit"], [PL, "net profit", "Net Profit"], [PL, "opm %", "OPM %"], [RT, "roce %", "ROCE %"]];
      var anyRow = false;
      var tbl = '<div class="card" style="margin-top:10px;padding:0;overflow:auto"><table><thead><tr><th>10Y</th>';
      cols.forEach(function (ci2) { tbl += "<th>" + esc(String(yrs[ci2])) + "</th>"; });
      tbl += "</tr></thead><tbody>";
      defs.forEach(function (d) {
        var r = plRow(d[0], d[1]);
        if (!r) return;
        anyRow = true;
        tbl += "<tr><td>" + esc(d[2]) + "</td>";
        cols.forEach(function (ci2) { tbl += "<td>" + esc(String(r[ci2] != null ? r[ci2] : "\u2014")) + "</td>"; });
        tbl += "</tr>";
      });
      tbl += "</tbody></table></div>";
      if (anyRow) h += tbl;
      var SH = c.shareholding || [];
      if (SH.length > 1) {
        var lastCol = SH[0].length - 1;
        h += '<div class="card" style="margin-top:10px"><div class="sh2">Shareholding \u2014 ' + esc(String(SH[0][lastCol] || "")) + '</div><div style="padding:6px 14px 10px">';
        ["promoters", "fiis", "diis", "public"].forEach(function (k2) {
          var r = plRow(SH, k2);
          if (r) h += '<div class="zrow"><span>' + esc(String(r[0]).replace("+", "").trim()) + "</span><b>" + esc(String(r[lastCol])) + "</b></div>";
        });
        h += "</div></div>";
      }
      h += '<div style="padding:8px 14px 12px;font-size:11px;opacity:.6">Source: ' + esc(c.source || "screener.in") + " \u00b7 updated " + esc(String(c.updated || "").slice(0, 16)) + " \u00b7 <a href='" + esc(c.url || "#") + "' target='_blank' style='color:var(--accent)'>screener.in</a></div>";
      card.innerHTML = h;
      card.style.display = "";
    }).catch(function () { card.style.display = "none"; });
  }
  function renderCompanySummary() {
    var v = sec("v-fundamentals");
    if (!v) return;
    var inp = $("input[type=search]", v);
    if (!inp) return;
    inp.placeholder = "Company naam ya symbol \u2014 RELIANCE, Aarti, TCS\u2026";
    if (!CIDX) fj("data/company-index.json").then(function (d) { CIDX = d; }).catch(function () {});
    if (inp.__ldcs) return;
    inp.__ldcs = 1;
    var card = document.createElement("div");
    card.className = "card";
    card.style.margin = "0 0 10px";
    card.style.display = "none";
    var srow = $(".srow", v);
    if (srow && srow.parentNode) srow.parentNode.insertBefore(card, srow.nextSibling);
    var t = null;
    inp.addEventListener("input", function () {
      clearTimeout(t);
      var q = inp.value.trim().toLowerCase();
      t = setTimeout(function () { lookupCompany(q, card); }, 350);
    });
  }

  /* ---------- 19) MF live search (8,668 funds) ---------- */
  var MFALL = null, MFTOP = {};
  function mfSearch(q) {
    var v = sec("v-mf");
    if (!v || !MFALL) return;
    var tb = $("tbody", v);
    if (!tb) return;
    if (!q || q.length < 2) return;
    var out = [];
    for (var i = 0; i < MFALL.length && out.length < 15; i++) {
      var f = MFALL[i];
      if ((f.n || "").toLowerCase().indexOf(q) > -1 || (f.c || "").indexOf(q) === 0) out.push(f);
    }
    var h = "";
    out.forEach(function (f) {
      var tp = MFTOP[f.c] || {};
      var parts = String(f.n || "").split("\u00b7").map(function (s) { return s.trim(); });
      var plan = parts[1] || "";
      h += "<tr><td>" + esc(parts[0]) + (plan ? " <small>(" + esc(plan) + ")</small>" : "") + " <small>\u00b7 " + esc(f.k || f.h || "") + "</small></td><td>\u20b9" + (f.v != null ? f.v.toFixed(4) : "\u2014") + "</td><td>" + (tp.r1 != null ? sp(tp.r1) : "\u2014") + "</td><td>" + (tp.r3 != null ? sp(tp.r3) : "\u2014") + "</td><td>" + (tp.r5 != null ? sp(tp.r5) : "\u2014") + "</td></tr>";
    });
    if (h) tb.innerHTML = h;
  }
  function wireMF() {
    var v = sec("v-mf");
    if (!v) return;
    var inp = $("input", v);
    if (!inp) return;
    if (!MFALL) {
      fj("data/mf.json").then(function (d) { MFALL = d.funds || []; }).catch(function () {});
      fj("data/mf-top.json").then(function (d) { (d.funds || []).forEach(function (f) { MFTOP[f.c] = f; }); }).catch(function () {});
    }
    if (inp.__ldm) return;
    inp.__ldm = 1;
    inp.placeholder = "Fund dhoondo \u2014 naam ya code (bluechip / hdfc / 120502)";
    inp.addEventListener("input", function () {
      clearTimeout(inp.__t);
      var q = inp.value.trim().toLowerCase();
      inp.__t = setTimeout(function () { mfSearch(q); }, 300);
    });
  }

  /* ---------- 20) Economy Radar + Smart Money Radar ---------- */
  function renderEconomy() {
    var v = sec("v-news");
    if (!v) return;
    Promise.all([fj("data/economy-pulse.json"), fj("data/macro.json")].map(function (p) { return p.catch(function () { return null; }); })).then(function (rs) {
      var ep = rs[0] || {}, mc = rs[1] || {};
      var card = v.__econ;
      if (!card) {
        card = document.createElement("div");
        card.className = "card";
        card.style.margin = "0 0 10px";
        var g = $(".grid3", v);
        if (g && g.parentNode) v.insertBefore(card, g);
        v.__econ = card;
      }
      var h = '<div class="sh2">Economy Radar <span class="fr">' + esc(String(ep.updated || "").slice(0, 10)) + "</span></div>" + '<div style="padding:6px 14px 10px">';
      (ep.ind || []).forEach(function (x) {
        h += '<div class="zrow"><span>' + esc(x.icon || "\u2022") + " " + esc(x.name) + "</span><b>" + esc(String(x.val)) + "</b></div>";
        if (x.sub) h += '<div class="zrow" style="border:0"><span style="opacity:.55;font-size:11px">' + esc(String(x.sub)) + "</span><span></span></div>";
      });
      var t2 = mc.today || {};
      var mb = [["Crude", t2.crude], ["Gold", t2.gold], ["USD/INR", t2.usdinr], ["US 10Y", t2.us10y], ["DXY", t2.dxy], ["FII net", t2.fii_net_cr != null ? t2.fii_net_cr + " Cr" : null]];
      h += '<div class="sect" style="margin:10px 0 4px">MACRO \u2014 TODAY</div>';
      mb.forEach(function (m) { h += '<div class="zrow"><span>' + m[0] + "</span><b>" + (m[1] != null ? m[1] : "\u2014") + "</b></div>"; });
      h += "</div>";
      card.innerHTML = h;
    });
  }
  function renderSmartRadar() {
    var v = sec("v-internals");
    if (!v) return;
    fj("data/radar.json").then(function (r) {
      if (!r) return;
      var card = v.__radar;
      if (!card) {
        card = document.createElement("div");
        card.className = "card";
        card.style.margin = "10px 0 0";
        var g = $(".grid3", v);
        if (g && g.parentNode) g.parentNode.insertBefore(card, g.nextSibling);
        v.__radar = card;
      }
      function col(list, title) {
        var h = '<div class="sect" style="margin:8px 0 4px">' + title + "</div>";
        (list || []).slice(0, 5).forEach(function (x) {
          h += '<div class="zrow"><span><b>' + esc(x.sym) + "</b> \u20b9" + num(x.close, 1) + " \u00b7 deliv " + (x.deliv != null ? x.deliv + "%" : "\u2014") + '</span><b class="' + (x.chg >= 0 ? "up" : "dn") + '">' + pctS(x.chg) + "</b></div>";
        });
        return h;
      }
      card.innerHTML = '<div class="sh2">Smart Money Radar \u2014 delivery + volume</div><div style="padding:6px 14px 10px">' +
        col(r.accumulation, "ACCUMULATION \u2014 smart paisa aa raha") +
        col(r.hidden_selling, "HIDDEN SELLING \u2014 sambhal") +
        col(r.volume_blast, "VOLUME BLAST \u2014 aaj ke shockers") +
        '<div style="font-size:11px;opacity:.6;padding-top:6px">' + esc(r.note || "") + " \u00b7 " + esc(String(r.date || "")) + "</div></div>";
    }).catch(function () {});
  }


  /* ---------- 22) legacy features: xray, preopen, circuits, bigplayer, results, stress ---------- */
  function renderLegacy() {
    /* X-ray verdict - AI Brain ke top par */
    fj("data/xray.json").then(function (d) {
      var v = sec("v-aibrain");
      if (!v) return;
      var card = v.__xray;
      if (!card) {
        card = document.createElement("div");
        card.className = "card";
        card.style.margin = "0 0 10px";
        var g2 = q1(".grid2", v);
        try { if (g2 && g2.parentNode) v.insertBefore(card, g2); else v.insertBefore(card, v.firstChild); } catch (e) { try { v.appendChild(card); } catch (e2) {} }
        v.__xray = card;
      }
      var h = '<div class="sh2">Market X-Ray <span class="fr">' + esc(String(d.date || "")) + "</span></div>" + '<div style="padding:8px 14px 12px">';
      h += '<div class="num ' + (String(d.vc || "").indexOf("ff8b8b") > -1 ? "dn" : "up") + '" style="font-size:15px;margin-bottom:6px">' + esc(d.verdict || "") + "</div>";
      h += '<div class="mono s11" style="color:var(--dim);margin-bottom:8px">' + esc(d.headline || "") + "</div>";
      (d.points || []).forEach(function (p) {
        h += '<div class="zrow"><span><b>' + esc(p.h || "") + "</b> \u2014 " + esc(String(p.t || "").slice(0, 160)) + '</span><b class="' + (p.c === "g" ? "up" : "dn") + '">' + (p.c === "g" ? "\u2713" : "\u2717") + "</b></div>";
      });
      h += "</div>";
      card.innerHTML = h;
      /* stress - crash monitor mein */
      fj("data/stress.json").then(function (s) {
        var g3 = $$(".grid2 > .card", v)[1];
        if (!g3) return;
        var body = $("div[style]", g3);
        if (body) {
          var kk = $$(".kpi", body);
          if (kk.length === 3) {
            var el = document.createElement("div");
            el.className = "card kpi";
            el.style.border = "0";
            el.innerHTML = '<div class="lbl">STRESS</div><div class="num" style="font-size:17px">' + (s.score != null ? s.score + "/100" : "\u2014") + '</div><div class="chg ' + (String(s.band || "").toLowerCase().indexOf("high") > -1 ? "dn" : "hold") + '">' + esc(s.band || "") + "</div>";
            body.appendChild(el);
          }
        }
      }).catch(function () {});
    }).catch(function () {});

    /* Preopen - screener ke top par */
    fj("data/preopen.json").then(function (p) {
      var v = sec("v-screener");
      if (!v) return;
      var card = v.__pre;
      if (!card) {
        card = document.createElement("div");
        card.className = "card";
        card.style.margin = "0 0 10px";
        var chips = $(".chips", v);
        if (chips && chips.parentNode) v.insertBefore(card, chips);
        v.__pre = card;
      }
      var h = '<div class="sh2">Preopen \u2014 IEP movers <span class="fr">' + esc(String((p.updated || "").slice(11, 16) || "")) + "</span></div>" + '<div style="padding:6px 14px 10px">';
      var gb = p.gainer_buckets || {}, lb = p.loser_buckets || {};
      h += '<div class="mono s11" style="margin-bottom:6px;color:var(--dim)">up 5%+: <b class="up">' + (gb.up_ge_5pct || 0) + "</b> \u00b7 up 2%+: <b class=\"up\">" + (gb.up_ge_2pct || 0) + "</b> \u00b7 down 5%+: <b class=\"dn\">" + (lb.down_ge_5pct || 0) + "</b> \u00b7 down 2%+: <b class=\"dn\">" + (lb.down_ge_2pct || 0) + "</b></div>";
      function col(list, cls) {
        var x = "";
        (list || []).slice(0, 4).forEach(function (s) {
          x += '<div class="zrow"><span><b>' + esc(s.symbol) + "</b> IEP \u20b9" + num(s.iep) + " (prev \u20b9" + num(s.prev_close, 1) + ')</span><b class="' + cls + '">' + pctS(s.change_pct) + "</b></div>";
        });
        return x;
      }
      h += col(p.top20_gainers, "up");
      h += col(p.top20_losers, "dn");
      h += "</div>";
      card.innerHTML = h;
    }).catch(function () {});

    /* Circuits + Big Player - internals mein */
    Promise.all([fj("data/circuits.json"), fj("data/bigplayer.json")].map(function (p) { return p.catch(function () { return null; }); })).then(function (rs) {
      var ci = rs[0], bp = rs[1];
      var v = sec("v-internals");
      if (!v) return;
      var card = v.__circ;
      if (!card) {
        card = document.createElement("div");
        card.className = "card";
        card.style.margin = "10px 0 0";
        var g4 = $(".grid3", v);
        var anchorEl = v.__radar || (g4 && g4.nextSibling) || null;
        if (anchorEl && anchorEl.parentNode) v.insertBefore(card, anchorEl);
        else v.appendChild(card);
        v.__circ = card;
      }
      var h = "";
      if (ci) {
        h += '<div class="sh2">Circuits \u2014 aaj <span class="fr">' + esc(String(ci.updated || "")) + "</span></div>" + '<div style="padding:6px 14px 4px">' +
          '<div class="zrow"><span>Upper circuits</span><b class="up">' + num(ci.n_uc, 0) + "</b></div>" +
          '<div class="zrow"><span>Lower circuits</span><b class="dn">' + num(ci.n_lc, 0) + "</b></div></div>";
      }
      if (bp) {
        h += '<div class="sh2" style="margin-top:8px">Big Player \u2014 bulk / block deals <span class="fr">' + esc(String(bp.updated || "")) + "</span></div>" + '<div style="padding:6px 14px 10px">';
        var bd = (bp.bulk || []).slice(0, 5);
        if (!bd.length) bd = (bp.block || []).slice(0, 5);
        bd.forEach(function (b2) {
          h += '<div class="zrow"><span><b>' + esc(b2.s) + "</b> \u20b9" + num(b2.t, 1) + "Cr \u00b7 " + esc(String((b2.c && b2.c[0]) || "deal")) + '</span><b class="dn">SELL</b></div>';
        });
        h += "</div>";
      }
      if (h) card.innerHTML = h;
    });

    /* Results calendar - events mein */
    fj("data/results.json").then(function (d) {
      var v = sec("v-events");
      if (!v) return;
      var card = v.__res;
      if (!card) {
        card = document.createElement("div");
        card.className = "card";
        card.style.margin = "10px 0 0";
        var tb = $("table", v);
        var tcard = tb ? (tb.closest ? tb.closest(".card") : null) : null;
        if (tcard && tcard.parentNode) tcard.parentNode.insertBefore(card, tcard.nextSibling);
        else if (tb && tb.parentNode) tb.parentNode.insertBefore(card, tb.nextSibling);
        v.__res = card;
      }
      var h = '<div class="sh2">Earnings \u2014 ' + esc(d.quarter || "") + ' <span class="fr">' + esc(String(d.updated || "")) + "</span></div>" + '<div style="padding:6px 14px 10px">';
      (d.results || []).forEach(function (r2) {
        h += '<div class="zrow"><span><b>' + esc(r2.company) + "</b>" + (r2.div ? " \u00b7 " + esc(r2.div) : "") + '</span><b>' + esc(String(r2.date).slice(5)) + "</b></div>";
      });
      h += "</div>";
      card.innerHTML = h;
    }).catch(function () {});
  }

  /* ---------- 21) GTI hub — aaj ke zones mini cards ---------- */
  function renderGtiHub() {
    var v = sec("v-gti");
    if (!v || v.__gth) return;
    var trow = $(".trow", v);
    if (!trow) return;
    v.__gth = 1;
    var wrap = document.createElement("div");
    wrap.className = "grid3";
    wrap.style.marginTop = "10px";
    trow.parentNode.insertBefore(wrap, trow.nextSibling);
    fj("data/gti.json").then(function (d) {
      var syms = d.symbols || {};
      var want = ["NIFTY 50", "BANKNIFTY", "RELIANCE"];
      var h = "";
      want.forEach(function (w) {
        var x = syms[w];
        if (!x) return;
        var z = x.day_zones || {};
        var sd = z.SD || z.WD || [], ss = z.SS || z.WS || [];
        h += '<div class="card"><div class="sh2">' + esc(w) + '</div><div style="padding:6px 14px 10px">' +
          '<div class="zrow"><span>Price</span><b>' + (x.price != null ? num(x.price, 0) : "\u2014") + "</b></div>" +
          '<div class="zrow"><span>Demand</span><b class="up">' + (sd.length ? num(sd[0], 0) + " \u2013 " + num(sd[1], 0) : "\u2014") + "</b></div>" +
          '<div class="zrow"><span>Supply</span><b class="dn">' + (ss.length ? num(ss[0], 0) + " \u2013 " + num(ss[1], 0) : "\u2014") + "</b></div>" +
          '<div class="zrow"><span>POC day</span><b>' + (x.day_poc != null ? num(x.day_poc, 0) : "\u2014") + "</b></div></div></div>";
      });
      if (h) wrap.innerHTML = h;
    }).catch(function () {});
  }


  /* ---------- 23) Options chain / greeks (futures section mein) ---------- */
  var OPTS = null, OPT_SYM = "NIFTY";
  function renderOptions() {
    var v = sec("v-futures");
    if (!v) return;
    if (!OPTS) {
      fj("data/greeks.json").then(function (d) { OPTS = d; drawOpt(); }).catch(function () {});
    } else drawOpt();
    function drawOpt() {
      if (!OPTS || !OPTS.u) return;
      var names = Object.keys(OPTS.u);
      var card = v.__opt;
      if (!card) {
        card = document.createElement("div");
        card.className = "card";
        card.style.margin = "10px 0 0";
        card.style.padding = "0";
        card.style.overflow = "auto";
        var tb = q1("table", v);
        try {
          if (tb && tb.parentNode) tb.parentNode.insertBefore(card, tb.parentNode.lastChild);
          else v.appendChild(card);
        } catch (e) { try { v.appendChild(card); } catch (e2) {} }
        v.__opt = card;
        /* symbol chips */
        var chips = document.createElement("div");
        chips.className = "chips";
        chips.style.margin = "10px 0 0";
        try { v.insertBefore(chips, card); } catch (e) { v.appendChild(chips); }
        v.__optChips = chips;
        chips.addEventListener("click", function (e) {
          var t = e.target.closest("[data-osym]");
          if (!t) return;
          OPT_SYM = t.getAttribute("data-osym");
          chips.querySelectorAll("span").forEach(function (x) { x.classList.toggle("on", x === t); });
          drawOpt();
        });
      }
      var pick = names.indexOf(OPT_SYM) > -1 ? OPT_SYM : (names.indexOf("NIFTY") > -1 ? "NIFTY" : names[0]);
      OPT_SYM = pick;
      if (v.__optChips) {
        var want = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50", pick].filter(function (x, i, a) { return names.indexOf(x) > -1 && a.indexOf(x) === i; });
        v.__optChips.innerHTML = want.map(function (s) {
          return '<span class="fch' + (s === pick ? " on" : "") + '" data-osym="' + esc(s) + '">' + esc(s) + "</span>";
        }).join("");
      }
      var x = OPTS.u[pick];
      var ch = (x.c || [])[0] || {};
      var rows = ch.r || [];
      var h = '<div class="sh2" style="padding:10px 14px 4px">Options \u2014 ' + esc(pick) + " <span class=\"fr\">expiry " + esc(String(ch.d || "\u2014")) + " \u00b7 spot \u20b9" + num(x.s, 0) + "</span></div>" +
        '<table><thead><tr><th>Strike</th><th>CE LTP</th><th>CE IV</th><th>CE \u0394</th><th>CE \u0398</th><th>PE \u0398</th><th>PE \u0394</th><th>PE IV</th><th>PE LTP</th></tr></thead><tbody>';
      var srt = rows.slice().sort(function (a, b2) { return a[0] - b2[0]; });
      srt.forEach(function (r) {
        var atm = Math.abs(r[0] - x.s) <= 50 || (srt.length && Math.abs(r[0] - x.s) === Math.min.apply(null, srt.map(function (q) { return Math.abs(q[0] - x.s); })));
        h += "<tr" + (atm ? ' style="background:color-mix(in srgb,var(--accent) 12%,transparent)"' : "") + "><td><b>" + num(r[0], 0) + "</b></td><td>" + (r[1] != null ? num(r[1], 1) : "\u2014") + "</td><td>" + (r[2] != null ? r[2] : "\u2014") + "</td><td>" + (r[3] != null ? r[3] : "\u2014") + "</td><td>" + (r[4] != null ? r[4] : "\u2014") + "</td><td>" + (r[8] != null ? r[8] : "\u2014") + "</td><td>" + (r[7] != null ? r[7] : "\u2014") + "</td><td>" + (r[6] != null ? r[6] : "\u2014") + "</td><td>" + (r[5] != null ? num(r[5], 1) : "\u2014") + "</td></tr>";
      });
      h += "</tbody></table>";
      card.innerHTML = h;
    }
  }

  /* ---------- 24) Watchlist + price alerts (localStorage) + bot alerts ---------- */
  var FCAST = {};
  function watchRd(k) { try { return JSON.parse(localStorage.getItem(k) || "[]") || []; } catch (e) { return []; } }
  function watchWr(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function ldToast(m) {
    try {
      var ts = document.getElementById("toast");
      if (!ts) { ts = document.createElement("div"); ts.id = "toast"; document.body.appendChild(ts); }
      ts.textContent = m;
      ts.classList.add("show");
      setTimeout(function () { ts.classList.remove("show"); }, 2600);
    } catch (e) {}
  }
  function checkAlerts() {
    var al = watchRd("mbAlerts");
    al.forEach(function (a) {
      var p = PM[a.sym] ? PM[a.sym].price : null;
      if (p == null || a.hit) return;
      if ((a.dir === "above" && p >= a.level) || (a.dir === "below" && p <= a.level)) {
        a.hit = 1;
        ldToast("ALERT: " + a.sym + " " + a.level + " " + a.dir + " cross \u2014 abhi \u20b9" + p);
      }
    });
    watchWr("mbAlerts", al);
  }
  function renderWatchlist() {
    var v = sec("v-company");
    if (!v) return;
    var card = v.__wl;
    if (!card) {
      card = document.createElement("div");
      card.className = "card";
      card.style.margin = "0 0 10px";
      var k = q1(".kpis", v);
      try { if (k && k.parentNode) v.insertBefore(card, k); else v.insertBefore(card, v.firstChild); } catch (e) { try { v.appendChild(card); } catch (e2) {} }
      v.__wl = card;
    }
    var w = watchRd("mbWatch");
    var h = '<div class="sh2">My Watchlist <span class="fr">' + w.length + " stocks</span></div>" + '<div style="padding:6px 14px 10px">';
    if (!w.length) h += '<div class="zrow"><span style="opacity:.6">khali \u2014 symbol add karo (RELIANCE, TCS\u2026)</span><span></span></div>';
    w.forEach(function (s, i) {
      var p = PM[s.sym];
      h += '<div class="zrow"><span><b>' + esc(s.sym) + "</b> \u20b9" + (p ? num(p.price) : "\u2014") + '</span><span><b class="' + (p && p.change_pct >= 0 ? "up" : "dn") + '">' + (p ? pctS(p.change_pct) : "\u2014") + '</b> <small data-wx="' + i + '" style="cursor:pointer;opacity:.5;padding-left:8px">\u2715</small></span></div>';
    });
    h += '<div style="display:flex;gap:8px;margin-top:8px"><input id="wlAdd" placeholder="symbol add (RELIANCE)" style="flex:1;padding:9px 12px;border-radius:10px;border:1px solid var(--border2);background:var(--surface);color:var(--text);font:400 12.5px var(--font);outline:none">' +
      '<small id="wlAddB" style="cursor:pointer;color:var(--accent);padding-top:9px">+ ADD</small></div>';
    /* local alerts */
    var al = watchRd("mbAlerts");
    h += '<div class="sect" style="margin:10px 0 4px">MY PRICE ALERTS</div>';
    if (!al.length) h += '<div class="zrow"><span style="opacity:.6">koi alert nahi</span><span></span></div>';
    al.forEach(function (a, i) {
      h += '<div class="zrow"><span><b>' + esc(a.sym) + "</b> " + (a.dir === "above" ? "\u2191" : "\u2193") + " \u20b9" + num(a.level, 0) + (a.hit ? " \u00b7 HIT" : "") + '</span><small data-ax="' + i + '" style="cursor:pointer;opacity:.5">\u2715</small></div>';
    });
    h += '<div style="display:flex;gap:6px;margin-top:6px"><input id="alSym" placeholder="SYM" style="width:70px;padding:9px 10px;border-radius:10px;border:1px solid var(--border2);background:var(--surface);color:var(--text);font:400 12px var(--font);outline:none">' +
      '<input id="alLvl" placeholder="level" inputmode="decimal" style="width:80px;padding:9px 10px;border-radius:10px;border:1px solid var(--border2);background:var(--surface);color:var(--text);font:400 12px var(--font);outline:none">' +
      '<select id="alDir" style="border-radius:10px;border:1px solid var(--border2);background:var(--surface);color:var(--text);font:400 12px var(--font);outline:none"><option value="above">above</option><option value="below">below</option></select>' +
      '<small id="alAddB" style="cursor:pointer;color:var(--accent);padding-top:9px">+ SET</small></div>';
    h += "</div>";
    /* bot alerts */
    h += '<div style="padding:0 14px 12px">';
    h += '<div class="sect" style="margin:4px 0 6px">BOT ALERTS (auto)</div>';
    h += '<div id="botAlerts" style="font-size:12px;color:var(--dim)">loading\u2026</div></div>';
    card.innerHTML = h;
    card.onclick = function (e) {
      var t = e.target;
      var wx = t.getAttribute && t.getAttribute("data-wx");
      var ax = t.getAttribute && t.getAttribute("data-ax");
      if (wx != null) { var w2 = watchRd("mbWatch"); w2.splice(+wx, 1); watchWr("mbWatch", w2); renderWatchlist(); }
      if (ax != null) { var a2 = watchRd("mbAlerts"); a2.splice(+ax, 1); watchWr("mbAlerts", a2); renderWatchlist(); }
      if (t.id === "wlAddB") {
        var s = (document.getElementById("wlAdd").value || "").trim().toUpperCase();
        if (s && PM[s]) { var w3 = watchRd("mbWatch"); if (!w3.filter(function (z) { return z.sym === s; }).length) { w3.push({ sym: s }); watchWr("mbWatch", w3); renderWatchlist(); } else ldToast("watchlist mein already hai"); }
        else ldToast("symbol nahi mila \u2014 exact symbol likho (RELIANCE)");
      }
      if (t.id === "alAddB") {
        var sy = (document.getElementById("alSym").value || "").trim().toUpperCase();
        var lv = parseFloat(document.getElementById("alLvl").value);
        var dr = document.getElementById("alDir").value;
        if (sy && lv > 0) { var a3 = watchRd("mbAlerts"); a3.push({ sym: sy, level: lv, dir: dr }); watchWr("mbAlerts", a3); renderWatchlist(); ldToast("alert set \u2014 " + sy + " " + dr + " " + lv); }
      }
    };
    fj("data/alerts.json").then(function (d) {
      var ba = document.getElementById("botAlerts");
      if (ba && d.alerts && d.alerts.length) {
        ba.innerHTML = d.alerts.map(function (a) {
          return '<div class="zrow"><span><b>' + esc(a.symbol) + "</b> " + (a.dir === "above" ? "\u2191" : "\u2193") + " \u20b9" + num(a.level, 0) + " \u00b7 " + esc(a.note || "") + '</span><small class="mono">' + esc(String(a.added || "")) + "</small></div>";
        }).join("");
      } else if (ba) ba.textContent = "abhi koi active nahi";
    }).catch(function () { var ba = document.getElementById("botAlerts"); if (ba) ba.textContent = "\u2014"; });
    checkAlerts();
  }

  /* ---------- 25) Backtest (learn mein) ---------- */
  function renderBacktest() {
    var v = sec("v-learn");
    if (!v) return;
    fj("data/backtest.json").then(function (b) {
      if (!b || !b.days) return;
      var card = v.__bt;
      if (!card) {
        card = document.createElement("div");
        card.className = "card";
        card.style.margin = "10px 0 0";
        v.appendChild(card);
        v.__bt = card;
      }
      card.innerHTML = '<div class="sh2">Strategy Backtest \u2014 Nifty 1y <span class="fr">' + b.days + " din</span></div>" + '<div style="padding:6px 14px 10px">' +
        '<div class="zrow"><span>Buy {"+"} Hold</span><b class="' + (b.buy_hold_pct >= 0 ? "up" : "dn") + '">' + pctS(b.buy_hold_pct) + "</b></div>" +
        '<div class="zrow"><span>EMA 20{"+"}50 crossover</span><b class="' + (b.ema_pct >= 0 ? "up" : "dn") + '">' + pctS(b.ema_pct) + " (" + b.ema_trades + " trades)</b></div>" +
        '<div class="zrow"><span>RSI 30-70</span><b class="' + (b.rsi_pct >= 0 ? "up" : "dn") + '">' + pctS(b.rsi_pct) + " (" + b.rsi_trades + " trades)</b></div>" +
        '<div style="font-size:11px;opacity:.6;padding-top:6px">' + esc(b.note || "") + "</div></div>";
    }).catch(function () {});
  }

  /* ---------- 26) Bank health (fundamentals mein) ---------- */
  function renderBanks() {
    var v = sec("v-fundamentals");
    if (!v) return;
    fj("data/banks.json").then(function (d) {
      if (!d || !d.banks) return;
      var r = d.rules || {};
      var card = v.__bk;
      if (!card) {
        card = document.createElement("div");
        card.className = "card";
        card.style.margin = "10px 0 0";
        card.style.padding = "0";
        card.style.overflow = "auto";
        var tbc = q1("table", v);
        var tcard = tbc ? (tbc.closest ? tbc.closest(".card") : null) : null;
        if (tcard && tcard.parentNode) tcard.parentNode.insertBefore(card, tcard.nextSibling);
        else v.appendChild(card);
        v.__bk = card;
      }
      function verd(b2) {
        var bad = [];
        if (b2.npa != null && r.npa_max != null && b2.npa > r.npa_max) bad.push("NPA");
        if (b2.roe != null && r.roe_min != null && b2.roe < r.roe_min) bad.push("ROE");
        if (b2.casa != null && r.casa_avg != null && b2.casa < r.casa_avg) bad.push("CASA");
        if (b2.car != null && r.car_min != null && b2.car < r.car_min) bad.push("CAR");
        return bad.length ? '<span class="b dn">' + bad.join("+") + "</span>" : '<span class="b buy">HEALTHY</span>';
      }
      var h = '<div class="sh2" style="padding:10px 14px 4px">Bank Health <span class="fr">' + esc(d.asof || "") + "</span></div>" +
        '<table><thead><tr><th>Bank</th><th>NPA</th><th>ROE</th><th>ROA</th><th>CASA</th><th>CAR</th><th>Price</th><th>Verdict</th></tr></thead><tbody>';
      d.banks.forEach(function (b2) {
        h += "<tr><td>" + esc(b2.n) + "</td><td>" + b2.npa + "%</td><td>" + b2.roe + "%</td><td>" + b2.roa + "%</td><td>" + b2.casa + "%</td><td>" + b2.car + "%</td><td>\u20b9" + num(b2.p, 0) + "</td><td>" + verd(b2) + "</td></tr>";
      });
      h += "</tbody></table>";
      h += '<div style="font-size:11px;opacity:.6;padding:8px 14px">rules \u2014 NPA<' + (r.npa_max || "?") + "% \u00b7 ROE " + (r.roe_min || "?") + "-" + (r.roe_max || "?") + "% \u00b7 CASA>" + (r.casa_avg || "?") + "% \u00b7 CAR>" + (r.car_min || "?") + "%" + (d.note ? " \u00b7 " + esc(d.note) : "") + "</div>";
      card.innerHTML = h;
    }).catch(function () {});
  }

  /* ---------- 27) per-stock AI forecast (gtiai + company card) ---------- */
  function fcFind(q) {
    q = (q || "").trim().toUpperCase();
    if (!q || !FCAST._loaded) return null;
    var L = FCAST._list || [];
    var norm = function (s) { return String(s || "").toUpperCase().replace("^", "").replace(".NS", "").replace("-USD", "").replace("USD", ""); };
    var i;
    for (i = 0; i < L.length; i++) if (norm(L[i].symbol) === q || String(L[i].name || "").toUpperCase() === q) return L[i];
    for (i = 0; i < L.length; i++) if (norm(L[i].symbol).indexOf(q) === 0 || String(L[i].name || "").toUpperCase().indexOf(q) === 0) return L[i];
    for (i = 0; i < L.length; i++) if (String(L[i].name || "").toUpperCase().indexOf(q) > -1) return L[i];
    return null;
  }
  function loadForecasts() {
    if (FCAST._loaded) return;
    fj("data/timesfm_forecasts.json").then(function (d) {
      FCAST._list = d.forecasts || [];
      FCAST._model = d.model || "TimesFM";
      FCAST._loaded = 1;
      /* company card mein AI forecast line + watchlist ke baad render */
      try { renderWatchlist(); } catch (e) {}
    }).catch(function () {});
  }
  function renderFcSearch() {
    var v = sec("v-gtiai");
    if (!v || v.__fcs) return;
    v.__fcs = 1;
    var inp = document.createElement("input");
    inp.type = "search";
    inp.placeholder = "kisi bhi stock ka 21-din AI forecast \u2014 RELIANCE, INFY, NIFTY\u2026";
    inp.style.cssText = "width:100%;padding:10px 12px;border-radius:10px;border:1px solid var(--border2);background:var(--surface);color:var(--text);font:400 12.5px var(--font);outline:none;margin:0 0 10px";
    var ks = q1(".kpis", v);
    try { if (ks && ks.parentNode) ks.parentNode.insertBefore(inp, ks); else v.insertBefore(inp, v.firstChild); } catch (e) { try { v.appendChild(inp); } catch (e2) {} }
    var t = null;
    inp.addEventListener("input", function () {
      clearTimeout(t);
      var q = inp.value;
      t = setTimeout(function () { drawFc(q); }, 350);
    });
    function drawFc(q) {
      var f = fcFind(q);
      if (!f) return;
      var ks2 = q1(".kpis", v);
      if (ks2) {
        ks2.innerHTML =
          '<div class="card kpi"><div class="lbl">' + esc(f.name || f.symbol) + ' \u2014 ' + f.horizon_days + 'D TARGET</div><div class="num">' + num(f.median_end, 0) + '</div><div class="chg ' + (f.median_chg_pct >= 0 ? "up" : "dn") + '">' + pctS(f.median_chg_pct) + " expected</div></div>" +
          '<div class="card kpi"><div class="lbl">CONFIDENCE</div><div class="num">' + (f.confidence != null ? f.confidence + "%" : "\u2014") + '</div><div class="chg hold">model agreement</div></div>' +
          '<div class="card kpi"><div class="lbl">TREND</div><div class="num ' + (f.median_chg_pct >= 0 ? "up" : "dn") + '">' + String(f.direction || (f.median_chg_pct >= 0 ? "up" : "down")).toUpperCase() + '</div><div class="chg hold">median path</div></div>' +
          '<div class="card kpi"><div class="lbl">RANGE 10-90</div><div class="num" style="font-size:15px">' + num(f.low10_end, 0) + "\u2013" + num(f.high90_end, 0) + '</div><div class="chg hold">10% \u2013 90% band</div></div>';
      }
      var mv = v.querySelectorAll(".card")[0];
      var cards2 = Array.prototype.slice.call(v.querySelectorAll(".card"));
      for (var ci = 0; ci < cards2.length; ci++) { var sh2 = cards2[ci].querySelectorAll(".sh2")[0]; if (sh2 && /Model View/i.test(sh2.textContent)) { mv = cards2[ci]; break; } }
      if (mv) {
        var body = mv.querySelectorAll("div[style]")[0];
        if (body) body.textContent = (f.name || f.symbol) + ": " + f.horizon_days + "-din ka median target " + num(f.median_end, 0) + " (" + pctS(f.median_chg_pct) + "). Model band " + num(f.low10_end, 0) + " se " + num(f.high90_end, 0) + " tak. Base case " + (f.median_chg_pct >= 0 ? "upar" : "neeche") + " \u2014 band ke andar trade karo.";
      }
    }
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
    try { renderCharts(); } catch (e) {}
    try { wireFilters(); } catch (e) {}
    try { renderLearn(); } catch (e) {}
    try { renderCompanySummary(); } catch (e) {}
    try { wireMF(); } catch (e) {}
    try { renderEconomy(); } catch (e) {}
    try { renderSmartRadar(); } catch (e) {}
    try { wireScreenerChips(); } catch (e) {}
    try { renderGtiHub(); } catch (e) {}
    try { renderLegacy(); } catch (e) {}
    try { renderOptions(); } catch (e) {}
    try { renderWatchlist(); } catch (e) {}
    try { renderBacktest(); } catch (e) {}
    try { renderBanks(); } catch (e) {}
    try { loadForecasts(); } catch (e) {}
    try { renderFcSearch(); } catch (e) {}
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
    try { renderCharts(); } catch (e) {}
    try { wireFilters(); } catch (e) {}
    try { renderLearn(); } catch (e) {}
    try { renderEconomy(); } catch (e) {}
    try { renderSmartRadar(); } catch (e) {}
    try { renderWatchlist(); } catch (e) {}
  }, 5 * 60 * 1000);
})();
