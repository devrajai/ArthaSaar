#!/usr/bin/env python3
"""Scanning built from bhavcopy OHLC - three things the site could not show before.

  1. BREADTH   - the share of stocks above their 50- and 200-day average. A broader trend
                 signal than advances/declines, which only ever describes ONE day.
  2. GAPS      - today's gap-ups and gap-downs, with how often past gaps got filled.
  3. LEVELS    - pivot, Fibonacci and Camarilla support/resistance for every stock.

Breadth reads docs/screener.json (sma_50/sma_200 are already computed there). Gaps and
levels read the candle archive through _archive.read_candles, so they get the adjusted
prices - the raw archive is only right for looking at the literal printed price.

Every section writes a `note` and the site shows it, so a thin archive reads as "not enough
history yet" rather than as an empty table.
"""
import json, os, sys
from datetime import datetime, timezone

OUT_BREADTH = "docs/breadth.json"
OUT_GAPS = "docs/gaps.json"
OUT_LEVELS = "docs/levels.json"
GAP_LOOKBACK = 120          # sessions to look back over for gaps
FILL_WINDOW = 10            # sessions a gap has to close within to count as filled
LEVEL_SYMBOLS = 300         # keep the file small; the deepened names


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


# ---------------------------------------------------------------- 1. breadth
def breadth():
    out = {"updated": _now(), "above_50": None, "above_200": None,
           "total": 0, "note": ""}
    s = load("docs/screener.json")
    rows = (s or {}).get("rows") or []
    if not rows:
        out["note"] = "No screener metrics yet, so breadth cannot be computed."
        return out

    n50 = n200 = tot = 0
    for r in rows:
        close = r.get("close")
        try:
            close = float(close)
        except (TypeError, ValueError):
            continue
        tot += 1
        for key, bucket in (("sma_50", "50"), ("sma_200", "200")):
            v = r.get(key)
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
            if bucket == "50":
                n50 += 1 if close > v else 0
            else:
                n200 += 1 if close > v else 0
    if not tot:
        out["note"] = "Screener rows carried no usable closes."
        return out
    out["total"] = tot
    out["above_50"] = round(n50 / tot * 100, 1)
    out["above_200"] = round(n200 / tot * 100, 1)
    out["note"] = ("Share of the %d stocks with a full page that closed above their own "
                   "50- and 200-day average. This describes the trend across the market, not "
                   "one day's move - advances and declines only ever describe today." % tot)
    return out


# ---------------------------------------------------------------- 2. gaps
def gaps():
    out = {"updated": _now(), "up": [], "down": [], "count": 0,
           "fill_rate_up": None, "fill_rate_down": None, "note": ""}
    try:
        import sys as _s
        _s.path.insert(0, "scripts")
        from _archive import pick_candles, read_candles
    except Exception as e:
        out["note"] = "Candle reader unavailable (%s)." % type(e).__name__
        return out

    src = pick_candles()
    if not src:
        out["note"] = "No candle archive yet, so gaps cannot be found."
        return out

    try:
        df = read_candles(src, GAP_LOOKBACK + 5)
    except Exception as e:
        out["note"] = "Could not read the archive (%s)." % type(e).__name__
        return out
    if df is None or df.empty:
        out["note"] = "Candle archive was empty."
        return out

    sortcol = "date" if "date" in df.columns else "ts"
    up_hits = down_hits = 0
    up_filled = down_filled = 0
    for sym, g in df.groupby("symbol", sort=False):
        g = g.sort_values(sortcol)
        if len(g) < 20:
            continue
        o = g["open"].tolist(); h = g["high"].tolist()
        l = g["low"].tolist(); c = g["close"].tolist(); d = [str(x) for x in g[sortcol].tolist()]
        # only look at the most recent session as "today"
        i = len(g) - 1
        gap_up = o[i] > h[i - 1]
        gap_dn = o[i] < l[i - 1]
        if gap_up:
            pct = (o[i] / h[i - 1] - 1) * 100
            out["up"].append([sym, round(o[i], 2), round(h[i - 1], 2), round(pct, 2), d[i]])
        elif gap_dn:
            pct = (o[i] / l[i - 1] - 1) * 100
            out["down"].append([sym, round(o[i], 2), round(l[i - 1], 2), round(pct, 2), d[i]])
        # historical fill rate: a gap is "filled" when price trades back through the level
        for j in range(1, len(g) - FILL_WINDOW):
            if o[j] > h[j - 1]:
                up_hits += 1
                level = h[j - 1]
                if min(l[j:j + FILL_WINDOW]) <= level:
                    up_filled += 1
            elif o[j] < l[j - 1]:
                down_hits += 1
                level = l[j - 1]
                if max(h[j:j + FILL_WINDOW]) >= level:
                    down_filled += 1

    out["up"].sort(key=lambda r: -r[3])
    out["down"].sort(key=lambda r: r[3])
    out["count"] = len(out["up"]) + len(out["down"])
    if up_hits:
        out["fill_rate_up"] = round(up_filled / up_hits * 100, 1)
    if down_hits:
        out["fill_rate_down"] = round(down_filled / down_hits * 100, 1)
    out["samples"] = {"up": up_hits, "down": down_hits, "window": FILL_WINDOW}
    if not out["count"]:
        out["note"] = "No stock gapped today."
    else:
        out["note"] = ("A gap-up is an open above yesterday's high; a gap-down an open below "
                       "yesterday's low. The fill rate is over %d sessions of history and a "
                       "%d-session window - it says how often price came back through the gap, "
                       "not that it will." % (GAP_LOOKBACK, FILL_WINDOW))
    return out


