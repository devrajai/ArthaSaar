#!/usr/bin/env python3
"""Lead-lag: what the prior US session does to India's next one.

THE IDEA
India trades and closes before the US session finishes. So the US move on calendar date D is
only partly reflected in India's D session, and fully reflected in India's NEXT session. If
that transmission is strong enough, it is the one timing relationship an Indian investor can
actually act on: the US closes at 1:30 AM IST, India opens at 9:15 AM IST.

WHAT IT MEASURES
  * the correlation between the prior S&P session and Nifty's next session
  * the conditional distribution of Nifty's next move, bucketed by how big the US move was
  * the same for other markets that close before India's next open

WHAT IT FOUND (10 years, 2,511 sessions)
  correlation, prior S&P vs Nifty next session   +0.263
  R-squared                                       6.9%  - the US explains ~7% of the move

  That sounds weak, and on an average day it is. The relationship lives in the TAILS:

    S&P prior move      n      Nifty next session
    up   > +2%          63     73% up,   mean +0.69%
    up   +1..2%        271     67% up,   mean +0.37%
    flat -1..+1%      1899     55% up,   mean +0.06%
    down -1..-2%       191     33% up,   mean -0.41%
    down < -2%          87     31% up,   mean -0.76%
    down < -3%          32     16% up,   mean -1.63%

WHAT THIS IS NOT
A forecast. It is a conditional base rate with the sample size attached, and the big-move
buckets are thin - 32 observations for the <-3% case. It also cannot see what happens between
the US close and the Indian open: an Asian selloff, a currency move or a domestic headline can
override it entirely, and often does.
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

OUT = "docs/leadlag.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"}

# Markets whose session ends BEFORE India's next open, so their move is transmitted overnight.
LEADERS = [
    ("^GSPC", "S&P 500 (US)"),
    ("^IXIC", "Nasdaq (US)"),
    ("^DJI", "Dow (US)"),
    ("^FTSE", "FTSE 100 (London)"),
    ("^GDAXI", "DAX (Germany)"),
    ("^FCHI", "CAC 40 (France)"),
    ("^STOXX50E", "Euro Stoxx 50"),
    ("^HSI", "Hang Seng (HK)"),
    ("^N225", "Nikkei (Japan)"),
]
TARGET = ("^NSEI", "Nifty 50")

BUCKETS = [
    ("up > +2%", lambda a: a > 2),
    ("up +1 to +2%", lambda a: 1 < a <= 2),
    ("up 0 to +1%", lambda a: 0 < a <= 1),
    ("down 0 to -1%", lambda a: -1 <= a < 0),
    ("down -1 to -2%", lambda a: -2 <= a < -1),
    ("down < -2%", lambda a: a < -2),
    ("down < -3%", lambda a: a < -3),
]


def closes(symbol, rng="10y"):
    import datetime as dt
    u = ("https://query1.finance.yahoo.com/v8/finance/chart/"
         + urllib.parse.quote(symbol) + "?interval=1d&range=" + rng)
    try:
        j = json.loads(urllib.request.urlopen(
            urllib.request.Request(u, headers=UA), timeout=60).read())
        r = j["chart"]["result"][0]
        q = r["indicators"]["quote"][0]
        return {dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d"): c
                for t, c in zip(r["timestamp"], q["close"]) if c is not None}
    except Exception:
        return {}


def returns(series):
    d = sorted(series)
    return {d[i]: (series[d[i]] / series[d[i - 1]] - 1) * 100 for i in range(1, len(d))}


def corr(pairs):
    xs = [a for a, _ in pairs]
    ys = [b for _, b in pairs]
    n = len(xs)
    if n < 30:
        return None, n
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = sum((a - mx) ** 2 for a in xs) ** 0.5
    dy = sum((b - my) ** 2 for b in ys) ** 0.5
    return (num / (dx * dy) if dx and dy else None), n


def main():
    import statistics as st

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "target": TARGET[1], "leaders": [], "buckets": [], "note": ""}

    tgt = closes(TARGET[0])
    rt = returns(tgt)
    tgt_dates = sorted(rt)
    if len(tgt_dates) < 200:
        out["note"] = "Nifty history unavailable."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("leadlag: no Nifty data")
        return 0

    def next_target(d):
        for x in tgt_dates:
            if x > d:
                return x
        return None

    for sym, name in LEADERS:
        rs = returns(closes(sym))
        if not rs:
            continue
        pairs = [(rs[d], rt[next_target(d)]) for d in rs if next_target(d)]
        c, n = corr(pairs)
        if c is None:
            continue
        out["leaders"].append({"symbol": sym, "name": name,
                               "correlation": round(c, 3),
                               "r_squared_pct": round(c * c * 100, 1), "n": n})
        if sym == "^GSPC":
            # the bucket table, for the market that transmits most
            for label, cond in BUCKETS:
                sel = [b for a, b in pairs if cond(a)]
                if len(sel) < 10:
                    continue
                up = [v for v in sel if v > 0]
                dn = [v for v in sel if v <= 0]
                out["buckets"].append({
                    "label": label, "n": len(sel),
                    "mean_pct": round(st.mean(sel), 2),
                    "up_pct": round(len(up) / len(sel) * 100, 0),
                    "up_median": round(st.median(up), 2) if up else None,
                    "down_pct": round(len(dn) / len(sel) * 100, 0),
                    "down_median": round(st.median(dn), 2) if dn else None,
                    "worst": round(min(sel), 2),
                })

    if not out["leaders"]:
        out["note"] = "No leader series available."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("leadlag: no leader data")
        return 0

    out["leaders"].sort(key=lambda x: -x["correlation"])

    # ---- what the most recent US session implies for the next Indian open ---------------
    # This is the live, actionable form of the study: not "the correlation is 0.26" but
    # "the S&P fell 1.8% overnight, and after a fall that size Nifty's next session was down
    # 69% of the time". It is a base rate, not a forecast - the site says so.
    sp = returns(closes("^GSPC"))
    if sp and out["buckets"]:
        last_date = max(sp)
        last_move = sp[last_date]
        label = None
        for lbl, cond in BUCKETS:
            try:
                if cond(last_move):
                    label = lbl
                    break
            except Exception:
                continue
        bucket = next((b for b in out["buckets"] if b["label"] == label), None)
        out["latest"] = {
            "us_date": last_date,
            "us_move_pct": round(last_move, 2),
            "bucket": label or "outside the studied range",
            "n": (bucket or {}).get("n"),
            "up_pct": (bucket or {}).get("up_pct"),
            "down_pct": (bucket or {}).get("down_pct"),
            "mean_pct": (bucket or {}).get("mean_pct"),
            "worst": (bucket or {}).get("worst"),
        }
    out["note"] = ("How each market's session relates to Nifty's NEXT session. India closes "
                   "before the US does, so the US move lands the following morning.")
    out["cautions"] = {
        "not_a_forecast": ("A conditional base rate, not a prediction. The prior US session "
                           "explains about 7% of Nifty's next move on an average day."),
        "tails_only": ("The relationship is weak on average and only sharp in the tails. "
                       "The big-move buckets are thin - 32 observations for S&P down >3%."),
        "overnight_gap": ("This cannot see what happens between the US close and the Indian "
                          "open. An Asian selloff, a currency move or a domestic headline "
                          "overrides it regularly."),
        "alignment": ("US date D is matched to India's first session after D. India trades "
                      "before the US closes on D, so the same-date correlation is not the "
                      "transmission effect."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("\ncorrelation with Nifty's NEXT session:")
    for l in out["leaders"]:
        print("  %-24s %+.3f  (R2 %.1f%%, n=%d)" % (l["name"], l["correlation"],
                                                     l["r_squared_pct"], l["n"]))
    if out["buckets"]:
        print("\nNifty next session, by prior S&P move:")
        for b in out["buckets"]:
            print("  %-16s n=%-4d mean %+6.2f%%  %3.0f%% up  %3.0f%% down  worst %+.2f"
                  % (b["label"], b["n"], b["mean_pct"], b["up_pct"], b["down_pct"], b["worst"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
