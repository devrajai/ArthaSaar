#!/usr/bin/env python3
"""
check_schemas.py - stop a broken file from being published.

WHY THIS EXISTS
The pipeline has published empty and malformed files more than once: breadth.json with
total=0, series.json holding 2 price series for 2,225 stocks, shareholding.json at 204
bytes. Every one of those runs finished green, because nothing checked the files that were
about to be committed. validate_data.py checks the candle archive, not the website files.

WHAT IT CHECKS
  ERROR  the file does not parse, or is empty, or declares a count its payload contradicts
  WARN   the file is valid but thinner than it should be (a feed that has stopped working)

Two levels on purpose. Structural corruption is always a bug, so it fails the run. Thin
data is sometimes a real market condition - a holiday, a new feed - so it is reported
loudly and only blocks the build when you ask for it with --strict. Turning warnings into
errors on day one would stop the nightly run for a file that was already thin before this
existed.

Usage:
  python scripts/check_schemas.py                    # errors fail, warnings report
  python scripts/check_schemas.py --strict           # warnings fail too
  python scripts/check_schemas.py --dir docs --json  # machine-readable summary
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Files that must carry real data, and the smallest payload that counts as real.
# The numbers come from what these files actually hold today, rounded well below it -
# the point is to catch a collapse to zero or a handful, not to police normal variation.
CRITICAL = {
    "data.json":        {"key": "daily",     "path": ("items",),      "min": 1},
    "screener.json":    {"key": "rows",      "path": (),             "min": 300},
    "universe.json":    {"key": "rows",      "path": (),             "min": 300},
    "stocks.json":      {"key": "stocks",    "path": (),             "min": 50},
    "series.json":      {"key": "series",    "path": (),             "min": 20},
    "indices.json":     {"key": "indices",   "path": (),             "min": 5},
    "sectors.json":     {"key": "sectors",   "path": (),             "min": 5},
    "deals.json":       {"key": "bulk",      "path": (),             "min": 1},
    "oi_strikes.json":  {"key": "indices",   "path": (),             "min": 1},
    "option_chain.json": {"key": "indices",  "path": (),             "min": 1},
    "fii_dii.json":     {"key": "latest",    "path": (),             "min": 1},
    "news.json":        {"key": "items",     "path": (),             "min": 1},
    "search.json":      {"key": "items",     "path": (),             "min": 100},
}

# Lists that are legitimately empty today, with the reason. Anything here is not reported,
# so the report stays short enough to read.
ALLOW_EMPTY = {
    ("timesfm_score.json", "by_run"): "no forecast has settled yet - by design",
    ("timesfm_score.json", "recent"): "no forecast has settled yet - by design",
    ("ipo.json", "upcoming"): "IPO section is handed off to another site",
    ("ipo.json", "open"): "IPO section is handed off to another site",
    ("ipo.json", "closed"): "IPO section is handed off to another site",
    ("data_asof.json", "missing"): "empty means every file agrees - the good state",
    ("data_asof.json", "behind"): "empty means every file agrees - the good state",
    ("deals.json", "failed"): "empty means no feed failed",
    ("insider.json", "failed"): "empty means no feed failed",
    ("calendar.json", "recent"): "the last-30-days list is not being filled yet",
    ("sebi.json", "circulars"): "circulars feed is not being filled yet",
    ("report_cards.json", "cards"): "report cards are not being filled yet",
    ("breakers.json", "breakers"): "no circuit breakers today is a normal day",
    ("breakers.json", "by_horizon"): "no circuit breakers today is a normal day",
    ("presentations.json", "by_company"): "presentations feed is empty",
    ("presentations.json", "recent"): "presentations feed is empty",
    ("market_stats.json", "cautions"): "cautions are optional prose",
    ("report_cards.json", "cautions"): "cautions are optional prose",
    ("_guard_report.json", "repaired"): "empty means nothing needed repairing",
    ("watchlists.json", "ban"): "no ban list entries today",
}


def walk(payload, path):
    cur = payload
    for step in path:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(step)
    return cur


def size_of(v):
    if isinstance(v, (list, dict, str)):
        return len(v)
    return 1 if v is not None else 0


def check_file(path: Path) -> tuple[list[str], list[str]]:
    """Return (errors, warnings) for one published file."""
    errs, warns = [], []
    name = path.name
    try:
        raw = path.read_text()
    except Exception as e:
        return [f"{name}: unreadable ({type(e).__name__})"], []
    if not raw.strip():
        return [f"{name}: file is empty"], []
    try:
        payload = json.loads(raw)
    except Exception as e:
        return [f"{name}: does not parse ({str(e)[:60]})"], []

    if payload is None:
        return [f"{name}: parses to null"], []
    if isinstance(payload, (dict, list)) and len(payload) == 0:
        return [f"{name}: empty {type(payload).__name__}"], []

    # A declared count its payload contradicts is a lie the page will repeat in a header.
    if isinstance(payload, dict) and isinstance(payload.get("count"), int):
        cnt = payload["count"]
        collections = [(k, v) for k, v in payload.items()
                       if k != "count" and isinstance(v, (list, dict))]
        for k, v in collections:
            if v and cnt == 0:
                errs.append(f"{name}: count says 0 but '{k}' has {len(v)} entries")
        # declares rows and carries none anywhere - the empty-publish case
        if cnt > 0 and collections and all(len(v) == 0 for _, v in collections):
            errs.append(f"{name}: count says {cnt} but every collection in it is empty")

    # empty collections that are not on the allowed list
    if isinstance(payload, dict):
        for k, v in payload.items():
            if isinstance(v, (list, dict)) and len(v) == 0:
                if (name, k) in ALLOW_EMPTY:
                    continue
                warns.append(f"{name}: '{k}' is empty")

    # the critical files, with a floor
    spec = CRITICAL.get(name)
    if spec:
        v = walk(payload, (spec["key"],) + tuple(spec["path"]))
        n = size_of(v)
        if n < spec["min"]:
            msg = (f"{name}: '{spec['key']}' holds {n}, expected at least {spec['min']} "
                   f"- the feed has collapsed or the builder failed")
            errs.append(msg)
    return errs, warns


def main() -> int:
    ap = argparse.ArgumentParser(description="Schema and emptiness checks on published files.")
    ap.add_argument("--dir", default="docs")
    ap.add_argument("--strict", action="store_true", help="treat warnings as errors")
    ap.add_argument("--json", action="store_true", help="print a machine-readable summary")
    args = ap.parse_args()

    root = Path(args.dir)
    if not root.is_dir():
        print(f"no {root}/ directory - nothing to check")
        return 0

    files = sorted(p for p in root.glob("*.json") if p.is_file())
    errors, warnings = [], []
    for p in files:
        e, w = check_file(p)
        errors.extend(e)
        warnings.extend(w)

    for e in errors:
        print(f"ERROR {e}")
    for w in warnings:
        print(f"WARN  {w}")

    if args.json:
        print(json.dumps({"files": len(files), "errors": errors, "warnings": warnings}))

    print(f"\nchecked {len(files)} files | {len(errors)} errors | {len(warnings)} warnings")
    if errors:
        print("FAIL - a broken file would have been published")
        return 1
    if args.strict and warnings:
        print("FAIL - strict mode, warnings count")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
