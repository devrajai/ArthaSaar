import pathlib

# ---------- calm.css v3 -> v4 ----------
p = pathlib.Path("calm.css")
s = p.read_text()

OLD_STATUS = """/* ---------- status bar ---------- */
.as-status{position:fixed;left:0;right:0;bottom:0;display:flex;z-index:60;
  font-family:var(--mono);font-size:8.5px;letter-spacing:.05em;color:#fff;opacity:.95}
.as-status i{flex:1;padding:5px 4px;text-align:center;font-style:normal}
.as-status .s1{background:var(--down)}
.as-status .s2{background:var(--amber);color:#231a00}
.as-status .s3{background:var(--up);color:#0a2617}
.as-status .s4{background:var(--blue);color:#0a1b2e}
"""
NEW_STATUS = """/* ---------- status bar REMOVED (user 25 Sep) ---------- */
.as-status{display:none !important}

/* ---------- hero panel ---------- */
.as-hero{background:linear-gradient(160deg,var(--panel2),var(--panel));border:1px solid var(--hair);
  border-radius:14px;padding:14px 14px 12px;margin:0 0 14px}
.as-ht{display:flex;justify-content:space-between;font-family:var(--mono);font-size:8px;
  letter-spacing:.18em;color:var(--faint);margin-bottom:6px}
.as-hv{font-family:'Space Grotesk',var(--font);font-size:27px;font-weight:700;letter-spacing:-.01em;
  margin-bottom:11px;font-variant-numeric:tabular-nums;line-height:1.1}
.as-hv .u,.as-hv .d{font-size:13.5px;font-family:var(--mono);font-weight:600;margin-left:6px}
.as-hv .u{color:var(--up)} .as-hv .d{color:var(--down)}
.as-hg{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:var(--hair);
  border:1px solid var(--hair);border-radius:10px;overflow:hidden}
.as-hc{background:var(--panel);padding:8px 4px;text-align:center}
.as-hc i{display:block;font-style:normal;font-family:var(--mono);font-size:7px;
  letter-spacing:.14em;color:var(--faint);margin-bottom:3px}
.as-hc b{font-family:var(--mono);font-size:11.5px;font-weight:700}
.as-hc b.u{color:var(--up)} .as-hc b.d{color:var(--down)}
"""
assert OLD_STATUS in s, "calm: status block missing"
s = s.replace(OLD_STATUS, NEW_STATUS)
s = s.replace("padding-bottom:34px;", "padding-bottom:16px;")

OLD_IC = """.t-ic{grid-row:1/3;width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;
  font-size:18px;background:var(--panel2);border:1px solid var(--hair);flex:0 0 auto}"""
NEW_IC = """.t-ic{grid-row:1/3;width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;
  font-size:18px;background:linear-gradient(135deg,var(--blue-dim),var(--up-dim));border:1px solid var(--hair);flex:0 0 auto}"""
assert OLD_IC in s, "calm: t-ic missing"
s = s.replace(OLD_IC, NEW_IC)
s = s.replace("calm.css v3 — ARTHASAAR PRO", "calm.css v4 — ARTHASAAR PREMIUM")
p.write_text(s)

# ---------- themefix.js v3 -> v4 ----------
p2 = pathlib.Path("themefix.js")
j = p2.read_text()
j = j.replace("/* themefix.js v3 - ARTHASAAR PRO retheme:", "/* themefix.js v4 - ARTHASAAR PREMIUM retheme:")
j = j.replace("6) desk summary strip  7) status bar", "6) hero NIFTY panel (status bar removed)")

OLD_SB = """  /* ---------- 7) status bar ---------- */
  function statusbar() {
    try {
      if (document.querySelector(".as-status")) return;
      var s = document.createElement("div");
      s.className = "as-status";
      s.innerHTML = "<i class='s1'>EDUCATIONAL</i><i class='s2'>NOT ADVICE</i><i class='s3'>FREE SOURCES</i><i class='s4'>ARTHASAAR</i>";
      (document.body || document.documentElement).appendChild(s);
    } catch (e) {}
  }

  function boot() { if (window.MB_LOCKED) return; apply(); statusbar(); ticker(); desk(); }"""
