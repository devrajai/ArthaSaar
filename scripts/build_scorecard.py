#!/usr/bin/env python3
"""Signal scorecard: every call logged the day it is made, then scored against reality.

WHY THIS IS THE ONE THING WORTH BUILDING
A competitor can copy this code tomorrow. They cannot copy three years of timestamped,
publicly scored calls - and that record is the only asset here that compounds.

It is also the only honest way to publish a signal. Anyone can say "our model flags big
moves". Publishing "41 flagged days, 17 were big moves, against a 9.4% base rate" is
uncomfortable, which is exactly why almost nobody does it, and exactly why it differentiates.

WHAT IS LOGGED
Every run appends today's readings before the outcome is known:
  early_pctile   where the early-warning score sat
  early_score    the raw score
  setup          which scenario bucket the session fell in
  nifty_move     filled in LATER, once the session has actually happened

WHAT IS SCORED
  hit rate on flagged days   (percentile >= 80)  against the unconditional base rate
  hit rate on quiet days     (percentile <  50)
  the same for the scenario buckets
Nothing is scored until the outcome exists, so a day is never counted twice or guessed at.
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

LOG = "data/signals/log.json"
OUT = "docs/scorecard.json"
NIFTY = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=10y"
BIG = 1.5              # a "big day" is |move| >= 1.5%, same definition used everywhere else
FLAG = 80              # percentile at or above which the signal is counted as a call
QUIET = 50


def nifty_moves():
    """date -> that session's % move, from the previous close."""
    import datetime as dt
    try:
        j = json.loads(urllib.request.urlopen(
            urllib.request.Request(NIFTY, headers={"User-Agent": "Mozilla/5.0"}),
            timeout=60).read())
        r = j["chart"]["result"][0]
        q = r["indicators"]["quote"][0]
        rows = [(dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d"), c)
                for t, c in zip(r["timestamp"], q["close"]) if c is not None]
        rows.sort()
        return {rows[i][0]: round((rows[i][1] / rows[i - 1][1] - 1) * 100, 2)
                for i in range(1, len(rows))}
    except Exception as e:
        print("  nifty fetch failed: %s" % type(e).__name__)
        return {}


def load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def main():
    os.makedirs("data/signals", exist_ok=True)
    os.makedirs("docs", exist_ok=True)

    moves = nifty_moves()
    log = load(LOG, {"entries": []})
    entries = log.get("entries") or []
    by_date = {e["date"]: e for e in entries if e.get("date")}

    # ---- 1. backfill outcomes for anything not yet scored -------------------------------
    filled = 0
    for e in entries:
        if e.get("nifty_move_pct") is None and e["date"] in moves:
            e["nifty_move_pct"] = moves[e["date"]]
            e["big_day"] = abs(moves[e["date"]]) >= BIG
            filled += 1

    # ---- 2. append today's reading, before the outcome is known -------------------------
    early = load("docs/earlymove.json", {})
    scen = load("docs/scenarios.json", {})
    today = (early.get("today") or {})
    if today.get("date") and today["date"] not in by_date:
        e = {"date": today["date"],
             "early_pctile": today.get("percentile"),
             "early_score": today.get("score"),
             "setup": (scen.get("today") or {}).get("setup"),
             "nifty_move_pct": moves.get(today["date"]),      # filled later if not yet known
             "logged_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
        if e["nifty_move_pct"] is not None:
            e["big_day"] = abs(e["nifty_move_pct"]) >= BIG
        entries.append(e)
        by_date[today["date"]] = e
        print("  logged %s at percentile %s" % (today["date"], today.get("percentile")))

    entries.sort(key=lambda x: x["date"])
    json.dump({"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "big_day_threshold_pct": BIG, "flag_percentile": FLAG,
               "entries": entries[-1200:]},
              open(LOG, "w"), ensure_ascii=False, separators=(",", ":"))

    # ---- 3. score what has an outcome --------------------------------------------------
    scored = [e for e in entries if e.get("big_day") is not None]

    def block(rows, label):
        if not rows:
            return None
        big = sum(1 for e in rows if e["big_day"])
        return {"label": label, "n": len(rows), "big_days": big,
                "hit_pct": round(big / len(rows) * 100, 1)}

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "logged": len(entries), "scored": len(scored),
           "base_rate_pct": None, "slices": [], "recent": [], "note": ""}

    if scored:
        out["base_rate_pct"] = round(sum(1 for e in scored if e["big_day"]) / len(scored) * 100, 1)
        flagged = [e for e in scored if (e.get("early_pctile") or 0) >= FLAG]
        quiet = [e for e in scored if (e.get("early_pctile") or 100) < QUIET]
        mid = [e for e in scored if QUIET <= (e.get("early_pctile") or 0) < FLAG]
        for rows, label in ((flagged, "flagged (percentile >= %d)" % FLAG),
                            (mid, "middle (%d-%d)" % (QUIET, FLAG - 1)),
                            (quiet, "quiet (percentile < %d)" % QUIET)):
            b = block(rows, label)
            if b:
                b["lift"] = round(b["hit_pct"] / out["base_rate_pct"], 2) if out["base_rate_pct"] else None
                out["slices"].append(b)

        # last 10 scored calls, so the record is visible as a record and not just a number
        for e in scored[-10:][::-1]:
            out["recent"].append({"date": e["date"], "pctile": e.get("early_pctile"),
                                  "move_pct": e["nifty_move_pct"],
                                  "big_day": e["big_day"],
                                  "called": "flagged" if (e.get("early_pctile") or 0) >= FLAG else ""})

    out["note"] = ("Every signal is logged the day it is made, before the outcome is known, and "
                   "scored once the session has happened. Nothing here is backfilled by hand.")
    out["cautions"] = {
        "young": ("The record starts the day this was first run. Early numbers are noise - a "
                  "handful of calls cannot distinguish a real edge from luck."),
        "one_signal": ("Only the early-warning score is scored here. Other signals are logged "
                       "for the record but not yet graded."),
        "no_shifting": ("The threshold and the big-day definition are fixed in the code, not "
                        "chosen after seeing results."),
    }

    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  |  logged %d, scored %d" % (OUT, out["logged"], out["scored"]))
    if out["base_rate_pct"] is not None:
        print("   base rate %.1f%%" % out["base_rate_pct"])
        for s in out["slices"]:
            print("   %-30s n=%-3d %5.1f%% big  lift %s"
                  % (s["label"], s["n"], s["hit_pct"], s.get("lift")))
    else:
        print("   no outcomes yet - the record starts now and scores from tomorrow")
    return 0


if __name__ == "__main__":
    sys.exit(main())
