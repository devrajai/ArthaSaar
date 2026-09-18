#!/usr/bin/env python3
"""
BUDGET DAY STUDY — measures Nifty around every Union Budget since 2015.

For each budget date it computes:
  - Nifty % on budget day itself
  - Nifty % in the 10 trading days BEFORE the budget (pre-budget rally/decay)
  - Nifty % in the 10 trading days AFTER the budget (post-budget rally/decay)

Source: Yahoo chart API ^NSEI (free, no key). Result -> data/budget-study.json
Self-healing: if Yahoo fails, existing JSON is kept; next run retries.
Budget dates are historical facts (verified from ET Now / Fortune India /
Telegraph India research, Jan 2026).
"""
import json
import time
import datetime as dt
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "budget-study.json"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

# (year, date, type, finance_minister, nifty_budget_day_pct from research)
BUDGETS = [
    ("2015", "2015-02-28", "Full",    "Arun Jaitley",          0.60),
    ("2016", "2016-02-29", "Full",    "Arun Jaitley",         -0.60),
    ("2017", "2017-02-01", "Full",    "Arun Jaitley",          1.80),
    ("2018", "2018-02-01", "Full",    "Arun Jaitley",         -0.10),
    ("2019", "2019-02-01", "Interim", "Piyush Goyal",          0.58),
    ("2019", "2019-07-05", "Full",    "Nirmala Sitharaman",   -1.13),
    ("2020", "2020-02-01", "Full",    "Nirmala Sitharaman",   -2.51),
    ("2021", "2021-02-01", "Full",    "Nirmala Sitharaman",    4.74),
    ("2022", "2022-02-01", "Full",    "Nirmala Sitharaman",    1.40),
    ("2023", "2023-02-01", "Full",    "Nirmala Sitharaman",   -0.26),
    ("2024", "2024-02-01", "Interim", "Nirmala Sitharaman",   -0.13),
    ("2024", "2024-07-23", "Full",    "Nirmala Sitharaman",   -0.12),
    ("2025", "2025-02-01", "Full",    "Nirmala Sitharaman",   -0.11),
    ("2026", "2026-02-01", "Full (Sunday special session)", "Nirmala Sitharaman", None),
]


def nifty_history_10y():
    """Fetch ~12y of Nifty daily closes from Yahoo. -> {date: close}"""
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" \
          + quote("^NSEI") + "?range=12y&interval=1d"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(3):
        try:
            with urlopen(req, timeout=30) as r:
                j = json.loads(r.read().decode())
            res = j["chart"]["result"][0]
            ts = res.get("timestamp") or []
            q = res["indicators"]["quote"][0]
            hist = {}
            for i, t in enumerate(ts):
                c = q["close"][i]
                if c is None:
                    continue
                d = dt.datetime.fromtimestamp(
                    t, dt.timezone.utc).strftime("%Y-%m-%d")
                hist[d] = c
            return hist
        except Exception:  # noqa: BLE001
            time.sleep(4 * (attempt + 1))
    return None


def window_stats(hist, date, days, before):
    """% change over N trading days before/after a date."""
    ds = sorted(hist)
    idx = None
    for i, d in enumerate(ds):
        if d >= date:
            idx = i
            break
    if idx is None:
        return None
    try:
        if before:
            a, b = ds[idx - days], ds[idx]
        else:
            a, b = ds[idx], ds[min(idx + days, len(ds) - 1)]
    except IndexError:
        return None
    return round((hist[b] / hist[a] - 1) * 100, 2)


def main():
    hist = nifty_history_10y()
    if not hist:
        if OUT.exists():
            print("Yahoo unavailable — keeping existing budget-study.json")
            return
        hist = {}
    rows = []
    for year, date, btype, fm, day_known in BUDGETS:
        row = {
            "year": year, "date": date, "type": btype,
            "finance_minister": fm,
            "nifty_budget_day_pct": day_known,
            "nifty_10d_before_pct": window_stats(hist, date, 10, before=True),
            "nifty_10d_after_pct": window_stats(hist, date, 10, before=False),
        }
        rows.append(row)

    known = [r["nifty_budget_day_pct"] for r in rows
             if r["nifty_budget_day_pct"] is not None]
    summary = {
        "budget_days_measured": len(rows),
        "positive_budget_days": sum(1 for k in known if k > 0),
        "negative_budget_days": sum(1 for k in known if k < 0),
        "avg_budget_day_pct": round(sum(known) / len(known), 2) if known else None,
        "best": max(rows, key=lambda r: (r["nifty_budget_day_pct"] or -99))["year"] if known else None,
        "worst": min(rows, key=lambda r: (r["nifty_budget_day_pct"] or 99))["year"] if known else None,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"updated": dt.datetime.now(dt.timezone.utc).isoformat(),
                               "summary": summary, "budgets": rows},
                              indent=1, ensure_ascii=False))
    print(f"budget study: {len(rows)} budgets | {summary}")


if __name__ == "__main__":
    main()
