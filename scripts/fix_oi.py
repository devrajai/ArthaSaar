#!/usr/bin/env python3
"""fix_oi.py - app.js loader mein oi.js add + index.html version bump (x->y)."""
def main():
    app = open("app.js", encoding="utf-8").read()
    if "oi.js" not in app:
        assert '"gtiinfo.js"' in app, "app.js anchor missing"
        app = app.replace('"gtiinfo.js"', '"gtiinfo.js", "oi.js"')
        open("app.js", "w", encoding="utf-8").write(app)
        print("app.js: oi.js added to loader")
    else:
        print("app.js: already present")
    idx = open("index.html", encoding="utf-8").read()
    old = "app.js?v=21sep26x"
    if old in idx:
        idx = idx.replace(old, "app.js?v=21sep26y")
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: bumped to 21sep26y")
    elif "21sep26y" in idx:
        print("index.html: already bumped")
    else:
        print("WARN: version anchor not found")

if __name__ == "__main__":
    main()
