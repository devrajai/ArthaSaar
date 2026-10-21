"""
_archive.py - one place that decides WHICH candle archive to read.

Corporate-action adjustment produces `<name>_adj.parquet` alongside the raw archive.
Adjusted prices are always the right input for indicators, forecasts, backtests and
patterns - the raw archive is only right for looking at the literal printed price.

So every consumer calls `pick_candles()`, which prefers the adjusted file when it
exists and falls back to the raw one. That way the adjustment is actually USED, instead
of being produced and then ignored.
"""

from __future__ import annotations

from pathlib import Path

# order matters: adjusted first, then raw
CANDIDATES = [
    "data/candles/daily_adj.parquet",
    "data/candles/cm_daily_adj.parquet",
    "data/candles/daily.parquet",
    "data/candles/cm_daily.parquet",
]


def pick_candles(prefer_adjusted: bool = True) -> str:
    """Return the best available candle archive path, or '' if none exists."""
    order = CANDIDATES if prefer_adjusted else CANDIDATES[2:]
    for c in order:
        if Path(c).exists():
            return c
    return ""


def is_adjusted(path: str) -> bool:
    return bool(path) and path.endswith("_adj.parquet")
