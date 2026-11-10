#!/usr/bin/env python3
"""The one lakh time machine: what a real investment became, and the worst it fell on the way.

WHY THIS EXISTS
"₹1 lakh invested five years ago is worth ₹2.4 lakh" is the sentence every fund house prints.
It is true and it is half the story. The other half is the worst fall between the start and
the end - the number that decides whether a real person actually stayed invested.

Both are published together here, and neither is shown without the other.

WHAT IT BUILDS
  funds   ₹1 lakh into each of 400 funds, 1/3/5/10 years, with the fund's worst drawdown
  stocks  the same for the largest stocks, computed from closing prices
  spread  how many of them would have been underwater at some point, and by how much

WHAT IT REFUSES TO DO
  rank by return alone. A fund that made 20% a year through a 45% fall is a different thing
  from one that made 18% smoothly, and the table shows the fall beside the return.
"""
import json, os, sys

MF = "docs/mf.json"
SERIES = "docs/series.json"
OUT = "docs/timemachine.json"
LAKH = 100000
YEARS = {"1y": 1, "3y": 3, "5y": 5, "10y": 10}
MAX_STOCKS = 120


def value(amount, pct):
    """What an amount becomes at a compound annual rate."""
    if pct is None:
        return None
    return round(amount * ((1 + pct / 100.0)), 0)


def main():
    out = {"available": False, "funds": [], "stocks": [], "note": "", "cautions": {}}
    if not os.path.exists(MF):
        print("no %s" % MF)
        json.dump(out, open(OUT, "w"), separators=(",", ":"))
        return 0

    mf = json.load(open(MF))
    rows = mf.get("rows") or []
    print("  %d funds" % len(rows))

    funds = []
    for r in rows:
        rec = {"name": r.get("name"), "house": r.get("fund_house"),
               "category": r.get("category"), "nav": r.get("nav"),
               "max_dd": r.get("max_dd")}
        got = False
        for k, yrs in YEARS.items():
            pct = r.get(k)
            if pct is None:
                continue
            # the annual figure compounded over the period, not multiplied by years
            total_pct = ((1 + pct / 100.0) ** yrs - 1) * 100
            rec[k] = {"cagr": pct, "value": value(LAKH, total_pct),
                      "gain_pct": round(total_pct, 1)}
            got = True
        if got:
            funds.append(rec)

    # how many would have been underwater at some point - the honest headline
    dd = [f["max_dd"] for f in funds if isinstance(f.get("max_dd"), (int, float))]
    if dd:
        over20 = sum(1 for x in dd if x <= -20)
        over35 = sum(1 for x in dd if x <= -35)
        worst = min(dd)
        out["drawdown_finding"] = (
            "Of %d funds, %d fell more than 20%% at some point and %d fell more than 35%%. "
            "The worst was %.0f%%. A return quoted without this is half a number."
            % (len(dd), over20, over35, worst))

    # stocks, from closing prices
    stocks = []
    if os.path.exists(SERIES):
        sj = json.load(open(SERIES)).get("series") or {}
        for sym, closes in list(sj.items())[:MAX_STOCKS]:
            if not closes or len(closes) < 260:
                continue
            last = closes[-1]
            rec = {"symbol": sym.replace(".NS", ""), "last": round(last, 2)}
            got = False
            for k, yrs in YEARS.items():
                n = 252 * yrs
                if len(closes) <= n:
                    continue
                then = closes[-1 - n]
                if then <= 0:
                    continue
                total_pct = (last / then - 1) * 100
                rec[k] = {"value": round(LAKH * (1 + total_pct / 100.0), 0),
                          "gain_pct": round(total_pct, 1)}
                got = True
            # worst fall from a running peak across the whole series
            peak = closes[0]
            worst_dd = 0.0
            for c in closes:
                if c > peak:
                    peak = c
                if peak > 0:
                    ddp = (c / peak - 1) * 100
                    if ddp < worst_dd:
                        worst_dd = ddp
            rec["max_dd"] = round(worst_dd, 1)
            if got:
                stocks.append(rec)

    out["funds"] = funds
    out["stocks"] = stocks
    out["available"] = bool(funds or stocks)
    out["count_funds"] = len(funds)
    out["count_stocks"] = len(stocks)
    out["note"] = ("What %d into each fund and %d stocks became over 1, 3, 5 and 10 years, "
                   "with the worst fall along the way. Returns are annual figures compounded "
                   "over each period." % (LAKH, len(stocks)))
    out["cautions"] = {
        "worst_fall_matters": ("A return quoted without the drawdown is half a number. Most "
                               "people sell during the fall, so the fall decides the outcome "
                               "more than the average does."),
        "past_not_future": "These are historical. A fund's past return is not a forecast.",
        "no_charges": ("Direct-plan NAVs exclude commission but not every cost; a regular plan "
                       "would return less."),
        "survivorship": ("Only funds that still exist are listed. Funds that closed are absent, "
                         "which flatters the average."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   funds: %d | stocks: %d" % (len(funds), len(stocks)))
    if out.get("drawdown_finding"):
        print("   %s" % out["drawdown_finding"])
    for f in funds[:3]:
        if f.get("5y"):
            print("     %-46s Rs 1L -> Rs %s in 5y (%.0f%%)  worst fall %.0f%%"
                  % ((f["name"] or "")[:46], f"{f['5y']['value']:,.0f}",
                     f["5y"]["gain_pct"], f.get("max_dd") or 0))
    return 0


if __name__ == "__main__":
    sys.exit(main())
