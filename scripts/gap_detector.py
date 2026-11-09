#!/usr/bin/env python3
"""
ARTHASAAR - trading-day gap detector and backfill.

WHY
The site's stats are only as good as the sessions behind them. A skipped day is
silent: no error, just a hole in the history that skews every average, base rate
and backtest across it. This has already happened here - the Muhurat backfill
walked weekdays only and skipped weekend special sessions.

HOW IT DECIDES
It takes the sessions the site actually holds (docs/history.json), walks the
calendar, and for every day that is NOT held it asks NSE directly whether a
bhavcopy exists for that date:
    200 -> the exchange traded, we are missing it  -> GAP (backfillable)
    404 -> the exchange was closed                 -> closed, not a gap
Weekends are probed too, so special sessions (Muhurat) are caught rather than
assumed closed.

Usage
    python scripts/gap_detector.py                  # detect, write docs/data_gaps.json
    python scripts/gap_detector.py --days 120
    python scripts/gap_detector.py --backfill       # then re-fetch each gap
"""
import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def held_sessions():
    """Dates the site already has, from history.json (falling back to data.json)."""
    for name, keys in (("history.json", ("rows", "sessions", "days")),
                       ("data.json", ("sessions", "days"))):
        p = DOCS / name
        if not p.exists():
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        for k in keys:
            v = d.get(k)
            if isinstance(v, list) and v:
                out = set()
                for r in v:
                    if isinstance(r, dict):
                        for dk in ("d", "date", "dt"):
                            if r.get(dk):
                                out.add(str(r[dk])[:10]); break
                    elif isinstance(r, str):
                        out.add(r[:10])
                if out:
                    return out
    return set()


def bhavcopy_exists(day):
    url = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{day}_F_0000.csv.zip"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return r.status == 200
    except urllib.error.HTTPError as e:
        return e.code == 200
    except Exception:  # noqa: BLE001
        return None  # unknown - do not call it either way


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=60)
    ap.add_argument("--backfill", action="store_true")
    args = ap.parse_args()

    held = held_sessions()
    if not held:
        print("no session list found (docs/history.json) - cannot detect gaps")
        return 1

    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=args.days)
    gaps, closed, unknown, special = [], [], [], []

    d = start
    while d <= today:
        iso = d.isoformat()
        if iso not in held:
            exists = bhavcopy_exists(d.strftime("%Y%m%d"))
            if exists is True:
                rec = {"date": iso, "weekday": d.strftime("%a")}
                if d.weekday() >= 5:
                    special.append(rec)   # weekend with data = special session
                gaps.append(rec)
            elif exists is False:
                closed.append(iso)
            else:
                unknown.append(iso)
        d += timedelta(days=1)

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window_days": args.days,
        "held_sessions": len(held),
        "gaps": gaps,
        "special_sessions_missing": special,
        "closed_days": len(closed),
        "unknown": unknown,
        "note": ("Days the exchange traded but this site has no session for. Each is "
                 "confirmed against NSE's own archive rather than guessed from a holiday "
                 "list: a 200 means the bhavcopy exists, so the day traded. Weekends are "
                 "probed too, because Muhurat sessions fall on weekends."),
    }
    DOCS.mkdir(exist_ok=True)
    (DOCS / "data_gaps.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"held {len(held)} sessions | window {args.days}d | gaps {len(gaps)} | "
          f"closed {len(closed)} | unknown {len(unknown)}")
    for g in gaps:
        print("  GAP", g["date"], g["weekday"], "(special session)" if g["weekday"] in ("Sat", "Sun") else "")

    if args.backfill and gaps:
        ok = 0
        for g in gaps:
            print("  backfilling", g["date"])
            try:
                r = subprocess.run([sys.executable, "scripts/fetch_bhavcopy.py", "--date", g["date"]],
                                   cwd=ROOT, capture_output=True, text=True, timeout=240)
                if r.returncode == 0:
                    ok += 1
                else:
                    print("   failed:", (r.stderr or r.stdout or "")[-160:])
            except Exception as e:  # noqa: BLE001
                print("   failed:", e)
        print(f"  backfilled {ok}/{len(gaps)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
