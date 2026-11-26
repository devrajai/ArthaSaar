#!/usr/bin/env python3
"""
build_economy.py - Indian policy releases from the RBI, for an economy window.

macro.json holds two entries, both US Federal Reserve. There is no Indian policy date anywhere on
the site, which is odd for a site about the Indian market.

This pulls the RBI's own press-release RSS - free, no key, English, and dated - and sorts each
release into a topic by keyword. It does not attempt to summarise or interpret: the headline and
the date are the content.

What it is not
--------------
  * Not a calendar. The RBI feed carries what it published, not what it will publish. CPI, IIP and
    GDP dates come from MoSPI, whose portal needs scraping, so they are not here.
  * PIB is skipped on purpose: its RSS returns Hindi-only items with no publication date, which
    cannot be placed on a timeline.
  * No interpretation of any release. A repo auction notice is not a policy signal.

Usage
-----
  python scripts/build_economy.py
  python scripts/build_economy.py --max 60

Output: docs/economy.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

OUT = "docs/economy.json"
FEED = "https://www.rbi.org.in/pressreleases_rss.xml"
UA = {"User-Agent": "Mozilla/5.0 (compatible; ArthaSaar/1.0)"}

# topic -> keywords. Order matters: the first match wins, so the most specific topic sits first.
TOPICS = [
    ("Rates", ["repo", "reverse repo", "policy rate", "marginal standing", "msf", "bank rate",
               "monetary policy", "mpc", "liquidity adjustment", "vrr", "sdf"]),
    ("Inflation", ["inflation", "cpi", "wpi", "price index"]),
    ("Growth", ["gdp", "gva", "iip", "industrial production", "growth rate", "national income"]),
    ("Currency", ["rupee", "foreign exchange", "forex", "reference rate", "fema", "usd/inr"]),
    ("Banking", ["bank", "nbfc", "co-operative", "deposit", "loan", "npa", "basel"]),
    ("Markets", ["government securities", "g-sec", "auction", "treasury bill", "bond", "t-bill",
                 "underwriting", "switch auction"]),
    ("Regulation", ["circular", "master direction", "guidelines", "notification", "penalty",
                    "directions", "framework"]),
]


def topic_of(title: str) -> str:
    low = title.lower()
    for name, words in TOPICS:
        for w in words:
            if w in low:
                return name
    return "Other"


def parse_date(raw: str):
    """RFC-822 pubDate -> ISO date. Returns None if it cannot be read."""
    if not raw:
        return None
    for fmt in ("%a, %d %b %Y %H:%M:%S", "%a, %d %b %Y %H:%M:%S %z",
                "%d %b %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip()[:25].strip(), fmt).strftime("%Y-%m-%d")
        except Exception:
            continue
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})\s+(\d{4})", raw)
    if m:
        try:
            return datetime.strptime(" ".join(m.groups()), "%d %b %Y").strftime("%Y-%m-%d")
        except Exception:
            return None
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--max", type=int, default=80)
    args = ap.parse_args()

    try:
        req = urllib.request.Request(FEED, headers=UA)
        raw = urllib.request.urlopen(req, timeout=45).read()
    except Exception as e:
        print(f"RBI feed unreachable ({type(e).__name__}) - leaving the existing file alone")
        return 0

    try:
        root = ET.fromstring(raw)
    except Exception as e:
        print(f"RBI feed did not parse ({type(e).__name__}) - skipping")
        return 0

    items = []
    for it in root.findall(".//item")[: args.max]:
        title = re.sub(r"\s+", " ", (it.findtext("title") or "")).strip()
        if not title:
            continue
        # the feed carries HTML entities such as &#8377;
        title = (title.replace("&#8377;", "\u20b9").replace("&amp;", "&")
                      .replace("&quot;", '"').replace("&#39;", "'"))
        items.append({
            "date": parse_date(it.findtext("pubDate") or ""),
            "title": title,
            "link": (it.findtext("link") or "").strip(),
            "topic": topic_of(title),
        })

    if not items:
        print("no items in the feed - leaving the existing file alone")
        return 0

    counts = {}
    for x in items:
        counts[x["topic"]] = counts.get(x["topic"], 0) + 1

    Path(args.out).write_text(json.dumps({
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(items),
        "source": "RBI press releases RSS",
        "counts": counts,
        "note": ("Reserve Bank of India press releases, as published. This is what the RBI has "
                 "released, not a calendar of what it will release - CPI, IIP and GDP dates come "
                 "from MoSPI, which is not collected here. A repo auction notice is an "
                 "operational announcement, not a policy signal, and nothing here interprets a "
                 "release."),
        "items": items,
    }, separators=(",", ":"), ensure_ascii=False))
    print(f"-> {args.out}  {Path(args.out).stat().st_size/1024:.0f} KB | {len(items)} releases")
    for x in items[:4]:
        print(f"   {x['date'] or '-'}  [{x['topic']:10s}] {x['title'][:60]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
