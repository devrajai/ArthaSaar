import io
s = io.open("index.html", encoding="utf-8").read()
old = '<a class="tile" href="#fundamentals"><span class="t-ic">\U0001F3E2</span><span class="t-nm">Fundamentals</span><span class="t-sb">PE \u00b7 ROE \u00b7 debt</span></a>'
mf = old + '<a class="tile" href="#mf"><span class="t-ic">\U0001F4CA</span><span class="t-nm">MF Tracker</span><span class="t-sb">nav \u00b7 sip \u00b7 my funds</span></a>'
if 'href="#mf"' not in s:
    assert old in s, "fundamentals tile not found"
    s = s.replace(old, mf, 1)
s = s.replace("app.js?v=21sep26i", "app.js?v=21sep26j")
io.open("index.html", "w", encoding="utf-8").write(s)
print("index patched, mf tile:", 'href="#mf"' in s, "| v=j:", "v=21sep26j" in s)
