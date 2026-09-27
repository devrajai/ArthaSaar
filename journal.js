/* journal.js v1 -- Watchlist + Trade Journal (ek section, dono sath).
   - watchlist: symbol chips + last price (data/candles.json se, jo milta hai)
   - journal: trades add/edit/delete, P&L, R-multiple, win-rate stats
   - sab localStorage me -- XOR + base64 encrypted (device key alag key me)
   - export/import: encrypted text copy-paste se device transfer */
(function () {
  "use strict";
  var UP = "#34d399", DN = "#ff8b8b";
  var KEYN = "wlj:key", DATAN = "wlj:data";

  function esc(s) {
    if (s == null) s = "";
    return String(s).replace(/[&<>"']/g, function (c) { return "&#" + c.charCodeAt(0) + ";"; });
  }
  function inr(x) {
    if (!isFinite(x)) return "--";
    x = Math.round(x);
    var neg = x < 0; x = Math.abs(x);
    return (neg ? "\u2212\u20b9" : "\u20b9") + x.toLocaleString("en-IN");
  }
  function n2(x) { return isFinite(x) ? Number(x).toFixed(2) : "--"; }

  /* ---- light encryption: XOR with device key + base64 ---- */
  function b64e(s) { return btoa(unescape(encodeURIComponent(s))); }
  function b64d(s) { return decodeURIComponent(escape(atob(s))); }
  function xor(s, k) {
    var o = "";
    for (var i = 0; i < s.length; i++) o += String.fromCharCode(s.charCodeAt(i) ^ k.charCodeAt(i % k.length) & 255);
    return o;
  }
  function getKey() {
    var k = null;
    try { k = localStorage.getItem(KEYN); } catch (e) {}
    if (!k) {
      k = "";
      for (var i = 0; i < 3; i++) k += Math.random().toString(36).slice(2);
      try { localStorage.setItem(KEYN, k); } catch (e) {}
    }
    return k;
  }
  function save(obj) {
    try { localStorage.setItem(DATAN, b64e(xor(JSON.stringify(obj), getKey()))); }
    catch (e) {}
  }
  function load() {
    try {
      var raw = localStorage.getItem(DATAN);
      if (!raw) return { wl: [], tr: [] };
      return JSON.parse(xor(b64d(raw), getKey()));
    } catch (e) { return { wl: [], tr: [] }; }
  }
  var D = load();

  /* ---- prices from candles.json (jo intraday symbols milte hain) ---- */
  var PX = {};
  function loadPx() {
    fetch("data/candles.json?t=" + Date.now())
      .then(function (r) { return r.json(); })
      .then(function (d) {
        PX = {};
        var syms = (d && d.syms) || {};
        for (var s in syms) {
          var b = syms[s] && (syms[s]["5m"] || syms[s]["15m"] || syms[s]["1h"]);
          if (b && b.c && b.c.length) PX[s] = { last: b.c[b.c.length - 1], pc: syms[s].pc };
        }
        render();
      }).catch(function () {});
  }

  /* ---- watchlist ---- */
  function wlRender() {
    var el = document.getElementById("jWl"); if (!el) return;
    if (!D.wl.length) {
      el.innerHTML = '<div class="note">koi symbol add nahi kiya \u2014 upar likh ke Add dabao</div>';
      return;
    }
    var h = "";
    for (var i = 0; i < D.wl.length; i++) {
      var s = D.wl[i];
      var p = PX[s];
      var chg = p && p.pc ? (p.last - p.pc) / p.pc * 100 : null;
      h += '<div style="display:flex;justify-content:space-between;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.06)">' +
        '<b style="font-size:13px">' + esc(s) + '</b>' +
        '<span style="display:flex;align-items:center;gap:8px">' +
        (p ? '<span style="font-family:var(--mono);font-size:12.5px">' + n2(p.last) +
          ' <span style="color:' + (chg >= 0 ? UP : DN) + '">' + (chg >= 0 ? "+" : "") + chg.toFixed(2) + '%</span></span>' : "") +
        '<button data-j-delwl="' + esc(s) + '" style="background:none;border:1px solid rgba(255,139,139,.4);color:' + DN + ';border-radius:7px;padding:2px 8px;cursor:pointer;font-size:11px">\u00d7</button>' +
        '</span></div>';
    }
    el.innerHTML = h;
  }

  /* ---- journal ---- */
  function trPnl(t) {
    if (!(t.exit > 0)) return null;
    var d = t.exit - t.entry;
    if (t.side === "S") d = -d;
    return d * t.qty;
  }
  function trR(t) {
    if (!(t.sl > 0)) return null;
    var risk = Math.abs(t.entry - t.sl);
    if (!risk) return null;
    var rew = t.exit - t.entry;
    if (t.side === "S") rew = -rew;
    return rew / risk;
  }
  function trRender() {
    var el = document.getElementById("jTr"); if (!el) return;
    var st = document.getElementById("jStats");
    if (!D.tr.length) {
      el.innerHTML = '<div class="note">koi trade add nahi kiya \u2014 upar form se add karo</div>';
      if (st) st.innerHTML = "";
      return;
    }
    var h = "";
    var closed = 0, wins = 0, tot = 0, aw = 0, awn = 0, al = 0, aln = 0, bw = -1e18, bl = 1e18;
    for (var i = D.tr.length - 1; i >= 0; i--) {
      var t = D.tr[i];
      var p = trPnl(t), r = trR(t);
      var sideCol = t.side === "B" ? UP : DN;
      h += '<div style="padding:8px 0;border-bottom:1px solid rgba(255,255,255,.06)">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;gap:6px;flex-wrap:wrap">' +
        '<b style="font-size:13px">' + esc(t.sym) + ' <span style="color:' + sideCol + '">' + (t.side === "B" ? "BUY" : "SELL") + '</span></b>' +
        '<span style="font-family:var(--mono);font-size:12px">' + esc(t.dt || "") + '</span>' +
        '<button data-j-deltr="' + i + '" style="background:none;border:1px solid rgba(255,139,139,.4);color:' + DN + ';border-radius:7px;padding:2px 8px;cursor:pointer;font-size:11px">\u00d7</button></div>' +
        '<div class="note" style="display:flex;gap:14px;flex-wrap:wrap;margin-top:3px">' +
        '<span>qty ' + t.qty + ' @ ' + n2(t.entry) + (t.exit > 0 ? ' \u2192 ' + n2(t.exit) : ' <i>(open)</i>') + '</span>' +
        (p != null ? '<b style="color:' + (p >= 0 ? UP : DN) + '">' + inr(p) + '</b>' : "") +
        (r != null ? '<span style="color:' + (r >= 0 ? UP : DN) + '">' + (r >= 0 ? "+" : "") + r.toFixed(1) + 'R</span>' : "") +
        '</div>' +
        (t.note ? '<div class="note" style="opacity:.75;margin-top:2px">' + esc(t.note) + '</div>' : "") +
        '</div>';
      if (p != null) {
        closed++; tot += p;
        if (p >= 0) { wins++; aw += p; awn++; if (p > bw) bw = p; }
        else { al += p; aln++; if (p < bl) bl = p; }
      }
    }
    el.innerHTML = h;
    if (st) {
      st.innerHTML = closed ?
        '<div class="note" style="display:flex;gap:14px;flex-wrap:wrap">' +
        '<span>trades: <b>' + D.tr.length + '</b> (closed ' + closed + ')</span>' +
        '<span>net P&L: <b style="color:' + (tot >= 0 ? UP : DN) + '">' + inr(tot) + '</b></span>' +
        '<span>win rate: <b style="color:' + (wins / closed >= 0.5 ? UP : "#d4af37") + '">' + (100 * wins / closed).toFixed(0) + '%</b></span>' +
        (awn ? '<span>avg win: <span style="color:' + UP + '">' + inr(aw / awn) + '</span></span>' : "") +
        (aln ? '<span>avg loss: <span style="color:' + DN + '">' + inr(al / aln) + '</span></span>' : "") +
        (bw > -1e17 ? '<span>best: <span style="color:' + UP + '">' + inr(bw) + '</span></span>' : "") +
        (bl < 1e17 ? '<span>worst: <span style="color:' + DN + '">' + inr(bl) + '</span></span>' : "") +
        '</div>' : '<div class="note">koi closed trade nahi \u2014 exit price bharoge tab P&L dikhega</div>';
    }
  }

  function render() { wlRender(); trRender(); }

  function addTr() {
    var sym = (document.getElementById("jSym") || {}).value || "";
    var sb = document.getElementById("jSideB");
    var side = (sb && sb.className.indexOf("on") >= 0) ? "B" : "S";
    var qty = parseFloat((document.getElementById("jQty") || {}).value);
    var entry = parseFloat((document.getElementById("jEntry") || {}).value);
    var exit = parseFloat((document.getElementById("jExit") || {}).value);
    var sl = parseFloat((document.getElementById("jSl") || {}).value);
    var note = (document.getElementById("jNote") || {}).value || "";
    if (!sym.trim() || !(qty > 0) || !(entry > 0)) return;
    D.tr.push({
      sym: sym.trim().toUpperCase(), side: side, qty: qty, entry: entry,
      exit: exit > 0 ? exit : 0, sl: sl > 0 ? sl : 0, note: note.trim().slice(0, 140),
      dt: new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short" })
    });
    save(D);
    var c;
    if ((c = document.getElementById("jSym"))) c.value = "";
    if ((c = document.getElementById("jQty"))) c.value = "";
    if ((c = document.getElementById("jEntry"))) c.value = "";
    if ((c = document.getElementById("jExit"))) c.value = "";
    if ((c = document.getElementById("jSl"))) c.value = "";
    if ((c = document.getElementById("jNote"))) c.value = "";
    render();
  }

  function mount() {
    if (document.getElementById("journal")) return;
    /* tile -- portfolio tile ke baad */
    try {
      var hg = document.querySelector("section#home .homegrid");
      var pf = hg ? hg.querySelector('a[href="#portfolio"]') : null;
      var tile = document.createElement("a");
      tile.className = "tile";
      tile.href = "#journal";
      tile.innerHTML = '<span class="t-ic">\uD83D\uDCD3</span><span class="t-nm">Watchlist + Journal</span><span class="t-sb">my stocks \u00b7 trade log</span>';
      if (pf && pf.nextSibling) hg.insertBefore(tile, pf.nextSibling);
      else if (hg) hg.appendChild(tile);
    } catch (e) {}
    var INP = 'style="width:100%;box-sizing:border-box;padding:8px 12px;border-radius:10px;border:1px solid rgba(125,180,255,.35);background:rgba(96,165,250,.08);color:inherit;font-size:13px;font-family:var(--mono)"';
    var sec = document.createElement("section");
    sec.id = "journal";
    sec.style.display = "none";
    sec.innerHTML =
      '<a class="backbtn" href="#home">\u2302 Home</a>' +
      '<h2>Watchlist + Trade Journal</h2>' +
      '<div class="card"><div class="subhead">Watchlist</div>' +
      '<div style="display:flex;gap:8px;margin:6px 0">' +
      '<input id="jWlIn" placeholder="symbol (RELIANCE, NIFTY...)" ' + INP + '>' +
      '<button id="jWlAdd" class="chip" style="white-space:nowrap">Add</button></div>' +
      '<div id="jWl"></div>' +
      '<div class="note" style="opacity:.7;margin-top:4px">price live unhi symbols ke liye jo intraday feed me hain (NIFTY, BANKNIFTY, bade stocks); baaki sirf list me rehte hain</div></div>' +
      '<div class="card"><div class="subhead">Trade add karo</div>' +
      '<div class="grid g2" style="margin-top:6px">' +
      '<input id="jSym" placeholder="symbol" ' + INP + '>' +
      '<div class="controls"><button id="jSideB" class="chip on" style="flex:1">BUY</button><button id="jSideS" class="chip" style="flex:1">SELL</button></div>' +
      '<input id="jQty" type="number" inputmode="decimal" placeholder="qty" ' + INP + '>' +
      '<input id="jEntry" type="number" inputmode="decimal" placeholder="entry" ' + INP + '>' +
      '<input id="jExit" type="number" inputmode="decimal" placeholder="exit (khali = open)" ' + INP + '>' +
      '<input id="jSl" type="number" inputmode="decimal" placeholder="stop-loss (R ke liye)" ' + INP + '>' +
      '</div>' +
      '<input id="jNote" placeholder="note (setup, reason...)" ' + INP + ' style="margin-top:8px">' +
      '<button id="jAdd" class="chip" style="margin-top:8px">+ Add trade</button></div>' +
      '<div class="card"><div class="subhead">Journal</div><div id="jStats"></div><div id="jTr"></div></div>' +
      '<div class="card"><div class="subhead">Backup (encrypted)</div>' +
      '<div class="note" style="opacity:.75">data isi phone me encrypted save hota hai. dusre phone pe le jaana ho to yahan se copy karke import karo.</div>' +
      '<textarea id="jExp" readonly placeholder="export yahan aayega" style="width:100%;box-sizing:border-box;height:64px;margin-top:8px;border-radius:10px;border:1px solid rgba(125,180,255,.35);background:rgba(96,165,250,.06);color:inherit;font-size:11px;font-family:var(--mono);padding:8px"></textarea>' +
      '<div class="controls" style="margin-top:8px">' +
      '<button id="jCopy" class="chip">Export</button>' +
      '<button id="jImp" class="chip">Import (paste pehle)</button>' +
      '<button id="jWipe" class="chip" style="color:' + DN + '">Sab mitao</button></div></div>' +
      '<div class="footer-note">journal sirf tumhare phone me rehta hai \u2014 koi server pe nahi jata. honest tracking hi trading sudharti hai.</div>';
    var foot = document.querySelector("footer");
    if (foot && foot.parentNode) foot.parentNode.insertBefore(sec, foot);
    else document.body.appendChild(sec);

    document.getElementById("jWlAdd").addEventListener("click", function () {
      var s = (document.getElementById("jWlIn").value || "").trim().toUpperCase();
      if (!s) return;
      if (D.wl.indexOf(s) < 0 && D.wl.length < 40) { D.wl.push(s); save(D); }
      document.getElementById("jWlIn").value = "";
      render();
    });
    document.getElementById("jSideB").addEventListener("click", function () {
      document.getElementById("jSideB").className = "chip on";
      document.getElementById("jSideS").className = "chip";
    });
    document.getElementById("jSideS").addEventListener("click", function () {
      document.getElementById("jSideS").className = "chip on";
      document.getElementById("jSideB").className = "chip";
    });
    document.getElementById("jAdd").addEventListener("click", addTr);
    sec.addEventListener("click", function (e) {
      var t = e.target || e.srcElement;
      if (!(t && t.getAttribute)) return;
      var wl = t.getAttribute("data-j-delwl");
      var tr = t.getAttribute("data-j-deltr");
      if (wl) { D.wl = D.wl.filter(function (x) { return x !== wl; }); save(D); render(); }
      if (tr != null) { D.tr.splice(parseInt(tr, 10), 1); save(D); render(); }
    });
    document.getElementById("jCopy").addEventListener("click", function () {
      try {
        document.getElementById("jExp").value = localStorage.getItem(DATAN) || "";
        document.getElementById("jExp").select();
      } catch (e) {}
    });
    document.getElementById("jImp").addEventListener("click", function () {
      var v = (document.getElementById("jExp").value || "").trim();
      if (!v) { document.getElementById("jExp").value = "pehle dusre phone ka export text paste karo"; return; }
      try {
        var obj = JSON.parse(xor(b64d(v), getKey()));
        if (!obj.wl || !obj.tr) throw 0;
        /* paste walon ke records append karo -- {wl:[],tr:[]} */
        D.wl = D.wl.concat(obj.wl.filter(function (x) { return D.wl.indexOf(x) < 0; }));
        D.tr = D.tr.concat(obj.tr);
        save(D); render();
        document.getElementById("jExp").value = "import OK";
      } catch (e) { document.getElementById("jExp").value = "ye text nahi pada -- sahi export paste karo"; }
    });
    document.getElementById("jWipe").addEventListener("click", function () {
      if (window.confirm("watchlist + journal dono mit jayenge. pakka?")) {
        D = { wl: [], tr: [] }; save(D); render();
      }
    });
    loadPx();
    render();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", mount);
  else mount();
})();