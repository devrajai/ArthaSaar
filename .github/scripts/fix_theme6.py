import pathlib

# ---------- calm.css v4 -> v5 (reference header) ----------
p = pathlib.Path("calm.css")
s = p.read_text()
R = [
 ("""/* ---------- green line REMOVED ---------- */
.as-rline{display:none !important}""",
  """/* ---------- gradient rline (reference design) ---------- */
.as-rline{height:2px;border-radius:2px;margin:2px 0 10px;
  background:linear-gradient(90deg,var(--blue),var(--up))}"""),
 ("  margin:12px 0;padding:8px 0}", "  margin:10px 0;padding:8px 0}"),
 ("""header .logo{background:none !important;border:none !important;color:transparent !important;font-size:0 !important;
  width:42px;height:48px;padding:0 !important;display:flex;align-items:center;box-shadow:none !important}
header .logo svg{width:42px;height:48px}""",
  """header .logo{background:none !important;border:none !important;color:transparent !important;font-size:0 !important;
  width:44px;height:44px;padding:0 !important;display:flex;align-items:center;box-shadow:none !important}
header .logo svg{width:44px;height:44px}"""),
 ("""#themeBtn{font-family:var(--mono);font-size:13px;width:32px;height:32px;border-radius:8px;
  background:var(--panel2);border:1px solid var(--hair);color:var(--dim)}
#refreshBtn{font-family:var(--mono);font-size:9px;letter-spacing:.1em;padding:5px 11px;border-radius:7px;
  background:linear-gradient(135deg,var(--blue),var(--up));border:none;color:#0a1622;font-weight:700}
#themeBtn:active{border-color:var(--blue)}""",
  """#themeBtn{font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.08em;width:auto;
  height:32px;padding:0 13px;border-radius:8px;border:none;
  background:linear-gradient(135deg,var(--blue),var(--up));color:#0a1622}
#refreshBtn{font-family:var(--mono);font-size:9px;letter-spacing:.1em;padding:5px 11px;border-radius:7px;
  background:linear-gradient(135deg,var(--blue),var(--up));border:none;color:#0a1622;font-weight:700}"""),
 ("calm.css v4 — ARTHASAAR PREMIUM", "calm.css v5 — ARTHASAAR PREMIUM (reference header)"),
]
for old, new in R:
    assert old in s, "missing: " + old[:50]
    s = s.replace(old, new)
p.write_text(s)

# ---------- ipo/index.html: sheet status first ----------
p3 = pathlib.Path("ipo/index.html")
t = p3.read_text()
OLD_ST = """function status(x){const now=new Date(),o=parseDate(x.open_date),c=parseDate(x.close_date,true);if(o&&now<o)return'UPCOMING';if(o&&c&&now>=o&&now<=c)return'OPEN';if(c&&now>c)return'CLOSED';return String(x.status||'UPCOMING').toUpperCase()}"""
NEW_ST = """function status(x){const s=String(x.status||'').toLowerCase();if(s==='upcoming')return'UPCOMING';if(s==='open'||s==='closing')return'OPEN';if(s==='closed'||s==='allotment')return'CLOSED';const now=new Date(),o=parseDate(x.open_date),c=parseDate(x.close_date,true);if(o&&now<o)return'UPCOMING';if(o&&c&&now>=o&&now<=c)return'OPEN';if(c&&now>c)return'CLOSED';return'UPCOMING'}"""
assert OLD_ST in t, "ipo status fn missing"
p3.write_text(t.replace(OLD_ST, NEW_ST))

# ---------- scripts/global_collect.py: add SENSEX ----------
p4 = pathlib.Path("scripts/global_collect.py")
g = p4.read_text()
if '"SENSEX"' not in g:
    anchor = '    "S&P 500": "^GSPC",'
    assert anchor in g, "GSPC anchor missing"
    g = g.replace(anchor, anchor + '\n    "SENSEX": "^BSESN",')
p4.write_text(g)

# ---------- index bump ----------
ix = pathlib.Path("index.html")
s = ix.read_text()
s = s.replace("calm.css?v=as5", "calm.css?v=as6").replace("themefix.js?v=25sep26a45", "themefix.js?v=25sep26a46")
ix.write_text(s)
print("v5 applied | sensex in global_collect:", '"SENSEX"' in pathlib.Path("scripts/global_collect.py").read_text(),
      "| ipo fixed:", "if(s==='upcoming')return'UPCOMING'" in pathlib.Path("ipo/index.html").read_text(),
      "| index a46:", "25sep26a46" in s)
