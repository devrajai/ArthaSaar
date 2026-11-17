#!/usr/bin/env python3
"""What the Telegram channels said, beside what the data actually did.

WHY THIS EXISTS
The collector reads public Telegram channels through t.me/s/<name> - no login, no bot token.
What it stores is somebody's post. What it never stored was any way to check that post against
the market it describes.

This does that. For every stock a channel names, it shows what the same stock did that session
and, where we hold the chain, which side saw the largest open-interest increase.

WHAT IT FOUND ABOUT THE CHANNELS THEMSELVES
LIVEOPTIONDATA posts mostly carry no text at all - 129 messages, and the majority read only
"Sent via TeleFeed" because the content is a screenshot of a PCR table. That is not a parsing
failure; there is nothing in the text to parse. The file records how many posts were image-only
so a reader knows the coverage limit rather than assuming silence means nothing was said.

WHAT THIS IS NOT
Not a score of any channel. A mention is not a prediction, and a post that names a stock to
warn against it looks identical to one that names it as a pick.

LEGAL NOTE
Reading a public page that requires no login is not the same act as republishing it. This file
stores which channel named which ticker, and the market's own numbers beside it. It does not
reproduce the posts, and the site should not display them in full - the analysis is the point,
the channel's text is theirs.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import pandas as pd

MSGS = "data/telegram/messages.parquet"
SCREENER = "docs/screener.json"
CHAIN = "docs/option_chain.json"
OUT = "docs/telegram_vs_chain.json"

WINDOW_DAYS = 21
MIN_SYM_LEN = 3
# a post with fewer real characters than this is an image post, not a text post
MIN_TEXT_CHARS = 25


def jload(p):
    try:
        return json.loads(open(p).read())
    except Exception:
        return None


def dominant_action(entry):
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

    chain = (jload(CHAIN) or {}).get("stocks") or {}

    try:
        df = pd.read_parquet(MSGS)
    except Exception as e:
        print("no messages.parquet (%s)" % type(e).__name__)
        return 0
    if df.empty:
        print("messages.parquet is empty")
        return 0

    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce", utc=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=WINDOW_DAYS)
    recent = df[df["datetime"] >= cutoff].copy()
    if recent.empty:
        recent = df.sort_values("datetime").tail(200).copy()

    # how much of what was posted is even text?
    txt = recent["text"].fillna("").astype(str).str.strip()
    image_only = int((txt.str.len() < MIN_TEXT_CHARS).sum())

    word = re.compile(r"\b[A-Z][A-Z0-9&\-]{2,14}\b")
    mentions = []
    for _, r in recent.iterrows():
        t = str(r.get("text") or "")
        if len(t.strip()) < MIN_TEXT_CHARS:
            continue                      # an image post says nothing in text
        seen = set()
        for tok in word.findall(t):
            s = tok.strip("-&")
            if s in symbols and s not in seen:
                seen.add(s)
                mentions.append({
                    "symbol": s,
                    "channel": str(r.get("channel") or ""),
                    "datetime": (r["datetime"].strftime("%Y-%m-%d %H:%M")
                                 if pd.notna(r["datetime"]) else ""),
                    "views": (int(r["views"]) if pd.notna(r.get("views")) else None),
                })

    for m in mentions:
        rr = by_sym.get(m["symbol"]) or {}
        ch = rr.get("chg_1d")
        m["chg_1d"] = round(float(ch), 2) if ch is not None and pd.notna(ch) else None
        if m["symbol"] in chain:
            da = dominant_action(chain[m["symbol"]])
            if da:
                m["chain"] = da

    grouped = {}
    for m in mentions:
        g = grouped.setdefault(m["symbol"], {
            "symbol": m["symbol"], "mentions": 0, "channels": [],
            "chg_1d": m.get("chg_1d"), "chain": m.get("chain"), "latest": m,
        })
        g["mentions"] += 1
        if m["channel"] and m["channel"] not in g["channels"]:
            g["channels"].append(m["channel"])
        if m["datetime"] > (g["latest"].get("datetime") or ""):
            g["latest"] = m

    top = sorted(grouped.values(), key=lambda g: (-g["mentions"], g["symbol"]))[:40]

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": WINDOW_DAYS,
        "messages_in_window": int(len(recent)),
        "image_only_posts": image_only,
        "text_posts": int(len(recent) - image_only),
        "channels": sorted({str(c) for c in recent["channel"].dropna().unique()}),
        "mentions": len(mentions),
        "symbols": len(grouped),
        "with_chain": sum(1 for g in top if g.get("chain")),
        "top": top,
        "note": ("Stocks named in the last %d days of public Telegram channels, beside what the "
                 "same stock did that session and which side of its chain saw the largest "
                 "open-interest increase. A mention is not a prediction." % WINDOW_DAYS),
        "cautions": {
            "image_posts": ("%d of %d posts in this window carry no usable text - they are "
                            "screenshots, usually of a PCR table. Nothing is extracted from "
                            "those, so a silent channel may simply be an image-only channel."
                            % (image_only, len(recent))),
            "not_accuracy": ("Nothing here says whether a channel was right. That needs what "
                             "the stock did AFTER the post, which this file does not compute."),
            "text_only": ("Ticker matching runs on post text. A stock named in an image, or "
                          "spelled out in words, is not counted."),
            "copyright": ("Only the fact that a channel named a symbol is stored, with the "
                          "market's own numbers beside it. The posts themselves are not "
                          "reproduced here or on the site."),
        },
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %d messages (%d image-only, %d with text) · %d mentions · %d symbols · %d with chain"
          % (out["messages_in_window"], image_only, out["text_posts"],
             out["mentions"], out["symbols"], out["with_chain"]))
    for g in top[:6]:
        ch = g.get("chain") or {}
        print("     %-12s %dx  %s  %s"
              % (g["symbol"], g["mentions"],
                 ("%+.2f%%" % g["chg_1d"]) if g.get("chg_1d") is not None else "  -",
                 (ch.get("side", "") + " " + str(ch.get("action", ""))) if ch else "no chain"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
