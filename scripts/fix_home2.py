#!/usr/bin/env python3
"""fix_home2.py - revert home to old tile grid; Learn topics (#learnChips) horizontal one-line + scroll-hide."""
import io

AMP = chr(38) + "amp;"

# ---------- 1. index.html: hrow -> original homegrid (no charts tile) ----------
s = io.open("index.html", encoding="utf-8").read()
if 'id="homeRow"' in s:
    i = s.find('<div class="hrow" id="homeRow">')
    assert i > 0, "homeRow not found"
    j = s.find("</section>", i)
    assert j > i
    grid = '<div class="homegrid">\n' \
        '    <a class="tile" href="#company" style="grid-column:1/-1;flex-direction:row;align-items:center;gap:12px"><span class="t-ic">🏢</span><span><span class="t-nm">Company Card — search any stock</span><br><span class="t-sb">story · management · growth · results · shareholding</span></span></a>\n' \
        '    <div class="hgroup">MARKETS</div>\n' \
        '    <a class="tile" href="#dash"><span class="t-ic">📊</span><span class="t-nm">Dashboard</span><span class="t-sb">today at a glance</span></a>\n' \
        '    <a class="tile" href="#indices"><span class="t-ic">📈</span><span class="t-nm">Indices</span><span class="t-sb">139 tracked</span></a>\n' \
        '    <a class="tile" href="#heatmap"><span class="t-ic">🔥</span><span class="t-nm">Sector Map</span><span class="t-sb">today by sector</span></a>\n' \
        '    <a class="tile" href="#screener"><span class="t-ic">🔍</span><span class="t-nm">Screener</span><span class="t-sb">2,085 stocks</span></a>\n' \
        '    <div class="hgroup">STOCKS</div>\n' \
        '    <a class="tile" href="#fundamentals"><span class="t-ic">🏢</span><span class="t-nm">Fundamentals</span><span class="t-sb">PE · ROE · debt</span></a><a class="tile" href="#mf"><span class="t-ic">📊</span><span class="t-nm">MF Tracker</span><span class="t-sb">nav · sip · my funds</span></a>\n' \
        '    <a class="tile" href="#deepfund"><span class="t-ic">💎</span><span class="t-nm">Deep Fund</span><span class="t-sb">screener.in weekly</span></a>\n' \
        '    <a class="tile" href="#filings"><span class="t-ic">📄</span><span class="t-nm">Filings</span><span class="t-sb">company results</span></a>\n' \
        '    <div class="hgroup">TRADING</div>\n' \
        '    <a class="tile" href="#futures"><span class="t-ic">🧾</span><span class="t-nm">Futures</span><span class="t-sb">F' + AMP + 'O chains</span></a>\n' \
        '    <a class="tile" href="#ipo"><span class="t-ic">🚀</span><span class="t-nm">IPO</span><span class="t-sb">GMP · listing</span></a>\n' \
        '    <a class="tile" href="#ai"><span class="t-ic">🤖</span><span class="t-nm">AI Forecast</span><span class="t-sb">TimesFM 21-day</span></a><a class="tile" href="#aibrain"><span class="t-ic">🧠</span><span class="t-nm">AI Brain</span><span class="t-sb">mood · crash · report</span></a>\n' \
        '    <div class="hgroup">WATCH</div>\n' \
        '    <a class="tile" href="#crypto"><span class="t-ic">🪙</span><span class="t-nm">Crypto</span><span class="t-sb">top 100 coins</span></a>\n' \
        '    <a class="tile" href="#global"><span class="t-ic">🌍</span><span class="t-nm">Global</span><span class="t-sb">US · gold · crude</span></a>\n' \
        '    <a class="tile" href="#news"><span class="t-ic">📰</span><span class="t-nm">News</span><span class="t-sb">India market</span></a>\n' \
        '    <a class="tile" href="#events"><span class="t-ic">📅</span><span class="t-nm">Events</span><span class="t-sb">GDP · jobs · Fed · RBI</span></a>\n' \
        '    <a class="tile" href="#portfolio"><span class="t-ic">💼</span><span class="t-nm">Portfolio</span><span class="t-sb">my holdings · P' + AMP + 'L</span></a>\n' \
        '    <div class="hgroup">LEARN</div>\n' \
        '    <a class="tile learnchip" href="#learn"><span class="t-ic">📚</span><span class="t-nm">Learn</span><span class="t-sb">strategies · glossary · rules</span></a>\n' \
        '    <a class="tile" href="#studies"><span class="t-ic">🧪</span><span class="t-nm">Studies</span><span class="t-sb">history heatmap</span></a>\n' \
        '    <a class="tile" href="#mynotes"><span class="t-ic">📝</span><span class="t-nm">My Notes</span><span class="t-sb">course notes</span></a>\n' \
        '  </div>\n</section>'
    s = s[:i] + grid + s[j + len("</section>"):]
    n = s.count("?v=21sep26m")
    s = s.replace("?v=21sep26m", "?v=21sep26n")
    io.open("index.html", "w", encoding="utf-8").write(s)
    print("index.html: homegrid restored (no charts tile) | versions bumped:", n)
else:
    print("index.html: homegrid already present")

# ---------- 2. style.css: #learnChips one horizontal line ----------
c = io.open("style.css", encoding="utf-8").read()
if "#learnChips{" not in c:
    c += "\n/* --- learn topics: single horizontal line --- */\n#learnChips{display:flex;flex-wrap:nowrap;gap:8px;overflow-x:auto;padding:6px 2px 12px;-webkit-overflow-scrolling:touch;scrollbar-width:none}\n#learnChips::-webkit-scrollbar{display:none}\n#learnChips .chip{flex:0 0 auto;white-space:nowrap}\n"
    io.open("style.css", "w", encoding="utf-8").write(c)
    print("style.css: learnChips horizontal added")
else:
    print("style.css: learnChips already set")

# ---------- 3. homefix.js: now targets learn chips row ----------
io.open("homefix.js", "w", encoding="utf-8").write(
"""/* homefix.js - Learn ke topics row: scroll down par chhupao, up par wapas */
(function () {
  var row = document.getElementById("learnChips");
  if (!row) return;
  var last = 0;
  window.addEventListener("scroll", function () {
    var y = window.scrollY || document.documentElement.scrollTop || 0;
    if (y > last + 8 && y > 60) { row.style.display = "none"; }
    else if (last - y > 8) { row.style.display = ""; }
    last = y;
  }, { passive: true });
})();
""")
print("homefix.js rewritten (learn chips)")
print("ALL DONE")
