#!/usr/bin/env python3
"""Daily index history for Nifty, Bank Nifty and Sensex - the piece that was missing.

WHY THIS EXISTS
A weekly market wrap needs daily index prices. The site had none: charts.json holds MONTHLY
closes and only Nifty ETFs, series.json holds 2,214 stocks but no index, and data.json carries
a single day's index value. So "where did Nifty close this week, what was the range, what are
next week's levels" could not be answered from our own published data at all.

Yahoo serves about two years of daily bars for these three indices, free and keyless. This
writes them, plus the weekly aggregation the wrap actually reads.

WHAT IT IS NOT
A weekly bar is a summary, not a prediction. The levels below are arithmetic on last week's
range - the same pivot formula every charting package uses. They describe where price has
traded, not where it will go, and the note says so.
"""
import json, os, sys, time, urllib.parse, urllib.request
from datetime import datetime, timezone

OUT = "docs/index_history.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36"}
CHART = "https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=2y"

INDICES = [("^NSEI", "Nifty 50"), ("^NSEBANK", "Bank Nifty"), ("^BSESN", "Sensex")]

DAILY_KEEP = 260      # about one trading year, enough for a 52-week range
WEEKLY_KEEP = 16      # four months of weeks


def fetch(sym, tries=3):
    delay = 2.0
    last = None
    for _ in range(tries):
        try:
            u = CHART.format(sym=urllib.parse.quote(sym))
            with urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=45) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e
            time.sleep(delay)
            delay *= 2
    raise last


def bars(sym):
    d = fetch(sym)
    r = d["chart"]["result"][0]
    ts = r.get("timestamp") or []
    q = (r.get("indicators", {}).get("quote") or [{}])[0]
    o, h, l, c = q.get("open"), q.get("high"), q.get("low"), q.get("close")
    out = []
    for i, t in enumerate(ts):
        try:
            row = [o[i], h[i], l[i], c[i]]
        except Exception:
            continue
        if any(x is None for x in row):
            continue
        day = datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d")
        out.append([day, round(row[0], 2), round(row[1], 2), round(row[2], 2), round(row[3], 2)])
    return out


def weekly(daily):
    """Group daily bars into ISO weeks ending Friday, keeping real OHLC."""
    weeks = {}
    for day, o, h, l, c in daily:
        dt = datetime.strptime(day, "%Y-%m-%d")
        key = "%d-W%02d" % dt.isocalendar()[:2]
        if key not in weeks:
            weeks[key] = {"start": day, "o": o, "h": h, "l": l, "c": c, "n": 1}
        else:
            w = weeks[key]
            w["h"] = max(w["h"], h)
            w["l"] = min(w["l"], l)
            w["c"] = c          # daily bars arrive in order, so the last close is the week's
            w["n"] += 1
    out = []
    for key in sorted(weeks):
        w = weeks[key]
        out.append([w["start"], w["o"], w["h"], w["l"], w["c"], w["n"]])
    return out


def levels(o, h, l, c):
    """Classic pivot and two support/resistance bands from the week's own range."""
    p = (h + l + c) / 3.0
    rng = h - l
    return {
        "pivot": round(p, 2),
        "r1": round(2 * p - l, 2),
        "r2": round(p + rng, 2),
        "s1": round(2 * p - h, 2),
        "s2": round(p - rng, 2),
    }


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "indices": [], "count": 0, "note": "", "cautions": {}}
    failed = []
    for sym, name in INDICES:
        try:
            d = bars(sym)
        except Exception as e:
            failed.append("%s (%s)" % (sym, type(e).__name__))
            continue
        if len(d) < 30:
            failed.append("%s (only %d bars)" % (sym, len(d)))
            continue
        wk = weekly(d)
        if not wk:
            failed.append("%s (no weeks)" % sym)
            continue
        cur = wk[-1]
        prev = wk[-2] if len(wk) > 1 else None
        _, o, h, l, c, n = cur
        chg = (c / o - 1.0) * 100.0 if o else 0.0
        prev_chg = ((c / prev[4] - 1.0) * 100.0) if prev and prev[4] else None
        closes = [x[4] for x in d[-252:]]
        out["indices"].append({
            "symbol": sym,
            "name": name,
            "last": c,
            "week": {
                "start": cur[0], "open": o, "high": h, "low": l, "close": c,
                "days": n,
                "chg_pct": round(chg, 2),
                "range": round(h - l, 2),
                "range_pct": round((h - l) / l * 100.0, 2) if l else None,
                "vs_prev_week_pct": round(prev_chg, 2) if prev_chg is not None else None,
            },
            "levels": levels(o, h, l, c),
            "high_52w": round(max(closes), 2) if closes else None,
            "low_52w": round(min(closes), 2) if closes else None,
            "from_high_pct": round((c / max(closes) - 1) * 100.0, 2) if closes else None,
            "daily": d[-DAILY_KEEP:],
            "weekly": wk[-WEEKLY_KEEP:],
        })
        time.sleep(0.4)

    out["count"] = len(out["indices"])
    if out["indices"]:
        n0 = out["indices"][0]
        w = n0["week"]
        out["note"] = (
            "%s closed the week at %s, %s%% on the week, in a %s-point range. "
            "Levels for next week are arithmetic on that range, not a forecast."
            % (n0["name"], "{:,.2f}".format(w["close"]),
               ("+" if w["chg_pct"] >= 0 else "") + str(w["chg_pct"]), w["range"]))
    out["failed"] = failed
    out["cautions"] = {
        "not_a_forecast": ("Weekly levels are the standard pivot arithmetic on last week's "
                           "high, low and close. They mark where price has traded, not where "
                           "it will go. No level here is a buy or sell instruction."),
        "yahoo_source": ("Daily index bars come from Yahoo, which is an unofficial endpoint. "
                         "The nightly NSE bhavcopy does not carry index history, so this is "
                         "the only free source for it here."),
        "partial_week": ("If the newest week has fewer than five sessions the numbers describe "
                         "a part-week and change as it fills in."),
        "two_years": ("About two years of daily history. A 52-week high or low is computed from "
                      "the last 252 sessions in that window."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %d indices, %d failed" % (len(out["indices"]), len(failed)))
    for i in out["indices"]:
        w = i["week"]
        print("     %-10s %10s  week %+6.2f%%  range %8.2f  pivot %9.2f  (%d days)"
              % (i["name"], "{:,.2f}".format(w["close"]), w["chg_pct"], w["range"],
                 i["levels"]["pivot"], w["days"]))
    if failed:
        print("   failed:", failed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
