/* power2.js - FII/DII activity + Portfolio tracker + Stock Deep Charts + MF Verdict */
(function () {
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; }); }
  function inpt(id, ph) { return '<input id="' + id + '" placeholder="' + ph + '" style="width:100%;box-sizing:border-box;padding:9px 12px;border-radius:9px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.05);color:inherit;font-size:14px;margin-top:5px">'; }
  function getV(id) { var e = document.getElementById(id); return e ? parseFloat(e.value) || 0 : 0; }

  function buildFii(card) {
    card.innerHTML = '<div class="subhead">FII / DII Activity (aaj ka paisa kahan gaya)</div><div class="note">load...</div>';
    fetch("data/fii-dii.json?t=" + Date.now()).then(function (r) { return r.json(); }).then(function (d) {
      var cats = d.categories || {};
      var rows = [["FII/FPI", "FII (videshi)"], ["DII", "DII (domestic - MF+insurance)"]];
      var h = '<div class="note" style="margin-top:8px">data: ' + esc(d.date || "") + ' (cash market, Cr)</div>';
      rows.forEach(function (r0) {
        var c = cats[r0[0]] || {};
        var net = c.net_cr || 0;
        var good = net >= 0;
        h += '<div class="note" style="margin-top:10px"><b>' + r0[1] + '</b><br>Buy: ' + Math.round(c.buy_cr || 0).toLocaleString("en-IN") +
          ' Cr | Sell: ' + Math.round(c.sell_cr || 0).toLocaleString("en-IN") + ' Cr</div>' +
          '<div class="note" style="display:flex;align-items:center;gap:8px;margin-top:4px">' +
          '<span style="flex:1;height:10px;border-radius:5px;background:rgba(255,255,255,.08);overflow:hidden;position:relative">' +
          '<span style="position:absolute;top:0;bottom:0;left:0;width:' + Math.min(100, Math.abs(net) / 100) + '%;background:' + (good ? "#77f37b" : "#ff8b8b") + '"></span></span>' +
          '<b style="color:' + (good ? "#77f37b" : "#ff8b8b") + '">' + (net >= 0 ? "+" : "") + Math.round(net).toLocaleString("en-IN") + ' Cr net</b></div>';
      });
      var f = (cats["FII/FPI"] || {}).net_cr || 0, di = (cats.DII || {}).net_cr || 0;
      h += '<div class="note" style="margin-top:10px;border-left:3px solid rgba(240,180,41,.7);padding:8px 12px;background:rgba(240,180,41,.07)"><b>Verdict:</b> ' +
        (f < 0 && di > 0 ? "FII bech rahe, DII support de raha - market tikta hai but upar jaldi nahi" :
         f > 0 && di > 0 ? "Dono kharid rahe - bullish combo" :
         f < 0 && di < 0 ? "Dono bech rahe - sambhal ke, weakness" :
         "FII kharid rahe, DII book kar rahe - mixed") + '</div>';
      card.innerHTML = '<div class="subhead">FII / DII Activity (aaj ka paisa kahan gaya)</div>' + h;
    }).catch(function () { card.innerHTML = '<div class="subhead">FII/DII Activity</div><div class="note">data nahi mila.</div>'; });
  }

  function buildPort(card) {
    function rd() { try { return JSON.parse(localStorage.getItem("mbPortfolio") || "[]"); } catch (e) { return []; } }
    function wr(x) { try { localStorage.setItem("mbPortfolio", JSON.stringify(x)); } catch (e) {} }
    function render() {
      var rows = rd();
      fetch("data/bullish.json?t=" + Date.now()).then(function (r) { return r.json(); }).then(function (b) {
        var priceMap = {};
        (b.week || []).concat(b.month || [], b.year || [], b.decade || []).forEach(function (x) { priceMap[x.s] = x.price; });
        var h = "", inv = 0, cur = 0;
        rows.forEach(function (r0, i) {
          var p = priceMap[r0.sym] || r0.avg;
          var pl = (p - r0.avg) * r0.qty, plp = r0.avg ? (p - r0.avg) / r0.avg * 100 : 0;
          inv += r0.avg * r0.qty; cur += p * r0.qty;
          h += '<div class="note" style="display:flex;justify-content:space-between;align-items:center;margin-top:6px">' +
            '<span><b>' + esc(r0.sym) + '</b> ' + r0.qty + ' @ ' + r0.avg + ' -> now ' + p + '</span>' +
            '<span style="color:' + (pl >= 0 ? "#77f37b" : "#ff8b8b") + '"><b>' + (pl >= 0 ? "+" : "") + Math.round(pl) + ' (' + plp.toFixed(1) + '%)</b> <a href="#" data-i="' + i + '" style="opacity:.5;text-decoration:none">x</a></span></div>';
        });
        var tot = cur - inv;
        h += rows.length ? '<div class="note" style="margin-top:12px;border-left:3px solid rgba(240,180,41,.7);padding:8px 12px;background:rgba(240,180,41,.07)">Invested: <b>' + Math.round(inv).toLocaleString("en-IN") + '</b> | Now: <b>' + Math.round(cur).toLocaleString("en-IN") + '</b> | <b style="color:' + (tot >= 0 ? "#77f37b" : "#ff8b8b") + '">P&L: ' + (tot >= 0 ? "+" : "") + Math.round(tot).toLocaleString("en-IN") + '</b></div>' : '<div class="note">khali - apne trades add karo (price roz EOD update hota hai)</div>';
        card.innerHTML = '<div class="subhead">My Portfolio (virtual tracker)</div>' +
          inpt("pfSym", "Symbol (RELIANCE)") + inpt("pfQty", "Quantity") + inpt("pfAvg", "Avg buy price") +
          '<div class="note" id="pfAdd" style="margin-top:8px;color:#5fb0ff;cursor:pointer">+ Add trade</div>' + h +
          '<div class="footer-note">localStorage - sirf isi phone me save. Prices EOD (500 stocks covered)</div>';
        document.getElementById("pfAdd").onclick = function () {
          var s = (document.getElementById("pfSym").value || "").trim().toUpperCase();
          var q = getV("pfQty"), a = getV("pfAvg");
          if (s && q > 0 && a > 0) { var x = rd(); x.push({ sym: s, qty: q, avg: a }); wr(x); render(); }
        };
        card.querySelectorAll("a[data-i]").forEach(function (a0) {
          a0.onclick = function (ev) { ev.preventDefault(); var x = rd(); x.splice(+a0.getAttribute("data-i"), 1); wr(x); render(); };
        });
      });
    }
    render();
  }

  function buildCharts(card) {
    card.innerHTML = '<div class="subhead">Stock Deep Charts (kisi bhi stock ka colorful score)</div>' +
      inpt("dcSym", "Symbol daalo (RELIANCE, TCS...)") +
      '<div class="note" id="dcOut" style="margin-top:10px">symbol daalo - PE/ROE/growth bars + 13-quarter profit trend milega</div>';
    var cached = null;
    document.getElementById("dcSym").addEventListener("input", function () {
      var s = this.value.trim().toUpperCase();
      if (s.length < 3) return;
      function go() {
        var st = (cached.stocks || {})[s];
        var o = document.getElementById("dcOut");
        if (!st) { o.innerHTML = '<div class="note">' + esc(s) + ' 500-list mein nahi (ya spelling check karo)</div>'; return; }
        function bar(label, val, max, good, unit) {
          var w = Math.max(2, Math.min(100, Math.abs(val) / max * 100));
          var col = good ? "#77f37b" : "#ff8b8b";
          return '<div class="note" style="display:flex;align-items:center;gap:8px;margin-top:6px"><span style="min-width:70px">' + label + '</span>' +
            '<span style="flex:1;height:10px;border-radius:5px;background:rgba(255,255,255,.08);overflow:hidden"><span style="display:block;height:100%;width:' + w + '%;background:' + col + '"></span></span>' +
            '<b style="min-width:56px;text-align:right;color:' + col + '">' + val + unit + '</b></div>';
        }
        var h = '<div class="note" style="margin-top:8px"><b>' + esc(s) + '</b> - Rs ' + st["Current Price"] + ' | Market Cap: ' + (st["Market Cap"] || 0).toLocaleString("en-IN") + ' Cr</div>';
        var pe = st["Stock P/E"] || 0;
        h += bar("P/E", pe, 100, pe > 0 && pe <= 30, "");
        h += bar("ROE", st.ROE || 0, 30, (st.ROE || 0) >= 15, "%");
        h += bar("ROCE", st.ROCE || 0, 30, (st.ROCE || 0) >= 12, "%");
        h += bar("Profit YoY", st["Net Profit_yoy"] || 0, 100, (st["Net Profit_yoy"] || 0) >= 15, "%");
        var np = st["Net Profit"] || [];
        if (np.length) {
          var mx = Math.max.apply(null, np.map(Math.abs)) || 1;
          h += '<div class="note" style="margin-top:12px"><b>Quarterly Net Profit trend (13Q):</b></div><div style="display:flex;align-items:flex-end;gap:3px;height:70px;margin-top:6px">';
          np.forEach(function (v) {
            var hh = Math.max(3, Math.abs(v) / mx * 70);
            h += '<span style="flex:1;height:' + hh + 'px;border-radius:2px;background:' + (v >= 0 ? "#77f37b" : "#ff8b8b") + '" title="' + v + '"></span>';
          });
          h += '</div><div class="note" style="font-size:11px;opacity:.6">' + esc((st.quarters || []).slice(-2).join(" <- ")) + ' tak</div>';
        }
        o.innerHTML = h;
      }
      if (cached) { go(); return; }
      fetch("data/screener-fundamentals.json").then(function (r) { return r.json(); }).then(function (d) { cached = d; go(); });
    });
  }

  function buildMf(card) {
    card.innerHTML = '<div class="subhead">MF Verdict (phase 2)</div><div class="note">load...</div>';
    fetch("data/mf-top.json?t=" + Date.now()).then(function (r) { return r.json(); }).then(function (d) {
      var funds = (d.funds || []).slice().sort(function (a, b) { return (b.r1 || 0) - (a.r1 || 0); });
      var bench = (d.bench || {}).r1 || 0;
      var beat = funds.slice(0, 5).filter(function (f) { return (f.r1 || 0) > bench; }).length;
      var h = '<div class="note" style="margin-top:8px">1-yr benchmark: <b>' + bench + '%</b> | aaj top-5 me se <b>' + beat + '</b> benchmark beat kar rahe</div>';
      h += '<div class="note" style="margin-top:8px;border-left:3px solid ' + (beat >= 3 ? "#77f37b" : "#ff8b8b") + ';padding:8px 12px;background:rgba(240,180,41,.07)"><b>Verdict:</b> ' +
        (beat >= 4 ? "MF season badhiya - equity MF me theek hai" : beat >= 3 ? "Normal - SIP continue rakho" : "Weak season - FD/debt side dekho") + '</div>';
      funds.slice(0, 6).forEach(function (f) {
        h += '<div class="note" style="display:flex;justify-content:space-between;margin-top:6px"><span style="flex:1">' + esc(String(f.n).split("·")[0]) + ' <span style="opacity:.5;font-size:11px">' + esc(f.k || "") + '</span></span><span style="color:' + ((f.r1 || 0) >= bench ? "#77f37b" : "#ff8b8b") + '"><b>1Y ' + f.r1 + '%</b></span></div>';
      });
      card.innerHTML = '<div class="subhead">MF Verdict (kaunsa fund chal raha hai)</div>' + h;
    }).catch(function () { card.innerHTML = '<div class="subhead">MF Verdict</div><div class="note">data nahi mila.</div>'; });
  }

  function mount() {
    var t = document.querySelector("section#tools");
    if (t && !document.getElementById("mbFii")) {
      [["mbFii", buildFii], ["mbPort", buildPort], ["mbCharts", buildCharts]].forEach(function (d0) {
        var c = document.createElement("div"); c.className = "card"; c.id = d0[0]; c.style.marginTop = "14px";
        t.appendChild(c); try { d0[1](c); } catch (e) {}
      });
    }
    var m = document.querySelector("section#mf");
    if (m && !document.getElementById("mbMfV")) {
      var c2 = document.createElement("div"); c2.className = "card"; c2.id = "mbMfV"; c2.style.marginTop = "14px";
      var first = m.querySelector(".card");
      if (first) m.insertBefore(c2, first); else m.appendChild(c2);
      try { buildMf(c2); } catch (e) {}
    }
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount); else mount();
})();
