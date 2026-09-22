#!/usr/bin/env python3
"""fix_notoolkit.py - Free Toolkit (external links) card REMOVE + version bump."""
def main():
    open("tools5.js", "w", encoding="utf-8").write(
        "/* removed: external links card (Dev request) */\n")
    print("tools5.js: stubbed (card removed)")
    idx = open("index.html", encoding="utf-8").read()
    if "21sep26z" in idx:
        idx = idx.replace("21sep26z", "21sep26a1")
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: bumped to 21sep26a1")
    elif "21sep26a1" in idx:
        print("index.html: already bumped")
    else:
        print("WARN: version anchor not found")

if __name__ == "__main__":
    main()
