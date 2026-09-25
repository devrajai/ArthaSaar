# fix_bold.py - one-shot: IPO-style BOLD theme + CORRECTION ALARM top + css cache bump.
from pathlib import Path

# 1) alarm.js: mount CORRECTION ALARM at top (after h2, F&O Radar ke saath) instead of bottom
p = Path('alarm.js')
s = p.read_text()
old = '    sec.appendChild(c);'
new = ('    var h2 = sec.querySelector("h2");\n'
       '    if (h2 && h2.parentNode) sec.insertBefore(c, h2.nextSibling); else sec.appendChild(c);')
if 'insertBefore' not in s and old in s:
    s = s.replace(old, new, 1)
    p.write_text(s)
    print('alarm.js: CORRECTION ALARM moved to top')
else:
    print('alarm.js: skipped (done already or pattern missing)')

# 2) index.html: cache-bump stylesheet link
p = Path('index.html')
s = p.read_text()
if 'style.css?v=as1' not in s:
    s = s.replace('href="style.css"', 'href="style.css?v=as1"', 1)
    p.write_text(s)
    print('index.html: css bump as1')
else:
    print('index.html: already bumped')

# 3) style.css: append ARTHASAAR BOLD THEME (IPO-style)
p = Path('style.css')
s = p.read_text()
if 'ARTHASAAR BOLD THEME' not in s:
    block = """

/* ===== ARTHASAAR BOLD THEME (IPO-style, 25 Sep) =====
   Bigger numbers, 900-weight fonts, brighter colours - IPO terminal look.
   NO backdrop-filter (Android perf), glass gradient + inset highlight instead. */
:root{
  --font:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;
  --mono:ui-monospace,Menlo,Consolas,"SF Mono",monospace;
  --text:#f8fafc; --dim:#a5b2c2; --faint:#71809a;
  --up:#22c55e; --down:#ef4444; --amber:#f5a623; --blue:#3b82f6;
  --border:rgba(255,255,255,.14); --border2:rgba(255,255,255,.22);
}
[data-theme="light"]{
  --up:#16a34a; --down:#dc2626; --amber:#c07d10; --blue:#2563eb;
}
body{font-size:14.5px;line-height:1.5}
h1{font-size:23px;font-weight:800;letter-spacing:.02em}
h2{font-weight:800}
#clock{font-weight:800}
.card{border-radius:20px;background:linear-gradient(135deg,var(--glass2),var(--glass));
  box-shadow:var(--shadow),inset 0 1px 0 rgba(255,255,255,.08)}
.subhead{font-weight:800;font-size:11.5px;letter-spacing:.09em}
.note{font-size:12px}
.kpi{border-radius:18px}
.kpi .k-name{font-weight:800}
.kpi .k-val{font-size:27px;font-weight:900}
.kpi .k-chg{font-size:13px;font-weight:800}
table{font-size:13px}
th{font-weight:800;font-size:10.5px}
td{font-weight:600}
.num{font-weight:700}
.statline{font-size:12px}
.statline b{font-weight:800}
.chg-badge{font-size:12px;font-weight:800;padding:3px 9px}
.tab{font-weight:800}
.chip{font-weight:700}
.morebtn{font-weight:700}
.hchip{font-weight:800}
.badge-tier{font-weight:800}
details.gl summary{font-weight:700}
.kv span:nth-child(odd){font-weight:700}
a{font-weight:600}
"""
    p.write_text(s + block)
    print('style.css: bold theme appended')
else:
    print('style.css: theme already present')
print('DONE')
