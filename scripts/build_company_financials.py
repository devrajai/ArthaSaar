#!/usr/bin/env python3
"""
build_company_financials.py - company profile, management and financial history, as charts.

docs/fundamentals.json carries one period per company: latest revenue, latest profit, the year
ago, and a margin. That answers "how is it doing now" and cannot answer "how has it grown", which
needs a series.

This pulls, per symbol, from Yahoo Finance via yfinance:
  * the business description, sector, industry, employees, website, city
  * the officers (CEO, CFO and the rest) with their titles
  * four to five years of revenue, net income, EBITDA, total debt and equity
  * five to six quarters of revenue and net income
  * insider and institutional holding

Honest limits: yfinance is an unofficial wrapper on Yahoo, the figures are as reported and often
restated later, Indian annual columns are fiscal years ending in March, and a missing line is
written as null rather than zero because zero is a real number a company can report.

Usage
-----
  python scripts/build_company_financials.py
  python scripts/build_company_financials.py --limit 120 --sleep 0.3
  python scripts/build_company_financials.py --symbols RELIANCE.NS TCS.NS

Output: docs/company_financials.json
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OUT = "docs/company_financials.json"
SCREENER = "docs/screener.json"
INDICES = "docs/indices.json"
FUND = "docs/fundamentals.json"

ROWS_ANNUAL = [
    ("revenue", ["Total Revenue", "Operating Revenue"]),
    ("profit", ["Net Income", "Net Income Common Stockholders"]),
    ("ebitda", ["EBITDA", "Normalized EBITDA"]),
]
ROWS_BALANCE = [
    ("debt", ["Total Debt"]),
    ("equity", ["Stockholders Equity", "Total Equity Gross Minority Interest"]),
    ("cash", ["Cash And Cash Equivalents", "Cash Cash Equivalents And Short Term Investments"]),
]
ROWS_Q = [
    ("revenue", ["Total Revenue", "Operating Revenue"]),
    ("profit", ["Net Income", "Net Income Common Stockholders"]),
]

CR = 1e7  # one crore in rupees


def _load(p):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def pick(limit):
    syms = []
    ix = _load(INDICES) or {}
    for i in (ix.get("indices") or []):
        if i.get("id") == "nifty50":
            syms += [(c.get("symbol") or "") + ".NS" for c in (i.get("constituents") or []) if c.get("symbol")]
            break
    fu = _load(FUND) or {}
    for c in (fu.get("companies") or []):
        s = c.get("symbol")
        if s:
            syms.append(s if "." in s else s + ".NS")
    scr = _load(SCREENER) or {}
    for r in sorted((scr.get("rows") or []), key=lambda r: -(r.get("mcap") or 0)):
        if r.get("symbol"):
            syms.append(r["symbol"] + ".NS")
    seen, out = set(), []
    for s in syms:
        if s not in seen:
            seen.add(s); out.append(s)
        if len(out) >= limit:
            break
    return out


def _row(df, names):
    if df is None or getattr(df, "empty", True):
        return None
    for n in names:
        if n in df.index:
            vals = []
            for v in df.loc[n].values:
                try:
                    f = float(v)
                    vals.append(None if f != f else round(f / CR, 1))
                except Exception:
                    vals.append(None)
            return vals
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    ap.add_argument("--limit", type=int, default=220)
    ap.add_argument("--sleep", type=float, default=0.25)
    ap.add_argument("--symbols", nargs="*", default=None)
    args = ap.parse_args()

    try:
        import yfinance as yf
    except Exception:
        print("yfinance unavailable - skipping")
        return 0

    syms = args.symbols or pick(args.limit)
    print(f"fetching {len(syms)} company profile(s)")

    out, failed = {}, []
    for i, sym in enumerate(syms, 1):
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            rec = {
                "symbol": sym,
                "name": info.get("longName") or info.get("shortName"),
                "summary": (info.get("longBusinessSummary") or "")[:900] or None,
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "employees": info.get("fullTimeEmployees"),
                "website": info.get("website"),
                "city": info.get("city"),
                "country": info.get("country"),
                "insiders": info.get("heldPercentInsiders"),
                "institutions": info.get("heldPercentInstitutions"),
            }
            off = info.get("companyOfficers") or []
            rec["officers"] = [{"n": str(o.get("name") or "")[:60],
                                "t": str(o.get("title") or "")[:70]}
                               for o in off[:4] if o.get("name")]

            fin = t.financials
            if fin is not None and not fin.empty:
                cols = list(fin.columns)
                rec["annual_years"] = [str(c)[:4] for c in cols][:5]
                for key, names in ROWS_ANNUAL:
                    v = _row(fin, names)
                    if v: rec[key] = v[:5]

            bs = t.balance_sheet
            if bs is not None and not bs.empty:
                for key, names in ROWS_BALANCE:
                    v = _row(bs, names)
                    if v: rec[key] = v[:5]

            q = t.quarterly_financials
            if q is not None and not q.empty:
                qcols = list(q.columns)
                rec["q_periods"] = [str(c)[:10] for c in qcols][:6]
                for key, names in ROWS_Q:
                    v = _row(q, names)
                    if v: rec["q_" + key] = v[:6]

            if rec.get("annual_years") or rec.get("summary"):
                out[sym] = rec
            else:
                failed.append(sym)
        except Exception as e:
            failed.append(sym)
            if len(failed) <= 5:
                print(f"  {sym:16s} FAILED ({type(e).__name__})")
        import time as _t; _t.sleep(args.sleep)
        if i % 25 == 0:
            print(f"  {i}/{len(syms)} kept {len(out)}")

    if not out:
        print("nothing fetched - leaving the existing file alone")
        return 0

    Path(args.out).write_text(json.dumps({
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(out),
        "note": ("Company profile, officers and reported financials from Yahoo Finance via "
                 "yfinance - an unofficial wrapper, delayed, and restated by companies after "
                 "the fact. Indian annual columns are fiscal years ending in March. A null "
                 "means the line was not reported, which is not the same as zero."),
        "failed": failed[:40],
        "companies": out,
    }, separators=(",", ":"), ensure_ascii=False))
    print(f"\n-> {args.out}  {Path(args.out).stat().st_size/1024:.0f} KB | {len(out)} companies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
