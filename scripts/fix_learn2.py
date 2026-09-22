#!/usr/bin/env python3
"""fix_learn2.py - Learn ke SAB cards collapsible (Beginner/Intermediate/Advanced/Quick tips/strategies...)
+ My Notebook collapsible + naya 'Sab Topics' card (2-line chips). Writer script."""
import io

# ---------- 1. learnfold.js: eduBox ke sab cards -> collapsible (har render par) ----------
io.open("learnfold.js", "w", encoding="utf-8").write(
"""/* learnfold.js - Learn ke andar ke sab cards collapsible (Naye Tools jaise tap-to-open) */
(function () {
  var box = document.getElementById("eduBox");
  if (!box) return;
  function fold() {
    var cards = box.querySelectorAll(".card");
    for (var i = 0; i < cards.length; i++) {
      var c = cards[i];
      var sh = c.querySelector(".subhead");
      if (!sh) continue;
      var d = document.createElement("details");
      d.className = "gl";
      var s = document.createElement("summary");
      s.innerHTML = "<b>" + sh.textContent + "</b>";
      d.appendChild(s);
      c.removeChild(sh);
      while (c.firstChild) d.appendChild(c.firstChild);
      if (c.parentNode) c.parentNode.replaceChild(d, c);
    }
  }
  fold();
  if (window.MutationObserver) new MutationObserver(fold).observe(box, { childList: true, subtree: true });
})();
""")
print("learnfold.js written")

# ---------- 2. learnfix.js: My Notebook -> collapsible details ----------
s = io.open("learnfix.js", encoding="utf-8").read()
if 'document.createElement("details")' not in s:
    a1 = 'var card = document.createElement("div");'
    b1 = 'var card = document.createElement("details");'
    assert a1 in s, "card anchor missing"
    s = s.replace(a1, b1, 1)
    a2 = 'card.className = "card"; card.id = "devNoteCard";'
    b2 = 'card.className = "gl"; card.id = "devNoteCard"; card.style.marginTop = "12px";'
    assert a2 in s, "classname anchor missing"
    s = s.replace(a2, b2, 1)
    a3 = "card.innerHTML = '<div class=\"subhead\">My Notebook"
    b3 = "card.innerHTML = '<summary><b>My Notebook"
    assert a3 in s, "subhead anchor missing"
    s = s.replace(a3, b3, 1)
    a4 = "own rules (Advance.pdf)</div>' +"
    b4 = "own rules (Advance.pdf)</b></summary>' +"
    assert a4 in s, "close anchor missing"
    s = s.replace(a4, b4, 1)
    io.open("learnfix.js", "w", encoding="utf-8").write(s)
    print("learnfix.js: My Notebook collapsible")
else:
    print("learnfix.js: already collapsible")

# ---------- 3. learnadd.js: + third card 'Sab Topics' ----------
s = io.open("learnadd.js", encoding="utf-8").read()
if "siteTopicsCard" not in s:
    chips = [("#company", "🏢", "Company Card"), ("#dash", "📊", "Dashboard"),
             ("#indices", "📈", "Indices"), ("#heatmap", "🔥", "Sector Map"),
             ("#screener", "🔍", "Screener"), ("#fundamentals", "🏢", "Fundamentals"),
             ("#mf", "📊", "MF Tracker"), ("#deepfund", "💎", "Deep Fund"),
             ("#filings", "📄", "Filings"), ("#futures", "🧾", "Futures"),
             ("#ipo", "🚀", "IPO"), ("#ai", "🤖", "AI Forecast"),
             ("#aibrain", "🧠", "AI Brain"), ("#crypto", "🪙", "Crypto"),
             ("#global", "🌍", "Global"), ("#news", "📰", "News"),
             ("#events", "📅", "Events"), ("#portfolio", "💼", "Portfolio"),
             ("#learn", "📚", "Learn"), ("#studies", "🧪", "Studies"),
             ("#mynotes", "📝", "My Notes")]
    inner = '<div style="display:flex;flex-wrap:wrap;gap:8px;padding:4px 0 8px">' + "".join(
        '<a class="hchip" href="%s">%s %s</a>' % (h, ic, nm) for h, ic, nm in chips) + "</div>"
    tp = ('  var tp = glCard("siteTopicsCard", "🗺️ Sab Topics - poori site",
'
          "    '" + inner + "');\n")
    a5 = "  var first = sec.querySelector(\".card\");"
    assert a5 in s, "first anchor missing"
    s = s.replace(a5, tp + a5, 1)
    a6 = "    sec.insertBefore(wn, first);\n    sec.insertBefore(gd, wn.nextSibling);"
    b6 = "    sec.insertBefore(wn, first);\n    sec.insertBefore(gd, wn.nextSibling);\n    sec.insertBefore(tp, gd.nextSibling);"
    assert a6 in s, "insert anchor missing"
    s = s.replace(a6, b6, 1)
    a7 = "    sec.appendChild(wn);\n    sec.appendChild(gd);"
    b7 = "    sec.appendChild(wn);\n    sec.appendChild(gd);\n    sec.appendChild(tp);"
    assert a7 in s, "append anchor missing"
    s = s.replace(a7, b7, 1)
    io.open("learnadd.js", "w", encoding="utf-8").write(s)
    print("learnadd.js: Sab Topics card added")
else:
    print("learnadd.js: already has topics card")

# ---------- 4. app.js loader: + learnfold.js ----------
a = io.open("app.js", encoding="utf-8").read()
if "learnfold.js" not in a:
    assert '"homefix.js"]' in a, "loader anchor missing"
    a = a.replace('"homefix.js"]', '"homefix.js", "learnfold.js"]')
    io.open("app.js", "w", encoding="utf-8").write(a)
    print("app.js: learnfold.js added")
else:
    print("app.js: already has learnfold")

# ---------- 5. index version bump o -> p ----------
s = io.open("index.html", encoding="utf-8").read()
n = s.count("?v=21sep26o")
s = s.replace("?v=21sep26o", "?v=21sep26p")
io.open("index.html", "w", encoding="utf-8").write(s)
print("index.html version bumped:", n)
print("ALL DONE")
