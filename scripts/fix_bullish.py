#!/usr/bin/env python3
"""fix_bullish.py - loader += bullish.js + version bump (a2 -> a3)."""
def main():
    app = open("app.js", encoding="utf-8").read()
    if "bullish.js" not in app:
        assert '"history.js"' in app, "app.js anchor missing"
        app = app.replace('"history.js"', '"history.js", "bullish.js"')
        open("app.js", "w", encoding="utf-8").write(app)
        print("app.js: bullish.js added")
    else:
        print("app.js: already present")
    idx = open("index.html", encoding="utf-8").read()
    if "21sep26a2" in idx:
        idx = idx.replace("21sep26a2", "21sep26a3")
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: bumped to 21sep26a3")
    elif "21sep26a3" in idx:
        print("index.html: already bumped")
    else:
        print("WARN: version anchor not found")

if __name__ == "__main__":
    main()
