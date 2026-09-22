#!/usr/bin/env python3
"""fix_money.py - loader += money.js, history.js + version bump (a1 -> a2)."""
def main():
    app = open("app.js", encoding="utf-8").read()
    if "money.js" not in app:
        assert '"powerpack.js"' in app, "app.js anchor missing"
        app = app.replace('"powerpack.js"', '"powerpack.js", "money.js", "history.js"')
        open("app.js", "w", encoding="utf-8").write(app)
        print("app.js: money.js + history.js added")
    else:
        print("app.js: already present")
    idx = open("index.html", encoding="utf-8").read()
    if "21sep26a1" in idx:
        idx = idx.replace("21sep26a1", "21sep26a2")
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: bumped to 21sep26a2")
    elif "21sep26a2" in idx:
        print("index.html: already bumped")
    else:
        print("WARN: version anchor not found")

if __name__ == "__main__":
    main()
