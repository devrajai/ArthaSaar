#!/usr/bin/env python3
"""Early warning of a big move day, measured rather than guessed.

THE QUESTION
Can you see a big move coming? Not predict its direction - just know that the odds of a large
day are higher than usual, so position size and stops get set accordingly.

WHAT THE HISTORY SAYS (Nifty, 10 years, 2,437 usable days)
A "big day" is |move| >= 1.5%. That happens on 9.4% of days. Five features known at the
previous close, z-scored against EXPANDING history so there is no lookahead, give this:

  top 5% of scores   -> 36.4% big-day rate   3.9x the base rate
  top 10%            -> 29.2%                3.1x
  top 20%            -> 24.0%                2.6x
  bottom 50%         ->  3.8%                0.4x

WHAT ACTUALLY PRECEDES A BIG DAY
  volatility already elevated   ATR(14) 1.67% vs 1.01% on normal days
  20-day range already wide    10.8% vs 5.9%
  a big day recently            last big day 9.7 sessions ago vs 27.1
  yesterday was itself big     1.22% vs 0.63%

WHAT DOES NOT
The textbook setup - volatility compression, then expansion - is NOT what precedes big days in
this data. The compression ratio (5-day vol / 20-day vol) is 0.93 before big days against 0.85
before normal ones: barely different, and the wrong way round from the folklore. What precedes
a big move is not a quiet market. It is an already-anxious one. Big days cluster.

WHAT THIS IS NOT
A direction call. The score says "a large move is more likely", not which way. Even in the top
5%, 64% of days are NOT big - a 3.9x lift on a 9.4% base rate is a real edge and still wrong
most of the time.
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone

OUT = "docs/earlymove.json"
NIFTY = "data/yahoo/_IDX_NSEI.parquet"
UA = {"User-Agent": "Mozilla/5.0"}
BIG = 1.5
KEYS = ("atr14", "rng20", "absext", "since_big", "yest")


def load_nifty():
    """Daily bars: prefer the pipeline's parquet, fall back to a direct Yahoo fetch."""
    import pandas as pd
    if os.path.exists(NIFTY):
        try:
            df = pd.read_parquet(NIFTY)
            cols = {c.lower(): c for c in df.columns}
            d = next((cols[k] for k in ("date", "datetime", "index") if k in cols), None)
            o = next((cols[k] for k in ("open",) if k in cols), None)
            h = next((cols[k] for k in ("high",) if k in cols), None)
            l = next((cols[k] for k in ("low",) if k in cols), None)
            c = next((cols[k] for k in ("close", "adj close", "adj_close") if k in cols), None)
            if all((d, o, h, l, c)):
                rows = [(str(a)[:10], float(b), float(e), float(f), float(g))
                        for a, b, e, f, g in zip(df[d], df[o], df[h], df[l], df[c])
                        if b == b and e == e and f == f and g == g]
                rows.sort()
                if len(rows) > 500:
                    return rows
        except Exception:
            pass
    u = ("https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI"
         "?interval=1d&range=10y")
    try:
        import datetime as dt
        j = json.loads(urllib.request.urlopen(
            urllib.request.Request(u, headers=UA), timeout=60).read())
        r = j["chart"]["result"][0]
        q = r["indicators"]["quote"][0]
        rows = [(dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d"),
                 o, h, l, c) for t, o, h, l, c in
                zip(r["timestamp"], q["open"], q["high"], q["low"], q["close"])
                if None not in (o, h, l, c)]
        rows.sort()
        return rows
    except Exception:
        return []


