#!/usr/bin/env python3
"""India market news collector — Google News RSS (free, no key, no bot-wall).
Outputs data/news.json. Each query becomes a topic; items deduped, latest 60."""
import html as _html
import json
import re
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import quote
import urllib.request

DATA = Path(__file__).resolve().parents[1] / "data"

QUERIES = [
    ("Markets", "nifty OR sensex OR stock market"),
    ("Economy", "india economy OR RBI OR repo rate OR inflation"),
    ("Companies", "indian stocks earnings OR quarterly results"),
    ("Global", "us fed OR wall street OR crude oil price OR gold price"),
    ("Crypto", "bitcoin OR ethereum india"),
]

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

def clean(s):
    s = re.sub(r"<[^>]+>", "", s or "")
    return re.sub(r"\s+", " ", _html.unescape(s)).strip()

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "ignore")

def parse_feed(topic, url):
    root = ET.fromstring(fetch(url))
    for item in root.iter("item"):
        title = link = pub = src = None
        for ch in item:
            if ch.tag == "title": title = clean(ch.text)
            elif ch.tag == "link": link = (ch.text or "").strip()
            elif ch.tag == "pubDate": pub = ch.text
            elif ch.tag == "source": src = clean(ch.text)
        if title and link:
            # Google News titles end with " - Publisher"; strip it if source tag matches
            if src and title.endswith(" - " + src):
                title = title[: -(len(src) + 3)]
            try:
                ts = parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat()
            except Exception:
                ts = None
            yield {"topic": topic, "title": title, "link": link,
                   "publisher": src or "", "published": ts}

def main():
    items, seen = [], set()
    for topic, q in QUERIES:
        url = "https://news.google.com/rss/search?q=" + quote(q) + \
              "&hl=en-IN&gl=IN&ceid=IN:en"
        n = 0
        try:
            for it in parse_feed(topic, url):
                key = it["title"].lower()[:70]
                if key in seen:
                    continue
                seen.add(key)
                items.append(it)
                n += 1
            print(f"ok   {topic:10s} {n} items")
        except Exception as e:
            print(f"FAIL {topic:10s} {e}")
    items.sort(key=lambda x: x.get("published") or "", reverse=True)
    items = items[:60]
    out = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(items),
        "topics": [q[0] for q in QUERIES],
        "items": items,
        "note": "Free Google News RSS — India market news. Times in UTC.",
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "news.json").write_text(json.dumps(out, indent=1))
    print(f"\nwrote data/news.json — {len(items)} items")
    if not items:
        print("ERROR: no news collected", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
