#!/usr/bin/env python3
"""fix_fd.py - (1) remove guide card (mbguide.js) + About card (guide2.js)
(2) add fdinvest.js to loader (3) version bump. Idempotent. fdinvest.js comes from repo root."""
import os


def main():
    for f in ("mbguide.js", "guide2.js"):
        if os.path.exists(f):
            os.remove(f)
            print("removed", f)
        else:
            print("already gone", f)

    s = open("app.js", encoding="utf-8").read()
    orig = s
    s = s.replace('"guide2.js", ', '')
    s = s.replace(', "mbguide.js"', '')
    if '"fdinvest.js"' not in s:
        if '"xray.js" ]' in s:
            s = s.replace('"xray.js" ]', '"xray.js", "fdinvest.js" ]')
        elif '"xray.js"]' in s:
            s = s.replace('"xray.js"]', '"xray.js", "fdinvest.js"]')
    if s != orig:
        open("app.js", "w", encoding="utf-8").write(s)
        print("app.js: loader updated")
    elif '"fdinvest.js"' in s and "mbguide" not in s and "guide2" not in s:
        print("app.js: already updated")
    else:
        print("WARN: loader anchor issue")

    idx = open("index.html", encoding="utf-8").read()
    if "21sep26a10" in idx:
        idx = idx.replace("21sep26a10", "21sep26a11")
        open("index.html", "w", encoding="utf-8").write(idx)
        print("index.html: bumped to a11")
    elif "21sep26a11" in idx:
        print("index.html: already a11")
    else:
        print("WARN: version anchor not found")


if __name__ == "__main__":
    main()
