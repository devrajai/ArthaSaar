#!/usr/bin/env python3
"""
fetch_news.py - market headlines from free RSS feeds.

RSS is the one free news route that is stable and permitted: publishers expose it on
purpose. No scraping, no key, no login.

Feeds are listed in config/news_feeds.json. Output is one row per headline with the
source, so the YouTube "brain" can be extended to news later.

Some networks block these domains (this sandbox does); a failure is reported and
skipped rather than treated as an error.

Usage
-----
  python scripts/fetch_news.py
  python scripts/fetch_news.py --out data/news --max-per-feed 40
"""

from __future__ import annotations

import argparse
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0 Safari/537.36"}
NS = {"a": "http://www.w3.org/2005/Atom", "rss": "", "dc": "http://purl.org/dc/elements/1.1/"}


def _text(node, *paths, default=""):
    for p in paths:
        el = node.find(p, NS) if ":" in p else node.find(p)
        if el is not None and (el.text or "").strip():
            return el.text.strip()
    return default


def parse_feed(raw: bytes, source: str) -> list[dict]:
    root = ET.fromstring(raw)
    items = root.findall(".//item") or root.findall(".//a:entry", NS)
    out = []
    for it in items:
        link = _text(it, "link")
        if not link:
            l = it.find("a:link", NS)
            if l is not None:
                link = l.get("href", "")
        out.append({
            "source": source,
            "title": _text(it, "title", "a:title"),
            "link": link,
            "published": _text(it, "pubDate", "a:published", "dc:date"),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Free market headlines via RSS.")
    ap.add_argument("--config", default="config/news_feeds.json")
    ap.add_argument("--out", default="data/news")
    ap.add_argument("--max-per-feed", type=int, default=50)
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text()) if Path(args.config).exists() else {"feeds": []}
    feeds = cfg.get("feeds", [])
    if not feeds:
        print("no feeds configured")
        return 0

    rows, ok, failed = [], 0, []
    for f in feeds:
        try:
            req = urllib.request.Request(f["url"], headers=UA)
            raw = urllib.request.urlopen(req, timeout=25).read()
            got = parse_feed(raw, f.get("name", f["url"]))[: args.max_per_feed]
            rows += got
            ok += 1
            print(f"  {f.get('name','?'):24s} {len(got)} item(s)")
        except Exception as e:
            failed.append(f.get("name", "?"))
            print(f"  {f.get('name','?'):24s} FAILED ({type(e).__name__}: {str(e)[:40]})")

    if not rows:
        print(f"\nno headlines fetched ({len(failed)} feed(s) unreachable) - skipping. "
              "RSS is often blocked behind proxies; it works from most CI runners.")
        return 0

    df = pd.DataFrame(rows).drop_duplicates(subset=["title"])
    df["fetched_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    df.to_csv(out / "headlines.csv", index=False)
    print(f"\n{len(df)} unique headlines from {ok}/{len(feeds)} feeds")
    print(f"Wrote {out}/headlines.csv")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
