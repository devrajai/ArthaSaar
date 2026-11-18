#!/usr/bin/env python3
"""Classify the news feed so the page can filter it.

WHY THIS EXISTS
docs/data.json carries 30 headlines from ET Markets with a source, a title, a link and a time -
and nothing else. A page that wants tabs (All / Results / General / Global) needs a category,
and a page that wants a company chip needs the company.

HOW CLASSIFICATION WORKS
By keyword on the headline, and it says so. This is a keyword classifier, not a model:
    results   - results, earnings, Q1-Q4, profit, revenue, margin, guidance
    global    - US, Fed, Trump, China, global, S&P, Nasdaq, oil, dollar
    policy    - SEBI, RBI, regulator, policy, circular, tax
    general   - everything else
A headline can match several; the first match in that order wins. Every item keeps the
category it was given and the word that triggered it, so a wrong tag is visible rather than
silent.

COMPANY MATCHING
Against the real symbol list in screener.json, on the company's first distinctive word. A
headline that names no listed company gets no chip - it does not get a guess.
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
from datetime import datetime, timezone

DATA = "docs/data.json"
SCREENER = "docs/screener.json"
OUT = "docs/news_feed.json"

CATS = [
    ("results", ["results", "earnings", "profit", "revenue", "margin", "guidance",
                 "q1 ", "q2 ", "q3 ", "q4 ", "fy2", "net loss", "beats", "misses"]),
    ("global", ["u.s.", "us ", "fed", "trump", "china", "global", "s&p", "nasdaq",
                "wall street", "dollar", "oil", "opec", "europe", "japan"]),
    ("policy", ["sebi", "rbi", "regulator", "policy", "circular", "tax", "budget",
                "tariff", "gst", "ipo approval"]),
]


def jload(p):
    try:
        return json.loads(open(p).read())
    except Exception:
        return None


def classify(title):
    # unescape first: the feed carries "S&amp;P 500", and a raw entity means the "s&p" keyword
    # never matches. One headline was filed as general for exactly this reason.
    import html
    t = " " + html.unescape(str(title)).lower() + " "
    for name, words in CATS:
        for w in words:
            if w in t:
                return name, w.strip()
    return "general", ""


def main() -> int:
    d = jload(DATA) or {}
    news = d.get("news") or {}
    cols = [str(c).strip().lower() for c in (news.get("columns") or [])]
    rows = news.get("rows") or []
    if not rows:
        print("no news rows")
        return 0

    def ix(name, default=None):
        return cols.index(name) if name in cols else default

    i_src, i_title, i_link = ix("source", 0), ix("title", 1), ix("link", 2)
    i_pub = ix("published")

    # COMPANY MATCHING BY FULL NAME, NOT BY ONE WORD.
    #
    # A single-word index produced nonsense: "Trump Media" matched HT Media, "Share Price"
    # matched Share India Securities, "Morgan Stanley" matched Stanley Lifestyles, "capital
    # gains" matched Capital Trust. Every one of those would have put a wrong company chip on a
    # headline, which is worse than no chip.
    #
    # So the match is now on the company's NAME as a phrase, with the legal suffix stripped:
    # "Dabur India Limited" becomes "Dabur India", and only that phrase counts. "Swiggy" is one
    # word and distinctive enough to stand alone; "Summit" is not and never appears alone.
    scr = jload(SCREENER) or {}
    phrases = []
    SUFFIX = re.compile(r"\b(LIMITED|LTD|PRIVATE|PVT|INDIA|INDUSTRIES|INDUSTRIAL|"
                        r"SERVICES|TECHNOLOGIES|TECHNOLOGY|CORPORATION|CORP|COMPANY|"
                        r"ENTERPRISES|HOLDINGS|GROUP|AND|&)\b", re.I)
    for r in (scr.get("rows") or []):
        nm = html.unescape(str(r.get("name") or "")).strip()
        sym = str(r.get("symbol") or "").upper()
        if not nm or not sym:
            continue
        core = SUFFIX.sub(" ", nm)
        core = re.sub(r"\s+", " ", core).strip(" ,.-")
        if len(core) < 5:
            continue
        phrases.append((core, sym))
    # longest phrase first, so "Dabur India" wins over a hypothetical "Dabur"
    phrases.sort(key=lambda x: -len(x[0]))

    items = []
    for r in rows:
        try:
            title = str(r[i_title])
            src = str(r[i_src])
            link = str(r[i_link])
            pub = str(r[i_pub]) if i_pub is not None and i_pub < len(r) else ""
        except Exception:
            continue
        cat, cue = classify(title)
        comp = None
        raw = html.unescape(title)
        low = raw.lower()
        for phrase, sym in phrases:
            if phrase.lower() in low:
                # require word boundaries so "ITC" does not match inside "switch"
                pat = r"(?<![A-Za-z])" + re.escape(phrase) + r"(?![A-Za-z])"
                if re.search(pat, raw, re.I):
                    comp = sym
                    break
        items.append({
            "title": title, "source": src, "link": link, "published": pub,
            "category": cat, "cue": cue, "company": comp,
        })

    counts = {}
    for it in items:
        counts[it["category"]] = counts.get(it["category"], 0) + 1

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(items),
        "counts": counts,
        "items": items,
        "note": ("Headlines from the sources the pipeline already collects, tagged by keyword. "
                 "A tag is a description of the words in the headline, not an editorial "
                 "judgement, and each item keeps the word that triggered it."),
        "cautions": {
            "keyword_classifier": ("Categories come from a keyword list, not a model. A "
                                   "headline can belong to more than one and the first match "
                                   "wins."),
            "no_company_guess": ("A company chip appears only when the headline names a listed "
                                 "company. No chip is better than a wrong one."),
            "source": ("Headlines and links belong to the publishers named on each item."),
        },
    }
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("-> %s  %.1f KB | %d items" % (OUT, os.path.getsize(OUT) / 1024, len(items)))
    print("   counts:", counts)
    for it in items[:4]:
        print("     [%-8s] %-12s %s" % (it["category"], it["company"] or "-", it["title"][:62]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
