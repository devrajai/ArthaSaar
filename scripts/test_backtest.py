#!/usr/bin/env python3
"""
test_backtest.py - prove the backtester's execution rules, don't assume them.

The claims that matter in a backtest are about TIMING, so they are tested precisely:
  1. a signal on bar i is executed at bar i+1's OPEN (not bar i's close)
  2. an exit signal on bar i exits at bar i+1's OPEN
  3. a stop is checked intrabar against the LOW, not the close
  4. costs are charged on both sides
  5. a cheating (future-peeking) signal does NOT produce absurd returns

Run: python scripts/test_backtest.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from backtest import run_symbol  # noqa: E402

fails: list[str] = []


def make(dates, opens, highs, lows, closes):
    return pd.DataFrame({"symbol": "X", "date": dates, "open": opens, "high": highs,
                         "low": lows, "close": closes, "volume": [1000] * len(dates)})


def sig(vals):
    return pd.Series([float(v) for v in vals])


def check(name, cond, detail=""):
    if cond:
        print(f"  ok   {name}")
    else:
        fails.append(f"{name} {detail}")
        print(f"  FAIL {name} {detail}")


def main() -> int:
    dates = [f"2024-01-{i:02d}" for i in range(1, 11)]
    o = [100, 101, 102, 103, 104, 105, 106, 107, 108, 109]
    h = [x + 2 for x in o]
    l = [x - 2 for x in o]
    c = [x + 1 for x in o]
    df = make(dates, o, h, l, c)

    print("1) entry timing")
    s = sig([0, 0, 1, 1, 1, 1, 1, 1, 1, 1])   # signal turns on at bar index 2
    trades, _ = run_symbol(df, s, cost_bps=0, stop=0, target=0, sortcol="date")
    if not trades:
        fails.append("entry timing: no trade taken")
    else:
        t = trades[0]
        check("entry lands on the bar AFTER the signal",
              t["entry_date"] == dates[3], f"(got {t['entry_date']}, expected {dates[3]})")
        check("entry price is that bar's open", abs(t["entry"] - o[3]) < 1e-9,
              f"(got {t['entry']}, expected {o[3]})")

    print("2) exit timing")
    s2 = sig([1, 1, 1, 0, 0, 0, 0, 0, 0, 0])   # exit signal at bar index 3
    trades2, _ = run_symbol(df, s2, cost_bps=0, stop=0, target=0, sortcol="date")
    if trades2:
        check("exit lands on the bar AFTER the exit signal",
              trades2[0]["exit_date"] == dates[4], f"(got {trades2[0]['exit_date']})")
    else:
        fails.append("exit timing: no trade taken")

    print("3) stop is intrabar (checked against the low)")
    # entry at bar1 open=101; stop 10% -> 90.9. bar2 low=100 does not hit; make a bar with a deep wick
    o3 = [100, 100, 100, 100]
    h3 = [101, 101, 101, 101]
    l3 = [99, 99, 89, 99]      # bar index 2 dips to 89 -> below 90.9
    c3 = [100, 100, 100, 100]
    df3 = make(dates[:4], o3, h3, l3, c3)
    s3 = sig([0, 1, 1, 1])
    t3, _ = run_symbol(df3, s3, cost_bps=0, stop=0.10, target=0, sortcol="date")
    if t3:
        check("stop fires on an intrabar low", t3[0]["reason"] == "stop", f"(got {t3[0]['reason']})")
        check("stop fill is at the stop price", abs(t3[0]["exit"] - 100 * 0.90) < 1e-6,
              f"(got {t3[0]['exit']})")
    else:
        fails.append("stop: no trade taken")

    print("4) costs are charged")
    s4 = sig([1] * 10)
    free, _ = run_symbol(df, s4, cost_bps=0, stop=0, target=0, sortcol="date")
    costly, _ = run_symbol(df, s4, cost_bps=50, stop=0, target=0, sortcol="date")
    if free and costly:
        check("higher costs give a worse return",
              costly[0]["ret_pct"] < free[0]["ret_pct"],
              f"({costly[0]['ret_pct']} vs {free[0]['ret_pct']})")
        check("cost drag is about 2 sides",
              abs((free[0]["ret_pct"] - costly[0]["ret_pct"]) - 1.0) < 0.05,
              f"(drag {free[0]['ret_pct'] - costly[0]['ret_pct']:.3f}%, expected ~1.0%)")
    else:
        fails.append("costs: no trade taken")

    print("5) a future-peeking signal does not pay off")
    # build a series where the next bar is knowable, then cheat with it.
    # if the engine executed at bar i's close, this would be wildly profitable.
    rng = np.random.default_rng(5)
    n = 300
    c5 = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, n)))
    o5 = c5 * 0.995
    h5 = c5 * 1.01
    l5 = c5 * 0.99
    d5 = [f"2024-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}" for i in range(n)]
    df5 = make(d5, o5, h5, l5, c5)
    peek = pd.Series(np.append((c5[1:] > c5[:-1]).astype(float), 0.0))   # uses the FUTURE
    trades5, eq5 = run_symbol(df5, peek, cost_bps=5, stop=0, target=0, sortcol="date")
    total = float(eq5.iloc[-1]) - 1
    check("cheating signal does not produce an absurd return",
          total < 3.0, f"(got {total * 100:.1f}% - if this is huge, the engine has look-ahead)")

    print("\n" + "=" * 60)
    if fails:
        print(f"FAILED {len(fails)} check(s):")
        for f in fails:
            print("  -", f)
        return 1
    print("ALL BACKTEST TIMING CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
