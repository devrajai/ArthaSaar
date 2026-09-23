#!/usr/bin/env python3
"""fix_btn.py - version bump a14 -> a15 (course button styling). Idempotent."""


def main():
    idx = open("index.html", encoding="utf-8").read()
    if "21sep26a14" in idx:
        idx = idx.replace("21sep26a14", "21sep26a15")
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: bumped to a15")
    elif "21sep26a15" in idx:
        print("index.html: already a15")
    else:
        print("WARN: version anchor not found")


if __name__ == "__main__":
    main()
