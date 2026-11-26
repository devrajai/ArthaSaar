#!/usr/bin/env python3
"""
build_crypto_fundamentals.py - supply, dilution and range data for coins.

crypto.json carries price, market cap, 24h volume, RSI, trend, ATR and rank. It does not carry
supply, so the page could not answer the two questions that matter most for a coin: how much of
it can still be created, and what would it be worth if all of it were.

yfinance reports circulatingSupply, maxSupply, totalSupply, 52-week high and low, average volume
and 24h volume. That is enough to compute fully diluted valuation, the share already issued, and
turnover - which is what separates a liquid coin from a thin one.

A maxSupply of zero or null is real information: an unlimited-supply token can be minted without
limit, which is the opposite of a capped one.

Usage
-----
  python scripts/build_crypto_fundamentals.py
  python scripts/build_crypto_fundamentals.py --limit 60

Output: docs/crypto_fundamentals.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OUT = "docs/crypto_fundamentals.json"
CRYPTO = "docs/crypto.json"

FIELDS = ("marketCap", "circulatingSupply", "maxSupply", "totalSupply",
          "fiftyTwoWeekHigh", "fiftyTwoWeekLow", "averageVolume", "volume24Hr")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--limit", type=int, default=60)
    ap.add_argument("--sleep", type=float, default=0.2)
    args = ap.parse_args()

    try:
        import yfinance as yf
    except Exception:
        print("yfinance unavailable - skipping")
        return 0

    try:
        d = json.loads(Path(CRYPTO).read_text())
        rows = d.get("rows") or []
    except Exception:
        print("crypto.json unreadable - skipping")
        return 0

    rows = sorted(rows, key=lambda r: -(r.get("mcap") or 0))[: args.limit]
    print(f"fetching supply and range data for {len(rows)} coin(s)")

    out, failed = {}, []
    for i, r in enumerate(rows, 1):
        sym = (r.get("symbol") or "").upper()
        if not sym:
            continue
        try:
            info = yf.Ticker(sym + "-USD").info or {}
            rec = {k: info.get(k) for k in FIELDS}
            price = r.get("close")
            maxs, circ = rec.get("maxSupply"), rec.get("circulatingSupply")

            # fully diluted valuation: what it would be worth if the maximum supply existed
            if price and maxs:
                rec["fdv"] = round(price * maxs, 0)
                if rec.get("marketCap"):
                    rec["mcap_fdv_ratio"] = round(rec["marketCap"] / rec["fdv"] * 100, 2)
            # how much of the cap is already issued
            if circ and maxs:
                rec["pct_issued"] = round(circ / maxs * 100, 2)
            elif maxs in (0, None):
                rec["unlimited_supply"] = True

            vol = r.get("volume_24h")
            if vol and rec.get("averageVolume"):
                rec["volume_vs_avg"] = round(vol / rec["averageVolume"] * 100, 1)
            if vol and r.get("mcap"):
                rec["turnover_pct"] = round(vol / r["mcap"] * 100, 2)

            out[sym] = {k: v for k, v in rec.items() if v is not None}
        except Exception as e:
            failed.append(sym)
            if len(failed) <= 4:
                print(f"  {sym:10s} FAILED ({type(e).__name__})")
        import time as _t; _t.sleep(args.sleep)
        if i % 20 == 0:
            print(f"  {i}/{len(rows)} kept {len(out)}")

    if not out:
        print("nothing fetched - leaving the existing file alone")
        return 0

    Path(args.out).write_text(json.dumps({
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(out),
        "note": ("Supply, 52-week range and turnover from Yahoo Finance via yfinance. FDV is "
                 "price times maximum supply - what the coin would be worth if every token that "
                 "can ever exist existed. A null or zero maximum supply means the token is "
                 "uncapped, which is information rather than a missing value. CoinGecko, which "
                 "would carry more, is not reachable from this pipeline."),
        "failed": failed[:30],
        "coins": out,
    }, separators=(",", ":"), ensure_ascii=False))
    print(f"\n-> {args.out}  {Path(args.out).stat().st_size/1024:.0f} KB | {len(out)} coins")
    return 0


if __name__ == "__main__":
    sys.exit(main())
