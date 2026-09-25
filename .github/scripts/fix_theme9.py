import pathlib

# ---------- calm.css v7 -> v8 (tagline removed) ----------
p = pathlib.Path("calm.css")
s = p.read_text()
OLD = """header .tagline{color:var(--faint);letter-spacing:.22em;text-transform:uppercase;font-size:6.5px;font-family:var(--mono)}"""
NEW = """header .tagline{display:none !important;color:var(--faint);letter-spacing:.22em;text-transform:uppercase;font-size:6.5px;font-family:var(--mono)}"""
assert OLD in s, "tagline rule missing"
s = s.replace(OLD, NEW)
s = s.replace("calm.css v7 — ARTHASAAR PREMIUM (compact header + radars)",
              "calm.css v8 — ARTHASAAR PREMIUM (compact header + radars, no tagline)")
p.write_text(s)

# ---------- index bump ----------
ix = pathlib.Path("index.html")
s = ix.read_text()
s = s.replace("calm.css?v=as8", "calm.css?v=as9").replace("themefix.js?v=25sep26a48", "themefix.js?v=25sep26a49")
ix.write_text(s)
print("v8 applied | tagline hidden:", "display:none !important;color:var(--faint)" in pathlib.Path("calm.css").read_text(), "| index a49:", "25sep26a49" in s)