NEW_SB = """  /* ---------- status bar REMOVED (user request 25 Sep) — purana ho to hatao ---------- */
  function rmstatus() {
    try {
      var sb = document.querySelector(".as-status");
      if (sb && sb.parentNode) sb.parentNode.removeChild(sb);
    } catch (e) {}
  }

  function boot() { if (window.MB_LOCKED) return; rmstatus(); apply(); ticker(); desk(); }"""
assert OLD_SB in j, "themefix: statusbar fn missing"
j = j.replace(OLD_SB, NEW_SB)

start = j.index("  /* ---------- 6) desk summary strip (home top) ---------- */")
end = j.index("  /* ---------- status bar REMOVED")
NEW_DESK = """  /* ---------- 6) hero NIFTY panel (home top) ---------- */
  function desk() {
    fetch("data/indices-all.json").then(function (r) { return r.json(); }).then(function (d) {
      if (!d || !d.indices || !d.indices.length) return;
      var home = document.querySelector("section#home");
      if (!home) return;
      var old = document.querySelector(".as-hero");
      if (old && old.parentNode) old.parentNode.removeChild(old);
      var idx = d.indices;
      var pos = 0;
      idx.forEach(function (i) { if ((i.change_pct || 0) > 0) pos++; });
      var by = {};
      idx.forEach(function (i) { by[i.index] = i; });
      var n = by["NIFTY 50"] || idx[0];
      var sen = by["SENSEX"];
      var v = by["INDIA VIX"];
      var chg = n ? (Number(n.change_pct) || 0) : 0;
      var el = document.createElement("div");
      el.className = "as-hero";
      var dt = new Date().toLocaleDateString("en-IN", { day: "2-digit", month: "short" }).toUpperCase();
      el.innerHTML = "<div class='as-ht'><span>NIFTY 50 · LIVE</span><span>" + dt + " IST</span></div>" +
        "<div class='as-hv'>" + (n ? Number(n.price).toLocaleString("en-IN") : "—") +
        "<span class='" + (chg >= 0 ? "u" : "d") + "'>" + (chg >= 0 ? "▲" : "▼") + " " + Math.abs(chg).toFixed(2) + "%</span></div>" +
        "<div class='as-hg'>" +
        "<div class='as-hc'><i>TREND</i><b class='" + (chg >= 0 ? "u" : "d") + "'>" + (chg >= 0 ? "UP" : "DOWN") + "</b></div>" +
        "<div class='as-hc'><i>BREADTH</i><b class='" + (pos > idx.length / 2 ? "u" : "d") + "'>" + pos + "/" + idx.length + "</b></div>" +
        "<div class='as-hc'><i>SENSEX</i><b>" + (sen ? Number(sen.price).toLocaleString("en-IN") : "—") + "</b></div>" +
        "<div class='as-hc'><i>VIX</i><b class='" + (v && (Number(v.change_pct) || 0) < 0 ? "u" : "d") + "'>" + (v ? Number(v.price).toFixed(1) : "—") + "</b></div>" +
        "</div>";
      home.insertBefore(el, home.firstChild);
    }).catch(function () {});
  }

"""
j = j[:start] + NEW_DESK + j[end:]
p2.write_text(j)

# ---------- index bump ----------
ix = pathlib.Path("index.html")
s = ix.read_text()
s = s.replace("calm.css?v=as4", "calm.css?v=as5").replace("themefix.js?v=25sep26a44", "themefix.js?v=25sep26a45")
ix.write_text(s)
print("v4 applied. calm has hero:", ".as-hero{background" in pathlib.Path("calm.css").read_text(),
      "| themefix no statusbar:", "statusbar()" not in pathlib.Path("themefix.js").read_text(),
      "| index a45:", "25sep26a45" in s)
