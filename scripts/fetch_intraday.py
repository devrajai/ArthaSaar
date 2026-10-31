#!/usr/bin/env python3
"""Save each day's intraday bars, because nobody will sell them to you later.

WHY THIS IS THE MOST URGENT STEP ON THE SITE
Yahoo keeps 1-minute bars for about 7 days and 5-minute bars for about 60. After that they
are gone - not paywalled, gone. Every day this does not run is a day of intraday history that
can never be recovered from any free source. In a year this file is something no free Indian
site has.

WHAT IT SAVES
1-minute bars for Nifty and Bank Nifty, plus the N most liquid stocks, for the current
session. One parquet per day, in the same layout as the daily candle archive so the rest of
the pipeline can read it without special cases.

DESIGNED TO FAIL QUIETLY
Yahoo is an unofficial endpoint and changes without notice. This step is allowed to fail -
a missing intraday day is annoying, but it must never stop the nightly data run. Hence the
per-symbol error handling and the always-zero exit.

STORAGE
About 375 one-minute bars per symbol per session. At 100 symbols that is roughly 38,000 rows
a day, or 9 million a year - around 60-90 MB as parquet.
"""
import argparse, json, os, random, sys, time
import urllib.error, urllib.parse, urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")}
CHART = ("https://query1.finance.yahoo.com/v8/finance/chart/{sym}"
         "?interval={iv}&range={rng}&includePrePost=false")
OUT_DIR = "data/intraday"

# always capture these - the two indices the option chain is built on
INDICES = {"^NSEI": "NIFTY", "^NSEBANK": "BANKNIFTY"}


def get_json(url, timeout=45, retries=3):
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=timeout) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code in (404, 401, 403):
                return None
            time.sleep((2 ** attempt) + random.uniform(0, 1))
        except Exception:
            time.sleep((2 ** attempt) + random.uniform(0, 1))
    return None


def bars(symbol, interval="1m", rng="1d"):
    """One session of bars for one symbol. Returns a list of dicts, or None."""
    j = get_json(CHART.format(sym=urllib.parse.quote(symbol), iv=interval, rng=rng))
    if not j:
        return None
    try:
        res = j["chart"]["result"][0]
    except (KeyError, IndexError, TypeError):
        return None
    ts = res.get("timestamp") or []
    q = (res.get("indicators", {}).get("quote") or [{}])[0]
    if not ts or not q:
        return None
    out = []
    for i, t in enumerate(ts):
        try:
            o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        except (KeyError, IndexError):
            continue
        if None in (o, h, l, c):
            continue
        out.append({"ts": int(t), "open": float(o), "high": float(h), "low": float(l),
                    "close": float(c),
                    "volume": (q["volume"][i] if q.get("volume") and i < len(q["volume"]) else None)})
    return out or None


def universe(limit):
    """Most liquid NSE names, from our own universe file if present, else Yahoo fallback."""
    syms = []
    for path in ("docs/universe.json", "data/universe/universe.json"):
        if not os.path.exists(path):
            continue
        try:
            rows = json.load(open(path)).get("rows") or []
        except Exception:
            continue
        rows = [r for r in rows if r.get("symbol") and (r.get("volume") or r.get("turnover"))]
        rows.sort(key=lambda r: -(r.get("turnover") or r.get("volume") or 0))
        syms = [r["symbol"] + ".NS" for r in rows[:limit]]
        if syms:
            print("  universe: %d symbols from %s" % (len(syms), path))
            break
    if not syms:
        # still capture the indices even with no universe file
        print("  universe: no file found - capturing indices only")
    return syms


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=100, help="how many stocks besides the indices")
    ap.add_argument("--interval", default="1m")
    ap.add_argument("--range", default="1d")
    ap.add_argument("--sleep", type=float, default=0.4)
    ap.add_argument("--date", default="", help="label the file with this date (YYYY-MM-DD)")
    args = ap.parse_args()

    import pandas as pd

    day = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    dest_dir = os.path.join(OUT_DIR, day[:4])
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, day.replace("-", "") + ".parquet")

    if os.path.exists(dest):
        print("already captured: %s" % dest)
        return 0

    targets = list(INDICES.items())
    for s in universe(args.top):
        targets.append((s, s.replace(".NS", "")))

    print("capturing %d symbols, interval=%s" % (len(targets), args.interval))
    rows, ok, fail = [], 0, 0
    for i, (sym, label) in enumerate(targets, 1):
        b = bars(sym, args.interval, args.range)
        if b:
            for x in b:
                x["symbol"] = label
            rows.extend(b)
            ok += 1
        else:
            fail += 1
        if i % 25 == 0 or i == len(targets):
            print("  %d/%d  ok %d  failed %d  bars %d" % (i, len(targets), ok, fail, len(rows)))
        time.sleep(args.sleep + random.uniform(0, 0.15))

    if not rows:
        print("::warning title=No intraday bars::Yahoo returned nothing for this session")
        return 0

    df = pd.DataFrame(rows)
    df["datetime"] = pd.to_datetime(df["ts"], unit="s", utc=True)
    df["date"] = day
    df = df[["date", "symbol", "datetime", "open", "high", "low", "close", "volume"]]
    df = df.sort_values(["symbol", "datetime"]).reset_index(drop=True)
    df.to_parquet(dest, index=False)

    n_sym = df["symbol"].nunique()
    print("\n-> %s  %.2f MB  |  %d bars, %d symbols"
          % (dest, os.path.getsize(dest) / 1e6, len(df), n_sym))
    # a sanity line, so a half-empty capture is visible in the log
    per = df.groupby("symbol").size()
    print("   bars per symbol: min %d, median %d, max %d"
          % (per.min(), int(per.median()), per.max()))
    if per.median() < 200:
        print("::warning title=Thin intraday capture::median %d bars per symbol - "
              "market may have been closed or Yahoo incomplete" % int(per.median()))
    return 0


if __name__ == "__main__":
    # Never fail the nightly run over an unofficial endpoint.
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:
        print("::warning title=Intraday capture failed::%s: %s" % (type(e).__name__, str(e)[:120]))
        sys.exit(0)
