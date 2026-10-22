#!/usr/bin/env python3
"""
fetch_mutual_funds.py - every mutual fund scheme, its record, and whether it beats the index.

WHAT WE CAN AND CANNOT GET FROM A FREE SOURCE - read this before trusting a column

  Available (mfapi.in, which republishes AMFI's own NAV history):
    scheme code, scheme name, fund house, scheme type, scheme category
    the full daily NAV history - for older schemes this is 10-15 years
    from which: 1/3/5/10-year CAGR, since-inception CAGR, maximum drawdown, volatility

  NOT available from any free structured source:
    fund manager names, CEO names, and "who runs the AMC".
    AMFI's feeds do not carry them and mfapi.in does not either. Getting them would
    mean scraping 40+ AMC websites, which breaks constantly and would give you a field
    that is silently stale. So the site says "not available from a free source" rather
    than showing a name that might be wrong. If you want them, the honest options are
    a paid data vendor or manual entry.

BENCHMARK COMPARISON
  The point of the exercise: which funds actually beat the index. We compute the same
  window returns for Nifty 50, Sensex and gold (from Yahoo), then flag each fund as
  beating or lagging each benchmark over 5 and 10 years. Costs matter here - a fund can
  beat the index gross and lose net of its expense ratio, so the flag is a starting
  point, not a verdict.

Output: docs/mf.json

Usage:
  python scripts/fetch_mutual_funds.py --limit 300
  python scripts/fetch_mutual_funds.py --equity-only
"""

from __future__ import annotations

import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.mfapi.in"
SCHEME_LIST = f"{API}/mf"


def try_json(url: str, timeout: int = 25, tries: int = 3):
    import requests
    for i in range(tries):
        try:
            r = requests.get(url, timeout=timeout, headers={"User-Agent": "ArthaSaar/1.0"})
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return None
        except Exception:
            pass
        time.sleep(1.5 * (i + 1))
    return None


def parse_nav(data: list) -> list[tuple[str, float]]:
    """mfapi returns newest-first 'DD-MM-YYYY' strings."""
    out = []
    for row in data or []:
        try:
            d = datetime.strptime(row["date"], "%d-%m-%Y")
            nav = float(row["nav"])
            if nav > 0:
                out.append((d.strftime("%Y-%m-%d"), nav))
        except Exception:
            continue
    out.sort()
    return out


def cagr(series: list[tuple[str, float]], years: float):
    """Annualised return over the last `years`, or None if the fund is younger."""
    if not series:
        return None
    last_date, last_nav = series[-1]
    target = datetime.strptime(last_date, "%Y-%m-%d").timestamp() - years * 365.25 * 86400
    past = None
    for d, nav in series:
        if datetime.strptime(d, "%Y-%m-%d").timestamp() <= target:
            past = (d, nav)
        else:
            break
    if not past or past[1] <= 0:
        return None
    # Use the real gap between the two NAV points, not the nominal window: the matched
    # point is the last one on or before the target date, so it can be weeks earlier.
    try:
        actual = (datetime.strptime(last_date, "%Y-%m-%d") -
                  datetime.strptime(past[0], "%Y-%m-%d")).days / 365.25
        if actual <= 0:
            return None
        return round(((last_nav / past[1]) ** (1.0 / actual) - 1) * 100, 2)
    except Exception:
        return None


def max_drawdown(series: list[tuple[str, float]]):
    """Deepest fall from a previous peak. A fund that never fell is 0%, not unknown."""
    if not series:
        return None
    peak, worst = -1e18, 0.0
    for _, nav in series:
        peak = max(peak, nav)
        if peak > 0:
            worst = min(worst, nav / peak - 1)
    return round(worst * 100, 2)


def volatility(series: list[tuple[str, float]]):
    """Annualised standard deviation of daily returns."""
    vals = [n for _, n in series]
    if len(vals) < 30:
        return None
    rets = [vals[i] / vals[i - 1] - 1 for i in range(1, len(vals)) if vals[i - 1] > 0]
    if len(rets) < 20:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return round(math.sqrt(var) * math.sqrt(252) * 100, 2)


