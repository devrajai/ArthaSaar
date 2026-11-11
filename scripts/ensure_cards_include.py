#!/usr/bin/env python3
"""
ARTHASAAR - make sure docs/index.html loads docs/cards.js exactly ONCE.

WHY
docs/index.html gets rewritten from older bases, so inline additions were being erased.
The UI additions live in docs/cards.js, loaded by one line in index.html, and this step
puts that line back if a rewrite dropped it.

THE BUG THIS FILE USED TO HAVE
It compared against the exact string '<script src="cards.js"></script>'. Once the tag
carried a cache-busting version - '<script src="cards.js?v=20261111b"></script>' - that
comparison failed, so this step concluded the include was missing and appended a SECOND
tag, this time without a version.

The page then loaded cards.js TWICE: once from the versioned URL and once from the bare
one, which is the URL browsers had cached months ago. Two copies meant two sets of
MutationObservers and two 400ms intervals, which is exactly the flicker and reshuffling
that kept coming back no matter how many times the file itself was fixed - and the stale
copy still carried UI that had been deleted from the real one.

So: match any cards.js tag, count them, keep one, and never append when one exists.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.html"
TAG = '<script src="cards-20261111d.js"></script>'
# any cards.js script tag, with or without a version query
ANY = re.compile(r'<script\s+src="cards[^"]*\.js(?:\?[^"]*)?"\s*>\s*</script>')


def main():
    if not INDEX.exists():
        print("no index.html")
        return 1
    s = INDEX.read_text(encoding="utf-8")
    found = ANY.findall(s)
    if len(found) == 1:
        print("include present once - nothing to do")
        return 0
    if len(found) > 1:
        # keep the first, drop the rest - a duplicate tag loads the script twice
        s = ANY.sub("", s)
        k = s.rfind("</body>")
        if k < 0:
            print("no </body> - leaving the file alone")
            return 1
        s = s[:k] + "\n" + TAG + "\n" + s[k:]
        INDEX.write_text(s, encoding="utf-8")
        print("found %d cards.js tags - collapsed to one" % len(found))
        return 0
    k = s.rfind("</body>")
    if k < 0:
        print("no </body> - leaving the file alone")
        return 1
    s = s[:k] + "\n" + TAG + "\n" + s[k:]
    INDEX.write_text(s, encoding="utf-8")
    print("include was missing - restored")
    return 0


if __name__ == "__main__":
    sys.exit(main())
