#!/usr/bin/env python3
"""The one lakh time machine: what a real investment became, and the worst it fell on the way.

WHY THIS EXISTS
"₹1 lakh invested five years ago is worth ₹2.4 lakh" is the sentence every fund house prints.
It is true and it is half the story. The other half is the worst fall between the start and the
end - the number that decides whether a real person actually stayed invested. Both are
published together, and neither without the other.

TWO BUGS THIS FILE ONCE HAD, BOTH SILENT
1. mf.json names its columns r1y, r3y, r5y, r10y. Reading "1y" instead returned None for every
   fund, and the file was written with zero funds and no error.
2. series.json holds only 120 points per symbol - about six months - so a five-year figure
   cannot come from it. Stocks now use charts.json, which carries 94 monthly closes since 2019.

A THIRD, WORSE ONE
The copy that shipped was not the copy that was tested: the output JSON was built from a fixed
local script while the repository still held the buggy one. The next pipeline run would have
overwritten a good file with an empty one. This rewrite is the tested version.
"""
import json, os, sys
from datetime import datetime, timezone

MF = "docs/mf.json"
CHARTS = "docs/charts.json"      # monthly closes since 2019
SCREENER = "docs/screener.json"  # the stocks that actually have a page
OUT = "docs/timemachine.json"
LAKH = 100000
# mf.json names its columns r1y/r3y/r5y/r10y - not 1y/3y.
YEARS = {"r1y": 1, "r3y": 3, "r5y": 5, "r10y": 10}
MAX_STOCKS = 800


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def value(amount, pct):
    return None if pct is None else round(amount * (1 + pct / 100.0), 0)


def main():
    out = {"updated": now(), "available": False, "funds": [], "stocks": [],
           "note": "", "cautions": {}}
    if not os.path.exists(MF):
        print("no %s" % MF)
        json.dump(out, open(OUT, "w"), separators=(",", ":"))
        return 0

    rows = (json.load(open(MF)).get("rows") or [])
    print("  %d funds" % len(rows))

    funds = []
    for r in rows:
        rec = {"name": r.get("name"), "house": r.get("fund_house"),
               "category": r.get("category"), "nav": r.get("nav"),
               "max_dd": r.get("max_dd")}
        got = False
        for k, yrs in YEARS.items():
            pct = r.get(k)
            if not isinstance(pct, (int, float)):
                continue
            total = ((1 + pct / 100.0) ** yrs - 1) * 100
            rec[k[1:]] = {"cagr": pct, "value": value(LAKH, total), "gain_pct": round(total, 1)}
            got = True
        if got:
            funds.append(rec)

    dd = [f["max_dd"] for f in funds if isinstance(f.get("max_dd"), (int, float))]
    if dd:
        out["drawdown_finding"] = (
            "Of %d funds, %d fell more than 20%% at some point and %d fell more than 35%%. "
            "The worst was %.0f%%. A return quoted without this is half a number."
            % (len(dd), sum(1 for x in dd if x <= -20), sum(1 for x in dd if x <= -35), min(dd)))

    stocks = []
    if os.path.exists(CHARTS):
        cj = json.load(open(CHARTS))
        allseries = cj.get("series") or {}
        want = None
        if os.path.exists(SCREENER):
            try:
                want = {r["symbol"] for r in json.load(open(SCREENER)).get("rows", [])
                        if isinstance(r, dict) and r.get("symbol")}
            except Exception:
                want = None
        cand = [k for k in allseries if (want is None or k in want)]
        # longest history first, so the five-year column is real rather than blank
        cand.sort(key=lambda k: -len(allseries[k] or []))
        for sym in cand[:MAX_STOCKS]:
            pts = allseries[sym]
            if not pts:
                continue
            closes = [x[1] for x in pts if isinstance(x, list) and len(x) == 2 and x[1]]
            if len(closes) < 13:
                continue
            last = closes[-1]
            rec = {"symbol": sym, "last": round(last, 2), "months": len(closes)}
            got = False
            for k, yrs in YEARS.items():
                n = 12 * yrs                      # months, not sessions
                if len(closes) <= n:
                    continue
                then = closes[-1 - n]
                if then <= 0:
                    continue
                total = (last / then - 1) * 100
                rec[k[1:]] = {"value": round(LAKH * (1 + total / 100.0), 0),
                              "gain_pct": round(total, 1)}
                got = True
            peak = closes[0]
            worst = 0.0
            for c in closes:
                if c > peak:
                    peak = c
                if peak > 0:
                    worst = min(worst, (c / peak - 1) * 100)
            rec["max_dd"] = round(worst, 1)
            if got:
                stocks.append(rec)

    out["funds"] = funds
    out["stocks"] = stocks
    out["available"] = bool(funds or stocks)
    out["count_funds"] = len(funds)
    out["count_stocks"] = len(stocks)
    out["note"] = ("What %d into each fund and %d stocks became over 1, 3, 5 and 10 years, with "
                   "the worst fall along the way." % (LAKH, len(stocks)))
    out["cautions"] = {
        "worst_fall_matters": ("A return quoted without the drawdown is half a number. Most "
                               "people sell during the fall, so the fall decides the outcome "
                               "more than the average does."),
        "past_not_future": "These are historical. A fund's past return is not a forecast.",
        "no_charges": ("Direct-plan NAVs exclude commission but not every cost; a regular plan "
                       "would return less."),
        "survivorship": ("Only funds that still exist are listed, which flatters the average."),
        "monthly_closes": ("Stock figures use MONTHLY closes, so an intra-month fall is not "
                           "seen. The real drawdown is equal or worse than shown, never better."),
    }

    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   funds: %d | stocks: %d" % (len(funds), len(stocks)))
    if out.get("drawdown_finding"):
        print("   %s" % out["drawdown_finding"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
