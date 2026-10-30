#!/usr/bin/env python3
"""Crypto price history, month-end closes, from the Yahoo files the pipeline already fetches.

WHY NO COLAB
Same as the ETFs: the source already works here. fetch_yahoo.py pulls the crypto group every
run and writes data/yahoo/<SAFE>.parquet, and docs/crypto.json already lists 82 coins with
price, RSI, market cap and rank. What was missing is keeping the SERIES rather than only
today's snapshot.

Colab could not even reach mfapi.in. Yahoo is reachable from this runner, and the pipeline
already proves it - it fetches ^NSEI, gold, crude and crypto here every night.

NAMING
fetch_yahoo.py sanitises symbols: BTC-USD becomes BTC_USD.parquet. This tries the obvious
variants so a naming change does not silently produce an empty file.

HONEST LIMITS
Crypto trades 24/7, so a "month" here is a calendar month, not 21 sessions like equities.
That is correct for crypto but means these bars are not directly comparable to a stock's.
"""
import json, os, sys
from datetime import datetime, timezone

CRYPTO = "docs/crypto.json"
YAHOO = "data/yahoo"
OUT = "docs/crypto_history.json"
MAX_COINS = 120


def safe(sym):
    return "".join(ch if ch.isalnum() else "_" for ch in sym).strip("_")


def main():
    import pandas as pd

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "series": {}, "note": ""}

    if not os.path.exists(CRYPTO):
        out["note"] = "No crypto.json on disk."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("crypto history: skipped (no crypto.json)")
        return 0

    coins = json.load(open(CRYPTO)).get("rows") or []
    print("  %d coins listed" % len(coins))
    if not coins:
        out["note"] = "crypto.json has no rows."
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        return 0

    # every yahoo file we have, keyed by its sanitised stem
    have = {}
    if os.path.isdir(YAHOO):
        for f in os.listdir(YAHOO):
            if f.endswith(".parquet"):
                have[f[:-8]] = os.path.join(YAHOO, f)
    print("  yahoo files on disk: %d" % len(have))

    series = {}
    used = 0
    for c in coins[:MAX_COINS]:
        sym = str(c.get("symbol") or "").strip()
        if not sym:
            continue
        # try the forms fetch_yahoo might have written
        for cand in (safe(sym + "-USD"), safe(sym + "USD"), safe(sym),
                     safe(sym + "-INR"), sym):
            path = have.get(cand)
            if not path:
                continue
            try:
                df = pd.read_parquet(path)
            except Exception:
                continue
            dcol = next((x for x in ("date", "Date", "index", "ts") if x in df.columns), None)
            ccol = next((x for x in ("close", "Close", "adj_close") if x in df.columns), None)
            if not dcol or not ccol:
                continue
            df = df[[dcol, ccol]].dropna()
            if df.empty:
                continue
            # month-end close: sort, then take the last row of each YYYY-MM
            df = df.copy()
            df["ym"] = df[dcol].astype(str).str[:7]
            df = df.sort_values(dcol).groupby("ym", as_index=False).last()
            # zip, not itertuples: itertuples is positional, so r[ccol] raises TypeError
            # when ccol is a column name rather than an integer index.
            pts = []
            for ym, val in zip(df["ym"], df[ccol]):
                try:
                    v = float(val)
                except (TypeError, ValueError):
                    continue
                if v == v and v > 0:
                    pts.append([str(ym), round(v, 2)])
            if len(pts) >= 3:
                series[sym] = pts
                used += 1
            break

    out["series"] = series
    out["count"] = used
    months = sorted({ym for v in series.values() for ym, _ in v})
    out["from"], out["to"] = (months[0], months[-1]) if months else (None, None)
    out["note"] = ("Month-end closes for the coins we hold Yahoo history for. Crypto trades "
                   "24/7, so a month here is a calendar month, not 21 sessions like equities - "
                   "these bars are not directly comparable to a stock's.")
    out["cautions"] = {
        "coverage": "Only coins with a Yahoo history file are included, not all 82 listed.",
        "cadence": "Calendar months, 24/7 market. Not comparable to equity monthly bars.",
        "usd": "Prices are in USD where the Yahoo ticker is a USD pair.",
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB  |  %d coins, %d months (%s to %s)"
          % (OUT, os.path.getsize(OUT) / 1024, used, len(months),
             out["from"], out["to"]))
    if used == 0:
        print("::warning title=No crypto history::no matching Yahoo files in data/yahoo")
    for sym in ("BTC", "ETH"):
        if sym in series:
            p = series[sym]
            print("   %-5s %d months, %s %.2f -> %s %.2f"
                  % (sym, len(p), p[0][0], p[0][1], p[-1][0], p[-1][1]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
