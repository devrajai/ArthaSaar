#!/usr/bin/env python3
"""fix_power.py - app.js loader mein powerpack.js add + index.html version bump (y->z)."""
def main():
    app = open("app.js", encoding="utf-8").read()
    if "powerpack.js" not in app:
        assert '"oi.js"' in app, "app.js anchor missing"
        app = app.replace('"oi.js"', '"oi.js", "powerpack.js"')
        open("app.js", "w", encoding="utf-8").write(app)
        print("app.js: powerpack.js added to loader")
    else:
        print("app.js: already present")
    idx = open("index.html", encoding="utf-8").read()
    old = "app.js?v=21sep26y"
    if old in idx:
        idx = idx.replace(old, "app.js?v=21sep26z")
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: bumped to 21sep26z")
    elif "21sep26z" in idx:
        print("index.html: already bumped")
    else:
        print("WARN: version anchor not found")

if __name__ == "__main__":
    main()
