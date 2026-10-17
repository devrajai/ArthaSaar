#!/usr/bin/env python3
"""
fetch_bhavcopy.py - download NSE EOD bhavcopy into a local archive (Parquet + CSV).

Usage
-----
  # the most recent trading day (walks back from today, skipping holidays/weekends)
  python scripts/fetch_bhavcopy.py --latest

  # one specific day
  python scripts/fetch_bhavcopy.py --date 2026-10-16

  # a range (backfill) - non-trading days are skipped automatically
  python scripts/fetch_bhavcopy.py --start 2024-01-01 --end 2026-10-16

  # last 30 calendar days
  python scripts/fetch_bhavcopy.py --days 30

  # equities only / F&O only
  python scripts/fetch_bhavcopy.py --latest --segments cm

Outputs (under --outdir, default ./data):
  raw/<segment>/<segment>_<YYYY-MM-DD>.csv.zip     original file, untouched
  parquet/<segment>/<segment>_<YYYY-MM-DD>.parquet  normalised, columnar (backtesting)
  csv/<segment>/<segment>_<YYYY-MM-DD>.csv          normalised, human/Sheets friendly
  manifest.csv                                      index of everything archived

This only downloads. It never redistributes. See README for the legal note.
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
from nse_source import NotATradingDay, build_source, download, fetch_day, parse  # noqa: E402

MANIFEST_COLS = ["date", "segment", "rows", "symbols", "era", "file_parquet", "file_csv"]


def _write(frames: dict[str, pd.DataFrame], d: date, outdir: Path, formats, raws: dict[str, bytes]):
    written = []
    for seg, df in frames.items():
        base = f"{seg}_{d.isoformat()}"
        (outdir / "raw" / seg).mkdir(parents=True, exist_ok=True)
        if seg in raws:
            (outdir / "raw" / seg / f"{base}.csv.zip").write_bytes(raws[seg])
        fp = fc = ""
        if "parquet" in formats:
            p = outdir / "parquet" / seg
            p.mkdir(parents=True, exist_ok=True)
            fp = str(p / f"{base}.parquet")
            df.to_parquet(fp, index=False)
        if "csv" in formats:
            p = outdir / "csv" / seg
            p.mkdir(parents=True, exist_ok=True)
            fc = str(p / f"{base}.csv")
            df.to_csv(fc, index=False)
        written.append({
            "date": d.isoformat(), "segment": seg, "rows": len(df),
            "symbols": df["symbol"].nunique(),
            "era": build_source(seg, d).era,
            "file_parquet": fp, "file_csv": fc,
        })
        print(f"  {d} {seg:>2}: {len(df):>6} rows, {df['symbol'].nunique():>5} symbols")
    return written


def _update_manifest(outdir: Path, rows: list[dict]):
    path = outdir / "manifest.csv"
    new = pd.DataFrame(rows, columns=MANIFEST_COLS)
    if path.exists():
        old = pd.read_csv(path, dtype=str)
        new = pd.concat([old, new], ignore_index=True)
    new = new.drop_duplicates(subset=["date", "segment"], keep="last")
    new = new.sort_values(["date", "segment"]).reset_index(drop=True)
    new.to_csv(path, index=False)


def _iter_dates(args) -> list[date]:
    if args.date:
        return [date.fromisoformat(args.date)]
    if args.start and args.end:
        s, e = date.fromisoformat(args.start), date.fromisoformat(args.end)
        return [s + timedelta(days=i) for i in range((e - s).days + 1)]
    if args.days:
        today = date.today()
        return [today - timedelta(days=i) for i in range(args.days)]
    if args.latest:
        today = date.today()
        return [today - timedelta(days=i) for i in range(10)]  # walk back to last trading day
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description="Download NSE EOD bhavcopy into a local archive.")
    g = ap.add_mutually_exclusive_group(required=False)
    g.add_argument("--date")
    g.add_argument("--days", type=int)
    g.add_argument("--latest", action="store_true")
    ap.add_argument("--start")
    ap.add_argument("--end")
    ap.add_argument("--segments", default="cm,fo", help="comma list: cm,fo (default both)")
    ap.add_argument("--outdir", default="data")
    ap.add_argument("--formats", default="parquet,csv")
    args = ap.parse_args()

    if (args.start or args.end) and not (args.start and args.end):
        ap.error("--start and --end must be given together")
    if not (args.date or args.days or args.latest or (args.start and args.end)):
        ap.error("give one of: --latest | --date YYYY-MM-DD | --days N | --start YYYY-MM-DD --end YYYY-MM-DD")

    outdir = Path(args.outdir)
    segments = tuple(s.strip().lower() for s in args.segments.split(",") if s.strip())
    formats = tuple(f.strip().lower() for f in args.formats.split(",") if f.strip())

    dates = _iter_dates(args)

    print(f"Archive -> {outdir.resolve()}  |  segments={segments}  formats={formats}")
    manifest_rows: list[dict] = []
    got_any = False

    for d in dates:
        try:
            raws: dict[str, bytes] = {}
            frames: dict[str, pd.DataFrame] = {}
            for seg in segments:
                src = build_source(seg, d)
                try:
                    raw = download(src)
                except NotATradingDay:
                    continue
                raws[seg] = raw
                frames[seg] = parse(raw, seg, src, d)
            if not frames:
                raise NotATradingDay(d.isoformat())
        except NotATradingDay:
            if args.latest and not got_any:
                continue  # walk back
            print(f"  {d}: no trading data (skipped)")
            continue
        except Exception as exc:  # noqa: BLE001
            print(f"  {d}: ERROR {type(exc).__name__}: {exc}")
            continue

        manifest_rows += _write(frames, d, outdir, formats, raws)
        got_any = True
        if args.latest:
            break  # we found the most recent trading day

    if manifest_rows:
        _update_manifest(outdir, manifest_rows)
        print(f"Done. {len(manifest_rows)} file(s) written; manifest updated.")
    else:
        print("Nothing written.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
