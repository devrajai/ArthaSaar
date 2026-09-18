#!/usr/bin/env python3
"""
FUNDAMENTALS COLLECTOR — PE, PB, ROE, ROA, D/E, promoter-style & institutional
holdings, market cap, dividend yield, margins, growth for the full universe.

Source: yfinance (free, no key). Yahoo's fields map to screener-style data:
  trailingPE               -> P/E
  priceToBook              -> P/B
  returnOnEquity           -> ROE %
  returnOnAssets           -> ROA %
  debtToEquity             -> D/E
  heldPercentInsiders      -> promoter + promoter group (approx)
  heldPercentInstitutions  -> FII + DII + institutions (approx)
  marketCap, beta, dividendYield, profitMargins, revenueGrowth,
  earningsGrowth, freeCashflow, totalCash, totalDebt, sector, industry

Smart refresh: fundamentals change quarterly — each symbol is refreshed only
if its record is older than MAX_AGE_DAYS. Staggered: PER_RUN symbols per run,
so the full ~2,300-stock universe stays fresh across a few runs. Self-healing.

Output: data/fundamentals.json
"""
import json
import time
import datetime as dt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
FUND = DATA / "fundamentals.json"
UNIVERSE = DATA / "universe.json"

PER_RUN = 300          # symbols per run (rate-limit friendly)
MAX_AGE_DAYS = 10     # refresh each symbol at most every 10 days

FIELDS = [
    "trailingPE", "priceToBook", "returnOnEquity", "returnOnAssets",
    "debtToEquity", "heldPercentInsiders", "heldPercentInstitutions",
    "marketCap", "beta", "dividendYield", "profitMargins",
    "revenueGrowth", "earningsGrowth", "freeCashflow", "totalCash",
    "totalDebt", "sector", "industry",
]


def main():
    try:
        import yfinance as yf
    except ImportError:
        print("yfinance not installed — run: pip install yfinance")
        return

    if not UNIVERSE.exists():
        print("No universe yet — run brain_collect.py first")
        return
    uni = json.loads(UNIVERSE.read_text(encoding="utf-8"))
    fund = {}
    if FUND.exists():
        try:
            fund = json.loads(FUND.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            fund = {}

    now = dt.datetime.now(dt.timezone.utc)
    done, skipped, failed = 0, 0, 0
    for m in uni:
        sym = m["symbol"]
        rec = fund.get(sym)
        if rec and "_updated" in rec:
            try:
                age = (now - dt.datetime.fromisoformat(rec["_updated"])).days
                if age < MAX_AGE_DAYS:
                    skipped += 1
                    continue
            except Exception:  # noqa: BLE001
                pass
        if done >= PER_RUN:
            break
        try:
            info = yf.Ticker(f"{sym}.NS").info or {}
            rec = {"_updated": now.isoformat()}
            for k in FIELDS:
                v = info.get(k)
                if isinstance(v, float):
                    v = round(v, 4)
                rec[k] = v
            fund[sym] = rec
            done += 1
        except Exception:  # noqa: BLE001
            failed += 1
        time.sleep(0.7)

    FUND.parent.mkdir(parents=True, exist_ok=True)
    FUND.write_text(json.dumps(fund, ensure_ascii=False), encoding="utf-8")
    print(f"fundamentals: updated {done} | fresh-skipped {skipped} | "
          f"failed {failed} | coverage {len(fund)}/{len(uni)}")


if __name__ == "__main__":
    main()
