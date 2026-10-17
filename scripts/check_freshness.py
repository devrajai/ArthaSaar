#!/usr/bin/env python3
"""
check_freshness.py - the watchdog. Fails loudly when the data goes stale.

The point: a daily job that breaks goes silent, not red. Scheduled workflows on a
public repo are disabled after 60 days with no activity, and a quiet gap looks
identical to a healthy hub. This checks that each feed has produced something recent
and exits non-zero if not, so a workflow can open an issue and tell you.

Signals checked (whatever exists):
  data/manifest.csv            bhavcopy archive - newest date
  data/youtube/videos.csv      YouTube poll    - newest published
  data/candles/cm_daily.parquet NSE candle archive - newest date

Usage
-----
  python scripts/check_freshness.py                 # default: warn after 4 days
  python scripts/check_freshness.py --max-age 7
  python scripts/check_freshness.py --bhavcopy-max-age 5 --youtube-max-age 10
Exit codes: 0 = all fresh, 1 = something stale or missing.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd


def _age_days(datestr: str) -> int | None:
    try:
        d = pd.to_datetime(datestr, utc=True).date()
    except Exception:  # noqa: BLE001
        return None
    return (date.today() - d).days


def check_bhavcopy(root: Path) -> tuple[str, int | None, str]:
    p = root / "data" / "manifest.csv"
    if not p.exists():
        return ("bhavcopy", None, "manifest.csv missing")
    try:
        df = pd.read_csv(p, dtype=str)
        if df.empty or "date" not in df.columns:
            return ("bhavcopy", None, "manifest.csv empty")
        latest = df["date"].max()
        return ("bhavcopy", _age_days(latest), f"newest {latest}")
    except Exception as e:  # noqa: BLE001
        return ("bhavcopy", None, f"unreadable: {e}")


def check_youtube(root: Path) -> tuple[str, int | None, str]:
    p = root / "data" / "youtube" / "videos.csv"
    if not p.exists():
        return ("youtube", None, "videos.csv missing")
    try:
        df = pd.read_csv(p, dtype=str)
        if df.empty or "published" not in df.columns:
            return ("youtube", None, "videos.csv empty")
        latest = df["published"].max()[:10]
        return ("youtube", _age_days(latest), f"newest {latest}")
    except Exception as e:  # noqa: BLE001
        return ("youtube", None, f"unreadable: {e}")


def check_candles(root: Path) -> tuple[str, int | None, str]:
    p = root / "data" / "candles" / "cm_daily.parquet"
    if not p.exists():
        return ("candles", None, "cm_daily.parquet missing (optional)")
    try:
        df = pd.read_parquet(p, columns=["date"])
        latest = df["date"].max()
        return ("candles", _age_days(latest), f"newest {latest}")
    except Exception as e:  # noqa: BLE001
        return ("candles", None, f"unreadable: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Fail if the data has gone stale.")
    ap.add_argument("--max-age", type=int, default=4, help="default staleness threshold (days)")
    ap.add_argument("--bhavcopy-max-age", type=int, default=None)
    ap.add_argument("--youtube-max-age", type=int, default=None)
    ap.add_argument("--candles-max-age", type=int, default=None)
    ap.add_argument("--root", default=".")
    args = ap.parse_args()

    root = Path(args.root)
    limits = {
        "bhavcopy": args.bhavcopy_max_age if args.bhavcopy_max_age is not None else args.max_age,
        "youtube": args.youtube_max_age if args.youtube_max_age is not None else args.max_age,
        "candles": args.candles_max_age if args.candles_max_age is not None else args.max_age,
    }

    results = [check_bhavcopy(root), check_youtube(root), check_candles(root)]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"freshness check @ {now}\n")

    stale = []
    for name, age, note in results:
        limit = limits[name]
        if age is None:
            if name == "candles":  # optional feed, never fails the run
                print(f"  [skip]  {name:9s} {note}")
                continue
            print(f"  [STALE] {name:9s} {note} (missing)")
            stale.append(f"{name}: {note}")
            continue
        flag = "STALE" if age > limit else "ok"
        print(f"  [{flag:5s}] {name:9s} {note}  ({age}d old, limit {limit}d)")
        if age > limit:
            stale.append(f"{name}: {note}, {age} days old (limit {limit})")

    if stale:
        print("\nFAIL - stale or missing feeds:")
        for s in stale:
            print("  -", s)
        return 1
    print("\nOK - all feeds fresh.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
