#!/usr/bin/env python3
"""Site gate: fail the build when a published file is empty, missing, or suspiciously thin.

WHY THIS EXISTS
Three failures this project hit recently, all of which ran green:
  * strike-wise OI published count=0 for days - the step "succeeded", it just found no data
  * docs/forecast.json was written and never committed, so the page 404'd it silently
  * series.json held 9 price series for 2,198 stocks, which looks like a file that worked

build_health.py already LISTS empties. Listing is not enough - nobody reads a green run. This
exits non-zero so the workflow turns red and someone is told.

Two kinds of check:
  HARD  - a file the page needs is missing, or a count is zero. Fails the run.
  SOFT  - a count is below a sanity floor (series.json under 500, say). Fails the run too,
          because "9 of 2,198" is exactly the shape of a silent breakage.
"""
import json, os, re, sys
from datetime import datetime, timezone

DOCS = "docs"
INDEX = os.path.join(DOCS, "index.html")

# Files the page loads and what a healthy count looks like.
# floor=0 means "must merely be present and non-empty".
EXPECT = {
    "data.json":            {"key": None, "floor": 1,   "why": "core payload"},
    "stocks.json":          {"key": "count", "floor": 500, "why": "stock pages"},
    "series.json":          {"key": "series", "floor": 500, "why": "sparkline + relative strength"},
    "screener.json":        {"key": "count", "floor": 100, "why": "screener rows"},
    "indices.json":         {"key": "count", "floor": 5,   "why": "index list"},
    "sectors.json":         {"key": "count", "floor": 5,   "why": "sector rows"},
    "mf.json":              {"key": "count", "floor": 50,  "why": "funds"},
    "seasonality.json":     {"key": "count", "floor": 100, "why": "monthly stats"},
    "levels.json":          {"key": "count", "floor": 50,  "why": "pivot levels"},
    "gaps.json":            {"key": "count", "floor": 50,  "why": "gap stats"},
    "correlation.json":     {"key": "count", "floor": 10,  "why": "correlation"},
    "gti.json":             {"key": "count", "floor": 50,  "why": "volume structure"},
    "report_cards.json":    {"key": "count", "floor": 100, "why": "stock report cards"},
    "oi_history.json":      {"key": "count", "floor": 500, "why": "PCR history"},
    "oi_strikes.json":      {"key": "count", "floor": 1,   "why": "strike-wise OI"},
    "oi_walls.json":        {"key": "count", "floor": 1,   "why": "option walls"},
    "oi_stats.json":        {"key": "count", "floor": 1,   "why": "PCR / max-pain study"},
    "charts.json":          {"key": "count", "floor": 500, "why": "multi-year charts"},
    "ipo.json":             {"key": "count", "floor": 1,   "why": "IPO list"},
    "breadth.json":         {"key": "count", "floor": 1,   "why": "advance/decline"},
    "health.json":          {"key": None, "floor": 1,      "why": "health page"},
}

# Known-empty and accepted, so the gate does not cry wolf every day.
ACCEPTED_EMPTY = {
    "shareholding.json": "NSE sends no promoter figures; the section says so.",
    "rs.json": "fills in once series.json is populated; checked separately via series floor.",
    "telegram_pcr.json": "channel web preview is off; the step is parked.",
}


def count_of(obj, key):
    if key is None:
        return None
    if key == "series" and isinstance(obj.get("series"), dict):
        return len(obj["series"])
    v = obj.get(key)
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, (list, dict)):
        return len(v)
    # fall back to the usual count keys
    for k in ("count", "total", "matched", "dates", "sessions"):
        if isinstance(obj.get(k), (int, float)):
            return int(obj[k])
    return None


def main():
    hard, soft, notes = [], [], []

    if not os.path.isdir(DOCS):
        print("FATAL: no docs/ directory")
        return 1

    # 1. every expected file present and non-trivial
    for name, spec in EXPECT.items():
        path = os.path.join(DOCS, name)
        if not os.path.exists(path):
            hard.append("%s is MISSING - the page will 404 it" % name)
            continue
        try:
            obj = json.load(open(path))
        except Exception as e:
            hard.append("%s is not valid JSON (%s)" % (name, type(e).__name__))
            continue
        n = count_of(obj, spec["key"])
        if n is None:
            notes.append("%s: present, count not measurable" % name)
            continue
        if n == 0:
            if name in ACCEPTED_EMPTY:
                notes.append("%s: empty, accepted - %s" % (name, ACCEPTED_EMPTY[name]))
            else:
                hard.append("%s published 0 rows (%s)" % (name, spec["why"]))
        elif n < spec["floor"]:
            soft.append("%s has only %d rows, floor is %d (%s)"
                        % (name, n, spec["floor"], spec["why"]))

    # 2. anything the page asks for but that does not exist
    if os.path.exists(INDEX):
        html = open(INDEX, encoding="utf-8", errors="replace").read()
        wanted = set(re.findall(r'"([a-z0-9_]+\.json)"', html))
        for name in sorted(wanted):
            if not os.path.exists(os.path.join(DOCS, name)):
                hard.append("%s is requested by index.html but does not exist" % name)
        notes.append("index.html asks for %d json files" % len(wanted))
    else:
        hard.append("docs/index.html is missing")

    # 3. files that exist but nothing references - not an error, just noise to know about
    present = {f for f in os.listdir(DOCS) if f.endswith(".json")}
    if os.path.exists(INDEX):
        orphan = sorted(present - wanted - {"config.json"})
        if orphan:
            notes.append("published but not referenced: %s" % ", ".join(orphan[:8]))

    # ---- report ----
    print("=" * 72)
    print("SITE CHECK  %s" % datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    print("=" * 72)
    for n in notes:
        print("  ok    %s" % n)
    for s in soft:
        print("  THIN  %s" % s)
    for h in hard:
        print("  FAIL  %s" % h)

    if hard or soft:
        print("\n%d hard, %d thin" % (len(hard), len(soft)))
        # GitHub annotation, so it shows on the run summary without opening logs
        for h in hard[:10]:
            print("::error title=Site check failed::%s" % h)
        for s in soft[:10]:
            print("::warning title=Thin data::%s" % s)
        return 1

    print("\nAll checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
