#!/usr/bin/env python3
"""fix_xray.py - loader += xray.js, mbguide.js + version bump (a5 -> a6)."""
def main():
    app = open("app.js", encoding="utf-8").read()
    if "xray.js" not in app:
        assert '"peers.js"' in app, "app.js anchor missing"
        app = app.replace('"peers.js"', '"peers.js", "xray.js", "mbguide.js"')
        open("app.js", "w", encoding="utf-8").write(app)
        print("app.js: xray.js + mbguide.js added")
    else:
        print("app.js: already present")
    idx = open("index.html", encoding="utf-8").read()
    if "21sep26a5" in idx:
        idx = idx.replace("21sep26a5", "21sep26a6")
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: bumped to 21sep26a6")
    elif "21sep26a6" in idx:
        print("index.html: already bumped")
    else:
        print("WARN: version anchor not found")

if __name__ == "__main__":
    main()
