#!/usr/bin/env python3
"""Score the Telegram channels' own calls against what the index actually did.

WHY THIS EXISTS
sureshsharma1 posts structured intraday calls:

    17.11.2026 NIFTY50 25291.10 Intraday (spot): buy @ 25230 + 25163
    (buy ce 25200, 23.11.2026) SL 25090 T 25365 + 25420  sell @ 25424 (buy pe 25400 ...)

Entry, strike, expiry, stoploss and target are all in the text. That makes the calls
falsifiable, which almost nothing else on these channels is. This file parses them, waits
until the sessions have actually happened, and reports how many were right.

HOW A CALL IS SCORED
For each session after the post, in order:
    - the buy entry fills if the low reaches the entry price
    - once filled, the stoploss and the first target are both live
    - whichever the price reaches FIRST decides the outcome
If neither is reached within the lookahead window, the call is 'open', not a win.

WHAT IS NOT SCORED
The premium, the option leg, and the charges. A call can be right on the index and still lose
money on the instrument it named - this measures the index call only, and says so.

WHY THIS IS THE MOST USEFUL FILE IN THE PIPELINE
A channel's own claims are the only thing it can be held to. Everything else it posts - a
screenshot, a "rocked", a "get ready" - cannot be checked. These can.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

import pandas as pd

MSGS = "data/telegram/messages.parquet"
IDX = "docs/index_history.json"
OUT = "docs/telegram_accuracy.json"

LOOKAHEAD = 5          # sessions after the post to resolve a call
MIN_SCORED = 10        # below this, report the count and refuse a hit rate


def jload(p):
    try:
        return json.loads(open(p).read())
    except Exception:
        return None


def num(s):
    try:
        return float(str(s).replace(",", "").strip())
    except Exception:
        return None


def parse_call(text):
    """Pull a structured index call out of a post. Returns None if it is not one."""
    t = str(text or "")
    if "SL" not in t.upper() or "T " not in t.upper():
        return None
    m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", t)
    if not m:
        return None
    day = "%s-%s-%s" % (m.group(3), m.group(2), m.group(1))

    inst = None
    for name in ("NIFTY50", "NIFTY", "BANKNIFTY", "SENSEX"):
        if name in t.upper():
            inst = "NIFTY" if name in ("NIFTY50", "NIFTY") else name
            break
    if not inst:
        return None

    buy = re.search(r"buy\s*@\s*([\d\s+.,]+)", t, re.I)
    sl = re.search(r"SL\s*([\d.,]+)", t, re.I)
    tgt = re.search(r"\bT\s*([\d\s+.,]+)", t)
    if not (buy and sl and tgt):
        return None

    def first_number(s):
        n = re.findall(r"\d[\d,]*\.?\d*", s)
        return num(n[0]) if n else None

    entry = first_number(buy.group(1))
    stop = first_number(sl.group(1))
    target = first_number(tgt.group(1))
    if not (entry and stop and target):
        return None
    # A long call has the stop below the entry and the target above it. When a post breaks
    # that, keep it and flag it rather than dropping it: sureshsharma1's Sensex call on
    # 17 Nov reads "buy @ 81921 SL 81435 T 81330 + 81500", which puts the targets BELOW the
    # stoploss. Silently discarding it would hide a real defect in the channel's own post.
    consistent = stop < entry < target

    strike = re.search(r"buy\s+(ce|pe)\s*([\d.,]+)", t, re.I)
    return {
        "date": day, "index": inst, "entry": entry, "stop": stop, "target": target,
        "leg": (strike.group(1).upper() if strike else None),
        "strike": (num(strike.group(2)) if strike else None),
        "consistent": consistent,
    }


def main() -> int:
    try:
        df = pd.read_parquet(MSGS)
    except Exception as e:
        print("no messages.parquet (%s)" % type(e).__name__)
        return 0
    if df.empty:
        print("messages.parquet is empty")
        return 0

    idx = jload(IDX) or {}
    bars = {}
    for ix in (idx.get("indices") or []):
        sym = str(ix.get("symbol") or "")
        key = {"^NSEI": "NIFTY", "^NSEBANK": "BANKNIFTY", "^BSESN": "SENSEX"}.get(sym)
        if not key:
            continue
        rows = []
        for d in (ix.get("daily") or []):
            try:
                rows.append({"date": d[0], "open": float(d[1]), "high": float(d[2]),
                             "low": float(d[3]), "close": float(d[4])})
            except Exception:
                continue
        if rows:
            bars[key] = sorted(rows, key=lambda r: r["date"])

    claims = []
    for _, r in df.iterrows():
        c = parse_call(r.get("text"))
        if not c:
            continue
        c["channel"] = str(r.get("channel") or "")
        c["posted"] = (pd.to_datetime(r.get("datetime"), errors="coerce", utc=True)
                       .strftime("%Y-%m-%d %H:%M") if pd.notna(r.get("datetime")) else "")
        claims.append(c)

    inconsistent = [c for c in claims if not c.get("consistent")]
    claims = [c for c in claims if c.get("consistent")]

    scored = []
    for c in claims:
        series = bars.get(c["index"]) or []
        after = [b for b in series if b["date"] > c["date"]][:LOOKAHEAD]
        if not after:
            c["outcome"] = "open"
            c["detail"] = "no sessions after the post yet"
            scored.append(c)
            continue
        filled = False
        outcome = "open"
        detail = "entry never filled"
        for b in after:
            if not filled:
                if b["low"] <= c["entry"]:
                    filled = True
                else:
                    continue
            # both live from the fill
            hit_stop = b["low"] <= c["stop"]
            hit_tgt = b["high"] >= c["target"]
            if hit_stop and hit_tgt:
                outcome = "ambiguous"
                detail = "%s touched both the stop and the target in one session" % b["date"]
                break
            if hit_stop:
                outcome = "loss"
                detail = "stop %s hit on %s" % (c["stop"], b["date"])
                break
            if hit_tgt:
                outcome = "win"
                detail = "target %s hit on %s" % (c["target"], b["date"])
                break
        c["outcome"] = outcome
        c["detail"] = detail
        scored.append(c)

    resolved = [c for c in scored if c["outcome"] in ("win", "loss", "ambiguous")]
    wins = sum(1 for c in resolved if c["outcome"] == "win")
    losses = sum(1 for c in resolved if c["outcome"] == "loss")

    by_channel = {}
    for c in scored:
        g = by_channel.setdefault(c["channel"], {"parsed": 0, "resolved": 0, "win": 0,
                                                 "loss": 0, "open": 0, "ambiguous": 0})
        g["parsed"] += 1
        if c["outcome"] in ("win", "loss"):
            g["resolved"] += 1
            g["win" if c["outcome"] == "win" else "loss"] += 1
        elif c["outcome"] == "ambiguous":
            g["ambiguous"] += 1
        else:
            g["open"] += 1
    for g in by_channel.values():
        g["hit_rate_pct"] = (round(g["win"] / g["resolved"] * 100.0, 1)
                             if g["resolved"] >= MIN_SCORED else None)

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lookahead_sessions": LOOKAHEAD,
        "min_for_hit_rate": MIN_SCORED,
        "calls_parsed": len(claims),
        "calls_inconsistent": len(inconsistent),
        "inconsistent_examples": [
            {"channel": c["channel"], "posted": c["posted"], "index": c["index"],
             "entry": c["entry"], "stop": c["stop"], "target": c["target"]}
            for c in inconsistent[:5]],
        "calls_resolved": len(resolved),
        "wins": wins,
        "losses": losses,
        "hit_rate_pct": (round(wins / (wins + losses) * 100.0, 1) if (wins + losses) else None),
        "by_channel": by_channel,
        "recent": sorted(scored, key=lambda c: c.get("posted") or "", reverse=True)[:25],
        "note": ("Structured intraday index calls parsed from public channel posts and scored "
                 "against the index's own daily bars. A call fills at its stated entry, then "
                 "whichever of the stated stoploss or first target the price reaches first "
                 "decides it. Calls still open are counted separately, not as wins."),
        "cautions": {
            "index_only": ("Only the INDEX call is scored. The option leg, the premium paid and "
                           "the charges are not modelled - a call can be right on the index and "
                           "still lose money on the instrument it named."),
            "daily_bars": ("Scoring uses daily high and low, so intraday sequence is unknown. "
                           "When one session touches both the stop and the target the call is "
                           "marked ambiguous and excluded from the hit rate rather than guessed."),
            "small_sample": ("Below %d resolved calls no hit rate is published. A 3-of-4 run is "
                             "not a track record." % MIN_SCORED),
            "inconsistent": ("A call whose target sits on the wrong side of its own stoploss "
                             "is counted separately, not scored. It is not a bad outcome, it is "
                             "a post that cannot be acted on as written."),
            "unparseable": ("Only posts containing an entry, an SL and a target are parsed. "
                            "Vague posts - 'rocked', 'get ready' - cannot be scored and are not "
                            "counted against the channel either."),
        },
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   parsed %d calls · resolved %d · win %d / loss %d · inconsistent %d"
          % (len(claims), len(resolved), wins, losses, len(inconsistent)))
    for ch, g in by_channel.items():
        hr = ("%.1f%%" % g["hit_rate_pct"]) if g["hit_rate_pct"] is not None else "not enough yet"
        print("     %-16s parsed %2d · resolved %2d · W%d/L%d · hit rate %s"
              % (ch, g["parsed"], g["resolved"], g["win"], g["loss"], hr))
    for c in out["recent"][:4]:
        print("     %s %s buy %.0f SL %.0f T %.0f -> %s"
              % (c.get("posted", "")[:10], c["index"], c["entry"], c["stop"],
                 c["target"], c["outcome"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
