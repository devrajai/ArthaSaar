import pathlib

# ---------- calm.css v5 -> v6 (compact header per Dev) ----------
p = pathlib.Path("calm.css")
s = p.read_text()
R = [
 ("""header h1{font-family:'Space Grotesk',var(--font);font-weight:700;letter-spacing:.045em;font-size:1.45em;line-height:1.1}""",
  """header h1{font-family:'Space Grotesk',var(--font);font-weight:700;letter-spacing:.045em;font-size:1.2em;line-height:1.1}
header h1::after{content:"";display:block;height:2px;border-radius:2px;margin-top:5px;
  background:linear-gradient(90deg,var(--blue),var(--up))}"""),
 ("""header .tagline{color:var(--faint);letter-spacing:.22em;text-transform:uppercase;font-size:7.5px;font-family:var(--mono)}""",
  """header .tagline{color:var(--faint);letter-spacing:.22em;text-transform:uppercase;font-size:6.5px;font-family:var(--mono)}"""),
 ("""#clock{font-family:var(--mono);font-size:15px;font-weight:600;letter-spacing:.02em}
#clockdate{font-size:9px;color:var(--faint);font-family:var(--mono);letter-spacing:.06em}
.meta-row{color:var(--faint);font-size:9px;letter-spacing:.04em;font-family:var(--mono)}""",
  """.clockbox{display:none !important}
.meta-row{display:none !important}
.header-right{align-self:flex-start;margin-top:3px}"""),
 ("margin:20px 0 9px;font-size:9.5px;", "margin:18px 0 8px;font-size:8.5px;"),
 ("""section h2{font-family:var(--mono);font-size:10px;letter-spacing:.2em;color:var(--text);""",
  """section h2{font-family:var(--mono);font-size:9px;letter-spacing:.2em;color:var(--text);"""),
 ("  font-size:18px;background:linear-gradient(135deg,var(--blue-dim),var(--up-dim));border:1px solid var(--hair);flex:0 0 auto}",
  "  font-size:16px;background:linear-gradient(135deg,var(--blue-dim),var(--up-dim));border:1px solid var(--hair);flex:0 0 auto}"),
 (""".t-nm{grid-column:2;align-self:end;font-size:13.5px;font-weight:600;line-height:1.2}""",
  """.t-nm{grid-column:2;align-self:end;font-size:12px;font-weight:600;line-height:1.2}"""),
 (""".t-sb{grid-column:2;align-self:start;font-size:8.5px;color:var(--faint);line-height:1.4;font-family:var(--mono);""",
  """.t-sb{grid-column:2;align-self:start;font-size:7.5px;color:var(--faint);line-height:1.4;font-family:var(--mono);"""),
 (""".as-ht{display:flex;justify-content:space-between;font-family:var(--mono);font-size:8px;""",
  """.as-ht{display:flex;justify-content:space-between;font-family:var(--mono);font-size:7px;"""),
 (""".as-hv{font-family:'Space Grotesk',var(--font);font-size:27px;font-weight:700;letter-spacing:-.01em;""",
  """.as-hv{font-family:'Space Grotesk',var(--font);font-size:23px;font-weight:700;letter-spacing:-.01em;"""),
 (""".as-hv .u,.as-hv .d{font-size:13.5px;font-family:var(--mono);font-weight:600;margin-left:6px}""",
  """.as-hv .u,.as-hv .d{font-size:12px;font-family:var(--mono);font-weight:600;margin-left:6px}"""),
 (""".as-hc i{display:block;font-style:normal;font-family:var(--mono);font-size:7px;""",
  """.as-hc i{display:block;font-style:normal;font-family:var(--mono);font-size:6.5px;"""),
 (""".as-hc b{font-family:var(--mono);font-size:11.5px;font-weight:700}""",
  """.as-hc b{font-family:var(--mono);font-size:10.5px;font-weight:700}"""),
 ("  font-family:var(--mono);font-size:10.5px;width:max-content}",
  "  font-family:var(--mono);font-size:9.5px;width:max-content}"),
 ("calm.css v5 — ARTHASAAR PREMIUM (reference header)", "calm.css v6 — ARTHASAAR PREMIUM (compact header)"),
]
for old, new in R:
    assert old in s, "missing: " + old[:50]
    s = s.replace(old, new)
p.write_text(s)

# ---------- index bump ----------
ix = pathlib.Path("index.html")
s = ix.read_text()
s = s.replace("calm.css?v=as6", "calm.css?v=as7").replace("themefix.js?v=25sep26a46", "themefix.js?v=25sep26a47")
ix.write_text(s)
print("v6 applied | index as7:", "25sep26a47" in s)
