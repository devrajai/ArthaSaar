#!/usr/bin/env python3
"""Track every statistic the site publishes, and say each week whether it still holds.

WHY THIS EXISTS
The site publishes base rates: PCR bands, gap fill rates, breadth. Each is a claim about the
past. Nothing checked whether last week's claim is still true this week - a number can drift as
sessions accumulate, and a statistic that quietly changes is worse than one that is wrong,
because nobody notices.

This stores each published figure with its sample size and date, then on the next run compares.
A claim is marked:
    held        the figure moved less than the tolerance
    moved       it changed by more than that, and by how much
    too few     the sample fell below the threshold - no verdict either way
    new         first time this claim has been recorded

WHAT IT IS NOT
Not a score of the market. It is a check on OUR OWN numbers. If a base rate says 74% and the
next week says 71%, that is the file's business to say so.

STORAGE
data/claim_ledger.json - a list of {claim, value, n, date}, newest last, capped so it stays
small. Append-only within the cap: old entries are dropped, never rewritten.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

LEDGER = "data/claim_ledger.json"
OUT = "docs/claim_ledger.json"
MAX_ENTRIES = 400
TOLERANCE = 1.0      # percentage points before a claim counts as moved
MIN_N = 60


def jload(p):
    try:
        return json.loads(open(p).read())
    except Exception:
        return None


def current_claims():
    """Every statistic we publish, read from the files that publish them."""
    out = []

    pcr = jload("docs/pcr_signal.json") or {}
    for b in (pcr.get("bands") or []):
        band = str(b.get("band") or "")
        for h in (b.get("horizons") or []):
            if h.get("h") != 21:
                continue
            if h.get("up_pct") is None or h.get("n") is None:
                continue
            out.append({
                "claim": "PCR band %s: share up over 21 sessions" % band,
                "value": round(float(h["up_pct"]), 2),
                "n": int(h["n"]),
                "unit": "%",
            })

    g = jload("docs/gaps.json") or {}
    sm = g.get("samples") or {}
    if g.get("fill_rate_up") is not None:
        out.append({"claim": "Gap-up fills within the window", "value": round(float(g["fill_rate_up"]), 2),
                    "n": int(sm.get("up") or 0), "unit": "%"})
    if g.get("fill_rate_down") is not None:
        out.append({"claim": "Gap-down fills within the window", "value": round(float(g["fill_rate_down"]), 2),
                    "n": int(sm.get("down") or 0), "unit": "%"})

    br = jload("docs/breadth.json") or {}
    if br.get("above_50") is not None:
        out.append({"claim": "Stocks above their 50-day average", "value": round(float(br["above_50"]), 2),
                    "n": int(br.get("total") or 0), "unit": "%"})

    return out


def main() -> int:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    claims = current_claims()
    if not claims:
        print("no published statistics found - nothing to log")
        return 0

    hist = jload(LEDGER) or []
    if not isinstance(hist, list):
        hist = []

    # the newest entry for each claim, before today
    last = {}
    for e in hist:
        if e.get("date") != now:
            last[e.get("claim")] = e

    rows = []
    for c in claims:
        prev = last.get(c["claim"])
        rec = {"claim": c["claim"], "value": c["value"], "n": c["n"],
               "unit": c["unit"], "date": now}
        if not prev:
            rec["status"] = "new"
            rec["detail"] = "first recording"
        elif c["n"] < MIN_N:
            rec["status"] = "too few"
            rec["detail"] = "n=%d, below the %d threshold" % (c["n"], MIN_N)
        else:
            delta = c["value"] - float(prev.get("value") or 0)
            if abs(delta) <= TOLERANCE:
                rec["status"] = "held"
                rec["detail"] = "moved %+.2f points since %s" % (delta, prev.get("date"))
            else:
                rec["status"] = "moved"
                # round both sides: 76.60000000000001 is a float artefact, not a measurement
                rec["detail"] = "%+.2f points since %s (%.2f -> %.2f)" % (
                    delta, prev.get("date"), float(prev.get("value") or 0), c["value"])
        rows.append(rec)

    # append today's, keeping the file bounded
    hist.extend(rows)
    hist = hist[-MAX_ENTRIES:]
    os.makedirs(os.path.dirname(LEDGER), exist_ok=True)
    json.dump(hist, open(LEDGER, "w"), separators=(",", ":"))

    held = sum(1 for r in rows if r["status"] == "held")
    moved = sum(1 for r in rows if r["status"] == "moved")
    few = sum(1 for r in rows if r["status"] == "too few")
    new = sum(1 for r in rows if r["status"] == "new")

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": now,
        "claims": rows,
        "held": held, "moved": moved, "too_few": few, "new": new,
        "tolerance_points": TOLERANCE,
        "min_n": MIN_N,
        "note": ("Every statistic this site publishes, recorded with its sample size, and "
                 "compared with the previous recording. A claim that moves more than the "
                 "tolerance is reported as moved, with both values - a base rate that quietly "
                 "drifts is worse than one that is wrong, because nobody notices."),
        "cautions": {
            "not_accuracy": ("This checks whether OUR numbers are stable, not whether the "
                             "market obeys them."),
            "drift_is_expected": ("Sample sizes grow as sessions accumulate, so small movement "
                                  "is normal. The tolerance exists so the report does not cry "
                                  "wolf about a tenth of a point."),
            "history_cap": ("The ledger keeps the last %d entries. Older records are dropped, "
                            "never rewritten." % MAX_ENTRIES),
        },
    }
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %d claims: held %d · moved %d · too few %d · new %d"
          % (len(rows), held, moved, few, new))
    for r in rows:
        if r["status"] in ("moved", "too few"):
            print("     [%s] %s" % (r["status"], r["claim"][:64]))
            print("        %s" % r["detail"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
