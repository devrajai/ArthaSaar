#!/usr/bin/env python3
"""Commodities, the gold-silver ratio, and the correlation that explains recent moves.

WHY THIS EXISTS
Gold fell 2.7% and silver 8.6% in the week to 30 October 2026, the worst October for both
since 2008. The explanation that circulated - "a stronger dollar and rising yields" - did not
fit the data: the dollar index was flat and the 10-year yield fell that week. What actually
happened is that gold traded like a tech stock: its daily correlation with Nasdaq futures ran
near +0.77, while its correlation with the dollar collapsed to about -0.09.

That is the point of this file. It publishes the ratio and the correlations so a claim about
why metals moved can be checked against numbers rather than accepted from a headline.

READS
data/yahoo/GC=F.parquet, SI=F.parquet, CL=F.parquet, ^IXIC.parquet, DX-Y.NYB.parquet
(all produced by scripts/fetch_yahoo.py --group commodities)

WRITES
docs/commodities.json
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _yahoo_paths import find_parquet
from datetime import datetime, timezone

YAHOO = "data/yahoo"
OUT = "docs/commodities.json"

# symbol -> (label, unit)
COMMODITIES = [
    ("GC=F", "Gold", "$/oz"),
    ("SI=F", "Silver", "$/oz"),
    ("CL=F", "WTI crude", "$/bbl"),
    ("BZ=F", "Brent crude", "$/bbl"),
    ("HG=F", "Copper", "$/lb"),
]
CONTEXT = [("^IXIC", "Nasdaq Composite"), ("DX-Y.NYB", "Dollar index")]


def load(sym):
    """Daily closes as {date_str: close} from the pipeline's parquet."""
    import pandas as pd
    # THREE naming conventions exist in this repo and they do not agree. Looking for only
    # the legacy one meant this script reported "no commodity parquet found" on every run,
    # forever, while fetch_yahoo was writing perfectly good files next to it.
    #   fetch_yahoo._safe()  re.sub(r"[^A-Za-z0-9]+","_",sym).strip("_")  -> "GC_F"
    #   legacy pipeline      ^ -> _IDX_, = -> _EQ_, . -> _                -> "GC_EQ_F"
    #   Colab                ^ -> IDX_                                   -> "GC_F"
    import re as _re
    names = []
    for base in (_re.sub(r"[^A-Za-z0-9]+", "_", sym).strip("_"),
                 sym.replace("^", "_IDX_").replace("=", "_EQ_").replace(".", "_"),
                 sym.replace("^", "IDX_").replace("=", "EQ_").replace(".", "_"),
                 sym):
        names += [base + ".parquet", "us_" + base + ".parquet"]
    for name in names:
        p = os.path.join(YAHOO, name)
        if os.path.exists(p):
            df = pd.read_parquet(p)
            cols = {c.lower(): c for c in df.columns}
            dcol = next((cols[k] for k in ("date", "datetime", "index") if k in cols), None)
            ccol = next((cols[k] for k in ("close", "adj close", "adj_close") if k in cols), None)
            if dcol is None or ccol is None:
                return {}
            out = {}
            for d, c in zip(df[dcol], df[ccol]):
                if c is None:
                    continue
                try:
                    if c != c:      # NaN
                        continue
                except Exception:
                    pass
                out[str(d)[:10]] = float(c)
            return out
    return {}


def pct(series, dates, back):
    """Change over `back` sessions, using the aligned date list."""
    if len(dates) < back + 1:
        return None
    a, b = series.get(dates[-1 - back]), series.get(dates[-1])
    if not a or not b:
        return None
    return round((b / a - 1) * 100, 2)


