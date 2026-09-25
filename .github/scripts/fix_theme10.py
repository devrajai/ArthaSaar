import pathlib

# ---------- calm.css v8 -> v9 (hide tile subtitles) ----------
p = pathlib.Path("calm.css")
s = p.read_text()
OLD = """.t-sb{grid-column:2;align-self:start;font-size:7.5px;color:var(--faint);line-height:1.4;font-family:var(--mono);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}"""
NEW = """.t-sb{display:none !important}"""
assert OLD in s, "t-sb rule missing"
s = s.replace(OLD, NEW)
s = s.replace("calm.css v8 — ARTHASAAR PREMIUM (compact header + radars, no tagline)",
              "calm.css v9 — ARTHASAAR PREMIUM (compact header + radars, no small words)")
p.write_text(s)

# ---------- index bump ----------
ix = pathlib.Path("index.html")
s = ix.read_text()
s = s.replace("calm.css?v=as9", "calm.css?v=as10").replace("themefix.js?v=25sep26a49", "themefix.js?v=25sep26a50")
ix.write_text(s)
print("v9 applied | t-sb hidden:", "display:none !important}" in pathlib.Path("calm.css").read_text(), "| index a50:", "25sep26a50" in s)
