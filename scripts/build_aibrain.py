#!/usr/bin/env python3
"""build_aibrain.py - writes aibrain.js, adds AI Brain tile+section to index.html,
adds aibrain.js to app.js loader list, bumps version. Idempotent."""
import io
Q = chr(34)

JS = '''/* aibrain.js - AI Brain: mood meter (news sentiment), crash warning system, TimesFM report card, sector rotation. */
(function () {
  if (window.__MB_AIB) return; window.__MB_AIB = 1;
  var sec = document.getElementById("aibrain");
  if (!sec) {
    sec = document.createElement("section");
    sec.id = "aibrain"; sec.style.display = "none";
    sec.innerHTML = '<a class="backbtn" href="#home">Home</a><h2>AI Brain</h2>' +
      '<div class="card" id="abMood"></div><div class="card" id="abRisk"></div>' +
      '<div class="card" id="abAcc"></div><div class="card" id="abRot"></div>';
    var ft = document.querySelector("footer");
    if (ft) ft.parentNode.insertBefore(sec, ft); else document.body.appendChild(sec);
  }
  var _A = String.fromCharCode(38,97,109,112,59), _L = String.fromCharCode(38,108,116,59), _G = String.fromCharCode(38,103,116,59);
  function esc(s) { s = String(s == null ? "" : s); return s.split("&").join(_A).split("<").join(_L).split(">").join(_G); }
  function badge(v) { var c = v >= 58 ? "pos" : (v <= 42 ? "neg" : ""); return '<b class="' + c + '">' + v + "</b>"; }

  function loadMood() {
    var box = document.getElementById("abMood");
    box.innerHTML = '<div class="subhead">Market Mood Meter</div><div class="note">load ho raha...</div>';
    jload("mood").then(function (d) {
      var o = d.overall || 50, tag = d.tag || "-";
      var emot = o >= 70 ? "\U0001F680" : (o >= 58 ? "\U0001F642" : (o >= 42 ? "\U0001F610" : (o >= 30 ? "\U0001F613" : "\U0001F631")));
      var color = o >= 58 ? "#22c55e" : (o >= 42 ? "#eab308" : "#ef4444");
      var html = '<div class="subhead">' + emot + ' Market Mood Meter <span style="float:right;font-size:22px;color:' + color + '">' + o + '/100</span></div>' +
        '<div style="height:14px;border-radius:7px;background:linear-gradient(90deg,#ef4444,#eab308,#22c55e);position:relative;margin:8px 0">' +
        '<i style="position:absolute;top:-4px;left:' + Math.max(0, Math.min(97, o - 1)) + '%;width:4px;height:22px;background:#fff;border-radius:2px;box-shadow:0 0 6px #fff"></i></div>' +
        '<div class="note"><b>' + esc(tag) + "</b> - " + (d.counted || 0) + " headlines scan karke (word-score AI, 100% free)</div>";
      if ((d.pos || []).length) {
        html += '<div class="subhead" style="margin-top:10px">\U0001F642 Positive headlines</div>';
        d.pos.slice(0, 3).forEach(function (h) { html += '<div class="note" style="margin:3px 0">' + badge(h.s) + " - " + esc(h.t).slice(0, 85) + "</div>"; });
      }
      if ((d.neg || []).length) {
        html += '<div class="subhead" style="margin-top:10px">\U0001F613 Negative headlines</div>';
        d.neg.slice(0, 3).forEach(function (h) { html += '<div class="note" style="margin:3px 0">' + badge(h.s) + " - " + esc(h.t).slice(0, 85) + "</div>"; });
      }
      if ((d.stocks || []).length) {
        html += '<div class="subhead" style="margin-top:10px">Stock sentiment (news se)</div><div>';
        d.stocks.slice(0, 8).forEach(function (s) { html += '<span class="chip" style="margin:2px">' + esc(s.sym) + " " + badge(s.s) + "</span>"; });
        html += "</div>";
      }
      html += '<div class="note" style="margin-top:6px;opacity:.7">har 6 ghante auto-update</div>';
      box.innerHTML = html;
    }, function () { box.innerHTML = '<div class="subhead">Market Mood Meter</div><div class="note">mood data nahi mila - thodi der baad try karo</div>'; });
  }

  function loadRisk() {
    var box = document.getElementById("abRisk");
    box.innerHTML = '<div class="subhead">Crash Warning System</div><div class="note">load ho raha...</div>';
    var acc = {}, need = 5, got = 0;
    function tick() { got++; if (got >= need) done(); }
    function done() {
      var tf = acc.tf || {}, fcs = (tf.forecasts || []);
      var vix = null, nif = null;
      fcs.forEach(function (f) { if (f.symbol === "^INDIAVIX") vix = f.as_of_last_close; if (f.symbol === "^NSEI") nif = f; });
      var pcr = (acc.fu && acc.fu.pcr) || {};
      var cats = (acc.fd && acc.fd.categories) || {};
      var fii = ((cats["FII/FPI"]) || {}).net_cr;
      var dii = ((cats.DII) || {}).net_cr;
      var brd = acc.br ? acc.br.above_ema200_pct : null;
      var sb = (acc.sb && acc.sb.guess) || {};
      var pts = [], score = 0;
      if (vix != null) { var p = vix >= 20 ? 30 : (vix >= 16 ? 20 : (vix >= 14 ? 10 : 0)); score += p; pts.push(["India VIX " + vix.toFixed(1), p]); }
      var pc = pcr.nifty_pcr_oi;
      if (pc != null) { var p2 = pc < 0.85 ? 20 : (pc < 1.0 ? 12 : 0); if (pc > 1.3) p2 = -5; score += p2; pts.push(["Nifty PCR " + pc, p2]); }
      if (fii != null) { var p3 = fii <= -4000 ? 20 : (fii <= -1500 ? 12 : (fii <= -500 ? 6 : 0)); if (fii >= 1000) p3 = -5; score += p3; pts.push(["FII net " + fii + " Cr", p3]); }
      if (brd != null) { var p4 = brd < 35 ? 15 : (brd < 45 ? 8 : 0); score += p4; pts.push(["Breadth " + brd + "% above EMA200", p4]); }
      if (sb.score != null) { var p5 = sb.score < 35 ? 10 : (sb.score < 45 ? 5 : (sb.score > 65 ? -5 : 0)); score += p5; pts.push(["Smart Brain " + sb.score, p5]); }
      if (nif && nif.median_chg_pct != null) { var c = nif.median_chg_pct; var p6 = c < -2 ? 8 : (c < -1 ? 4 : (c > 2 ? -5 : 0)); score += p6; pts.push(["TimesFM Nifty 21d " + (c >= 0 ? "+" : "") + c.toFixed(1) + "%", p6]); }
      if (dii != null && dii >= 2000) { score -= 5; pts.push(["DII support +" + dii.toFixed(0) + " Cr", -5]); }
      if (score < 0) score = 0; if (score > 100) score = 100;
      var st = score < 25 ? ["\U0001F7E2 SAB CLEAR", "#22c55e", "koi khaas khatra nahi"] :
               (score < 50 ? ["\U0001F7E1 CAUTION", "#eab308", "dhyan rakho - kuch signals weak hain"] :
               (score < 75 ? ["\U0001F7E0 ALERT", "#f97316", "risk badh raha hai - position size chhota rakho"] :
                            ["\U0001F534 DANGER", "#ef4444", "multiple warnings - capital bachao"]));
      var h = '<div class="subhead">\U0001F6A8 Crash Warning System <span style="float:right;color:' + st[1] + '">' + st[0] + "</span></div>" +
        '<div style="font-size:36px;font-weight:700;color:' + st[1] + ';margin:4px 0">' + score + '<span style="font-size:14px;opacity:.6">/100 risk</span></div>' +
        '<div class="note" style="color:' + st[1] + '">' + st[2] + "</div>" +
        '<div class="subhead" style="margin-top:10px">Factors (+ = risk, - = support)</div>';
      pts.forEach(function (p) { var cls = p[1] > 0 ? "neg" : (p[1] < 0 ? "pos" : ""); h += '<div class="note" style="display:flex;justify-content:space-between;margin:2px 0"><span>' + esc(p[0]) + '</span><b class="' + cls + '">' + (p[1] > 0 ? "+" : "") + p[1] + "</b></div>"; });
      h += '<div class="note" style="margin-top:8px;opacity:.7">VIX + PCR + FII + breadth + TimesFM + Smart Brain ka combination score. Signal hai, guarantee nahi.</div>';
      box.innerHTML = h;
    }
    jload("timesfm_forecasts").then(function (d) { acc.tf = d; }, tick).then(tick, tick);
    jload("futures").then(function (d) { acc.fu = d; }, tick).then(tick, tick);
    jload("fii-dii").then(function (d) { acc.fd = d; }, tick).then(tick, tick);
    jload("breadth").then(function (d) { acc.br = d; }, tick).then(tick, tick);
    jload("smart-brain").then(function (d) { acc.sb = d; }, tick).then(tick, tick);
  }

  function loadAcc() {
    var box = document.getElementById("abAcc");
    box.innerHTML = '<div class="subhead">TimesFM Report Card</div><div class="note">load ho raha...</div>';
    jload("timesfm_forecasts").then(function (d) {
      var a = d.accuracy || {};
      var h = '<div class="subhead">\U0001F393 TimesFM Report Card <span class="note" style="float:right">' + esc(d.model || "TimesFM") + "</span></div>";
      if (a.tracked) {
        var rate = a.rate == null ? "-" : (Math.round(a.rate * 100) + "%");
        h += '<div style="font-size:30px;font-weight:700" class="pos">' + rate + ' <span style="font-size:13px;opacity:.6">direction hit-rate</span></div>' +
          '<div class="note">' + a.hits + "/" + a.tracked + " predictions sahi disha mein - roz auto-check hota hai</div>";
      } else {
        h += '<div class="note">\U0001F4CA Accuracy tracker chalu - har roz ki prediction log ho rahi hai. <b>21 din</b> baad pehla report card banega (prediction vs actual).<br>Model khud check hoga - no gyan, sirf hisaab.</div>';
      }
      var fcs = d.forecasts || [], nif = null;
      fcs.forEach(function (f) { if (f.symbol === "^NSEI") nif = f; });
      if (nif && nif.median_chg_pct != null) {
        var med = nif.median_chg_pct, lo = nif.low10_chg_pct, hi = nif.high90_chg_pct;
        h += '<div class="subhead" style="margin-top:10px">Nifty 21-din AI forecast</div>' +
          '<div class="note">median <b class="' + (med >= 0 ? "pos" : "neg") + '">' + (med >= 0 ? "+" : "") + med.toFixed(1) + '%</b> - worst <b class="neg">' + lo.toFixed(1) + '%</b> - best <b class="pos">+' + hi.toFixed(1) + "%</b></div>" +
          '<div class="note" style="margin-top:4px;opacity:.7">worst/best = model ka 10%/90% confidence range</div>';
      }
      box.innerHTML = h;
    }, function () { box.innerHTML = '<div class="subhead">TimesFM Report Card</div><div class="note">forecast data nahi mila</div>'; });
  }

  function loadRot() {
    var box = document.getElementById("abRot");
    jload("timesfm_forecasts").then(function (d) {
      var rot = d.rotation || [];
      if (!rot.length) { box.innerHTML = ""; return; }
      var h = '<div class="subhead">\U0001F504 Sector Rotation - AI ranked</div>';
      rot.forEach(function (r) {
        var w = Math.max(4, Math.min(100, Math.abs(r.chg30) * 12));
        var cls = r.chg30 >= 0 ? "pos" : "neg";
        h += '<div style="display:flex;align-items:center;gap:8px;margin:4px 0">' +
          '<span style="width:92px;font-size:12px">' + esc(r.name) + "</span>" +
          '<span style="flex:1;height:9px;border-radius:5px;background:rgba(255,255,255,.07);overflow:hidden"><i style="display:block;width:' + w + '%;height:100%;border-radius:5px;background:' + (r.chg30 >= 0 ? "linear-gradient(90deg,#22c55e,#4ade80)" : "linear-gradient(90deg,#ef4444,#f87171)") + '"></i></span>' +
          '<span class="' + cls + '" style="width:52px;text-align:right;font-size:12px">' + (r.chg30 >= 0 ? "+" : "") + r.chg30.toFixed(1) + '%</span>' +
          '<span class="note" style="width:60px;text-align:right">conf ' + r.conf + "</span></div>";
      });
      h += '<div class="note" style="margin-top:6px">30-din momentum + TimesFM confidence se ranked</div>';
      box.innerHTML = h;
    }, function () { box.innerHTML = ""; });
  }

  loaders.aibrain = function () { loadMood(); loadRisk(); loadAcc(); loadRot(); };
})();
'''

