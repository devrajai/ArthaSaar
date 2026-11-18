#!/usr/bin/env python3
"""Which sectors are trending, and which stocks are dragging them.

WHY THIS EXISTS
The site could tell you Dabur was down 27% from its 52-week high. It could not tell you whether
that was Dabur or the whole of FMCG - and those are different facts. A stock falling while its
sector rises is a company problem; a stock falling with its sector is a sector problem, and the
same -27% means something different in each case.

This computes, per sector:
    how many stocks are in an uptrend, a downtrend, or mixed
    the median 20-session change
    the share above their 50-day average
    the strongest and weakest members
    and whether the sector's own breadth agrees with its median move

WHAT IT DOES NOT DO
No sector call, no rotation advice, no "buy FMCG". It describes where the money already went.
A sector can be up on one large stock; the breadth figure is there so you can see that.
"""
from __future__ import annotations

import json
import os
import statistics
import sys
from datetime import datetime, timezone

STOCKS = "docs/stocks.json"
SCREENER = "docs/screener.json"
OUT = "docs/sector_trend.json"

MIN_MEMBERS = 8          # a sector with fewer stocks is a sample, not a sector


def jload(p):
    try:
        return json.loads(open(p).read())
    except Exception:
        return None


def main() -> int:
    d = jload(STOCKS) or {}
    st = d.get("stocks") or {}
    if not st:
        print("no stocks.json")
        return 0

    scr = jload(SCREENER) or {}
    by_sym = {}
    for r in (scr.get("rows") or []):
        by_sym[str(r.get("symbol") or "").upper()] = r

    groups = {}
    for _, v in st.items():
        sec = str(v.get("sector") or "").strip()
        if not sec:
            continue
        tech = v.get("tech") or {}
        sym = str(v.get("symbol") or "").upper()
        row = by_sym.get(sym) or {}
        groups.setdefault(sec, []).append({
            "symbol": sym,
            "name": str(v.get("name") or "")[:48],
            "close": v.get("close"),
            "trend": tech.get("trend") or row.get("trend"),
            "rsi": tech.get("rsi_14") if tech.get("rsi_14") is not None else row.get("rsi"),
            "chg_20d": row.get("chg_20d"),
            "from_52w_high": row.get("from_52w_high"),
            "sma_50": tech.get("sma_50"),
            "sma_200": tech.get("sma_200"),
        })

    sectors = []
    for sec, members in groups.items():
        if len(members) < MIN_MEMBERS:
            continue
        up = sum(1 for m in members if str(m["trend"]).lower() == "up")
        down = sum(1 for m in members if str(m["trend"]).lower() == "down")
        mixed = len(members) - up - down

        ch = [float(m["chg_20d"]) for m in members if m.get("chg_20d") is not None]
        med20 = round(statistics.median(ch), 2) if ch else None

        above50 = 0
        have50 = 0
        for m in members:
            if m.get("close") and m.get("sma_50"):
                have50 += 1
                if float(m["close"]) > float(m["sma_50"]):
                    above50 += 1
        breadth = round(above50 / have50 * 100.0, 1) if have50 else None

        ranked = [m for m in members if m.get("chg_20d") is not None]
        ranked.sort(key=lambda m: -float(m["chg_20d"]))
        leaders = [{"symbol": m["symbol"], "chg_20d": round(float(m["chg_20d"]), 2),
                    "from_52w_high": m.get("from_52w_high")} for m in ranked[:3]]
        laggards = [{"symbol": m["symbol"], "chg_20d": round(float(m["chg_20d"]), 2),
                     "from_52w_high": m.get("from_52w_high")} for m in ranked[-3:][::-1]]

        # does breadth agree with the median move? A sector up on narrow breadth is one or two
        # large stocks carrying the rest, and that is worth flagging rather than averaging away.
        agree = None
        if breadth is not None and med20 is not None:
            if med20 > 0 and breadth < 40:
                agree = "narrow rally - the median is up but fewer than 40% are above their 50-day"
            elif med20 < 0 and breadth > 60:
                agree = "narrow fall - the median is down but most are above their 50-day"
            else:
                agree = "breadth and the median move point the same way"

        sectors.append({
            "sector": sec, "n": len(members),
            "up": up, "down": down, "mixed": mixed,
            "up_pct": round(up / len(members) * 100.0, 1),
            "median_chg_20d": med20,
            "breadth_above_50": breadth,
            "breadth_note": agree,
            "leaders": leaders, "laggards": laggards,
        })

    sectors.sort(key=lambda s: -(s["median_chg_20d"] if s["median_chg_20d"] is not None else -999))

    # A per-stock lookup was 200 KB of a 240 KB file and nothing read it. Dropped: the page
    # derives what it needs from sectors[], and a 240 KB fetch on a phone is a real cost for
    # data no one displays.
    lookup = {}
    for s in sectors:
        for m in groups.get(s["sector"], [])[:0]:
            pass

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sectors": sectors,
        "count": len(sectors),
        "lookup": lookup,
        "note": ("Per sector: how many stocks are trending up, down or mixed, the median "
                 "20-session change, the share above their 50-day average, and the strongest "
                 "and weakest members. A stock falling while its sector rises is a company "
                 "problem; falling with its sector is a sector problem, and the same fall means "
                 "something different in each case."),
        "cautions": {
            "no_call": ("This describes where money already went. It is not a rotation call and "
                        "not advice."),
            "breadth_matters": ("A sector can rise on one large stock. The breadth figure is "
                                "published beside the median so you can see when that happens."),
            "min_members": ("Sectors with fewer than %d stocks are omitted - a handful of names "
                            "is a sample, not a sector." % MIN_MEMBERS),
        },
    }
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("-> %s  %.1f KB | %d sectors" % (OUT, os.path.getsize(OUT) / 1024, len(sectors)))
    for s in sectors[:5]:
        print("   %-24s 20d %+6.2f%%  up %d/%d  breadth %s%%  %s"
              % (s["sector"], s["median_chg_20d"] or 0, s["up"], s["n"],
                 s["breadth_above_50"], (s["breadth_note"] or "")[:34]))
    print("   ...")
    for s in sectors[-3:]:
        print("   %-24s 20d %+6.2f%%  up %d/%d  breadth %s%%"
              % (s["sector"], s["median_chg_20d"] or 0, s["up"], s["n"], s["breadth_above_50"]))
    dab = lookup.get("DABUR")
    if dab:
        print("\n   DABUR -> sector %s | sector 20d %s | stock 20d %s"
              % (dab["sector"], dab["sector_median_20d"], dab["stock_chg_20d"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
