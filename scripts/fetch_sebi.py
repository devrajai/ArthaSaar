#!/usr/bin/env python3
"""SEBI orders and circulars (Task 17).

SEBI publishes RSS feeds. They are plain XML, no key, no auth. We keep the last
90 days and never invent an entry - if the feed is unreachable the file is written
with a `note` saying so, and the site shows that honestly rather than an empty table.
"""
import json, os, sys, urllib.request, re, html
from datetime import datetime, timedelta, timezone

OUT = "docs/sebi.json"
DAYS = 90
# SEBI publishes ONE combined feed. The separate circular paths that look obvious
# (/sebirss/circular.xml and friends) all 404 - checked. So there is a single list,
# and the site says so rather than pretending the two are separated.
FEEDS = [("orders", "https://www.sebi.gov.in/sebirss.xml")]
UA = {"User-Agent": "Mozilla/5.0 (compatible; ArthaSaar/1.0; +https://github.com/devrajai/ArthaSaar)"}


def fetch(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", "replace")
    except Exception as e:
        print("  %s -> %s" % (url, type(e).__name__))
        return None


def strip_tags(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def parse_items(xml):
    """Tolerant RSS/Atom reader - handles <item> and <entry>, CDATA and entities."""
    out = []
    for block in re.findall(r"<(?:item|entry)\b[\s\S]*?</(?:item|entry)>", xml, re.I):
        def pick(tag):
            m = re.search(r"<%s[^>]*>([\s\S]*?)</%s>" % (tag, tag), block, re.I)
            if not m:
                return ""
            v = m.group(1)
            v = re.sub(r"<!\[CDATA\[([\s\S]*?)\]\]>", r"\1", v)
            return strip_tags(v)
        title = pick("title")
        link = pick("link")
        if not link:
            m = re.search(r'<link[^>]*href="([^"]+)"', block, re.I)
            link = m.group(1) if m else ""
        date = pick("pubDate") or pick("updated") or pick("published") or ""
        desc = pick("description") or pick("summary")
        if title:
            out.append({"title": title[:220], "link": link.strip(), "date": date.strip(), "desc": desc[:300]})
    return out


def to_date(s):
    s = (s or "").strip()
    # SEBI's pubDate is "22 Oct 2026 22:00:02 +0530" - no weekday, so the usual RFC-822
    # format misses it. Try the string whole; do NOT slice it to the format length, which
    # is what broke this before: it chopped "+0530" down to "+053" and every parse failed.
    # The real item tag is "22 Oct, 2026 +0530" - a comma AND no time component, which is
    # neither RFC-822 nor any of the obvious variants. Found by printing the raw tag.
    for fmt in ("%d %b, %Y %z", "%d %b %Y %z", "%d %b, %Y %H:%M:%S %z",
                "%d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S %z",
                "%d %b %Y", "%d %b, %Y", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%d", "%d-%b-%Y"):
        try:
            d = datetime.strptime(s, fmt)
            return d.replace(tzinfo=d.tzinfo or timezone.utc)
        except Exception:
            continue
    return None


def main():
    cutoff = datetime.now(timezone.utc) - timedelta(days=DAYS)
    result = {"orders": [], "circulars": [], "note": ""}
    seen = set()
    got_any = False
    for kind, url in FEEDS:
        xml = fetch(url)
        if not xml:
            continue
        got_any = True
        items = parse_items(xml)
        print("  %s: %d items" % (url.rsplit("/", 1)[-1], len(items)))
        for it in items:
            d = to_date(it["date"])
            if d and d < cutoff:
                continue
            key = it["title"].lower()[:80]
            if key in seen:
                continue
            seen.add(key)
            row = [d.strftime("%Y-%m-%d") if d else (it["date"] or "")[:10], it["title"], it["link"]]
            result[kind].append(row)

    def sortr(rows):
        return sorted(rows, key=lambda r: r[0] or "", reverse=True)

    result["orders"] = sortr(result["orders"])[:400]
    result["circulars"] = sortr(result["circulars"])[:400]
    result["updated"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    result["count"] = len(result["orders"]) + len(result["circulars"])
    if not got_any:
        result["note"] = "SEBI's feeds were unreachable from this network, so nothing is shown rather than something stale."
    elif not result["count"]:
        result["note"] = "SEBI's feed responded but carried no items in the last %d days." % DAYS
    else:
        result["note"] = "SEBI publishes one combined feed, so orders and circulars are not separated here."

    os.makedirs("docs", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(result, fh, ensure_ascii=False)
    print("sebi: %d orders, %d circulars -> %s" % (len(result["orders"]), len(result["circulars"]), OUT))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
