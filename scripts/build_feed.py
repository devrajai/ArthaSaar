#!/usr/bin/env python3
"""RSS feed of the daily brief (Task 11).

Appends today's brief to a rolling history so older items persist, then writes the feed
from that history. Replaces rather than appends when run twice in a day.
"""
import json, os, sys, html
from datetime import datetime, timezone

OUT = "docs/feed.xml"
HIST = "docs/feed_history.json"
SITE = "https://devrajai.github.io/ArthaSaar/"
KEEP = 30


def load(p, default):
    try:
        return json.load(open(p))
    except Exception:
        return default


def main():
    brief = load("docs/brief.json", None)
    hist = load(HIST, [])
    if not isinstance(hist, list):
        hist = []

    if brief and (brief.get("headline") or brief.get("bullets")):
        day = (brief.get("updated") or "")[:10] or datetime.now(timezone.utc).strftime("%Y-%m-%d")
        entry = {"date": day, "headline": brief.get("headline") or "Market summary",
                 "bullets": brief.get("bullets") or []}
        hist = [h for h in hist if h.get("date") != day]   # re-running the same day replaces
        hist.append(entry)
    hist = sorted(hist, key=lambda h: h.get("date") or "", reverse=True)[:KEEP]

    def esc(t):
        return html.escape(str(t or ""), quote=True)

    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    items = []
    for h in hist:
        d = h.get("date") or ""
        try:
            pub = datetime.strptime(d, "%Y-%m-%d").strftime("%a, %d %b %Y 00:00:00 +0000")
        except Exception:
            pub = now
        body = "<p>" + esc(h.get("headline")) + "</p><ul>" + "".join(
            "<li>" + esc(b) + "</li>" for b in (h.get("bullets") or [])) + "</ul>"
        items.append(
            "  <item>\n"
            "    <title>%s</title>\n"
            "    <link>%s</link>\n"
            "    <guid isPermaLink=\"false\">arthasaar-%s</guid>\n"
            "    <pubDate>%s</pubDate>\n"
            "    <description><![CDATA[%s]]></description>\n"
            "  </item>" % (esc(h.get("headline")), SITE, esc(d), pub, body))

    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<rss version="2.0"><channel>\n'
           '  <title>ArthaSaar daily market brief</title>\n'
           '  <link>%s</link>\n'
           '  <description>What moved in the Indian market today, from ArthaSaar\'s own data.</description>\n'
           '  <language>en-in</language>\n'
           '  <lastBuildDate>%s</lastBuildDate>\n'
           '%s\n'
           '</channel></rss>\n' % (SITE, now, "\n".join(items)))

    os.makedirs("docs", exist_ok=True)
    json.dump(hist, open(HIST, "w"), ensure_ascii=False)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(xml)
    print("feed: %d items over %d days -> %s" % (len(items), len(hist), OUT))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
