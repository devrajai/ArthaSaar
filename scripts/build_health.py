#!/usr/bin/env python3
"""Data health: one page listing every published file with its age, size and row count.

WHY THIS EXISTS
Seasonality sat empty for days. Levels and gaps said "not enough history". The run stayed
green throughout, because each script did the correct thing with the data it was given -
the problem was upstream and invisible. A single page showing "seasonality: 0 rows, updated
2 days ago" next to "stocks: 2,032 rows" would have pointed at the cause in one glance.

It also reports file SIZES, because every byte here is paid for twice: once by the service
worker caching it, and once by a phone downloading it.

Output: docs/health.json - deliberately tiny.
"""
import json, os, sys
from datetime import datetime, timezone

OUT = "docs/health.json"
DOCS = "docs"

# Files that are expected to carry rows. Anything here showing 0 is a real problem.
EXPECT_ROWS = {
    "stocks.json", "screener.json", "universe.json", "indices.json", "sectors.json",
    "global.json", "mf.json", "etf.json", "rs.json", "seasonality.json", "correlation.json",
    "watchlists.json", "deals.json", "insider.json", "calendar.json", "ipo.json",
    "shareholding.json", "etf_premium.json", "breadth.json", "levels.json", "gaps.json",
    "patterns.json", "vix.json", "fo_ban.json", "metals.json", "listings.json",
    "recap.json", "report_cards.json", "market_stats.json",
}

# How to find the row count in each file, in order of preference.
COUNT_KEYS = ["count", "total", "matched", "dates", "sessions"]
LIST_KEYS = ["rows", "cards", "sectors", "indices", "series", "symbols", "days",
             "months", "sections", "events", "episodes", "stocks"]


def count_of(obj):
    """Best-effort row count. Returns (n, how) or (None, '') when it cannot tell."""
    if isinstance(obj, list):
        return len(obj), "list"
    if not isinstance(obj, dict):
        return None, ""
    for k in COUNT_KEYS:
        v = obj.get(k)
        if isinstance(v, int):
            return v, k
    for k in LIST_KEYS:
        v = obj.get(k)
        if isinstance(v, list):
            return len(v), k
        if isinstance(v, dict):
            return len(v), k
    return None, ""


def updated_of(obj):
    if isinstance(obj, dict):
        for k in ("updated", "generated_utc", "as_of", "date", "delisted_as_of"):
            v = obj.get(k)
            if isinstance(v, str) and v:
                return v
    return ""


def age_days(stamp):
    if not stamp:
        return None
    t = str(stamp).strip()
    try:
        if len(t) >= 19 and "T" in t:
            d = datetime.fromisoformat(t.replace("Z", "+00:00"))
        elif len(t) == 10:
            d = datetime.strptime(t, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        else:
            d = datetime.strptime(t[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return round((datetime.now(timezone.utc) - d).total_seconds() / 86400, 1)
    except Exception:
        return None


def main():
    if not os.path.isdir(DOCS):
        print("no docs/ directory")
        return 1

    rows, total_bytes = [], 0
    for name in sorted(os.listdir(DOCS)):
        if not name.endswith(".json"):
            continue
        path = os.path.join(DOCS, name)
        size = os.path.getsize(path)
        total_bytes += size
        try:
            obj = json.load(open(path))
        except Exception:
            rows.append({"file": name, "kb": round(size / 1024, 1), "count": None,
                         "updated": "", "age_days": None, "state": "unreadable"})
            continue

        n, how = count_of(obj)
        upd = updated_of(obj)
        age = age_days(upd)

        # state: what a reader needs to know at a glance
        if name in EXPECT_ROWS and (n == 0):
            state = "empty"
        elif age is not None and age > 2:
            state = "stale"
        elif n is None:
            state = "ok"          # config-like files legitimately have no rows
        else:
            state = "ok"

        rows.append({"file": name, "kb": round(size / 1024, 1), "count": n,
                     "updated": upd, "age_days": age, "state": state})

    empty = [r["file"] for r in rows if r["state"] == "empty"]
    stale = [r["file"] for r in rows if r["state"] == "stale"]
    biggest = sorted(rows, key=lambda r: -r["kb"])[:8]

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "files": len(rows),
        "total_kb": round(total_bytes / 1024, 1),
        "empty": empty,
        "stale": stale,
        "rows": rows,
        "biggest": [{"file": b["file"], "kb": b["kb"]} for b in biggest],
        "note": ("Every published file, with its age and row count. 'empty' means a file "
                 "that should carry rows carries none; 'stale' means older than two days. "
                 "If a section looks blank on the site, look here first - it names the file "
                 "and the reason."),
    }
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("files: %d | total %.0f KB" % (len(rows), total_bytes / 1024))
    print("empty: %s" % (", ".join(empty) or "none"))
    print("stale: %s" % (", ".join(stale) or "none"))
    print("biggest: %s" % ", ".join("%s %.0fKB" % (b["file"], b["kb"]) for b in biggest[:5]))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
