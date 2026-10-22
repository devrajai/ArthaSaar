#!/usr/bin/env python3
"""Correlation matrix (Task 3) - which stocks move together.

A portfolio of five stocks that all move as one is one bet, not five. This makes that
visible. Kept to the 40 stocks with the most observations so the matrix stays readable.
"""
import json, os, sys, math
from datetime import datetime, timezone

OUT = "docs/correlation.json"
TOP = 40
MIN_OBS = 60


def returns(series):
    out = []
    for i in range(1, len(series)):
        a, b = series[i - 1], series[i]
        if a:
            out.append(b / a - 1.0)
    return out


def pearson(a, b):
    n = min(len(a), len(b))
    if n < 2:
        return None
    a, b = a[-n:], b[-n:]
    ma, mb = sum(a) / n, sum(b) / n
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((x - mb) ** 2 for x in b)
    if va <= 0 or vb <= 0:
        return None
    cov = sum((a[i] - ma) * (b[i] - mb) for i in range(n))
    return cov / math.sqrt(va * vb)


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "symbols": [], "matrix": [], "count": 0, "note": ""}
    try:
        stocks = json.load(open("docs/stocks.json"))["stocks"]
    except Exception:
        out["note"] = "No stock series yet."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        return 0

    cand = []
    for sym, st in stocks.items():
        ser = st.get("series") or []
        if len(ser) > MIN_OBS:
            cand.append((len(ser), st.get("symbol") or sym, returns(ser)))
    cand.sort(reverse=True)
    cand = cand[:TOP]
    out["window"] = MIN_OBS

    if len(cand) < 2:
        out["note"] = ("Fewer than two stocks have the %d observations needed, so no matrix "
                       "is published." % MIN_OBS)
    else:
        syms = [c[1] for c in cand]
        rets = [c[2] for c in cand]
        m = []
        for i in range(len(syms)):
            row = []
            for j in range(len(syms)):
                r = 1.0 if i == j else pearson(rets[i], rets[j])
                row.append(round(r, 3) if r is not None else None)
            m.append(row)
        out["symbols"], out["matrix"], out["count"] = syms, m, len(syms)
        out["note"] = ("Daily-return correlation over the last %d sessions, for the %d stocks "
                       "with the longest history. Correlation is not stable: it rises toward 1 "
                       "in a crash, which is exactly when diversification is meant to help and "
                       "stops." % (MIN_OBS, len(syms)))
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    print("correlation: %d x %d -> %s" % (out["count"], out["count"], OUT))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
