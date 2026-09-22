#!/usr/bin/env python3
"""fix_power2.py - loader += movement.js, power2.js, financelearn.js + bump (a3 -> a4)."""
def main():
    app = open("app.js", encoding="utf-8").read()
    if "movement.js" not in app:
        assert '"bullish.js"' in app, "app.js anchor missing"
        app = app.replace('"bullish.js"', '"bullish.js", "movement.js", "power2.js", "financelearn.js"')
        open("app.js", "w", encoding="utf-8").write(app)
        print("app.js: 3 files added")
    else:
        print("app.js: already present")
    idx = open("index.html", encoding="utf-8").read()
    if "21sep26a3" in idx:
        idx = idx.replace("21sep26a3", "21sep26a4")
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: bumped to 21sep26a4")
    elif "21sep26a4" in idx:
        print("index.html: already bumped")
    else:
        print("WARN: version anchor not found")

if __name__ == "__main__":
    main()
