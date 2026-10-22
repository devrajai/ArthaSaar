#!/usr/bin/env python3
"""Relative strength vs Nifty (Task 1).

A stock up 5% while Nifty is up 8% is weak. This measures the gap, not the move.

Windows are 21 / 63 / 120 trading days because that is all the stored series covers
(120 daily closes). A 12-month window would silently return None for everything, so it
is not offered rather than being offered and always empty.
"""
import json, os, sys
from datetime import datetime, timezone

OUT = "docs/rs.json"
WINDOWS = [("1m", 21), ("3m", 63), ("6m", 120)]


def ret(series, n):
    """Return over n steps, in percent. None when the history is too short.

    The stored series is exactly 120 closes, so a 120-step window has no point 120 back.
    In that case the earliest point is used and the window is one session short - a
    rounding-level difference, and far better than a column that is silently all None.
    """
    if not series or len(series) < n:
        return None
    a = series[-n - 1] if len(series) > n else series[0]
    b = series[-1]
    if not a:
        return None
    return (b / a - 1.0) * 100.0


def nifty_series():
    """Nifty closes, oldest first. Falls back to None so the caller can say so."""
    try:
        import pandas as pd
        df = pd.read_parquet("data/yahoo/NSEI.parquet")
        df = df.sort_values("date")
        return [float(x) for x in df["close"].tolist() if x == x]
    except Exception as e:
        print("  NSEI.parquet -> %s" % type(e).__name__)
        return None


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "benchmark": "Nifty 50", "rows": [], "count": 0,
           "windows": [w for w, _ in WINDOWS], "note": ""}
    try:
        stocks = json.load(open("docs/stocks.json"))["stocks"]
    except Exception:
        out["note"] = "No stock series yet."
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        return 0

    nif = nifty_series()
    if not nif:
        out["note"] = ("Nifty's own series was unavailable, so relative strength cannot be "
                       "measured. It is computed on the runner where the index history exists.")
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("rs: skipped (no benchmark)")
        return 0

    bench = {w: ret(nif, n) for w, n in WINDOWS}
    out["benchmark_returns"] = bench
    print("  nifty:", {k: (round(v, 2) if v is not None else None) for k, v in bench.items()})

    rows = []
    for sym, st in stocks.items():
        ser = st.get("series") or []
        if len(ser) < WINDOWS[-1][1]:
            continue
        r = {w: ret(ser, n) for w, n in WINDOWS}
        if r["3m"] is None or bench["3m"] is None:
            continue
        rs = {w: (round(r[w] - bench[w], 2) if (r[w] is not None and bench[w] is not None) else None)
              for w, _ in WINDOWS}
        rows.append({"symbol": st.get("symbol") or sym, "name": st.get("name") or "",
                     "r1m": r["1m"], "r3m": r["3m"], "r6m": r["6m"],
                     "rs1m": rs["1m"], "rs3m": rs["3m"], "rs6m": rs["6m"]})

    rows.sort(key=lambda x: x["rs3m"], reverse=True)
    n = len(rows)
    for i, row in enumerate(rows):
        row["pct"] = round((1 - i / max(1, n - 1)) * 100) if n > 1 else 100

    out["rows"] = rows
    out["count"] = n
    if not n:
        out["note"] = ("No stock had the full 120 closes needed, so nothing is ranked. "
                       "This fills in as the pipeline accumulates history.")
    else:
        out["note"] = ("Ranked by 3-month return minus Nifty's over the same window. "
                       "Relative strength is a comparison, not a signal - a weak stock can "
                       "still rise, it is just lagging the index.")
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    print("rs: %d ranked -> %s" % (n, OUT))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
