/* dlvfix.js \u2014 screener D% (NSE delivery %) column.
   oldapp ka apna renderScreener chalta hai (loaders map seedha uska ref hold karta hai),
   isliye: (1) filteredStocks dobara define karte hain "dlv" sort ke saath,
   (2) MutationObserver har draw ke baad 9th cell (D%) add/refresh karta hai \u2014 idempotent.
   Data: data/delivery.json \u2014 eoddata.yml -> scripts/delivery_collect.py (NSE bhavcopy, EOD). */
(function () {
  var dlvMap = {}, dlvDate = "";

  function dlvCell(sym) {
    var v = dlvMap[sym];
    if (v == null) return "\u2014";
    var cls = v >= 60 ? "pos" : (v <= 25 ? "neg" : "");
    return '<span class="' + cls + '" style="font-weight:700">' + v + "%</span>";
  }

  function symOf(r) {
    var a = r.querySelector("td .sym a");
    return a ? a.textContent.trim() : "";
  }

  function ensureHeader() {
    var tr = document.querySelector("section#screener thead tr");
    if (tr) {
      var ths = tr.querySelectorAll("th");
      if (!ths.length || ths[ths.length - 1].textContent !== "D%") {
        var th = document.createElement("th");
        th.title = "Delivery % - NSE EOD";
        th.textContent = "D%";
        tr.appendChild(th);
      }
    }
    var sel = document.getElementById("scrSort");
    if (sel && !sel.querySelector('option[value="dlv"]')) {
      var o = document.createElement("option");
      o.value = "dlv";
      o.textContent = "Delivery% \u25bc";
      sel.appendChild(o);
    }
    if (!document.getElementById("scrDlvNote")) {
      var sc = document.getElementById("scrCount");
      if (sc && sc.parentNode) {
        var n = document.createElement("div");
        n.id = "scrDlvNote";
        n.className = "footer-note";
        sc.parentNode.insertBefore(n, sc.nextSibling);
      }
    }
  }

  function patchRows() {
    ensureHeader();
    var tb = document.getElementById("scrBody");
    if (!tb) return;
    var rows = tb.querySelectorAll("tr");
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i];
      var tds = r.querySelectorAll("td");
      if (!tds.length) continue;
      if (tds.length === 1 && (tds[0].className || "").indexOf("loading") > -1) {
        if (tds[0].getAttribute("colspan") !== "9") tds[0].setAttribute("colspan", "9");
        continue;
      }
      var sym = symOf(r);
      if (!sym) continue;
      var html = dlvCell(sym);
      if (tds.length >= 9) {
        if (tds[8].innerHTML !== html) tds[8].innerHTML = html;
        continue;
      }
      if (tds.length < 8) continue;
      var td = document.createElement("td");
      td.innerHTML = html;
      r.appendChild(td);
    }
  }

  function setNote() {
    var n = document.getElementById("scrDlvNote");
    if (n) n.textContent = "D% = NSE delivery " + (dlvDate ? "(" + dlvDate + " EOD)" : "") + " \u00b7 60%+ = haath me utha ke le gaye \u00b7 25%- = bas intraday khel";
  }

  function load() {
    fetch("data/delivery.json?t=" + Date.now()).then(function (r) { return r.json(); }).then(function (d) {
      dlvMap = (d && d.d) || {};
      dlvDate = (d && d.date) || "";
      setNote();
      patchRows();
    }).catch(function () {});
  }

  function start() {
    var tb = document.getElementById("scrBody");
    if (!tb) { setTimeout(start, 800); return; }
    try {
      new MutationObserver(function () { patchRows(); }).observe(tb, { childList: true, subtree: true });
    } catch (e) {}
    patchRows();
    load();
  }
  start();

  window.filteredStocks = function () {
    var q = $("#scrSearch").value.trim().toLowerCase();
    var tier = +$("#scrTier").value, rsi = $("#scrRsi").value, ema = $("#scrEma").value;
    var sort = $("#scrSort").value;
    var L = (scrData.stocks || []).filter(function (s) {
      return (!q || s.symbol.toLowerCase().includes(q) || (s.company || "").toLowerCase().includes(q)) &&
        (!tier || s.tier === tier) &&
        (!ema || ema === "all" || (ema === "above" ? s.above_ema200 : !s.above_ema200)) &&
        (!scrAI || !aiBullish || aiBullish.has(s.symbol));
    });
    if (rsi === "os") L = L.filter(function (s) { return s.rsi14 != null && s.rsi14 < 30; });
    if (rsi === "lt40") L = L.filter(function (s) { return s.rsi14 != null && s.rsi14 < 40; });
    if (rsi === "gt60") L = L.filter(function (s) { return s.rsi14 != null && s.rsi14 > 60; });
    if (rsi === "ob") L = L.filter(function (s) { return s.rsi14 != null && s.rsi14 > 70; });
    var cmp = {
      chg: function (a, b) { return (b.change_pct || 0) - (a.change_pct || 0); },
      rsi: function (a, b) { return (a.rsi14 || 99) - (b.rsi14 || 99); },
      rsid: function (a, b) { return (b.rsi14 || 0) - (a.rsi14 || 0); },
      "52w": function (a, b) { return (a.from_52w_high_pct || 0) - (b.from_52w_high_pct || 0); },
      up: function (a, b) { return (b.from_52w_high_pct || 0) - (a.from_52w_high_pct || 0); },
      vol: function (a, b) { return (b.vol_vs_avg20 || 0) - (a.vol_vs_avg20 || 0); },
      dlv: function (a, b) { return (dlvMap[b.symbol] || 0) - (dlvMap[a.symbol] || 0); },
    }[sort];
    return L.sort(cmp);
  };
})();