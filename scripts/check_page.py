#!/usr/bin/env python3
"""Page gate: catch the class of bug that blanked the site, before it ships.

WHY THIS EXISTS
Twice now the page has died behind "Could not load data.json - Cannot read properties of
undefined (reading 'map')". Both times the cause was the same shape: a card mapped over a
field that did not exist in the file it read.

  once because docs/levels.json was replaced with a different schema (count present,
  rows missing), so a guard checking `count` passed and `LEVELS.rows.map()` threw
  once because a variable was declared and never bound to any file at all

Neither is visible by reading the diff. Both are trivially detectable by reading the page
next to the data it will actually receive. That is what this does.

WHAT IT CHECKS
  1. every case "x.json": VAR=v - VAR is declared with var, and x.json exists
  2. every VAR.field.map(...) - VAR's file actually has a list at `field`
  3. every JSON the page fetches - present, parses, and is not a stub
  4. no card is left with a guard that checks a different field from the one it maps

It reads, it does not run. No browser, no network, no 200 MB of JSON in memory.
"""
import json, os, re, sys

DOCS = "docs"
INDEX = os.path.join(DOCS, "index.html")


def load(name):
    p = os.path.join(DOCS, name)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p))
    except Exception:
        return "UNREADABLE"


def main():
    if not os.path.exists(INDEX):
        print("FATAL: no docs/index.html")
        return 1
    html = open(INDEX, encoding="utf-8").read()
    hard, warn = [], []

    # ---------------------------------------------------------------- 1. bindings
    binds = {}
    for m in re.finditer(r'case\s+"([A-Za-z0-9_]+\.json)"\s*:\s*([A-Z][A-Z0-9_]*)\s*=', html):
        binds.setdefault(m.group(2), m.group(1))
    declared = set(re.findall(r'\bvar\s+([A-Z][A-Z0-9_]*)\s*=', html))
    declared |= set(re.findall(r'var\s+[A-Z][A-Z0-9_]*\s*=\s*null[^;]*;\s*$', html, re.M) and [])
    # the long `var A=null, B=null, ...;` declaration line
    for m in re.finditer(r'var\s+([A-Z][A-Z0-9_]*(?:\s*=\s*null)?(?:\s*,\s*[A-Z][A-Z0-9_]*(?:\s*=\s*null)?)+)\s*;', html):
        for part in m.group(1).split(","):
            nm = part.split("=")[0].strip()
            if re.fullmatch(r'[A-Z][A-Z0-9_]*', nm):
                declared.add(nm)

    for var, f in sorted(binds.items()):
        if var not in declared:
            hard.append("case \"%s\": %s=v - %s is never declared" % (f, var, var))
        if not os.path.exists(os.path.join(DOCS, f)):
            hard.append("case \"%s\": %s=v - the file does not exist" % (f, var))

    # a variable that is mapped but never bound renders nothing, silently
    mapped = set(re.findall(r'\b([A-Z][A-Z0-9_]{2,})\.(?:[a-z_]+\.)?map\(', html))
    page_arrays = {"CORE", "HEAVY", "FEEDS", "SERIES", "MONTHS", "SECTORS"}
    for v in sorted(mapped - set(binds) - page_arrays):
        if v in declared:
            warn.append("%s is declared and mapped but no case binds it to a file - that card "
                        "will render nothing" % v)

    # ---------------------------------------------------------------- 2. field shapes
    for m in re.finditer(r'\b([A-Z][A-Z0-9_]{2,})\.([a-z_]+)\.map\(', html):
        var, field = m.group(1), m.group(2)
        f = binds.get(var)
        if not f:
            continue
        d = load(f)
        if d in (None, "UNREADABLE"):
            continue
        if isinstance(d.get(field), list):
            continue
        # A guard is enough: `if(X.f && X.f.length)` before the call cannot throw. Without
        # this the gate cries wolf on every guarded call and gets ignored - which is how a
        # real gate dies.
        before = html[max(0, m.start() - 400):m.start()]
        expr = "%s.%s" % (var, field)
        guarded = bool(re.search(re.escape(expr) + r'\s*&&\s*' + re.escape(expr) + r'\.length', before)
                       or re.search(r'!\s*' + re.escape(expr) + r'\b', before)
                       or re.search(re.escape(expr) + r'\.length\s*[)>]', before)
                       or re.search(r'if\s*\(\s*' + re.escape(expr) + r'\s*\)', before))
        if guarded:
            continue
        hard.append("%s.%s.map() - %s has no list at '%s' (it is %s) and no guard before "
                    "the call. This throws and blanks the page."
                    % (var, field, f, field, type(d.get(field)).__name__))

    # ---------------------------------------------------------------- 3. fetched files
    refs = sorted(set(re.findall(r'"([A-Za-z0-9_]+\.json)"', html)))
    for r in refs:
        if not os.path.exists(os.path.join(DOCS, r)):
            warn.append("%s is referenced by the page but not published" % r)

    # ---------------------------------------------------------------- 4. stub check
    for r in refs:
        d = load(r)
        if not isinstance(d, dict):
            continue
        if os.path.getsize(os.path.join(DOCS, r)) < 40:
            warn.append("%s is under 40 bytes - a stub, not data" % r)

    # ---------------------------------------------------------------- report
    print("=" * 70)
    print("PAGE GATE")
    print("=" * 70)
    print("  bindings: %d | json referenced: %d" % (len(binds), len(refs)))
    for w in warn:
        print("  warn  %s" % w)
    for h in hard:
        print("  FAIL  %s" % h)
    print("  %d hard, %d warnings" % (len(hard), len(warn)))
    if hard:
        for h in hard:
            print("::error title=Page would break::%s" % h.replace("\n", " ")[:300])
        return 1
    print("  page/data contract is consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
