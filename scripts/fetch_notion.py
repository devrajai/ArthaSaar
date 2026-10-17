#!/usr/bin/env python3
"""
fetch_notion.py - read a Notion database into the hub.

Uses the public Notion API directly (no MCP, no extra dependency - just urllib), so it
runs the same way in GitHub Actions as on your laptop.

Setup
-----
  1. Create an internal integration at https://www.notion.so/my-integrations
  2. Copy its token into the NOTION_TOKEN secret
  3. In Notion, open the database -> ... -> Connections -> add your integration
  4. Grab the database id from its URL:
       notion.so/<workspace>/<32-char-database-id>?v=...
     (the 32 hex chars before the '?')

Usage
-----
  python scripts/fetch_notion.py --database-id <ID>
  python scripts/fetch_notion.py --database-id <ID> --name trades --out data/notion

Output: data/notion/<name>.csv (+ .parquet if pyarrow is present)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.request
from pathlib import Path

import pandas as pd

API = "https://api.notion.com/v1/databases/{db}/query"
VERSION = "2022-06-28"


def _flatten(prop: dict):
    """Turn one Notion property value into a plain scalar."""
    t = prop.get("type")
    v = prop.get(t)
    if v is None:
        return None
    if t in ("title", "rich_text"):
        return "".join(x.get("plain_text", "") for x in v) or None
    if t == "number":
        return v
    if t == "checkbox":
        return v
    if t == "select":
        return (v or {}).get("name")
    if t == "status":
        return (v or {}).get("name")
    if t == "multi_select":
        return ",".join(x.get("name", "") for x in v)
    if t == "date":
        return (v or {}).get("start")
    if t == "url":
        return v
    if t == "email":
        return v
    if t == "phone_number":
        return v
    if t in ("created_time", "last_edited_time"):
        return v
    if t in ("created_by", "last_edited_by"):
        return (v or {}).get("id")
    if t == "formula":
        return v.get("number", v.get("string", v.get("boolean")))
    if t == "relation":
        return ",".join(x.get("id", "") for x in v)
    if t == "rollup":
        return v.get("number", v.get("date"))
    if t in ("people", "files"):
        return ",".join(str(x.get("name") or x.get("url") or x.get("id")) for x in v)
    return str(v)


def query(db_id: str, token: str, page_size: int = 100) -> list[dict]:
    rows, cursor = [], None
    while True:
        body = {"page_size": page_size}
        if cursor:
            body["start_cursor"] = cursor
        req = urllib.request.Request(
            API.format(db=db_id), data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {token}",
                     "Notion-Version": VERSION,
                     "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=45) as r:
            data = json.loads(r.read().decode())
        for page in data.get("results", []):
            rec = {"_id": page.get("id"), "_url": page.get("url"),
                   "_last_edited": page.get("last_edited_time")}
            for k, p in (page.get("properties") or {}).items():
                rec[k] = _flatten(p)
            rows.append(rec)
        if not data.get("has_more"):
            break
        cursor = data.get("next_cursor")
        time.sleep(0.3)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description="Read a Notion database into the hub.")
    ap.add_argument("--database-id", required=True)
    ap.add_argument("--token-env", default="NOTION_TOKEN")
    ap.add_argument("--name", default="", help="output basename (default: db id)")
    ap.add_argument("--out", default="data/notion")
    args = ap.parse_args()

    token = os.environ.get(args.token_env)
    if not token:
        raise SystemExit(f"{args.token_env} is not set (create an integration and add it to the database).")

    db_id = re.sub(r"[^0-9a-fA-F]", "", args.database_id)
    rows = query(db_id, token)
    if not rows:
        raise SystemExit("database returned no rows (is it shared with the integration?)")

    df = pd.DataFrame(rows)
    name = args.name or db_id[:12]
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / f"{name}.csv", index=False)
    try:
        df.to_parquet(out / f"{name}.parquet", index=False)
    except Exception as e:  # noqa: BLE001
        print(f"  (parquet skipped: {e})")
    print(f"Wrote {out}/{name}.csv  |  {len(df)} rows x {df.shape[1]} cols")
    print(f"  columns: {list(df.columns)[:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
