#!/usr/bin/env python3
"""
ARTHASAAR - make sure docs/index.html still loads docs/cards.js.

WHY
docs/index.html gets rewritten from older bases (a concurrent agent, and some
builders), and inline additions were being silently erased each time. The UI
additions now live in docs/cards.js, loaded by one line in index.html. This step
puts that line back if a rewrite dropped it, so the cards survive a rebuild.

Idempotent and safe: it only inserts the tag when it is missing, and never
touches anything else.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "docs" / "index.html"
TAG = '<script src="cards.js"></script>'


def main():
    if not INDEX.exists():
        print("no index.html"); return 1
    s = INDEX.read_text(encoding="utf-8")
    if TAG in s:
        print("include present - nothing to do"); return 0
    k = s.rfind("</body>")
    if k < 0:
        print("no </body> - leaving the file alone"); return 1
    s = s[:k] + "\n" + TAG + "\n" + s[k:]
    INDEX.write_text(s, encoding="utf-8")
    print("include was missing - restored")
    return 0


if __name__ == "__main__":
    sys.exit(main())