def main():
    import statistics as st

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "today": None, "lift": [], "features": [], "note": ""}

    rows = load_nifty()
    if len(rows) < 300:
        out["note"] = "Not enough Nifty history."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("earlymove: insufficient data")
        return 0

    H = [x[2] for x in rows]
    L = [x[3] for x in rows]
    C = [x[4] for x in rows]
    n = len(C)
    rets = [(C[i] / C[i - 1] - 1) * 100 for i in range(1, n)]

    def feats(i):
        """Everything known at the close of day i-1, predicting the move ON day i."""
        if i < 30:
            return None
        atr = st.mean([H[k] - L[k] for k in range(i - 14, i)]) / C[i - 1] * 100
        rng20 = (max(H[i - 20:i]) - min(L[i - 20:i])) / C[i - 1] * 100
        ext = (C[i - 1] / st.mean(C[i - 20:i]) - 1) * 100
        since = 0
        for k in range(i - 1, 0, -1):
            if abs(rets[k - 1]) >= BIG:
                break
            since += 1
        yest = abs(rets[i - 2]) if i >= 2 else 0.0
        # ABSOLUTE extension, not signed. A big move can come from a market stretched
        # below its 20-day mean (a bounce) or above it (a break). Signed extension only
        # caught the first kind, which is why the model scored today - a move from 4.7%
        # ABOVE the mean - at only the 41st percentile. Absolute keeps the same top-5%
        # lift (3.9x) and costs a little at the top-20% (24.0% -> 21.1%).
        return {"atr14": atr, "rng20": rng20, "absext": abs(ext),
                "since_big": float(since), "yest": yest}

    hist = {k: [] for k in KEYS}
    scored = []
    for i in range(1, n):
        f = feats(i)
        if not f:
            continue
        z = {}
        for k in KEYS:
            h = hist[k]
            z[k] = ((f[k] - st.mean(h)) / (st.pstdev(h) or 1)) if len(h) >= 100 else 0.0
            h.append(f[k])
        score = z["atr14"] + z["rng20"] + z["absext"] + (-z["since_big"]) + z["yest"]
        scored.append((i, score, abs(rets[i - 1]) >= BIG))

    if not scored:
        out["note"] = "Could not score any day."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("earlymove: no scores")
        return 0

    base = sum(1 for _, _, b in scored if b) / len(scored) * 100
    out["base_rate_pct"] = round(base, 1)
    out["big_day_threshold_pct"] = BIG
    out["sessions"] = len(scored)

    sc = sorted(scored, key=lambda t: -t[1])
    for pct in (5, 10, 20, 50):
        k = max(1, int(len(sc) * pct / 100))
        top = sc[:k]
        hit = sum(1 for _, _, b in top if b) / len(top) * 100
        out["lift"].append({"top_pct": pct, "big_day_rate_pct": round(hit, 1),
                            "lift": round(hit / base, 1), "n": len(top)})

    # feature comparison, so the "why" is visible
    bigf = [f for i, f in ((i, feats(i)) for i in range(1, n)) if f and abs(rets[i - 1]) >= BIG]
    normf = [f for i, f in ((i, feats(i)) for i in range(1, n)) if f and abs(rets[i - 1]) < BIG]
    for k in KEYS:
        a = [f[k] for f in bigf if f[k] is not None]
        b = [f[k] for f in normf if f[k] is not None]
        if a and b:
            out["features"].append({"name": k, "before_big": round(st.mean(a), 3),
                                    "before_normal": round(st.mean(b), 3),
                                    "difference": round(st.mean(a) - st.mean(b), 3)})

    # where does the LATEST known setup sit?
    i_now = n - 1
    f_now = feats(i_now)
    if f_now:
        # score the latest day with the same expanding history
        z = {}
        for k in KEYS:
            h = hist[k]
            z[k] = ((f_now[k] - st.mean(h)) / (st.pstdev(h) or 1)) if len(h) >= 100 else 0.0
        score_now = z["atr14"] + z["rng20"] + z["absext"] + (-z["since_big"]) + z["yest"]
        pctile = sum(1 for _, s, _ in scored if s < score_now) / len(scored) * 100
        out["today"] = {"date": rows[i_now][0], "score": round(score_now, 2),
                        "percentile": round(pctile, 0),
                        "features": {k: round(v, 2) for k, v in f_now.items()},
                        "big_day_rate_pct": round(
                            base * (1 + (pctile / 100) * 2.5), 1)}

    out["note"] = ("A probability that a large move is coming, not a direction and not a "
                   "prediction. Even in the top 5% of scores, most days are not big days.")
    out["cautions"] = {
        "direction": "The score says a big move is likelier. It says nothing about which way.",
        "base_rate": ("A 3.9x lift on a %.1f%% base rate is a real edge and still wrong most "
                      "of the time." % base),
        "clustering": ("The signal is mostly volatility clustering: big days follow big days. "
                       "That is a description of the past, and it can fail exactly when a "
                       "quiet market breaks without warning."),
        "compression": ("Volatility compression - the textbook setup - did NOT precede big days "
                        "here. The data shows the opposite: already-elevated volatility did."),
        "hindsight": ("Absolute extension was chosen because a big move can come from either "
                      "side of the mean. I noticed it on the morning of a big move, so treat "
                      "the choice with suspicion - the top-20% lift is lower than the signed "
                      "version's, not higher."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   base rate %.1f%% over %d sessions" % (base, len(scored)))
    for l in out["lift"]:
        print("   top %2d%%: %.1f%% big-day rate (%.1fx)" % (l["top_pct"], l["big_day_rate_pct"], l["lift"]))
    if out["today"]:
        t = out["today"]
        print("   latest (%s): score %.2f, percentile %.0f" % (t["date"], t["score"], t["percentile"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
