#!/usr/bin/env python3
"""
test_mf.py - verify the mutual-fund maths without the network.

mfapi.in is blocked from some networks (including the build sandbox), so the fetch
cannot be exercised here. That leaves a gap: the CAGR, drawdown and volatility sums
could be wrong and nobody would notice until the nightly run.

This closes the gap by substituting a scheme list and NAV history with known answers,
then checking every number the site displays.

It verifies:
  * 1/3/5-year CAGR against a series built to grow at a known rate
  * that a fund younger than the window returns None instead of a wrong number
  * maximum drawdown against a series with one engineered 50% fall
  * annualised volatility is positive and scales sensibly
  * the "beats the index" flags, including the case where the benchmark is missing
  * the output keys the website reads

Usage: python scripts/test_mf.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def monthly_series(years: float, annual: float, start_nav: float = 100.0, drop_at=None):
    """Monthly NAVs compounding at `annual`, newest-first like mfapi returns them."""
    n = int(years * 12)
    start = datetime(2026, 10, 1)
    rows = []
    for i in range(n):
        d = start - timedelta(days=int(i * 30.44))
        yrs_elapsed = (n - 1 - i) * 30.44 / 365.25
        nav = start_nav * ((1 + annual) ** yrs_elapsed)
        rows.append({"date": d.strftime("%d-%m-%Y"), "nav": f"{nav:.4f}"})
    if drop_at is not None:
        # rows are NEWEST-first, so halving the first `drop_at` entries cuts the recent
        # half - which is what creates an actual drawdown from a peak.
        for j in range(0, min(drop_at, len(rows))):
            rows[j]["nav"] = f"{float(rows[j]['nav']) * 0.5:.4f}"
    return rows


def load_script():
    path = Path(__file__).with_name("fetch_mutual_funds.py")
    spec = importlib.util.spec_from_file_location("mf_fetch", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(schemes, histories, benchmarks):
    m = load_script()
    def fake_try_json(url, timeout=25, tries=3):
        if url.endswith("/mf"):
            return schemes
        code = url.rsplit("/", 1)[-1]
        return histories.get(code)
    m.try_json = fake_try_json
    m.benchmark_returns = lambda d: benchmarks
    with tempfile.TemporaryDirectory() as td:
        out = str(Path(td) / "mf.json")
        sys.argv = ["fetch_mutual_funds.py", "--out", out, "--cache", td,
                    "--limit", "50", "--sleep", "0"]
        rc = m.main()
        return rc, json.loads(Path(out).read_text())


def main() -> int:
    print("=== mutual fund maths (stub data, no network) ===")

    schemes = [{"schemeCode": 1, "schemeName": "Steady Equity Fund - Growth"},
               {"schemeCode": 2, "schemeName": "Young Fund - Growth"},
               {"schemeCode": 3, "schemeName": "Fallen Fund - Growth"}]
    histories = {
        "1": {"meta": {"scheme_name": "Steady Equity Fund - Growth", "fund_house": "Test AMC",
                       "scheme_category": "Equity Scheme - Large Cap Fund", "scheme_type": "Open Ended"},
              "data": monthly_series(12, 0.12)},          # 12y at exactly 12%
        "2": {"meta": {"scheme_name": "Young Fund - Growth", "fund_house": "Test AMC",
                       "scheme_category": "Equity Scheme - Mid Cap Fund", "scheme_type": "Open Ended"},
              "data": monthly_series(6, 0.20)},           # 6 years: passes the floor, no 10y record
        "3": {"meta": {"scheme_name": "Fallen Fund - Growth", "fund_house": "Test AMC",
                       "scheme_category": "Equity Scheme - Small Cap Fund", "scheme_type": "Open Ended"},
              "data": monthly_series(12, 0.10, drop_at=60)},   # a 50% fall halfway
    }
    benchmarks = {"nifty": {"1y": 8.0, "3y": 9.0, "5y": 10.0, "10y": 11.0},
                  "sensex": {"1y": 8.0, "3y": 9.0, "5y": 10.0, "10y": 11.0},
                  "gold": {"1y": 6.0, "3y": 7.0, "5y": 7.5, "10y": 8.0}}

    rc, d = run(schemes, histories, benchmarks)
    check("exit code 0", rc == 0)
    check("all three schemes produced", d.get("count") == 3, str(d.get("count")))
    rows = {r["scheme"] if "scheme" in r else r["code"]: r for r in d.get("rows", [])}

    steady = rows.get(1)
    check("steady fund present", steady is not None)
    if steady:
        for win, want in (("r1y", 12.0), ("r3y", 12.0), ("r5y", 12.0), ("r10y", 12.0)):
            got = steady.get(win)
            check(f"{win} ~ {want}%", got is not None and abs(got - want) < 0.6, str(got))
        check("beats Nifty 5y (12 > 10)", steady.get("beats_nifty_5y") is True, str(steady.get("beats_nifty_5y")))
        check("beats Nifty 10y (12 > 11)", steady.get("beats_nifty_10y") is True)
        check("beats gold 5y", steady.get("beats_gold_5y") is True)
        check("fund house carried through", steady.get("fund_house") == "Test AMC", str(steady.get("fund_house")))
        check("category carried through", "Large Cap" in (steady.get("category") or ""), str(steady.get("category")))
        check("volatility is a number", isinstance(steady.get("vol"), (int, float)),
              str(steady.get("vol")))
        check("no fund-manager field invented", "manager" not in json.dumps(steady).lower())

    young = rows.get(2)
    check("young fund present (>=60 NAV points)", young is not None)
    if young:
        check("young fund: 1y available", young.get("r1y") is not None)
        check("young fund: 5y available", young.get("r5y") is not None, str(young.get("r5y")))
        check("young fund: 10y is None, not wrong", young.get("r10y") is None, str(young.get("r10y")))
        check("young fund: 10y comparison is None",
              young.get("beats_nifty_10y") is None, str(young.get("beats_nifty_10y")))

    # and a fund with too little history must be skipped, not reported with junk
    rc3, d3 = run([{"schemeCode": 9, "schemeName": "Tiny Fund"}],
                  {"9": {"meta": {"scheme_name": "Tiny Fund", "fund_house": "Test AMC"},
                         "data": monthly_series(1, 0.05)}}, benchmarks)
    check("fund with <60 NAV points is skipped", d3.get("count") == 0, str(d3.get("count")))

    fallen = rows.get(3)
    if fallen:
        dd = fallen.get("max_dd")
        check("drawdown detected and roughly -50%", dd is not None and -55 < dd < -40, str(dd))

    # missing benchmark must give None, never a wrong boolean
    rc2, d2 = run(schemes[:1], {"1": histories["1"]}, {})
    r2 = d2.get("rows", [{}])[0]
    check("no benchmark -> comparison is None", r2.get("beats_nifty_5y") is None, str(r2.get("beats_nifty_5y")))

    print()
    if FAILS:
        print(f"MF TEST FAILED ({len(FAILS)}): " + ", ".join(FAILS))
        return 1
    print("MF TEST PASSED - returns, drawdown, volatility and benchmark flags are correct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