io.open("aibrain.js", "w", encoding="utf-8").write(JS)
print("aibrain.js written:", len(JS), "chars")

# ---- index.html: tile after AI Forecast tile + static section before footer + v bump ----
AI_TILE = ('<a class="tile" href="#ai"><span class="t-ic">\U0001F916</span>'
           '<span class="t-nm">AI Forecast</span><span class="t-sb">TimesFM 21-day</span></a>')
AB_TILE = ('<a class="tile" href="#aibrain"><span class="t-ic">\U0001F9E0</span>'
           '<span class="t-nm">AI Brain</span><span class="t-sb">mood · crash · report</span></a>')
AB_SEC = ('<section id="aibrain" style="display:none"><a class="backbtn" href="#home">Home</a>'
          '<h2>AI Brain</h2><div class="card" id="abMood"></div><div class="card" id="abRisk"></div>'
          '<div class="card" id="abAcc"></div><div class="card" id="abRot"></div></section>')
s = io.open("index.html", encoding="utf-8").read()
if 'href="#aibrain"' not in s:
    assert AI_TILE in s, "AI Forecast tile not found"
    s = s.replace(AI_TILE, AI_TILE + AB_TILE, 1)
if 'id="aibrain"' not in s:
    i = s.find("<footer")
    assert i > 0, "footer not found"
    s = s[:i] + AB_SEC + s[i:]
s = s.replace("app.js?v=21sep26k", "app.js?v=21sep26l")
io.open("index.html", "w", encoding="utf-8").write(s)
print("index.html patched")

# ---- app.js: add aibrain.js to loader list ----
s = io.open("app.js", encoding="utf-8").read()
old = Q + "learnadd.js" + Q + "]"
new = Q + "learnadd.js" + Q + ", " + Q + "aibrain.js" + Q + "]"
if Q + "aibrain.js" + Q not in s:
    assert old in s, "learnadd entry not found"
    s = s.replace(old, new, 1)
io.open("app.js", "w", encoding="utf-8").write(s)
print("app.js patched")
