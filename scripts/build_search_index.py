#!/usr/bin/env python3
"""
build_search_index.py - one searchable index across everything the hub knows.

Powers a Google-style search bar: type "rel", "hdfc", "crude", "crash", "candle" and
get stocks, global stocks, coins, news headlines and site sections in one list.

Kept deliberately small - it is downloaded on every page load, so it holds names and
pointers, not prices. The detail is already in the other JSON files.

Output: docs/search.json
  {"updated","count","items":[{"k","t","s","h"}]}
    k = kind (stock | global | coin | news | learn)
    t = title (what you type against)
    s = subtitle (what is shown under it)
    h = href / action hint

Usage:
  python scripts/build_search_index.py
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def load(p: str):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Build the site-wide search index.")
    ap.add_argument("--docs", default="docs")
    ap.add_argument("--out", default="docs/search.json")
    ap.add_argument("--max-news", type=int, default=400)
    args = ap.parse_args()

    d = Path(args.docs)
    items: list[dict] = []

    # ---- NSE listed stocks
    uni = load(str(d / "universe.json")) or {}
    deep = {v.get("symbol") for v in ((load(str(d / "stocks.json")) or {}).get("stocks") or {}).values()}
    for r in uni.get("rows") or []:
        items.append({"k": "stock", "t": r.get("symbol", ""), "s": r.get("name", ""),
                      "h": "stocks", "d": bool(r.get("deep")) or r.get("symbol") in deep})

    # ---- global stocks
    g = load(str(d / "global.json")) or {}
    for r in g.get("rows") or []:
        items.append({"k": "global", "t": r.get("symbol", ""),
                      "s": (r.get("name") or "") + (" · " + r["country"] if r.get("country") else ""),
                      "h": "global"})

    # ---- crypto
    c = load(str(d / "crypto.json")) or {}
    for r in c.get("rows") or []:
        items.append({"k": "coin", "t": r.get("symbol", ""),
                      "s": r.get("name") or r.get("base", ""), "h": "crypto"})

    # ---- news headlines
    news = (load(str(d / "data.json")) or {}).get("news") or {}
    cols = [str(x).lower() for x in (news.get("columns") or [])]
    ti = next((i for i, x in enumerate(cols) if "title" in x or "head" in x), 0)
    si = next((i for i, x in enumerate(cols) if "source" in x or "feed" in x), None)
    for row in (news.get("rows") or [])[:args.max_news]:
        try:
            title = str(row[ti])
        except Exception:
            continue
        items.append({"k": "news", "t": title[:120],
                      "s": (str(row[si]) if si is not None and len(row) > si else "news"),
                      "h": "news"})

    # ---- site sections (so the search bar doubles as navigation)
    for label, hid, sub in [
        ("Overview", "overview", "daily update and headline numbers"),
        ("Stocks", "stocks", "all NSE listed stocks"),
        ("Screener", "screener", "filter by fall, RSI, volume spike"),
        ("Market", "market", "bhavcopy archive, FII/DII, indices"),
        ("F&O", "fno", "PCR, max pain, open interest, OI spikes"),
        ("Global", "global", "world stocks by country"),
        ("Crypto", "crypto", "coins with technicals"),
        ("News", "news", "headlines from publisher RSS"),
        ("Corporate", "corporate", "dividends, splits, bonus"),
        ("YouTube", "youtube", "what the watched channels push"),
        ("Learn", "learn", "course material: candles, patterns, F&O"),
        ("Data", "data", "feed status and sources"),
    ]:
        items.append({"k": "learn", "t": label, "s": sub, "h": hid})

    payload = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "count": len(items), "items": items}
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    kinds = {}
    for i in items:
        kinds[i["k"]] = kinds.get(i["k"], 0) + 1
    print(f"Wrote {dest}  ({dest.stat().st_size / 1e3:.0f} KB)")
    print("  " + " · ".join(f"{v} {k}" for k, v in sorted(kinds.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
