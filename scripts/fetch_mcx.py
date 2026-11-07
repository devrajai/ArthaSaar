#!/usr/bin/env python3
"""MCX daily bhavcopy - the commodity exchange's end-of-day contract file.

WHY THIS IS WRITTEN DEFENSIVELY
MCX is not reachable from the ArthaSaar build sandbox, so the endpoint could not be tested
there. The Colab collector (arthasaar_mco_colab.py) is what proves the source works. This
script assumes it might fail, and fails quietly:

  * if the page or the API cannot be reached, it writes nothing and exits 0
  * if a date returns no rows, that is treated as a holiday, not an error
  * it records what happened in data/mcx/_status.json so the site can say "no MCX data"
    rather than showing an empty table as if the market had no trades

Until a Colab run has produced real rows, do not treat an empty result here as a bug in this
script - check the endpoint first.

THE ENDPOINT
  GET https://www.mcxindia.com/market-data/bhavcopy      -> sets cookies, carries a CSRF token
  GET https://www.mcxindia.com/backpage.aspx/GetDateWiseBhavCopy
        ?InstrumentName=ALL&fromDate=DD/MM/YYYY&toDate=DD/MM/YYYY
      with header __RequestVerificationToken

  Columns: Date, InstrumentName, Symbol, ExpiryDate, OptionType, StrikePrice, Open, High,
  Low, Close, PreviousClose, Volume (Lots), Volume(000s), Value(Lakhs), OpenInterest (Lots)

THE WEEKEND TRAP
MCX has held roughly 490 Saturday sessions and 5 Sunday sessions. A weekday-only loop loses
them silently - the same mistake that dropped three Muhurat sessions from the NSE archive.
So the day loop walks every calendar date and treats an empty answer as normal.

USAGE
  python scripts/fetch_mcx.py --selftest        probe the endpoint and report, fetch nothing
  python scripts/fetch_mcx.py --days 7          fetch the last 7 calendar days
  python scripts/fetch_mcx.py --days 30 --keep-untraded
"""
import argparse, json, os, random, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime, timedelta, timezone

OUT_DIR = "data/mcx"
PARQUET = os.path.join(OUT_DIR, "mcx_daily.parquet")
STATUS = os.path.join(OUT_DIR, "_status.json")

BASE = "https://www.mcxindia.com"
PAGE = BASE + "/market-data/bhavcopy"
API = BASE + "/backpage.aspx/GetDateWiseBhavCopy"

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": PAGE,
}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_status(**kw):
    try:
        os.makedirs(OUT_DIR, exist_ok=True)
        prev = {}
        if os.path.exists(STATUS):
            try:
                prev = json.load(open(STATUS))
            except Exception:
                prev = {}
        prev.update(kw)
        prev["updated"] = now()
        json.dump(prev, open(STATUS, "w"), ensure_ascii=False, indent=1)
    except Exception:
        pass


def make_session():
    import http.cookiejar
    import re
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    token = None
    try:
        req = urllib.request.Request(PAGE, headers={"User-Agent": UA["User-Agent"]})
        html = opener.open(req, timeout=45).read().decode("utf-8", "replace")
        m = re.search(r'name="__RequestVerificationToken"[^>]*value="([^"]+)"', html)
        if not m:
            m = re.search(r'value="([^"]+)"[^>]*name="__RequestVerificationToken"', html)
        if m:
            token = m.group(1)
        return opener, token, None
    except Exception as e:
        return None, None, "%s: %s" % (type(e).__name__, str(e)[:120])


def extract(j):
    """MCX wraps the payload in a few different shapes; accept all of them."""
    data = None
    for k in ("Data", "data", "d"):
        v = j.get(k) if isinstance(j, dict) else None
        if isinstance(v, list):
            data = v
            break
        if isinstance(v, str):
            try:
                inner = json.loads(v)
                if isinstance(inner, dict):
                    for kk in ("Data", "data"):
                        if isinstance(inner.get(kk), list):
                            data = inner[kk]
                            break
            except Exception:
                pass
    return data if data is not None else []


