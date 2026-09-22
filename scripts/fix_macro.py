#!/usr/bin/env python3
"""fix_macro.py - app.js loader mein macro.js + gti.js add karo, version bump."""
import io

a = io.open("app.js", encoding="utf-8").read()
if "macro.js" not in a:
    old = '"homefix.js", "learnfold.js"];'
    assert old in a, "app anchor"
    a = a.replace(old, '"homefix.js", "learnfold.js", "macro.js", "gti.js" ];', 1)
    io.open("app.js", "w", encoding="utf-8").write(a)
    print("app.js: macro.js + gti.js added to loader")
else:
    print("app.js: already added")

t = io.open("index.html", encoding="utf-8").read()
n = t.count("?v=21sep26s")
t = t.replace("?v=21sep26s", "?v=21sep26t")
io.open("index.html", "w", encoding="utf-8").write(t)
print("index version bumped:", n)
print("ALL DONE")
