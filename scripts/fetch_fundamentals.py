#!/usr/bin/env python3
"""Quarterly results per company - the "why" behind the price.

WHY THIS EXISTS
Price data can say a stock fell 2.8%. It cannot say the company's revenue grew 10% while its
net margin slipped from 5.9% to 5.0%. That second sentence is the difference between a chart
and an analysis, and it needs filings, not candles.

SOURCE
NSE's public results-comparision endpoint, which serves the last five quarters for a symbol:
revenue, net profit, EPS and debt/equity. No key, no login - the same JSON a browser gets.

WHAT THE NUMBERS ARE, EXACTLY
  * UNITS ARE RUPEE LAKH. RELIANCE's 12,826,000 is Rs 1,28,260 crore, not 1.28 crore.
  * The figures are STANDALONE, not consolidated. For a group like Reliance the consolidated
    numbers are larger and include subsidiaries, so this is the parent company only.
  * Only five quarters are served, which allows exactly one year-on-year comparison.
  * EPS and debt/equity are frequently null in this feed. Missing stays missing - nothing is
    filled in.

WHAT IT COMPUTES
Year-on-year revenue growth, net margin, and the change in margin over the year. Those three
answer "is this company growing, and is it keeping more or less of each rupee" - which is the
question a price chart cannot answer.

Output: data/fundamentals/quarterly.parquet and docs/fundamentals.json
"""
import json, os, sys, time, urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
      "Accept": "application/json, text/plain, */*",
      "Referer": "https://www.nseindia.com/"}
API = "https://www.nseindia.com/api/results-comparision?symbol=%s"
ARCHIVE = "data/fundamentals/quarterly.parquet"
OUT = "docs/fundamentals.json"
LAKH = 1e5          # 1 lakh
CRORE = 1e7         # 1 crore


def get(symbol, timeout=30, retries=3):
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(API % symbol, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "replace"))
        except Exception:
            time.sleep(attempt * 2)
    return None


def to_date(s):
    """'31-DEC-2024' -> '2024-12-31'. Returns None if it will not parse."""
    try:
        from datetime import datetime as dt
        return dt.strptime(s.strip(), "%d-%b-%Y").strftime("%Y-%m-%d")
    except Exception:
        return None


def parse(payload, symbol):
    """Rows for one symbol, oldest first, with the three derived measures."""
    rows = (payload or {}).get("resCmpData") or []
    out = []
    for r in rows:
        end = to_date(str(r.get("re_to_dt") or ""))
        if not end:
            continue
        sale = r.get("re_net_sale")
        profit = r.get("re_net_profit")
        try:
            sale = float(sale) if sale is not None else None
            profit = float(profit) if profit is not None else None
        except Exception:
            sale = profit = None
        out.append({"symbol": symbol, "period_end": end,
                    "revenue_cr": round(sale * LAKH / CRORE, 1) if sale is not None else None,
                    "profit_cr": round(profit * LAKH / CRORE, 1) if profit is not None else None,
                    "margin_pct": (round(profit / sale * 100, 2)
                                   if sale and profit is not None and sale > 0 else None),
                    "eps": r.get("re_basic_eps"),
                    "debt_equity": r.get("re_debt_eqt_rat")})
    out.sort(key=lambda x: x["period_end"])
    return out


def derive(rows):
    """YoY growth and the margin change over the same period."""
    if len(rows) < 5:
        return None
    latest, year_ago = rows[-1], rows[-5]
    res = {"latest_period": latest["period_end"], "year_ago_period": year_ago["period_end"],
           "revenue_cr": latest["revenue_cr"], "profit_cr": latest["profit_cr"],
           "margin_pct": latest["margin_pct"]}
    if latest["revenue_cr"] and year_ago["revenue_cr"]:
        res["revenue_yoy_pct"] = round(
            (latest["revenue_cr"] / year_ago["revenue_cr"] - 1) * 100, 1)
    if latest["profit_cr"] is not None and year_ago["profit_cr"]:
        res["profit_yoy_pct"] = round(
            (latest["profit_cr"] / year_ago["profit_cr"] - 1) * 100, 1)
    if latest["margin_pct"] is not None and year_ago["margin_pct"] is not None:
        res["margin_change_pp"] = round(latest["margin_pct"] - year_ago["margin_pct"], 2)
    return res


def main():
    import pandas as pd

    limit = int(os.environ.get("FUNDAMENTAL_LIMIT", "200"))
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "companies": [], "note": ""}

    # pick the largest companies we already track, so the fetch is bounded and useful
    symbols = []
    try:
        st = json.load(open("docs/stocks.json")).get("stocks") or {}
        sized = []
        for v in st.values():
            mc = (v.get("fund") or {}).get("mcap")
            if v.get("symbol") and mc:
                sized.append((mc, v["symbol"]))
        sized.sort(reverse=True)
        symbols = [s for _, s in sized[:limit]]
    except Exception as e:
        print("  stocks.json: %s" % type(e).__name__)

    if not symbols:
        out["note"] = "No symbols to fetch - docs/stocks.json missing or has no market caps."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("fundamentals: no symbols")
        return 0

    print("fetching quarterly results for %d companies" % len(symbols))
    all_rows, ok, fail = [], 0, 0
    for i, sym in enumerate(symbols, 1):
        rows = parse(get(sym), sym)
        if rows:
            all_rows.extend(rows)
            d = derive(rows)
            if d:
                d["symbol"] = sym
                out["companies"].append(d)
            ok += 1
        else:
            fail += 1
        if i % 25 == 0 or i == len(symbols):
            print("  %d/%d  ok %d  empty %d" % (i, len(symbols), ok, fail))
        time.sleep(0.45)

    if not all_rows:
        out["note"] = "NSE returned nothing - the endpoint may have changed."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("fundamentals: nothing collected")
        return 0

    os.makedirs(os.path.dirname(ARCHIVE), exist_ok=True)
    pd.DataFrame(all_rows).to_parquet(ARCHIVE, index=False)
    print("-> %s  %d rows" % (ARCHIVE, len(all_rows)))

    # rank by the two questions worth asking
    out["companies"].sort(key=lambda c: -(c.get("revenue_yoy_pct") or -999))
    out["count"] = len(out["companies"])
    out["top_growth"] = out["companies"][:5]
    squeezed = [c for c in out["companies"] if c.get("margin_change_pp") is not None]
    squeezed.sort(key=lambda c: c["margin_change_pp"])
    out["margin_squeezed"] = squeezed[:5]
    out["margin_expanded"] = squeezed[-5:][::-1]

    out["note"] = ("Standalone quarterly results from NSE, five quarters per company. Figures "
                   "are the parent company only, not the consolidated group, and EPS and "
                   "debt/equity are often null in this feed - missing stays missing.")
    out["cautions"] = {
        "standalone": ("These are standalone figures. For groups with large subsidiaries the "
                       "consolidated numbers differ, sometimes a lot."),
        "five_quarters": "Only five quarters are available, so exactly one year-on-year comparison.",
        "units": "Revenue and profit are in Rs crore, converted from NSE's rupee lakh.",
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.0f KB  |  %d companies with a full year" % (OUT, os.path.getsize(OUT) / 1024,
                                                                out["count"]))
    for c in out["top_growth"][:5]:
        print("   %-12s rev %+6s%%  profit %+7s%%  margin %s%% (%+s pp)"
              % (c["symbol"], c.get("revenue_yoy_pct"), c.get("profit_yoy_pct"),
                 c.get("margin_pct"), c.get("margin_change_pp")))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print("::warning title=Fundamentals failed::%s: %s" % (type(e).__name__, str(e)[:120]))
        sys.exit(0)
