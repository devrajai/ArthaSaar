#!/usr/bin/env python3
"""fix_peers.py - loader += peers.js + version bump (a4 -> a5)."""
def main():
    app = open("app.js", encoding="utf-8").read()
    if "peers.js" not in app:
        assert '"financelearn.js"' in app, "app.js anchor missing"
        app = app.replace('"financelearn.js"', '"financelearn.js", "peers.js"')
        open("app.js", "w", encoding="utf-8").write(app)
        print("app.js: peers.js added")
    else:
        print("app.js: already present")
    idx = open("index.html", encoding="utf-8").read()
    if "21sep26a4" in idx:
        idx = idx.replace("21sep26a4", "21sep26a5")
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: bumped to 21sep26a5")
    elif "21sep26a5" in idx:
        print("index.html: already bumped")
    else:
        print("WARN: version anchor not found")

if __name__ == "__main__":
    main()
