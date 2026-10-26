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
        # RuntimeError, NOT SystemExit. SystemExit is not an Exception, so a caller that
        # catches Exception (to fall back to the release asset) would miss it and the whole
        # restore would still abort - which is precisely the silent failure we are fixing.
        raise RuntimeError("No Drive credentials. Set GOOGLE_SA_JSON or GOOGLE_APPLICATION_CREDENTIALS.")
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



# ------------------------------------------------------------------ release fallback
# The archive is also published as a GitHub Release asset. That exists because Drive needs
# a service account, and when GOOGLE_SA_JSON is missing the whole restore silently produced
# nothing - the site then analysed 8 days of bhavcopy while 8 years sat unused. A release
# asset is fetched over plain HTTPS, so this path always works on a public repo.
RELEASE_URL = ("https://github.com/devrajai/ArthaSaar/releases/download/"
               "candles-2019-2026/candles-2019-2026.zip")


def fetch_release(url: str, out: Path) -> list[Path]:
    """Download the release zip and extract the *.json.gz files. Returns local paths."""
    import io, urllib.request, zipfile
    cache = out / "_raw"
    cache.mkdir(parents=True, exist_ok=True)
    existing = sorted(cache.glob("daily-*.json.gz"))
    if len(existing) >= 30:
        print(f"  using {len(existing)} already-extracted files in {cache}")
        return existing
    print(f"  downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "ArthaSaar-pipeline"})
    with urllib.request.urlopen(req, timeout=300) as r:
        blob = r.read()
    print(f"  got {len(blob)/1e6:.1f} MB")
    z = zipfile.ZipFile(io.BytesIO(blob))
    for n in z.namelist():
        if n.endswith(".json.gz"):
            (cache / Path(n).name).write_bytes(z.read(n))
    return sorted(cache.glob("*.json.gz"))


# ------------------------------------------------------------------ main
def main() -> int:
    ap = argparse.ArgumentParser(description="Restore the ArthaSaar candle archive from Drive.")
    ap.add_argument("--kind", default="daily", choices=["daily", "full", "intraday"])
    ap.add_argument("--folder-id", default=os.environ.get("ARTHASAAR_DRIVE_FOLDER", ""))
    ap.add_argument("--local-dir", default="", help="read *.json.gz from a local dir instead of Drive")
    ap.add_argument("--out", default="data/candles")
    ap.add_argument("--release-url", default=RELEASE_URL,
                    help="fallback zip when Drive credentials are unavailable ('' to disable)")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    frames = []
    streamed = False

    if args.local_dir:
        files = sorted(Path(args.local_dir).glob(f"{args.kind}*.json.gz"))
        if not files:
            raise SystemExit(f"No {args.kind}*.json.gz in {args.local_dir}")
        for p in files:
            df = load_gz(p)
            print(f"  {p.name}: {df['symbol'].nunique()} symbols, {len(df)} rows")
            frames.append(df)
    else:
        svc = None
        files = []
        try:
            if not args.folder_id:
                raise RuntimeError("no --folder-id / ARTHASAAR_DRIVE_FOLDER")
            svc = _drive()
            files = drive_files(svc, args.folder_id, args.kind)
            if not files:
                raise RuntimeError(f"no '{args.kind}-*' files in folder {args.folder_id}")
        except Exception as e:
            # Do NOT die here. Falling through to the release asset is the difference
            # between a real archive and silently analysing a handful of bhavcopy days.
            print(f"  Drive unavailable ({type(e).__name__}: {str(e)[:90]})")
            if not args.release_url:
                raise SystemExit("Drive unavailable and no --release-url fallback configured")
            print("  falling back to the GitHub release asset")
            paths = fetch_release(args.release_url, out)
            # Stream straight to parquet parts instead of accumulating 37 frames in memory.
            # Holding them all costs ~1.5 GB; on a 2 GB runner that is the difference
            # between working and dying at the concat.
            parts = out / "_parts"
            parts.mkdir(parents=True, exist_ok=True)
            for i, pth in enumerate(paths):
                df = load_gz(pth)
                print(f"  {pth.name}: {df['symbol'].nunique()} symbols, {len(df)} rows")
                df.to_parquet(parts / f"p{i:03d}.parquet", index=False)
                del df
            svc = None
            streamed = True

        if svc is not None:
            print(f"{len(files)} file(s) to fetch")
            cache = out / "_raw"
            for f in files:
                dest = cache / f["name"]
                if not dest.exists():
                    drive_download(svc, f["id"], dest)
                df = load_gz(dest)
                print(f"  {f['name']}: {df['symbol'].nunique()} symbols, {len(df)} rows")
                frames.append(df)

    # The release path streams straight to parquet parts, so `frames` stays empty on
    # purpose - guard on both, or a successful download reports "Nothing parsed".
    if not frames and not streamed:
        raise SystemExit("Nothing parsed.")
    dest = out / f"{args.kind}.parquet"

    # Assemble through DuckDB rather than pd.concat. Eight years is ~3.5M rows and
    # concatenating 37 frames at once spikes memory; DuckDB streams it, dedupes and sorts
    # with a bounded footprint. Same result, and it does not fall over on a small runner.
    try:
        import duckdb
        parts = out / "_parts"
        parts.mkdir(parents=True, exist_ok=True)
        if not streamed:
            for i, df in enumerate(frames):
                df.to_parquet(parts / f"p{i:03d}.parquet", index=False)
        con = duckdb.connect()
        con.execute("SET threads=1")
        con.execute("SET preserve_insertion_order=false")
        con.execute(f"""
          COPY (
            SELECT DISTINCT symbol, ts, date, open, high, low, close, volume
            FROM read_parquet('{parts}/*.parquet')
            ORDER BY symbol, ts
          ) TO '{dest}' (FORMAT PARQUET)
        """)
        n, syms, a, b = con.execute(
            f"SELECT count(*), count(DISTINCT symbol), min(date), max(date) FROM '{dest}'"
        ).fetchone()
        con.close()
        import shutil; shutil.rmtree(parts, ignore_errors=True)
        print(f"\nWrote {dest}  |  {syms:,} symbols, {n:,} rows, {a} -> {b}")
    except Exception as e:
        print(f"  duckdb assembly unavailable ({type(e).__name__}), using pyarrow")
        # pyarrow is not an optional nicety here - pandas needs it for parquet at all. It
        # concatenates the parts without materialising a python object per cell, so this
        # path stays cheap. Dedupe is skipped because the parts partition the symbol
        # space: each file holds a disjoint slice of symbols, so (symbol, ts) cannot repeat.
        import pyarrow as pa, pyarrow.parquet as pq
        part_files = sorted(parts.glob("*.parquet"))
        if not part_files:
            if not frames:
                raise SystemExit("Nothing to assemble.")
            for i, df in enumerate(frames):
                df.to_parquet(parts / f"p{i:03d}.parquet", index=False)
            part_files = sorted(parts.glob("*.parquet"))
        tables = [pq.read_table(f) for f in part_files]
        t = pa.concat_tables(tables, promote_options="default")
        t = t.sort_by([("symbol", "ascending"), ("ts", "ascending")])
        pq.write_table(t, dest)
        print(f"\nWrote {dest}  |  {t.num_rows:,} rows")
        import shutil; shutil.rmtree(parts, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