def corr(xs, ys):
    """Pearson correlation of two equal-length lists."""
    n = len(xs)
    if n < 3:
        return None
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    dx = sum((a - mx) ** 2 for a in xs) ** 0.5
    dy = sum((b - my) ** 2 for b in ys) ** 0.5
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def rolling_corr(a, b, window=10):
    """Correlation of daily returns over the last `window` sessions."""
    dates = sorted(set(a) & set(b))
    if len(dates) < window + 1:
        return None
    dates = dates[-(window + 1):]
    ra, rb = [], []
    for i in range(1, len(dates)):
        p0, p1 = a.get(dates[i - 1]), a.get(dates[i])
        q0, q1 = b.get(dates[i - 1]), b.get(dates[i])
        if None in (p0, p1, q0, q1) or not p0 or not q0:
            continue
        ra.append(p1 / p0 - 1)
        rb.append(q1 / q0 - 1)
    return corr(ra, rb)


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "rows": [], "ratio": None, "correlations": [], "note": ""}

    series = {sym: load(sym) for sym, _, _ in COMMODITIES}
    ctx = {sym: load(sym) for sym, _ in CONTEXT}

    have = {k: v for k, v in series.items() if v}
    if not have:
        out["note"] = ("No commodity parquet found. Run: "
                       "python scripts/fetch_yahoo.py --group commodities")
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("commodities: no data")
        return 0

    all_dates = sorted(set().union(*[set(v) for v in have.values()]))

    for sym, label, unit in COMMODITIES:
        s = series.get(sym) or {}
        if not s:
            continue
        dates = sorted(s)
        out["rows"].append({
            "symbol": sym, "label": label, "unit": unit,
            "close": round(s[dates[-1]], 2),
            "date": dates[-1],
            "chg_1d": pct(s, dates, 1),
            "chg_1w": pct(s, dates, 5),
            "chg_1m": pct(s, dates, 21),
        })

    # the gold-silver ratio: how many ounces of silver one ounce of gold buys
    gold, silver = series.get("GC=F") or {}, series.get("SI=F") or {}
    shared = sorted(set(gold) & set(silver))
    if len(shared) >= 2:
        cur = gold[shared[-1]] / silver[shared[-1]]
        prev_w = None
        if len(shared) >= 6:
            prev_w = gold[shared[-6]] / silver[shared[-6]]
        out["ratio"] = {
            "value": round(cur, 2),
            "date": shared[-1],
            "prev_week": round(prev_w, 2) if prev_w else None,
            "change_1w": round(cur - prev_w, 2) if prev_w else None,
            "history": [{"date": d, "ratio": round(gold[d] / silver[d], 2)}
                        for d in shared[-60:] if silver[d]],
        }

    # the correlation that explains the sell-off: metals tracking tech, not the dollar
    for csym, clabel in CONTEXT:
        c = ctx.get(csym) or {}
        for msym, mlabel in (("GC=F", "Gold"), ("SI=F", "Silver")):
            m = series.get(msym) or {}
            if not m or not c:
                continue
            r = rolling_corr(m, c, 10)
            if r is not None:
                out["correlations"].append({
                    "metal": mlabel, "against": clabel,
                    "window": "10 sessions",
                    "correlation": round(r, 2),
                })

    out["count"] = len(out["rows"])
    out["note"] = ("Prices are Yahoo Finance futures, delayed and unofficial. The ratio and the "
                   "correlations are computed from those closes, so a claim about why metals "
                   "moved can be checked rather than repeated.")
    out["cautions"] = {
        "unofficial": "Yahoo futures data is delayed and not a licensed feed.",
        "correlation": ("A high correlation with tech means metals moved with risk assets over "
                        "that window. It does not say which caused which."),
        "window": ("Correlations use only the last 10 sessions. With so few observations the "
                   "standard error is roughly 0.38, so anything between about -0.4 and +0.4 is "
                   "statistically indistinguishable from no relationship at all. Read the sign "
                   "and the rough size, never the exact figure."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    for r in out["rows"]:
        print("   %-12s %10.2f %-6s  1d %s  1w %s  1m %s"
              % (r["label"], r["close"], r["unit"],
                 r["chg_1d"], r["chg_1w"], r["chg_1m"]))
    if out["ratio"]:
        print("   gold/silver ratio: %.2f (was %s a week ago)"
              % (out["ratio"]["value"], out["ratio"]["prev_week"]))
    for c in out["correlations"]:
        print("   %s vs %s: %+.2f" % (c["metal"], c["against"], c["correlation"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
