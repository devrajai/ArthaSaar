#!/usr/bin/env python3
"""
build_screener.py - the numbers behind the screener filters.

Turns the per-stock series into the things a trader actually screens on:
  * how many days in a row it fell, and by how much
  * the move over the last 1 / 2 / 3 / 5 / 20 sessions
  * how far it sits from its 52-week high and low
  * RSI, MACD histogram, ADX, ATR%, volume versus its own average
  * a simple trend read

It also emits named preset screens so one tap gives a useful list instead of making
you rebuild the filter every time.

Where the numbers come from: docs/stocks.json (built by build_stock_pages.py from
Yahoo daily candles). Only stocks that have been deepened appear here - the full
2,600-symbol list carries today's snapshot only, because a fall over 5 days cannot be
computed without history. Coverage grows every run.

Output: docs/screener.json
  {"updated","count","rows":[{...}],"presets":[{id,label,note,test}]}

Usage:
  python scripts/build_screener.py
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load(p: str):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def pct_change(series: list[float], n: int):
    """Change over the last n sessions, in percent."""
    if len(series) < n + 1 or not series[-n - 1]:
        return None
    return round((series[-1] / series[-n - 1] - 1) * 100, 2)


def down_streak(series: list[float]) -> int:
    """How many consecutive sessions closed lower."""
    n = 0
    for i in range(len(series) - 1, 0, -1):
        if series[i] < series[i - 1]:
            n += 1
        else:
            break
    return n


def up_streak(series: list[float]) -> int:
    n = 0
    for i in range(len(series) - 1, 0, -1):
        if series[i] > series[i - 1]:
            n += 1
        else:
            break
    return n


def main() -> int:
    ap = argparse.ArgumentParser(description="Screener metrics + preset screens.")
    ap.add_argument("--stocks", default="docs/stocks.json")
    ap.add_argument("--out", default="docs/screener.json")
    args = ap.parse_args()

    s = load(args.stocks) or {}
    stocks = s.get("stocks") or {}
    if not stocks:
        print(f"no stock pages at {args.stocks} - run build_stock_pages.py first")
        return 0

    rows = []
    for key, r in stocks.items():
        series = r.get("series") or []
        t = r.get("tech") or {}
        if len(series) < 6:
            continue
        close = series[-1]
        hi, lo = t.get("high_52w"), t.get("low_52w")
        rows.append({
            "symbol": r.get("symbol"), "name": (r.get("name") or "")[:28],
            "close": close,
            "chg_1d": pct_change(series, 1), "chg_2d": pct_change(series, 2),
            "chg_3d": pct_change(series, 3), "chg_5d": pct_change(series, 5),
            "chg_20d": pct_change(series, 20),
            "down_streak": down_streak(series), "up_streak": up_streak(series),
            "from_52w_high": (round((close / hi - 1) * 100, 2) if hi else None),
            "above_52w_low": (round((close / lo - 1) * 100, 2) if lo else None),
            "rsi": t.get("rsi_14"), "adx": t.get("adx"), "atr_pct": t.get("atr_pct"),
            "macd_hist": t.get("macd_hist"), "vol_x": t.get("vol_x"),
            "trend": t.get("trend"), "sma_50": t.get("sma_50"), "sma_200": t.get("sma_200"),
        })

    # ---- named screens, so one tap is enough ----
    def has(v):
        return v is not None
    presets = [
        {"id": "falling", "label": "Falling hard",
         "note": "Down 3 sessions in a row and at least 3% over 5 days",
         "test": "r.down_streak>=3 && has(r.chg_5d) && r.chg_5d<=-3"},
        {"id": "falling5", "label": "Down 5 days",
         "note": "Five consecutive lower closes",
         "test": "r.down_streak>=5"},
        {"id": "drop2", "label": "Down 2%+ today", "note": "Sharp single-day fall",
         "test": "has(r.chg_1d) && r.chg_1d<=-2"},
        {"id": "drop5", "label": "Down 5%+ in a week", "note": "Weekly fall of 5% or more",
         "test": "has(r.chg_5d) && r.chg_5d<=-5"},
        {"id": "rising", "label": "Rising steadily", "note": "Up 3 in a row",
         "test": "r.up_streak>=3"},
        {"id": "nearlow", "label": "Near 52-week low", "note": "Within 5% of the year's low",
         "test": "has(r.above_52w_low) && r.above_52w_low<=5"},
        {"id": "nearhigh", "label": "Near 52-week high", "note": "Within 5% of the year's high",
         "test": "has(r.from_52w_high) && r.from_52w_high>=-5"},
        {"id": "oversold", "label": "RSI oversold", "note": "RSI under 30",
         "test": "has(r.rsi) && r.rsi<30"},
        {"id": "overbought", "label": "RSI overbought", "note": "RSI over 70",
         "test": "has(r.rsi) && r.rsi>70"},
        {"id": "volspike", "label": "Volume spike", "note": "Traded 2x its own 20-day average",
         "test": "has(r.vol_x) && r.vol_x>=2"},
        {"id": "macdbull", "label": "MACD turning up", "note": "Positive MACD histogram",
         "test": "has(r.macd_hist) && r.macd_hist>0"},
        {"id": "strongup", "label": "Strong uptrend", "note": "Trend up and ADX above 25",
         "test": "r.trend==='up' && has(r.adx) && r.adx>25"},
        {"id": "strongdown", "label": "Strong downtrend", "note": "Trend down and ADX above 25",
         "test": "r.trend==='down' && has(r.adx) && r.adx>25"},
    ]

    rows.sort(key=lambda r: (r.get("chg_5d") if r.get("chg_5d") is not None else 0))
    payload = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "count": len(rows), "rows": rows, "presets": presets}
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest}  ({dest.stat().st_size / 1e3:.0f} KB)  |  {len(rows)} stocks, "
          f"{len(presets)} preset screens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
