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

def sensex_guard(items):
    """Yahoo sometimes serves a stale ^BSESN snapshot that overwrites a fresh
    close with an older price (seen 25-26 Sep 2026: Friday close 73,895.74 got
    replaced by 73,580.54 at night). Cross-check SENSEX change against NIFTY 50
    (NSE source, reliable): if they diverge >1.5pp and the previously stored
    value IS consistent, keep the stored one."""
    try:
        old = json.loads((DATA / "global.json").read_text())
        prev_sx = next((i for i in old.get("items", []) if i.get("name") == "SENSEX"), None)
    except Exception:
        prev_sx = None
    try:
        ia = json.loads((DATA / "indices-all.json").read_text())
        nif = next((i for i in ia.get("indices", []) if i.get("index") == "NIFTY 50"), None)
        nif_chg = float(nif.get("change_pct")) if nif and nif.get("change_pct") is not None else None
    except Exception:
        nif_chg = None
    if nif_chg is None:
        return items
    for it in items:
        if it.get("name") != "SENSEX" or it.get("chg_pct") is None:
            continue
        if abs(it["chg_pct"] - nif_chg) <= 1.5:
            continue  # consistent with the broad market — accept
        if (prev_sx and prev_sx.get("as_of") == it.get("as_of")
                and prev_sx.get("chg_pct") is not None
                and abs(prev_sx["chg_pct"] - nif_chg) <= 1.5):
            print(f"SENSEX guard: yahoo {it['price']} ({it['chg_pct']:+.2f}%) diverges "
                  f"from NIFTY {nif_chg:+.2f}% — keeping previous {prev_sx['price']}")
            it.update(prev_sx)
        else:
            print(f"SENSEX warning: {it['price']} ({it['chg_pct']:+.2f}%) diverges from "
                  f"NIFTY {nif_chg:+.2f}% — no consistent previous value, accepting")
    return items

def main():
    items = sensex_guard(collect())
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