# ---------------------------------------------------------------- 3. levels
def levels():
    out = {"updated": _now(), "rows": [], "count": 0, "note": ""}
    try:
        import sys as _s
        _s.path.insert(0, "scripts")
        from _archive import pick_candles, read_candles
    except Exception as e:
        out["note"] = "Candle reader unavailable (%s)." % type(e).__name__
        return out
    src = pick_candles()
    if not src:
        out["note"] = "No candle archive yet, so levels cannot be computed."
        return out
    try:
        df = read_candles(src, 260)
    except Exception as e:
        out["note"] = "Could not read the archive (%s)." % type(e).__name__
        return out

    sortcol = "date" if "date" in df.columns else "ts"
    rows = []
    for sym, g in df.groupby("symbol", sort=False):
        g = g.sort_values(sortcol)
        if len(g) < 30:
            continue
        last = g.iloc[-1]
        h, l, c = float(last["high"]), float(last["low"]), float(last["close"])
        prev = g.iloc[-2]
        ph, pl, pc = float(prev["high"]), float(prev["low"]), float(prev["close"])
        pivot = (ph + pl + pc) / 3.0
        rng = ph - pl
        # classic pivot
        r1, s1 = 2 * pivot - pl, 2 * pivot - ph
        r2, s2 = pivot + rng, pivot - rng
        # Camarilla
        cam = {
            "h3": pc + rng * 1.1 / 4, "h4": pc + rng * 1.1 / 2,
            "l3": pc - rng * 1.1 / 4, "l4": pc - rng * 1.1 / 2,
        }
        # Fibonacci retracement of the 52-week range
        win = g.tail(252)
        hi, lo = float(win["high"].max()), float(win["low"].min())
        fib = {k: round(hi - (hi - lo) * f, 2) for k, f in
               (("23.6", 0.236), ("38.2", 0.382), ("50", 0.5), ("61.8", 0.618))}
        rows.append({
            "symbol": sym, "close": round(c, 2),
            "pivot": round(pivot, 2), "r1": round(r1, 2), "r2": round(r2, 2),
            "s1": round(s1, 2), "s2": round(s2, 2),
            "cam_h3": round(cam["h3"], 2), "cam_h4": round(cam["h4"], 2),
            "cam_l3": round(cam["l3"], 2), "cam_l4": round(cam["l4"], 2),
            "fib": fib, "hi52": round(hi, 2), "lo52": round(lo, 2),
        })
    rows.sort(key=lambda r: r["symbol"])
    out["rows"] = rows[:LEVEL_SYMBOLS]
    out["count"] = len(out["rows"])
    if not out["count"]:
        out["note"] = "No stock had the 30 sessions needed to compute levels."
    else:
        out["note"] = ("Pivot, Camarilla and 52-week Fibonacci levels from the previous "
                       "session's range. These are arithmetic reference points that many "
                       "traders watch, not predictions - price has no obligation to respect "
                       "any of them.")
    return out


def main():
    os.makedirs("docs", exist_ok=True)
    for fn, path, label in ((breadth, OUT_BREADTH, "breadth"),
                            (gaps, OUT_GAPS, "gaps"),
                            (levels, OUT_LEVELS, "levels")):
        try:
            data = fn()
        except Exception as e:
            data = {"updated": _now(), "count": 0,
                    "note": "Failed: %s: %s" % (type(e).__name__, str(e)[:120])}
        json.dump(data, open(path, "w"), ensure_ascii=False)
        print("%-8s -> %s  (%s)" % (label, path, data.get("note", "")[:60]))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
