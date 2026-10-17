#!/usr/bin/env python3
"""
candles_from_drive.py - restore the ArthaSaar candle archive from Google Drive.

Why this exists
---------------
The GitHub source (devrajai/ArthaSaar) returns 404 as of Oct 2026 - repo, raw files
and the `candles` release tag are all gone. The surviving copy is the **ArthaSaar
Backup** folder in Google Drive (27 Sep 2026):

  daily-00..21.json.gz : all NSE stocks + indices, ~5-year daily candles
  full-00..21.json.gz  : full history since listing
  intraday.json.gz     : core symbols, 5m/15m/1h rolling archive
  Total ~2,119 symbols. Sourced from Yahoo Finance via GitHub Actions.

Archive format (one file = ~96 symbols):
  {"syms": {"SYMBOL": {"t":[unix...], "o":[...], "h":[...], "l":[...], "c":[...], "v":[...]}}}

This turns those into one long-format Parquet table you can chart, backtest or train on.

Credentials (same service account as sync_google.py):
  GOOGLE_SA_JSON  or  GOOGLE_APPLICATION_CREDENTIALS
Share the Drive folder with the service-account email.

Usage
-----
  python scripts/candles_from_drive.py --folder-id <DRIVE_FOLDER_ID> --kind daily
  python scripts/candles_from_drive.py --folder-id <ID> --kind full --out data/candles
  python scripts/candles_from_drive.py --kind daily --local-dir ./downloaded   # no Drive creds

Output: <out>/<kind>.parquet   columns: symbol, ts, date, open, high, low, close, volume
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
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

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


# ------------------------------------------------------------------ parsing
def parse_archive(obj: dict) -> pd.DataFrame:
    """{"syms": {SYM: {t,o,h,l,c,v}}} -> long DataFrame."""
    syms = obj.get("syms") or {}
    rows = []
    for sym, d in syms.items():
        if not isinstance(d, dict):
            continue
        t = d.get("t") or []
        o, h, l, c, v = (d.get("o") or []), (d.get("h") or []), (d.get("l") or []), (d.get("c") or []), (d.get("v") or [])
        n = min(len(t), len(o), len(h), len(l), len(c))
        for i in range(n):
            rows.append((sym, t[i], o[i], h[i], l[i], c[i], v[i] if i < len(v) else None))
    df = pd.DataFrame(rows, columns=["symbol", "ts", "open", "high", "low", "close", "volume"])
    if df.empty:
        return df
    df["date"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.strftime("%Y-%m-%d")
    return df[["symbol", "ts", "date", "open", "high", "low", "close", "volume"]]


def load_gz(path: str | Path) -> pd.DataFrame:
    with gzip.open(path, "rb") as fh:
        return parse_archive(json.loads(fh.read()))


# ------------------------------------------------------------------ drive
def _drive():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    raw = os.environ.get("GOOGLE_SA_JSON")
    if raw:
        creds = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        creds = service_account.Credentials.from_service_account_file(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=SCOPES)
    else:
        raise SystemExit("No Drive credentials. Set GOOGLE_SA_JSON or GOOGLE_APPLICATION_CREDENTIALS.")
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def drive_files(svc, folder_id: str, kind: str) -> list[dict]:
    q = f"'{folder_id}' in parents and name contains '{kind}-' and name contains '.json.gz' and trashed = false"
    out, tok = [], None
    while True:
        res = svc.files().list(q=q, fields="nextPageToken, files(id,name,size)",
                               pageSize=1000, pageToken=tok).execute()
        out += res.get("files", [])
        tok = res.get("nextPageToken")
        if not tok:
            break
    return sorted(out, key=lambda f: f["name"])


def drive_download(svc, file_id: str, dest: Path):
    from googleapiclient.http import MediaIoBaseDownload
    import io as _io
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as fh:
        dl = MediaIoBaseDownload(fh, svc.files().get_media(fileId=file_id), chunksize=8 << 20)
        done = False
        while not done:
            _, done = dl.next_chunk()


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser(description="Restore the ArthaSaar candle archive from Drive.")
    ap.add_argument("--kind", default="daily", choices=["daily", "full", "intraday"])
    ap.add_argument("--folder-id", default=os.environ.get("ARTHASAAR_DRIVE_FOLDER", ""))
    ap.add_argument("--local-dir", default="", help="read *.json.gz from a local dir instead of Drive")
    ap.add_argument("--out", default="data/candles")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    frames = []

    if args.local_dir:
        files = sorted(Path(args.local_dir).glob(f"{args.kind}*.json.gz"))
        if not files:
            raise SystemExit(f"No {args.kind}*.json.gz in {args.local_dir}")
        for p in files:
            df = load_gz(p)
            print(f"  {p.name}: {df['symbol'].nunique()} symbols, {len(df)} rows")
            frames.append(df)
    else:
        if not args.folder_id:
            raise SystemExit("Need --folder-id (or ARTHASAAR_DRIVE_FOLDER) unless using --local-dir")
        svc = _drive()
        files = drive_files(svc, args.folder_id, args.kind)
        if not files:
            raise SystemExit(f"No '{args.kind}-*' files in folder {args.folder_id}")
        print(f"{len(files)} file(s) to fetch")
        cache = out / "_raw"
        for f in files:
            dest = cache / f["name"]
            if not dest.exists():
                drive_download(svc, f["id"], dest)
            df = load_gz(dest)
            print(f"  {f['name']}: {df['symbol'].nunique()} symbols, {len(df)} rows")
            frames.append(df)

    if not frames:
        raise SystemExit("Nothing parsed.")
    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df.drop_duplicates(subset=["symbol", "ts"]).sort_values(["symbol", "ts"])
    dest = out / f"{args.kind}.parquet"
    all_df.to_parquet(dest, index=False)
    print(f"\nWrote {dest}  |  {all_df['symbol'].nunique()} symbols, {len(all_df):,} rows, "
          f"{all_df['date'].min()} -> {all_df['date'].max()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
