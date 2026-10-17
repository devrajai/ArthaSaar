#!/usr/bin/env python3
"""
sync_google.py - OPTIONAL. Mirror the archive into Google Drive and/or push the
latest day's rows into the Google Sheet.

Both actions use a Google **service account** (a robot identity, not your login).
Create one, download its JSON key, and share the target Drive folder and the
Sheet with the service account's email address (…@….iam.gserviceaccount.com).

Credentials are read from the environment - never hard-code them:
  GOOGLE_SA_JSON   the service-account JSON itself (use a CI secret), OR
  GOOGLE_APPLICATION_CREDENTIALS  path to the JSON file

Usage
-----
  # upload today's parquet files to a Drive folder
  python scripts/sync_google.py drive --folder-id <DRIVE_FOLDER_ID> --pattern 'data/parquet/**/*.parquet'

  # push the latest CM day's rows for the watchlist into the Sheet's Daily_Snapshot tab
  python scripts/sync_google.py sheet --spreadsheet-id <SHEET_ID> --day 2026-10-16

NOTE: Google Sheets caps a workbook at 10,000,000 cells. This script appends only
the symbols you list in the Universe tab - the bulk archive stays in Drive files.
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from pathlib import Path

import pandas as pd

SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/spreadsheets",
]

DAILY_HEADER = ["Date", "Symbol", "Open", "High", "Low", "Close", "PrevClose",
                "Volume", "Turnover", "DeliverableQty", "DeliverablePct", "Series", "Source"]


def _creds():
    from google.oauth2 import service_account
    raw = os.environ.get("GOOGLE_SA_JSON")
    if raw:
        return service_account.Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if path:
        return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
    raise SystemExit("No service-account credentials found. Set GOOGLE_SA_JSON or "
                     "GOOGLE_APPLICATION_CREDENTIALS.")


def upload_drive(folder_id: str, files: list[str], *, mime: str = "application/octet-stream"):
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload

    svc = build("drive", "v3", credentials=_creds(), cache_discovery=False)
    for fp in files:
        name = Path(fp).name
        q = f"name = '{name}' and '{folder_id}' in parents and trashed = false"
        existing = svc.files().list(q=q, fields="files(id)", pageSize=1).execute().get("files", [])
        media = MediaFileUpload(fp, mimetype=mime, resumable=False)
        if existing:
            svc.files().update(fileId=existing[0]["id"], media_body=media).execute()
            print(f"  updated {name}")
        else:
            svc.files().create(body={"name": name, "parents": [folder_id]},
                               media_body=media, fields="id").execute()
            print(f"  uploaded {name}")


def _watchlist(spreadsheet_id: str, svc) -> list[str]:
    vals = svc.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id, range="Universe!A2:A").execute().get("values", [])
    return [r[0].strip().upper() for r in vals if r and r[0].strip()]


def push_sheet(spreadsheet_id: str, day: str, *, csv_path: str | None = None):
    from googleapiclient.discovery import build

    svc = build("sheets", "v4", credentials=_creds(), cache_discovery=False)
    symbols = set(_watchlist(spreadsheet_id, svc))
    if not symbols:
        raise SystemExit("Universe tab is empty - add symbols to the watchlist first.")

    path = csv_path or f"data/csv/cm/cm_{day}.csv"
    if not Path(path).exists():
        raise SystemExit(f"Normalised CSV not found: {path} (run fetch_bhavcopy first)")

    df = pd.read_csv(path, dtype=str)
    df = df[df["symbol"].str.upper().isin(symbols)]
    if df.empty:
        raise SystemExit("No watchlist symbols found in that day's file.")

    rows = [[
        r.get("date", day), r.get("symbol", ""), r.get("open", ""), r.get("high", ""),
        r.get("low", ""), r.get("close", ""), r.get("prevclose", ""), r.get("volume", ""),
        r.get("turnover", ""), "", "", r.get("series", ""), "bhavcopy",
    ] for _, r in df.iterrows()]

    svc.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id, range="Daily_Snapshot!A1",
        valueInputOption="RAW", insertDataOption="INSERT_ROWS",
        body={"majorDimension": "ROWS", "values": rows},
    ).execute()
    print(f"  appended {len(rows)} row(s) for {day}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Mirror archive to Drive / push to Sheet (optional).")
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("drive")
    d.add_argument("--folder-id", required=True)
    d.add_argument("--pattern", default="data/parquet/**/*.parquet")

    s = sub.add_parser("sheet")
    s.add_argument("--spreadsheet-id", required=True)
    s.add_argument("--day", required=True)
    s.add_argument("--csv-path", default=None)

    args = ap.parse_args()
    if args.cmd == "drive":
        files = sorted(glob.glob(args.pattern, recursive=True))
        if not files:
            print("No files matched."); return 0
        upload_drive(args.folder_id, files,
                     mime="application/vnd.apache.parquet" if files[0].endswith(".parquet")
                     else "application/octet-stream")
    elif args.cmd == "sheet":
        push_sheet(args.spreadsheet_id, args.day, csv_path=args.csv_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