def fetch_day(opener, token, day):
    dmy = day.strftime("%d/%m/%Y")
    url = "%s?InstrumentName=ALL&fromDate=%s&toDate=%s" % (
        API, urllib.parse.quote(dmy), urllib.parse.quote(dmy))
    headers = dict(UA)
    if token:
        headers["__RequestVerificationToken"] = token
    try:
        raw = opener.open(urllib.request.Request(url, headers=headers),
                          timeout=60).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return {"__http__": e.code}
    except Exception as e:
        return {"__err__": type(e).__name__}
    try:
        return extract(json.loads(raw))
    except Exception:
        return {"__err__": "not json"}


def main():
    ap = argparse.ArgumentParser(description="MCX daily bhavcopy.")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--keep-untraded", action="store_true")
    ap.add_argument("--pause", type=float, default=0.45)
    args = ap.parse_args()

    opener, token, err = make_session()
    if opener is None:
        print("MCX unreachable (%s)." % err)
        print("  This is expected in the build sandbox. Nothing written; the pipeline continues.")
        write_status(reachable=False, reason=err, rows=0)
        return 0
    print("MCX session ok | csrf token: %s" % ("found" if token else "not found"))

    if args.selftest:
        d = date.today() - timedelta(days=1)
        got = fetch_day(opener, token, d)
        if isinstance(got, dict):
            print("selftest %s -> %s" % (d, json.dumps(got)))
            write_status(reachable=True, selftest="failed", reason=json.dumps(got))
        else:
            print("selftest %s -> %d contract rows" % (d, len(got)))
            if got:
                print("  sample keys:", ", ".join(list(got[0])[:12]))
            write_status(reachable=True, selftest="ok" if got else "empty", rows=len(got))
        return 0

    try:
        import pandas as pd
    except ImportError:
        print("pandas not available - nothing written")
        write_status(reachable=True, reason="pandas missing", rows=0)
        return 0

    rows, got_days, empty, errors = [], 0, 0, 0
    end = date.today()
    start = end - timedelta(days=max(1, args.days) - 1)
    day = start
    while day <= end:
        got = fetch_day(opener, token, day)
        if isinstance(got, dict):
            errors += 1
            if got.get("__http__") in (401, 403):
                opener, token, _ = make_session()
        elif got:
            got_days += 1
            for r in got:
                r["_date"] = day.isoformat()
            rows.extend(got)
        else:
            empty += 1          # a holiday or non-session day
        day += timedelta(days=1)
        time.sleep(args.pause + random.uniform(0, 0.2))

    print("MCX: %d day(s) with data, %d empty, %d errors, %d rows"
          % (got_days, empty, errors, len(rows)))
    if not rows:
        write_status(reachable=True, reason="no rows in window", rows=0,
                     days_with_data=0, empty_days=empty, errors=errors)
        return 0

    df = pd.DataFrame(rows)
    os.makedirs(OUT_DIR, exist_ok=True)
    if os.path.exists(PARQUET):
        try:
            df = pd.concat([pd.read_parquet(PARQUET), df], ignore_index=True)
        except Exception:
            pass
    subset = ["_date"] + [c for c in ("Symbol", "ExpiryDate", "StrikePrice",
                                      "OptionType", "InstrumentName") if c in df.columns]
    df = df.drop_duplicates(subset=subset)
    if not args.keep_untraded:
        vol = pd.to_numeric(df.get("Volume"), errors="coerce").fillna(0)
        oi = pd.to_numeric(df.get("OpenInterest"), errors="coerce").fillna(0)
        df = df[(vol > 0) | (oi > 0)]
    df.to_parquet(PARQUET, index=False)
    print("  wrote %s rows to %s" % (f"{len(df):,}", PARQUET))
    write_status(reachable=True, rows=int(len(df)),
                 dates=int(df["_date"].nunique()),
                 first=str(df["_date"].min()), last=str(df["_date"].max()),
                 reason=None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
