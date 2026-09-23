#!/usr/bin/env python3
"""fix_num.py - version bump a13 -> a14 (financelearn renumbering pushed directly). Idempotent."""


def main():
    idx = open("index.html", encoding="utf-8").read()
    if "21sep26a13" in idx:
        idx = idx.replace("21sep26a13", "21sep26a14")
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: bumped to a14")
    elif "21sep26a14" in idx:
        print("index.html: already a14")
    else:
        print("WARN: version anchor not found")


if __name__ == "__main__":
    main()
