#!/usr/bin/env python3
"""Take a channel's claim, and ask history how often anything like it happens.

WHY THIS EXISTS
A channel says "Nifty 26,000 soon". That is a claim with a number in it, which makes it
falsifiable - and almost nothing else a channel posts is. This converts the claim into the move
it implies, then asks a simpler question: over the last ten years, how often did the Nifty move
that far within that many sessions?

WHAT THIS IS NOT
It does not say the claim is wrong. A 60th-percentile move is entirely possible; it is just not
insight. The value is in replacing "soon" with a number.

METHOD
    implied move % = (target / current - 1) * 100
    base rate      = share of historical N-session windows whose move was at least that large
                     in the same direction
A claim whose implied move sits inside the middle of the historical distribution is ordinary.
One that requires the 99th percentile is a different kind of statement, and a reader deserves
to know which they are being sold.

CLAIMS ARE READ, NOT INVENTED
Only a target level written next to an index name is parsed. "Nifty 26,000" counts. "Market
will rise" does not, and is skipped rather than guessed at.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

import pandas as pd

IDX = "docs/index_history.json"
VIDEOS = "data/youtube/videos.csv"
MSGS = "data/telegram/messages.parquet"
OUT = "docs/claim_vs_base.json"

HORIZONS = [5, 21, 60]      # sessions: about a week, a month, a quarter
INDEX_NAMES = {"NIFTY": "NIFTY", "NIFTY50": "NIFTY", "NIFTY 50": "NIFTY",
               "BANKNIFTY": "BANKNIFTY", "BANK NIFTY": "BANKNIFTY", "SENSEX": "SENSEX"}
YMAP = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "SENSEX": "^BSESN"}


def jload(p):
    try:
        return json.loads(open(p).read())
    except Exception:
        return None


def load_bars():
    d = jload(IDX) or {}
    out = {}
    for ix in (d.get("indices") or []):
        sym = str(ix.get("symbol") or "")
        name = {"^NSEI": "NIFTY", "^NSEBANK": "BANKNIFTY", "^BSESN": "SENSEX"}.get(sym)
        if not name:
            continue
        rows = []
        for r in (ix.get("daily") or []):
            try:
                rows.append((str(r[0]), float(r[4])))
            except Exception:
                continue
        if rows:
            out[name] = sorted(rows)
    return out


def base_rates(closes, horizons):
    """For each horizon, the distribution of forward moves, as sorted percentages."""
    out = {}
    for h in horizons:
        moves = []
        for i in range(len(closes) - h):
            a, b = closes[i], closes[i + h]
            if a:
                moves.append((b / a - 1.0) * 100.0)
        moves.sort()
        out[h] = moves
    return out


def percentile_of(moves, target_pct):
    """Share of historical windows that moved at least this far in this direction."""
    if not moves:
        return None
    if target_pct >= 0:
        hit = sum(1 for m in moves if m >= target_pct)
    else:
        hit = sum(1 for m in moves if m <= target_pct)
    return round(hit / len(moves) * 100.0, 1)


# A NUMBER IS NOT A TARGET JUST BECAUSE IT SITS NEAR AN INDEX NAME.
# "Nifty fell to 22,500" and "Nifty support at 22,500" both contain a level, and neither is a
# claim about the future. A target needs a forward word within a short distance of the number.
FORWARD_CUES = ("TARGET", "SOON", "TOWARDS", "TOWARD", "LOADING", "COMING", "WILL",
                "EXPECT", "HEADING", "EYE", "EYES", "ON THE WAY", "CROSS", "BREAK")
BACKWARD_CUES = ("FELL TO", "DROPPED TO", "SLIPPED TO", "CLOSED AT", "SUPPORT AT",
                 "RESISTANCE AT", "BELOW", "ABOVE", "LAST CLOSED", "TODAY AT")


def find_claims(text, index, spot):
    """A target level written next to an index name, with a forward-looking word beside it."""
    t = str(text or "")
    up = t.upper()
    if index not in up:
        return []
    out = []
    for m in re.finditer(r"\b(\d{2},\d{3}|\d{4,6})\b", t):
        try:
            lvl = float(m.group(1).replace(",", ""))
        except Exception:
            continue
        if spot and not (0.85 * spot <= lvl <= 1.25 * spot):
            continue          # not plausibly a level for this index
        # the 45 characters either side decide whether this is a claim or a description
        window = up[max(0, m.start() - 45): m.end() + 45]
        if any(b in window for b in BACKWARD_CUES) and not any(f in window for f in FORWARD_CUES):
            continue
        if not any(f in window for f in FORWARD_CUES):
            continue          # no forward word at all: a level, not a target
        if spot:
            out.append({"target": lvl, "implied_pct": round((lvl / spot - 1.0) * 100.0, 2)})
    # de-duplicate on the target
    seen = set()
    uniq = []
    for c in out:
        if c["target"] in seen:
            continue
        seen.add(c["target"])
        uniq.append(c)
    return uniq


def main() -> int:
    bars = load_bars()
    if not bars:
        print("no index history - cannot compute base rates")
        return 0
    rates = {}
    spot = {}
    for name, rows in bars.items():
        closes = [c for _, c in rows]
        spot[name] = closes[-1]
        rates[name] = base_rates(closes, HORIZONS)

    sources = []

    # video titles
    try:
        v = pd.read_csv(VIDEOS)
        for _, r in v.iterrows():
            sources.append({"kind": "video", "channel": str(r.get("channel_name") or ""),
                            "when": str(r.get("published") or "")[:10],
                            "text": str(r.get("title") or ""),
                            "url": str(r.get("url") or "")})
    except Exception:
        pass

    # telegram posts
    try:
        m = pd.read_parquet(MSGS)
        for _, r in m.iterrows():
            sources.append({"kind": "telegram", "channel": str(r.get("channel") or ""),
                            "when": str(r.get("datetime") or "")[:10],
                            "text": str(r.get("text") or ""), "url": ""})
    except Exception:
        pass

    claims = []
    for s in sources:
        for name in INDEX_NAMES:
            idx = INDEX_NAMES[name]
            if idx not in rates:
                continue
            for c in find_claims(s["text"], name, spot.get(idx)):
                claims.append({
                    "channel": s["channel"], "kind": s["kind"], "when": s["when"],
                    "index": idx, "target": c["target"], "implied_pct": c["implied_pct"],
                    "spot": round(spot[idx], 2), "text": s["text"][:120], "url": s["url"],
                })

    # ONE CLAIM PER CHANNEL PER TARGET. The same "Nifty 22,500" appeared in three videos and
    # was counted three times, which made one claim look like a pattern.
    dedup = {}
    for c in claims:
        key = (c["channel"], c["index"], c["target"])
        prev = dedup.get(key)
        if not prev or (c.get("when") or "") > (prev.get("when") or ""):
            dedup[key] = c
    claims = list(dedup.values())

    # attach the base rate at each horizon
    for c in claims:
        rr = rates.get(c["index"]) or {}
        c["base_rate"] = {}
        for h in HORIZONS:
            moves = rr.get(h) or []
            c["base_rate"][h] = {
                "pct": percentile_of(moves, c["implied_pct"]),
                "n": len(moves),
            }

    # rank by how remarkable the claim is at 21 sessions - lowest base rate first
    claims.sort(key=lambda c: (c["base_rate"].get(21, {}).get("pct") or 999))
    top = [c for c in claims if c["base_rate"].get(21, {}).get("pct") is not None][:25]

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "horizons": HORIZONS,
        "claims_found": len(claims),
        "sources_scanned": len(sources),
        "spot": {k: round(v, 2) for k, v in spot.items()},
        "claims": top,
        "note": ("A channel's stated target level, converted into the move it implies, beside "
                 "the share of historical windows that moved at least that far in the same "
                 "direction. It does not say the claim is wrong - a 60th-percentile move is "
                 "possible, it is just not insight. The value is in replacing 'soon' with a "
                 "number."),
        "cautions": {
            "not_a_verdict": ("A claim is not scored as right or wrong. Only the size of the "
                              "move it requires is measured against history."),
            "text_only": ("Only a target level written next to an index name is parsed. "
                          "'Market will rise' is skipped, not guessed at."),
            "survivorship": ("The index history is the Nifty itself, so it carries no "
                             "survivorship problem - but ten years is one regime, not all of them."),
        },
    }
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %d sources scanned, %d claims parsed" % (len(sources), len(claims)))
    for c in top[:8]:
        b = c["base_rate"].get(21) or {}
        print("     %-12s %s -> %s (%+.1f%%) · 21-session base rate %s%% (n=%s)"
              % (c["channel"][:12], c["index"], "{:,.0f}".format(c["target"]),
                 c["implied_pct"], b.get("pct"), b.get("n")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
