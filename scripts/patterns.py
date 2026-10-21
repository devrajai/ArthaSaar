#!/usr/bin/env python3
"""
patterns.py - detect chart patterns numerically on the candle archive.

Implements the detection rules from the "Chart Patterns" reference doc, so patterns are
found by rule rather than by eye. Every detector returns the most recent occurrence
within a lookback window, or None.

Detectors: double_top, double_bottom, head_shoulders, bull_flag, triangle,
           hammer, shooting_star, bullish_engulfing, bearish_engulfing

Honest note: these are shape heuristics with thresholds chosen by hand. They will fire
on things you would not call a pattern. Treat output as candidates to inspect, and
measure any rule you trade on with backtest.py before trusting it.

Usage
-----
  python scripts/patterns.py --all
  python scripts/patterns.py --symbol RELIANCE --lookback 120
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from _archive import pick_candles  # noqa: E402


def _pivots(high: pd.Series, low: pd.Series, k: int = 5):
    """Local highs/lows: a bar that is the extreme of the surrounding k bars."""
    n = len(high)
    ph, pl = [], []
    for i in range(k, n - k):
        win_h = high.iloc[i - k:i + k + 1]
        win_l = low.iloc[i - k:i + k + 1]
        if high.iloc[i] == win_h.max():
            ph.append(i)
        if low.iloc[i] == win_l.min():
            pl.append(i)
    return ph, pl


def double_top(g: pd.DataFrame, tol: float = 0.015, trough: float = 0.03) -> dict | None:
    ph, _ = _pivots(g["high"], g["low"])
    if len(ph) < 2:
        return None
    for a, b in zip(ph[-4:], ph[-3:]):
        if a >= b:
            continue
        if abs(g["high"].iloc[a] - g["high"].iloc[b]) / g["high"].iloc[a] <= tol:
            between = g["low"].iloc[a:b + 1].min()
            if (g["high"].iloc[a] - between) / g["high"].iloc[a] >= trough:
                return {"pattern": "double_top", "first": int(a), "second": int(b),
                        "neckline": round(float(between), 2), "bias": "bearish"}
    return None


def double_bottom(g: pd.DataFrame, tol: float = 0.015, peak: float = 0.03) -> dict | None:
    _, pl = _pivots(g["high"], g["low"])
    if len(pl) < 2:
        return None
    for a, b in zip(pl[-4:], pl[-3:]):
        if a >= b:
            continue
        if abs(g["low"].iloc[a] - g["low"].iloc[b]) / g["low"].iloc[a] <= tol:
            between = g["high"].iloc[a:b + 1].max()
            if (between - g["low"].iloc[a]) / g["low"].iloc[a] >= peak:
                return {"pattern": "double_bottom", "first": int(a), "second": int(b),
                        "neckline": round(float(between), 2), "bias": "bullish"}
    return None


def head_shoulders(g: pd.DataFrame, tol: float = 0.03) -> dict | None:
    ph, _ = _pivots(g["high"], g["low"])
    if len(ph) < 3:
        return None
    a, b, c = ph[-3], ph[-2], ph[-1]
    ha, hb, hc = g["high"].iloc[a], g["high"].iloc[b], g["high"].iloc[c]
    if hb > ha * (1 + 0.02) and hb > hc * (1 + 0.02) and abs(ha - hc) / ha <= tol:
        neck = min(g["low"].iloc[a:b + 1].min(), g["low"].iloc[b:c + 1].min())
        return {"pattern": "head_shoulders", "first": int(a), "second": int(b), "third": int(c),
                "neckline": round(float(neck), 2), "bias": "bearish"}
    return None


def bull_flag(g: pd.DataFrame, pole: float = 0.05, bars: int = 10) -> dict | None:
    if len(g) < bars * 3:
        return None
    for start in range(len(g) - bars * 3, len(g) - bars * 2):
        seg = g["close"].iloc[start:start + bars]
        move = seg.iloc[-1] / seg.iloc[0] - 1
        if move >= pole:
            flag = g["close"].iloc[start + bars:start + 2 * bars]
            if len(flag) < 3:
                continue
            drift = flag.iloc[-1] / flag.iloc[0] - 1
            rng = (flag.max() - flag.min()) / flag.mean()
            if drift <= 0.02 and rng < abs(move):
                return {"pattern": "bull_flag", "at": int(start + 2 * bars),
                        "pole_pct": round(float(move * 100), 1), "bias": "bullish"}
    return None


def triangle(g: pd.DataFrame, n: int = 15, shrink: float = 0.6) -> dict | None:
    if len(g) < n:
        return None
    seg = g.iloc[-n:]
    hh, ll = seg["high"].max(), seg["low"].min()
    first_rng = (seg["high"].iloc[:n // 2].max() - seg["low"].iloc[:n // 2].min())
    last_rng = (seg["high"].iloc[n // 2:].max() - seg["low"].iloc[n // 2:].min())
    if first_rng > 0 and last_rng / first_rng <= shrink:
        return {"pattern": "triangle", "range_pct": round(float((hh - ll) / seg["close"].iloc[-1] * 100), 1),
                "bias": "neutral"}
    return None


def _candle(prev, cur):
    o, c, h, l = cur["open"], cur["close"], cur["high"], cur["low"]
    body = abs(c - o)
    rng = max(h - l, 1e-9)
    upper = h - max(o, c)
    lower = min(o, c) - l
    return body, rng, upper, lower


def hammer(g: pd.DataFrame) -> dict | None:
    if len(g) < 2:
        return None
    cur = g.iloc[-1]
    body, rng, upper, lower = _candle(g.iloc[-2], cur)
    if body <= rng * 0.35 and lower >= 2 * max(body, 1e-9) and upper <= rng * 0.2:
        return {"pattern": "hammer", "bias": "bullish"}
    return None


def shooting_star(g: pd.DataFrame) -> dict | None:
    if len(g) < 2:
        return None
    cur = g.iloc[-1]
    body, rng, upper, lower = _candle(g.iloc[-2], cur)
    if body <= rng * 0.35 and upper >= 2 * max(body, 1e-9) and lower <= rng * 0.2:
        return {"pattern": "shooting_star", "bias": "bearish"}
    return None


def engulfing(g: pd.DataFrame) -> dict | None:
    if len(g) < 2:
        return None
    p, cur = g.iloc[-2], g.iloc[-1]
    if cur["close"] > cur["open"] and p["close"] < p["open"] \
            and cur["open"] <= p["close"] and cur["close"] >= p["open"]:
        return {"pattern": "bullish_engulfing", "bias": "bullish"}
    if cur["close"] < cur["open"] and p["close"] > p["open"] \
            and cur["open"] >= p["close"] and cur["close"] <= p["open"]:
        return {"pattern": "bearish_engulfing", "bias": "bearish"}
    return None


DETECTORS = [double_top, double_bottom, head_shoulders, bull_flag, triangle,
             hammer, shooting_star, engulfing]


def detect(g: pd.DataFrame) -> list[dict]:
    out = []
    for fn in DETECTORS:
        try:
            r = fn(g)
        except Exception:
            r = None
        if r:
            out.append(r)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Numeric chart-pattern detection.")
    ap.add_argument("--in", dest="infile", default="")
    ap.add_argument("--symbol", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--lookback", type=int, default=120)
    ap.add_argument("--min-history", type=int, default=60)
    ap.add_argument("--out", default="data/patterns")
    args = ap.parse_args()

    src = args.infile
    if not src:
        src = pick_candles()
    if not src or not Path(src).exists():
        print("no candle archive found - skipping")
        return 0
    df = pd.read_parquet(src)
    sortcol = "date" if "date" in df.columns else "ts"
    symbols = [args.symbol] if args.symbol else sorted(df["symbol"].unique())

    found = []
    for sym in symbols:
        g = df[df["symbol"] == sym].sort_values(sortcol)
        if len(g) < args.min_history:
            continue
        for r in detect(g.tail(args.lookback)):
            found.append({"symbol": sym, "as_of": str(g[sortcol].iloc[-1]), **r})

    if not found:
        print(f"no patterns detected across {len(symbols)} symbol(s)")
        return 0
    res = pd.DataFrame(found).sort_values(["pattern", "symbol"])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    res.to_csv(out / "detected.csv", index=False)
    print(f"detected {len(res)} pattern(s) across {res['symbol'].nunique()} symbols")
    print(res["pattern"].value_counts().to_string())
    print(f"\nWrote {out}/detected.csv")
    print("  candidates to inspect - measure any rule you trade on with backtest.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
