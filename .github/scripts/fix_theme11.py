import pathlib

# ---------- calm.css v9 -> v10 (remove brand underline) ----------
p = pathlib.Path("calm.css")
s = p.read_text()
OLD = """header h1::after{content:"";display:block;height:2px;border-radius:2px;margin-top:5px;
  background:linear-gradient(90deg,var(--blue),var(--up))}"""
NEW = """header h1::after{content:none}"""
assert OLD in s, "h1 underline rule missing"
s = s.replace(OLD, NEW)
s = s.replace("calm.css v9 — ARTHASAAR PREMIUM (compact header + radars, no small words)",
              "calm.css v10 — ARTHASAAR PREMIUM (no brand underline)")
p.write_text(s)

# ---------- oldapp.js + dtfix.js: pill CLOSED -> MARKET CLOSE ----------
for fn, old, new in [
    ("oldapp.js", 'let txt = "CLOSED", cls = "closed";', 'let txt = "MARKET CLOSE", cls = "closed";'),
    ("dtfix.js", 'var txt = "CLOSED", cls = "closed";', 'var txt = "MARKET CLOSE", cls = "closed";'),
]:
    p2 = pathlib.Path(fn)
    t = p2.read_text()
    if old in t:
        t = t.replace(old, new)
        p2.write_text(t)
        print(fn, "patched")
    else:
        print(fn, "pattern not found (skip)")

# ---------- index bump ----------
ix = pathlib.Path("index.html")
s = ix.read_text()
s = s.replace("calm.css?v=as10", "calm.css?v=as11")
ix.write_text(s)
print("v10 applied | underline removed:", 'content:none' in pathlib.Path("calm.css").read_text(),
      "| index as11:", "as11" in s)
