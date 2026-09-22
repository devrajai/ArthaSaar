#!/usr/bin/env python3
"""fix_gti2.py - GTI home tile + naya #gti section (Futures ke baad)."""
import io
A = chr(38)
t = io.open("index.html", encoding="utf-8").read()
if 'href="#gti"' not in t:
    fut = '<a class="tile" href="#futures"><span class="t-ic">\U0001F9FE</span><span class="t-nm">Futures</span><span class="t-sb">F' + A + 'amp;O chains</span></a>'
    assert fut in t, "fut tile"
    gti_tile = '<a class="tile" href="#gti"><span class="t-ic">\U0001F3AF</span><span class="t-nm">GTI Zones</span><span class="t-sb">demand · supply · POC</span></a>'
    t = t.replace(fut, fut + gti_tile, 1)
    print("tile added")
if 'id="gtiMount"' not in t:
    news = '<section id="news"'
    assert news in t, "news anchor"
    gsec = ('<section id="gti" style="display:none">\n'
            '  <a class="backbtn" href="#home">\u2302 Home</a>\n'
            '  <h2>GTI Zones \u2014 Ghost Trade Indicator</h2>\n'
            '  <div id="gtiMount"></div>\n'
            '</section>\n')
    t = t.replace(news, gsec + news, 1)
    print("section added")
n = t.count("?v=21sep26u")
t = t.replace("?v=21sep26u", "?v=21sep26w")
io.open("index.html", "w", encoding="utf-8").write(t)
print("version bumped:", n)
print("ALL DONE")
