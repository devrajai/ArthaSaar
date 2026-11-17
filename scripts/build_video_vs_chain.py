#!/usr/bin/env python3
"""What the YouTube channels talked about, next to what the data actually did.

WHY THIS EXISTS
The pipeline already collects 486 videos from 10 channels. They were stored and never read.
Meanwhile the site holds, for the same stocks, the day's price move and - for 30 of them -
the option chain with open interest changes and the writing/covering label.

Putting those side by side answers a question no channel answers about itself: when this
channel named a stock, what was actually happening in its derivatives? Not whether they were
right - that needs a forward record we do not have yet - but whether the attention lined up
with unusual positioning, or arrived after the move was already over.

WHAT THIS IS NOT
Not a score of any channel's accuracy. A mention is not a prediction, a title is not advice,
and a stock named in a video may have been mentioned to warn against it. The output says
which videos mentioned what and what the data showed; the reader draws the conclusion.

METHOD
  - only videos from the last N days (default 21)
  - a ticker counts only if it is an exact uppercase token matching a real symbol in
    screener.json, at least 3 characters - "IT" and "CAN" are words, not tickers
  - the chain label is the side (call or put) with the largest open-interest increase,
    which is what the close message reports
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd

VIDEOS = "data/youtube/videos.csv"
SCREENER = "docs/screener.json"
CHAIN = "docs/option_chain.json"
OUT = "docs/video_vs_chain.json"

WINDOW_DAYS = 21
MIN_SYM_LEN = 3


def jload(p):
    try:
        return json.loads(open(p).read())
    except Exception:
        return None


def dominant_action(entry):
    """The side with the biggest OI increase - the same reading the close message uses."""
    best = None
    for st in (entry.get("strikes") or []):
        for side, lbl in (("ce", "call"), ("pe", "put")):
            d = st.get(side) or {}
            ch = d.get("oi_chg") or 0
            if best is None or ch > best[0]:
                best = (ch, lbl, st.get("strike"), d.get("action"))
    if not best or not best[0]:
        return None
    return {"side": best[1], "strike": best[2], "action": best[3], "oi_chg": best[0]}


def main() -> int:
    sc = jload(SCREENER) or {}
    rows = sc.get("rows") or []
    if not rows:
        print("no screener rows - cannot resolve tickers")
        return 0
    by_sym = {}
    for r in rows:
        s = str(r.get("symbol") or "").strip().upper()
        if s:
            by_sym[s] = r
    symbols = {s for s in by_sym if len(s) >= MIN_SYM_LEN}

    # NAME MATCHING WAS TRIED AND REMOVED. Matching the distinctive word of a company name
    # produced 299 mentions against 20 from tickers alone - and almost all of the extra were
    # wrong: "TV Today Network" matched every video containing the word "today" (41 hits),
    # "Wealth First" matched "wealth" (23). A false "this channel talked about this stock" is
    # worse than a missed one, because the whole point of this file is that it can be trusted
    # over the channel's own claims. Ticker-only, and the caution says so.


    chain = (jload(CHAIN) or {}).get("stocks") or {}

    try:
        vids = pd.read_csv(VIDEOS)
    except Exception as e:
        print("no videos.csv (%s)" % type(e).__name__)
        return 0
    if vids.empty:
        print("videos.csv is empty")
        return 0

    vids["published"] = pd.to_datetime(vids["published"], errors="coerce", utc=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    recent = vids[vids["published"] >= cutoff].copy()
    if recent.empty:
        # a quiet fortnight still deserves a file rather than a missing one
        recent = vids.sort_values("published").tail(40).copy()
        note_extra = "No videos in the last %d days; showing the most recent 40." % WINDOW_DAYS
    else:
        note_extra = ""

    word = re.compile(r"\b[A-Z][A-Z0-9&\-]{2,14}\b")
    mentions = []
    for _, v in recent.iterrows():
        text = " ".join(str(v.get(c) or "") for c in ("title", "description"))
        seen = set()
        hits = set()
        for tok in word.findall(text):
            t = tok.strip("-&")
            if t in symbols:
                hits.add(t)
        for t in hits:
            if t not in seen:
                seen.add(t)
                mentions.append({
                    "symbol": t,
                    "channel": str(v.get("channel_name") or ""),
                    "title": str(v.get("title") or "")[:110],
                    "published": (v["published"].strftime("%Y-%m-%d")
                                  if pd.notna(v["published"]) else ""),
                    "url": str(v.get("url") or ""),
                    "via": "ticker" if t in symbols else "name",
                })

    # attach what the data showed
    for m in mentions:
        r = by_sym.get(m["symbol"]) or {}
        ch = r.get("chg_1d")
        m["chg_1d"] = round(float(ch), 2) if ch is not None and pd.notna(ch) else None
        m["has_chain"] = m["symbol"] in chain
        if m["has_chain"]:
            da = dominant_action(chain[m["symbol"]])
            if da:
                m["chain"] = da

    # group by symbol so the card can lead with the most-talked-about names
    grouped = {}
    for m in mentions:
        g = grouped.setdefault(m["symbol"], {
            "symbol": m["symbol"], "mentions": 0, "channels": [],
            "chg_1d": m.get("chg_1d"), "chain": m.get("chain"),
            "latest": m, "titles": [],
        })
        g["mentions"] += 1
        if m["channel"] and m["channel"] not in g["channels"]:
            g["channels"].append(m["channel"])
        if m["published"] > (g["latest"].get("published") or ""):
            g["latest"] = m
        if m["title"] and m["title"] not in g["titles"]:
            g["titles"].append(m["title"])

    top = sorted(grouped.values(), key=lambda g: (-g["mentions"], g["symbol"]))[:40]

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": WINDOW_DAYS,
        "videos_in_window": int(len(recent)),
        "videos_total": int(len(vids)),
        "mentions": len(mentions),
        "symbols": len(grouped),
        "top": top,
        "with_chain": sum(1 for g in top if g.get("chain")),
        "note": ("Stocks named in the last %d days of tracked YouTube videos, beside what the "
                 "same stock did that session and, where we hold its chain, which side saw the "
                 "largest open-interest increase. A mention is not a prediction and this is not "
                 "a score of any channel." % WINDOW_DAYS),
        "cautions": {
            "not_accuracy": ("Nothing here says whether a channel was right. That needs a "
                             "forward record - what the stock did AFTER the video - which this "
                             "file does not compute."),
            "title_only": ("Matching is on title and description text. A stock named as a "
                           "warning looks identical to one named as a pick."),
            "chain_coverage": ("Only %d of the %d stocks carry an option chain here; the rest "
                               "have a price move only." % (len(chain), len(by_sym))),
            "false_positives": ("Only exact uppercase tokens matching a real symbol of 3+ characters "
                                "count, so ordinary words are excluded. Company NAMES are not "
                                "matched: a trial matched the word 'today' to TV Today Network "
                                "41 times. Fewer mentions, but the ones here are real."),
        },
    }
    if note_extra:
        out["note"] = note_extra + " " + out["note"]

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %d videos in window, %d mentions, %d symbols, %d with a chain"
          % (out["videos_in_window"], out["mentions"], out["symbols"], out["with_chain"]))
    for g in top[:6]:
        ch = g.get("chain") or {}
        print("     %-12s %dx  %s  %s"
              % (g["symbol"], g["mentions"],
                 ("%+.2f%%" % g["chg_1d"]) if g.get("chg_1d") is not None else "  -",
                 (ch.get("side", "") + " " + str(ch.get("action", ""))) if ch else "no chain"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