def benchmark_returns(yahoo_dir: str) -> dict:
    """Window returns for Nifty, Sensex and gold, from the stored daily series."""
    import pandas as pd
    out = {}
    for label, sym in (("nifty", "^NSEI"), ("sensex", "^BSESN"), ("gold", "GC=F")):
        p = Path(yahoo_dir) / (sym.replace("^", "").replace("=", "_") + ".parquet")
        if not p.exists():
            continue
        try:
            df = pd.read_parquet(p).sort_values("date")
            s = [(str(r["date"])[:10], float(r["close"])) for _, r in df.iterrows() if r["close"]]
            if len(s) < 60:
                continue
            out[label] = {"1y": cagr(s, 1), "3y": cagr(s, 3), "5y": cagr(s, 5), "10y": cagr(s, 10)}
        except Exception:
            continue
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Mutual fund record + benchmark comparison.")
    ap.add_argument("--out", default="docs/mf.json")
    ap.add_argument("--cache", default="data/mf")
    ap.add_argument("--limit", type=int, default=300, help="how many schemes to fetch history for")
    ap.add_argument("--yahoo-dir", default="data/yahoo")
    ap.add_argument("--equity-only", action="store_true")
    ap.add_argument("--sleep", type=float, default=0.25)
    args = ap.parse_args()

    cache = Path(args.cache)
    cache.mkdir(parents=True, exist_ok=True)
    listfile = cache / "schemes.json"

    schemes = None
    if listfile.exists():
        try:
            schemes = json.loads(listfile.read_text())
        except Exception:
            schemes = None
    if not schemes:
        schemes = try_json(SCHEME_LIST, timeout=40)
        if isinstance(schemes, list) and schemes:
            listfile.write_text(json.dumps(schemes))
    if not isinstance(schemes, list) or not schemes:
        print("could not reach mfapi.in and no cached scheme list - nothing to do")
        return 0
    print(f"schemes available: {len(schemes)}")

    bm = benchmark_returns(args.yahoo_dir)
    print(f"benchmarks: {', '.join(bm) if bm else 'none available'}")

    rows, hist_dir = [], cache / "nav"
    hist_dir.mkdir(parents=True, exist_ok=True)
    taken = 0

    for s in schemes:
        if taken >= args.limit:
            break
        code = s.get("schemeCode")
        name = str(s.get("schemeName") or "")
        if not code:
            continue
        if args.equity_only and not any(k in name.lower() for k in
                                        ("equity", "elss", "index", "bluechip", "large cap",
                                         "mid cap", "small cap", "flexi", "multi cap", "focused")):
            continue
        hp = hist_dir / f"{code}.json"
        payload = None
        if hp.exists():
            try:
                payload = json.loads(hp.read_text())
            except Exception:
                payload = None
        if payload is None:
            payload = try_json(f"{API}/mf/{code}")
            if payload:
                hp.write_text(json.dumps(payload))
            time.sleep(args.sleep)
        if not payload:
            continue
        meta = payload.get("meta") or {}
        series = parse_nav(payload.get("data"))
        if len(series) < 60:
            continue
        taken += 1

        rec = {
            "code": code,
            "name": meta.get("scheme_name") or name,
            "fund_house": meta.get("fund_house") or "",
            "category": meta.get("scheme_category") or "",
            "type": meta.get("scheme_type") or "",
            "nav": series[-1][1],
            "nav_date": series[-1][0],
            "first_nav_date": series[0][0],
            "years": round((datetime.strptime(series[-1][0], "%Y-%m-%d") -
                            datetime.strptime(series[0][0], "%Y-%m-%d")).days / 365.25, 1),
            "r1y": cagr(series, 1), "r3y": cagr(series, 3),
            "r5y": cagr(series, 5), "r10y": cagr(series, 10),
            "max_dd": max_drawdown(series),
            "vol": volatility(series),
        }
        # beats the index over 5 and 10 years?
        for label, b in bm.items():
            for win in ("5y", "10y"):
                a, bb = rec.get("r" + win), b.get(win)
                rec[f"beats_{label}_{win}"] = (None if (a is None or bb is None) else a > bb)
        rows.append(rec)
        if taken % 25 == 0:
            print(f"  {taken} schemes processed")

    rows.sort(key=lambda r: -(r.get("r5y") or -999))
    payload = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "count": len(rows), "benchmarks": bm,
               "note": ("Fund manager and CEO names are not available from a free structured "
                        "source, so they are not shown rather than guessed."),
               "rows": rows}
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest}  ({dest.stat().st_size / 1e3:.0f} KB)  |  {len(rows)} schemes")
    if rows:
        beat = sum(1 for r in rows if r.get("beats_nifty_5y"))
        print(f"  beat Nifty over 5 years: {beat} of {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
