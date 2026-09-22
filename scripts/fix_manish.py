#!/usr/bin/env python3
"""fix_manish.py - app.js loader mein manish.js add karo, version bump."""
import io
a = io.open("app.js", encoding="utf-8").read()
if "manish.js" not in a:
    old = '"macro.js", "gti.js" ];'
    assert old in a, "app anchor"
    a = a.replace(old, '"macro.js", "gti.js", "manish.js" ];', 1)
    io.open("app.js", "w", encoding="utf-8").write(a)
    print("app.js: manish.js added")
else:
    print("app.js: already added")
t = io.open("index.html", encoding="utf-8").read()
n = t.count("?v=21sep26t")
t = t.replace("?v=21sep26t", "?v=21sep26u")
io.open("index.html", "w", encoding="utf-8").write(t)
print("index version bumped:", n)
print("ALL DONE")
