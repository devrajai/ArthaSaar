#!/usr/bin/env python3
"""fix_learn4.py - guide2.js ka 'About Market Brain' card collapsible banao
+ learnadd.js se duplicate About card hatao + version bump."""
import io

# ---------- 1. guide2.js: siteGuideCard -> collapsible details ----------
g = io.open("guide2.js", encoding="utf-8").read()
if 'createElement("details")' not in g:
    a1 = 'var card = document.createElement("div");'
    assert a1 in g, "g anchor1"
    g = g.replace(a1, 'var card = document.createElement("details");', 1)
    a2 = 'card.className = "card"; card.id = "siteGuideCard";'
    assert a2 in g, "g anchor2"
    g = g.replace(a2, 'card.className = "gl"; card.id = "siteGuideCard"; card.style.marginTop = "12px";', 1)
    a3 = "card.innerHTML = '<div class=\"subhead\">About Market Brain"
    assert a3 in g, "g anchor3"
    g = g.replace(a3, "card.innerHTML = '<summary><b>About Market Brain", 1)
    a4 = "kaise kaam karta hai</div>' +"
    assert a4 in g, "g anchor4"
    g = g.replace(a4, "kaise kaam karta hai</b></summary>' +", 1)
    io.open("guide2.js", "w", encoding="utf-8").write(g)
    print("guide2.js: About card collapsible")
else:
    print("guide2.js: already collapsible")

# ---------- 2. learnadd.js: duplicate About card hatao ----------
s = io.open("learnadd.js", encoding="utf-8").read()
if "aboutCard" in s:
    i = s.find('  var ab = glCard("aboutCard"')
    j = s.find("var first = sec.querySelector", i)
    assert i > 0 and j > i, "learnadd anchors"
    s = s[:i] + s[j:]
    s = s.replace("    sec.insertBefore(ab, gd.nextSibling);\n", "", 1)
    s = s.replace("    sec.appendChild(ab);\n", "", 1)
    assert "aboutCard" not in s
    io.open("learnadd.js", "w", encoding="utf-8").write(s)
    print("learnadd.js: duplicate About card removed")
else:
    print("learnadd.js: already clean")

# ---------- 3. version bump q -> r ----------
t = io.open("index.html", encoding="utf-8").read()
n = t.count("?v=21sep26q")
t = t.replace("?v=21sep26q", "?v=21sep26r")
io.open("index.html", "w", encoding="utf-8").write(t)
print("index version bumped:", n)
print("ALL DONE")
