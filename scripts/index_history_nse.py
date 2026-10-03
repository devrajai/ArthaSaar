#!/usr/bin/env python3
"""
NSE all-index daily history collector.

Free/public source:
  https://nsearchives.nseindia.com/content/indices/ind_close_all_DDMMYYYY.csv

The collector tries the latest five calendar days, keeps the newest 500 daily
points for every index, and writes one compact JSON file for the web chart.
This is EOD index history from NSE, not an intraday/live feed.
"""
import csv
import io
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "index-history-daily.json"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
KEEP = 500


def norm(s):
    return re.sub(r"[^a-z0-9]+", "", (s or "").strip().lower())


def pick(headers, *names):
    ns = {norm(h): h for h in headers}
    for name in names:
        key = norm(name)
        if key in ns:
            return ns[key]
    for h in headers:
        nh = norm(h)
        for name in names:
            key = norm(name)
            if key and key in nh:
                return h
    return None


def latest_csv():
    today = datetime.now(timezone.utc).date()
    for back in range(0, 8):
        d = today - timedelta(days=back)
        if d.weekday() >= 5:
            continue
        url = (
            "https://nsearchives.nseindia.com/content/indices/"
            f"ind_close_all_{d:%d%m%Y}.csv"
        )
        try:
            req = Request(url, headers={"User-Agent": UA, "Accept": "text/csv,*/*"})
            raw = urlopen(req, timeout=40).read().decode("utf-8", "replace")
            if len(raw) < 200 or "<html" in raw[:500].lower():
                continue
            return d, raw, url
        except Exception as e:
            print("retry", d, str(e)[:100])
    return None, None, None


def load_old():
    if not OUT.exists():
        return {"updated": None, "source": "NSE", "count": 0, "indices": {}}
    try:
        return json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:
        return {"updated": None, "source": "NSE", "count": 0, "indices": {}}


def main():
    d, raw, url = latest_csv()
    if raw is None:
        print("NSE index close file unavailable; preserving existing history")
        return

    lines = raw.splitlines()
    header_idx = next(
        (i for i, line in enumerate(lines) if "closing" in line.lower() and "index" in line.lower()),
        0,
    )
    text = "
".join(lines[header_idx:])
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows:
        print("empty NSE index CSV")
        return

    headers = rows[0].keys()
    idx_col = pick(headers, "Index Name", "Index", "IndexName")
    date_col = pick(headers, "Index Date", "Date", "IndexDate")
    open_col = pick(headers, "Open Index Value", "Open")
    high_col = pick(headers, "High Index Value", "High")
    low_col = pick(headers, "Low Index Value", "Low")
    close_col = pick(headers, "Closing Index Value", "Close", "Closing")
    chg_col = pick(headers, "Points Change", "Change")
    pct_col = pick(headers, "Percent Change", "Change %", "PercentChange")

    if not idx_col or not close_col:
        raise SystemExit("Could not identify index name/close columns in NSE CSV")

    old = load_old()
    series = old.get("indices") or {}

    for row in rows:
        name = (row.get(idx_col) or "").strip()
        if not name:
            continue
        try:
            close = float(str(row.get(close_col, "")).replace(",", "").strip())
        except Exception:
            continue
        if close != close:
            continue

        ds = (row.get(date_col) or "").strip() if date_col else ""
        if not ds:
            ds = d.isoformat()

        def f(col):
            if not col:
                return None
            try:
                return float(str(row.get(col, "")).replace(",", "").strip())
            except Exception:
                return None

        rec = {
            "date": ds,
            "open": f(open_col),
            "high": f(high_col),
            "low": f(low_col),
            "close": close,
            "change": f(chg_col),
            "change_pct": f(pct_col),
        }
        arr = series.setdefault(name, [])
        arr = [x for x in arr if x.get("date") != ds]
        arr.append(rec)
        arr.sort(key=lambda x: x.get("date", ""))
        series[name] = arr[-KEEP:]

    out = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "date": d.isoformat(),
        "source": "NSE",
        "source_url": url,
        "count": len(series),
        "points": sum(len(v) for v in series.values()),
        "indices": series,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print("NSE index history:", len(series), "indices /", out["points"], "points")


if __name__ == "__main__":
    main()
