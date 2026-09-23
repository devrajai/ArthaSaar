#!/usr/bin/env python3
"""fix_open2.py - IPO home tile -> direct website link + version bump. Idempotent."""

IPO_OLD = '<a class="tile" href="#ipo"><span class="t-ic">\U0001F680</span><span class="t-nm">IPO</span><span class="t-sb">GMP \u00b7 listing</span></a>'
IPO_NEW = '<a class="tile" href="https://devrajai.github.io/ipo-terminal/" target="_blank" rel="noopener"><span class="t-ic">\U0001F680</span><span class="t-nm">IPO \u2197</span><span class="t-sb">full terminal \u00b7 GMP \u00b7 listing</span></a>'


def main():
    idx = open("index.html", encoding="utf-8").read()
    if "devrajai.github.io/ipo-terminal/" in idx:
        print("index.html: IPO tile already linked")
    elif IPO_OLD in idx:
        idx = idx.replace(IPO_OLD, IPO_NEW)
        print("index.html: IPO tile -> website link")
    else:
        print("WARN: IPO tile anchor not found")
    if "21sep26a12" in idx:
        idx = idx.replace("21sep26a12", "21sep26a13")
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: bumped to a13")
    elif "21sep26a13" in idx:
        print("index.html: already a13")
    else:
        print("WARN: version anchor not found")


if __name__ == "__main__":
    main()
