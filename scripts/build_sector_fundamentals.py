#!/usr/bin/env python3
"""Sector-level fundamentals: where margins are being made and where they are being eaten.

WHY THIS EXISTS
A single company's margin tells you little. A whole sector's margin moving the same way tells
you something structural is happening - an import wave, a price war, a cost shock. That is the
layer between a price chart and an industry story.

WHAT IT SHOWS
For every sector with enough companies: median revenue growth, median net margin, and median
CHANGE in margin over the year. The median matters because one distressed name should not
define a sector.

WHY THE CHANGE MATTERS MORE THAN THE LEVEL
A chemicals company at 6% margin is not news. A chemicals sector whose median margin fell 1.6
percentage points in a year, while revenue barely grew, is news: it says pricing power went
somewhere. That is exactly what our own data shows for Basic Materials, and it is consistent
with cheap imports undercutting domestic producers.

READS
docs/fundamentals.json   per-company quarterly results
docs/stocks.json         sector labels and market cap

WRITES
docs/sector_fund.json
"""
import json, os, statistics as st, sys
from datetime import datetime, timezone

FUND = "docs/fundamentals.json"
STOCKS = "docs/stocks.json"
OUT = "docs/sector_fund.json"
MIN_MEMBERS = 3


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "sectors": [], "squeezed": [], "expanded": [], "note": ""}

    try:
        companies = json.load(open(FUND)).get("companies") or []
        stk = json.load(open(STOCKS)).get("stocks") or {}
    except Exception:
        out["note"] = "Missing docs/fundamentals.json or docs/stocks.json."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("sector fundamentals: no input")
        return 0

    if not companies:
        out["note"] = "fundamentals.json holds no companies yet."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("sector fundamentals: empty")
        return 0

    meta = {}
    for v in stk.values():
        if v.get("symbol"):
            meta[v["symbol"]] = {"sector": v.get("sector") or "Unclassified",
                                 "mcap": (v.get("fund") or {}).get("mcap"),
                                 "name": v.get("name")}

    by = {}
    for c in companies:
        s = meta.get(c["symbol"], {}).get("sector") or "Unclassified"
        by.setdefault(s, []).append(c)

    for sector, cs in by.items():
        if len(cs) < MIN_MEMBERS:
            continue
        rv = [c["revenue_yoy_pct"] for c in cs if c.get("revenue_yoy_pct") is not None]
        pf = [c["profit_yoy_pct"] for c in cs if c.get("profit_yoy_pct") is not None]
        mg = [c["margin_pct"] for c in cs if c.get("margin_pct") is not None]
        dm = [c["margin_change_pp"] for c in cs if c.get("margin_change_pp") is not None]
        if not (rv and mg):
            continue
        out["sectors"].append({
            "sector": sector, "n": len(cs),
            "median_revenue_yoy": round(st.median(rv), 1) if rv else None,
            "median_profit_yoy": round(st.median(pf), 1) if pf else None,
            "median_margin": round(st.median(mg), 2) if mg else None,
            "median_margin_change": round(st.median(dm), 2) if dm else None,
        })

    out["sectors"].sort(key=lambda x: -(x["median_revenue_yoy"] or -999))

    # the companies whose margins were eaten hardest, for the "why" behind a sector move
    # A margin change of -75pp is not a squeeze, it is a different business or a lumpy
    # revenue-recognition quarter: real estate books revenue when projects complete, and
    # ABCAPITAL's -95% revenue is a restructuring, not demand. Extreme moves are excluded
    # rather than ranked, because they make the list useless for spotting a sector trend.
    squeezed = [c for c in companies
                if c.get("margin_change_pp") is not None
                and c.get("revenue_yoy_pct") is not None
                and abs(c["revenue_yoy_pct"]) <= 60
                and abs(c["margin_change_pp"]) <= 15
                and (c.get("margin_pct") is None or c["margin_pct"] > 0)]
    squeezed.sort(key=lambda c: c["margin_change_pp"])
    for c in squeezed[:10]:
        m = meta.get(c["symbol"], {})
        c["_sector"] = m.get("sector")
        c["_mcap_cr"] = round((m.get("mcap") or 0) / 1e7) if m.get("mcap") else None
    out["squeezed"] = squeezed[:10]
    out["expanded"] = squeezed[-10:][::-1]

    out["count"] = len(out["sectors"])
    out["note"] = ("Sector medians of standalone quarterly results. The CHANGE in margin matters "
                   "more than its level: a whole sector losing margin while revenue stalls says "
                   "pricing power moved somewhere, which no price chart shows.")
    out["cautions"] = {
        "standalone": "Parent company only, not the consolidated group.",
        "median": ("Medians, not means, so one distressed company cannot define a sector. "
                   "Sectors with fewer than %d companies are omitted." % MIN_MEMBERS),
        "five_quarters": "Only five quarters are available, so one year-on-year comparison.",
        "structure": ("This shows THAT margins moved. It cannot show why - import volumes, "
                      "capacity additions and feedstock costs are not in our data."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB  |  %d sectors" % (OUT, os.path.getsize(OUT) / 1024, out["count"]))
    print("\n%-24s %3s %10s %10s %11s" % ("sector", "n", "med rev%", "med margin", "med dmargin"))
    for s in out["sectors"]:
        print("%-24s %3d %+10.1f %10.1f %+11.2f"
              % (s["sector"], s["n"], s["median_revenue_yoy"] or 0,
                 s["median_margin"] or 0, s["median_margin_change"] or 0))
    print("\nhardest margin squeeze:")
    for c in out["squeezed"][:6]:
        print("  %-12s %-20s rev %+7s%%  margin %+6s pp"
              % (c["symbol"], (c["_sector"] or "")[:20], c.get("revenue_yoy_pct"),
                 c.get("margin_change_pp")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
