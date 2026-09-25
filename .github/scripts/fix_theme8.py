import pathlib

# ---------- calm.css v6 -> v7 (+ radar styles) ----------
p = pathlib.Path("calm.css")
s = p.read_text()
ADDITION = '''
/* ---------- forecast + event radar ---------- */
.as-fr{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid var(--hair2)}
.as-fr:last-child{border-bottom:none}
.as-fr span{font-family:var(--mono);font-size:9px;color:var(--dim);letter-spacing:.04em}
.as-fr b{font-family:var(--mono);font-size:10.5px;font-weight:700;white-space:nowrap}
.as-fr b.u{color:var(--up)} .as-fr b.d{color:var(--down)}
.as-fr .c{color:var(--faint);font-size:8px;font-weight:500;margin-left:7px;font-style:normal}
.as-frt{border-bottom:1px solid var(--hair)}
.as-evh{display:flex;justify-content:space-between;margin:12px 0 4px;font-family:var(--mono);font-size:8px;letter-spacing:.18em;color:var(--faint)}
.as-evr{display:flex;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--hair2)}
.as-evr:last-child{border-bottom:none}
.as-evb{font-family:var(--mono);font-size:7.5px;font-weight:700;letter-spacing:.06em;padding:3px 7px;border-radius:5px;flex:0 0 auto}
.as-evb.open{background:var(--up-dim);color:var(--up)}
.as-evb.close{background:rgba(224,110,110,.12);color:#e08c8c}
.as-evn{font-size:11px;font-weight:600;line-height:1.25}
.as-evm{font-family:var(--mono);font-size:8px;color:var(--faint);letter-spacing:.04em}
'''
if "forecast + event radar" not in s:
    s = s.rstrip() + "\n" + ADDITION
s = s.replace("calm.css v6 — ARTHASAAR PREMIUM (compact header)", "calm.css v7 — ARTHASAAR PREMIUM (compact header + radars)")
p.write_text(s)

# ---------- index bump ----------
ix = pathlib.Path("index.html")
s = ix.read_text()
s = s.replace("calm.css?v=as7", "calm.css?v=as8").replace("themefix.js?v=25sep26a47", "themefix.js?v=25sep26a48")
ix.write_text(s)
print("v7 applied | radar css:", "forecast + event radar" in pathlib.Path("calm.css").read_text(), "| index a48:", "25sep26a48" in s)
