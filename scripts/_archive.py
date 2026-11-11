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


def last_date(path: str) -> str:
    """The newest date in one archive, or '' if it cannot be read. One column, so it is cheap."""
    try:
        import pyarrow.parquet as pq
        col = pq.read_table(path, columns=["date"]).column("date").to_pylist()
    except Exception:
        return ""
    if not col:
        return ""
    return max(str(v) for v in col)


def pick_candles(prefer_adjusted: bool = True) -> str:
    """Return the archive with the MOST RECENT data, or '' if none exists.

    THIS USED TO RETURN THE FIRST FILE THAT EXISTED, in a fixed order with
    daily_adj.parquet first. That file is restored from a Google Drive backup which stopped
    updating on 23 October, so it won every single time - and the entire technical layer
    (screener, RSI, ADX, moving averages, breadth, patterns, levels, setups, ranks) froze at
    23 October while candles_from_bhavcopy kept writing fresh prices into cm_daily.parquet
    that nothing ever read. The site looked healthy and was eleven sessions stale.

    Now the newest data wins, and "adjusted" only breaks a tie. Adjustment still matters -
    it is what makes a split not look like a crash - but being current matters more.
    """
    have = [c for c in CANDIDATES if Path(c).exists()]
    if not have:
        return ""
    if not prefer_adjusted:
        have = [c for c in have if not is_adjusted(c)]
        if not have:
            return ""
    if len(have) == 1:
        return have[0]

    def rank(path: str):
        # (date, is_adjusted) - a newer date always wins; on the same date the adjusted file does
        return (last_date(path), 1 if is_adjusted(path) else 0)

    best = max(have, key=rank)
    if len(have) > 1:
        others = ", ".join(f"{Path(c).name}={last_date(c) or '?'}" for c in have if c != best)
        print(f"  archive: using {Path(best).name} ({last_date(best) or '?'}) over {others}")
    return best


def is_adjusted(path: str) -> bool:
    return bool(path) and path.endswith("_adj.parquet")


def archive_dates(src) -> list:
    """Every distinct date in the archive, oldest first. Reads ONE column, so it is cheap."""
    try:
        import pyarrow.parquet as pq
        vals = pq.read_table(src, columns=["date"]).column("date").to_pylist()
    except Exception:
        return []
    seen, out = set(), []
    for v in vals:
        t = str(v)
        if t not in seen:
            seen.add(t)
            out.append(t)
    out.sort()
    return out


def read_candles(src, window: int | None = None):
    """Read the archive, optionally only the most recent `window` trading days.

    WHY: every analysis script used to do `pd.read_parquet(src)`, which materialises the
    WHOLE archive. Fine for a few days of bhavcopy, fatal for a twenty-year one - the runner
    has about 7 GB and a 20-year, 2,000-symbol parquet runs to several gigabytes, so it would
    die before computing a single indicator. Trimming after loading does not help, the memory
    is already spent. So this reads the date column first (one column, cheap), works out the
    cutoff, then asks pyarrow to read only rows on or after it.

    window=None or <=0 reads everything - what the deep-history readers want.
    """
    import pandas as pd
    if not window or window <= 0:
        return pd.read_parquet(src)

    dates = archive_dates(src)
    if not dates:
        print("  (no date column to filter on - reading the whole archive)")
        return pd.read_parquet(src)
    if len(dates) <= window:
        print("  archive holds %d dates, within the %d-day window - reading all" % (len(dates), window))
        return pd.read_parquet(src)

    cutoff = dates[-window]
    try:
        import pyarrow.parquet as pq
        df = pq.read_table(src, filters=[("date", ">=", cutoff)]).to_pandas()
        print("  window: last %d sessions (from %s) -> %s rows of %d dates"
              % (window, cutoff, f"{len(df):,}", len(dates)))
        return df
    except Exception as e:
        print("  filter read failed (%s) - full read then trim" % type(e).__name__)
        df = pd.read_parquet(src)
        if "date" in df.columns:
            df = df[df["date"].astype(str) >= cutoff]
        return df


def add_window_arg(ap, default: int = 500):
    """Register the standard --window flag. 500 sessions is about two years."""
    ap.add_argument("--window", type=int, default=default,
                    help="most recent N trading sessions (default %d); 0 reads everything" % default)
    return ap
