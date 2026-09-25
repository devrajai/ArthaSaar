#!/usr/bin/env python3
"""Global markets collector — US indices, commodities, FX via yfinance (free, no key).
Outputs data/global.json. Runs on GitHub Actions (yfinance reachable there)."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

DATA = Path(__file__).resolve().parents[1] / "data"

# name -> yahoo symbol
SERIES = {
    "S&P 500": "^GSPC",
    "SENSEX": "^BSESN",
    "Nasdaq Composite": "^IXIC",
    "Dow Jones": "^DJI",
    "Nikkei 225": "^N225",
    "Hang Seng": "^HSI",
    "Gold (COMEX)": "GC=F",
    "Silver (COMEX)": "SI=F",
    "Crude Oil WTI": "CL=F",
    "Natural Gas": "NG=F",
    "USD-INR": "USDINR=X",
    "Dollar Index (DXY)": "DX-Y.NYB",
    "US 10Y Yield": "^TNX",
    "Copper": "HG=F",
}

def collect():
    items = []
    for name, sym in SERIES.items():
        try:
            t = yf.Ticker(sym)
            h = t.history(period="1y", interval="1d", auto_adjust=False)
            if h is None or len(h) < 5:
                print(f"skip {sym}: no history")
                continue
            close = h["Close"].dropna()
            price = float(close.iloc[-1])
            prev = float(close.iloc[-2]) if len(close) >= 2 else price
            chg = round((price - prev) / prev * 100, 2) if prev else None
            items.append({
                "name": name,
                "symbol": sym,
                "price": round(price, 2),
                "chg_pct": chg,
                "high_52w": round(float(close.max()), 2),
                "low_52w": round(float(close.min()), 2),
                "as_of": str(h.index[-1].date()),
            })
            print(f"ok {name:22s} {price:>12,.2f}  {chg:+.2f}%")
        except Exception as e:
            print(f"FAIL {name} ({sym}): {e}")
    return items

def main():
    items = collect()
    out = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "items": items,
        "note": "Global context: US/global indices, commodities, FX via Yahoo (free). "
                "Commodities are futures prices in USD; US 10Y yield in %.",
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "global.json").write_text(json.dumps(out, indent=1))
    print(f"\nwrote data/global.json — {len(items)}/{len(SERIES)} series")
    if len(items) < len(SERIES) // 2:
        print("ERROR: too many failures", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
