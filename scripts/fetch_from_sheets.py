#!/usr/bin/env python3
"""
fetch_from_sheets.py - read a Google Sheet into the hub.

Why this matters for "Google Finance": there is NO Google Finance API, and its
historical data cannot be pulled programmatically (the Sheets function returns #N/A
through the API). The ONLY supported route is the GOOGLEFINANCE() formula living
inside a spreadsheet. So the pattern is:

  1. Put your formulas in a tab, e.g.  =GOOGLEFINANCE("NSE:RELIANCE","price")
  2. Point this script at that tab and range.
  3. It snapshots the values into data/sheets/ on every run.

That gives you a versioned history of whatever your Sheet computes - Google Finance
quotes, your own lookups, or a hand-maintained table - without needing an API that
does not exist.

Credentials: same service account as sync_google.py (GOOGLE_SA_JSON or
GOOGLE_APPLICATION_CREDENTIALS). Share the Sheet with the service-account email.

Usage
-----
  python scripts/fetch_from_sheets.py --spreadsheet-id <ID> --range "Quotes!A1:F50"
  python scripts/fetch_from_sheets.py --spreadsheet-id <ID> --range "Sheet1!A:Z" --name quotes
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


def _sheets():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    raw = os.environ.get("GOOGLE_SA_JSON")
    if raw:
        creds = service_account.Credentials.from_service_account_info(json.loads(raw), scopes=SCOPES)
    elif os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        creds = service_account.Credentials.from_service_account_file(
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"], scopes=SCOPES)
    else:
        raise SystemExit("No credentials. Set GOOGLE_SA_JSON or GOOGLE_APPLICATION_CREDENTIALS.")
    return build("sheets", "v4", credentials=creds, cache_discovery=False)


def read_range(svc, spreadsheet_id: str, rng: str) -> pd.DataFrame:
    vals = (svc.spreadsheets().values()
            .get(spreadsheetId=spreadsheet_id, range=rng)
            .execute().get("values", []))
    if not vals:
        return pd.DataFrame()
    width = max(len(r) for r in vals)
    rows = [r + [""] * (width - len(r)) for r in vals]
    return pd.DataFrame(rows[1:], columns=rows[0])


def main() -> int:
    ap = argparse.ArgumentParser(description="Snapshot a Google Sheet into the hub.")
    ap.add_argument("--spreadsheet-id", required=True)
    ap.add_argument("--range", required=True, help="A1 notation, e.g. 'Quotes!A1:F50'")
    ap.add_argument("--name", default="", help="output basename (default: from the range)")
    ap.add_argument("--out", default="data/sheets")
    args = ap.parse_args()

    name = args.name or args.range.split("!")[0].strip("'").replace(" ", "_").lower()
    df = read_range(_sheets(), args.spreadsheet_id, args.range)
    if df.empty:
        raise SystemExit(f"No values in {args.range}")

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df["_snapshot_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    df.to_csv(out / f"{name}.csv", index=False)
    try:
        df.to_parquet(out / f"{name}.parquet", index=False)
    except Exception as e:  # noqa: BLE001
        print(f"  (parquet skipped: {e})")
    print(f"Wrote {out}/{name}.csv  |  {len(df)} rows x {df.shape[1] - 1} cols")
    print(f"  columns: {list(df.columns)[:10]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
