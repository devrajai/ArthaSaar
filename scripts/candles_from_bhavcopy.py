#!/usr/bin/env python3
"""
candles_from_bhavcopy.py - grow a candle archive from NSE's own bhavcopy.

Why this exists
---------------
The ArthaSaar candle pipeline (Yahoo via GitHub Actions) is gone, and its Drive
backup is frozen at 27 Sep 2026. But this hub already downloads the *official* NSE
end-of-day bhavcopy every day. This script turns those daily files into a growing
candle archive - and can backfill history straight from NSE - so the price feed
becomes something the hub produces itself instead of a dead dependency.

It is the same idea as candles_from_drive.py, just fed by NSE instead of Yahoo.

Usage
-----
  # ingest whatever the daily job has already archived locally
  python scripts/candles_from_bhavcopy.py --from-local

  # backfill a date range from NSE (skips weekends/holidays automatically)
  python scripts/candles_from_bhavcopy.py --backfill 2024-01-01 2024-06-30

  # both, into one archive
  python scripts/candles_from_bhavcopy.py --from-local --backfill 2024-01-01 2024-06-30

Output: data/candles/cm_daily.parquet
  columns: symbol, date, open, high, low, close, volume, series, segment
The archive is append-safe: re-running never duplicates a symbol/date.

Note: bhavcopy is the exchange's own record (free, no key). Only trading days exist.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

# Cap Arrow's thread pool. Some containers (CI, sandboxes) have a low thread limit and
# pyarrow's default pool can fail with "Failed to launch worker thread".
try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from nse_source import NotATradingDay, fetch_day  # noqa: E402

CANDLE_COLS = ["symbol", "date", "open", "high", "low", "close", "volume", "series", "segment"]
NUM = ["open", "high", "low", "close", "volume"]


def _norm(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in CANDLE_COLS:
        if c not in out.columns:
            out[c] = pd.NA
    out = out[CANDLE_COLS]
    for c in NUM:
        out[c] = pd.to_numeric(out[c], errors="coerce")
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    return out.dropna(subset=["symbol", "date", "close"])


def ingest_local(archive: pd.DataFrame, csv_dir: Path) -> pd.DataFrame:
    files = sorted(csv_dir.glob("cm_*.csv"))
    if not files:
        print(f"  no bhavcopy CSVs in {csv_dir}")
        return archive
    frames = []
    for p in files:
        try:
            frames.append(_norm(pd.read_csv(p, dtype=str)))
        except Exception as e:  # noqa: BLE001
            print(f"  skip {p.name}: {e}")
    if frames:
        print(f"  ingested {len(files)} local bhavcopy file(s)")
        archive = pd.concat([archive] + frames, ignore_index=True)
    return archive


def backfill(archive: pd.DataFrame, start: date, end: date, segments=("cm",)) -> pd.DataFrame:
    frames, got, skipped, errs = [], 0, 0, 0
    d = start
    while d <= end:
        try:
            day = fetch_day(d, segments=segments)
            for seg, df in day.items():
                frames.append(_norm(df))
            got += 1
            if got % 25 == 0:
                print(f"  ... {got} trading days fetched (up to {d})")
        except NotATradingDay:
            skipped += 1
        except Exception as e:  # noqa: BLE001
            errs += 1
            print(f"  {d}: ERROR {type(e).__name__}: {str(e)[:60]}")
        d += timedelta(days=1)
    print(f"  backfill: {got} trading days, {skipped} non-trading skipped, {errs} errors")
    if frames:
        archive = pd.concat([archive] + frames, ignore_index=True)
    return archive


def main() -> int:
    ap = argparse.ArgumentParser(description="Grow a candle archive from NSE bhavcopy.")
    ap.add_argument("--from-local", action="store_true", help="ingest data/csv/cm/*.csv")
    ap.add_argument("--backfill", nargs=2, metavar=("START", "END"), help="YYYY-MM-DD YYYY-MM-DD")
    ap.add_argument("--csv-dir", default="data/csv/cm")
    ap.add_argument("--out", default="data/candles/cm_daily.parquet")
    args = ap.parse_args()

    if not args.from_local and not args.backfill:
        ap.error("give --from-local and/or --backfill START END")

    dest = Path(args.out)
    if dest.exists():
        archive = pd.read_parquet(dest)
        print(f"existing archive: {len(archive):,} rows, "
              f"{archive['symbol'].nunique()} symbols, up to {archive['date'].max()}")
    else:
        archive = pd.DataFrame(columns=CANDLE_COLS)

    if args.from_local:
        archive = ingest_local(archive, Path(args.csv_dir))
    if args.backfill:
        s, e = date.fromisoformat(args.backfill[0]), date.fromisoformat(args.backfill[1])
        archive = backfill(archive, s, e)

    if archive.empty:
        print("Nothing to write.")
        return 0

    before = len(archive)
    archive = archive.drop_duplicates(subset=["symbol", "date"], keep="last")
    archive = archive.sort_values(["symbol", "date"]).reset_index(drop=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    archive.to_parquet(dest, index=False)

    print(f"\nWrote {dest}")
    print(f"  {len(archive):,} rows ({before - len(archive):,} duplicates dropped), "
          f"{archive['symbol'].nunique()} symbols")
    print(f"  window: {archive['date'].min()} -> {archive['date'].max()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
