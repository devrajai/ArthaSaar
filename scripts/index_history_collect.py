#!/usr/bin/env python3
"""Index history — yfinance monthly closes, 25 years (free, no key).
Computes monthly and yearly % returns for NIFTY 50, BANK NIFTY, SENSEX.
Output: data/index-history.json — feeds the Studies year x month heatmap.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

DATA = Path(__file__).resolve().parents[1] / "data"
INDICES = [
    ("nifty", "^NSEI", "NIFTY 50"),
    ("banknifty", "^NSEBANK", "BANK NIFTY"),
    ("sensex", "^BSESN", "SENSEX"),
]

def main():
    out = {"updated": datetime.now(timezone.utc).isoformat(), "indices": []}
    import time
    for key, sym, name in INDICES:
        h = None
        for attempt in range(5):  # yahoo rate-limits, retry with backoff
            try:
                h = yf.Ticker(sym).history(period="25y", interval="1mo", auto_adjust=True)
                if not h.empty:
                    break
            except Exception as e:  # noqa: BLE001
                print("retry", key, attempt, str(e)[:50])
            time.sleep(20)
        try:
            if h is None or h.empty:
                raise RuntimeError("empty history for " + sym)
            months = {}   # {year: {mm: ret}}
            yearly = {}   # {year: ret}
            prev_close = None
            prev_year = None
            first_c = None   # close of first month seen in current year
            last_c = None    # close of last month seen in current year
            for ts, row in h.iterrows():
                y, m = ts.year, ts.month
                c = float(row["Close"])
                if prev_year is not None and y != prev_year:
                    yearly[str(prev_year)] = round((last_c / first_c - 1) * 100, 1)
                    first_c = c
                if first_c is None:
                    first_c = c
                if prev_close:
                    months.setdefault(y, {})[f"{m:02d}"] = round((c / prev_close - 1) * 100, 1)
                last_c = c
                prev_close = c
                prev_year = y
            # final year (current, partial)
            if prev_year is not None:
                yearly[str(prev_year)] = round((last_c / first_c - 1) * 100, 1)
            out["indices"].append({
                "key": key, "name": name,
                "years": {str(y): months[y] for y in sorted(months)},
                "yearly": yearly,
                "first": h.index[0].strftime("%b %Y"),
            })
            print(f"ok {key}: {len(months)} years, {len(h)} months, from {h.index[0].date()}")
        except Exception as e:  # noqa: BLE001
            print("FAIL", key, str(e)[:80])
    (DATA / "index-history.json").write_text(json.dumps(out, separators=(",", ":")))
    print("wrote data/index-history.json with", len(out["indices"]), "indices")

if __name__ == "__main__":
    main()
