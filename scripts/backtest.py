#!/usr/bin/env python3
"""
backtest.py - a walk-forward backtest harness for rule-based strategies.

This is the piece that turns indicators into evidence. Without it, everything else is
just numbers.

Correctness rules it enforces (the ones that make backtests lie when you skip them):
  * NO LOOK-AHEAD. A signal computed from bar i is executed at bar i+1's OPEN, never
    at bar i's close. Trading on the close you just used to decide is the classic
    way to manufacture a great-looking, worthless result.
  * COSTS. Commission + slippage in basis points, charged on every side.
  * STOPS/TARGETS are checked intrabar against the low/high, not the close.
  * TIME-SLICED reporting. Performance is shown per window as well as overall, so you
    can see whether an edge is stable or just one lucky stretch.

Strategies: sma_cross, rsi_reversion, breakout, momentum.

Usage
-----
  python scripts/backtest.py --strategy sma_cross --fast 20 --slow 50
  python scripts/backtest.py --strategy rsi_reversion --stop 0.08 --target 0.15
  python scripts/backtest.py --strategy breakout --cost-bps 5 --windows 4
"""

from __future__ import annotations

import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _archive import pick_candles, read_candles, add_window_arg  # noqa: E402
from indicators import rsi, sma, donchian, roc  # noqa: E402


# ---------------------------------------------------------------- strategies
def strat_sma_cross(df: pd.DataFrame, p: dict) -> pd.Series:
    f, s = sma(df["close"], p["fast"]), sma(df["close"], p["slow"])
    return (f > s).astype(float)


def strat_rsi_reversion(df: pd.DataFrame, p: dict) -> pd.Series:
    r = rsi(df["close"], p["rsi_n"])
    # hold while oversold, exit once it recovers past the exit level
    sig = pd.Series(np.nan, index=df.index)
    sig[r < p["rsi_buy"]] = 1.0
    sig[r > p["rsi_exit"]] = 0.0
    return sig.ffill().fillna(0.0)


def strat_breakout(df: pd.DataFrame, p: dict) -> pd.Series:
    d = donchian(df["high"], df["low"], p["dc_n"])
    return (df["close"] > d["dc_upper"].shift(1)).astype(float)


def strat_momentum(df: pd.DataFrame, p: dict) -> pd.Series:
    return (roc(df["close"], p["roc_n"]) > 0).astype(float)


STRATS = {
    "sma_cross": (strat_sma_cross, {"fast": 20, "slow": 50}),
    "rsi_reversion": (strat_rsi_reversion, {"rsi_n": 14, "rsi_buy": 30, "rsi_exit": 55}),
    "breakout": (strat_breakout, {"dc_n": 20}),
    "momentum": (strat_momentum, {"roc_n": 20}),
}


# ---------------------------------------------------------------- engine
def run_symbol(g: pd.DataFrame, signal: pd.Series, *, cost_bps: float,
               stop: float, target: float, sortcol: str) -> tuple[list[dict], pd.Series]:
    g = g.sort_values(sortcol).reset_index(drop=True)
    o, h, l, c = (g[x].astype(float).to_numpy() for x in ("open", "high", "low", "close"))
    sig = signal.reset_index(drop=True).to_numpy(float)
    dts = g[sortcol].astype(str).to_numpy()
    cost = cost_bps / 10_000.0

    trades, curve = [], [1.0]
    equity = 1.0
    in_pos, entry, entry_i = False, 0.0, 0

    for i in range(1, len(g)):
        # 1. manage an open position (intrabar stop/target, else signal exit at open)
        if in_pos:
            hit_stop = stop and (l[i] <= entry * (1 - stop))
            hit_tgt = target and (h[i] >= entry * (1 + target))
            exit_px = None
            if hit_stop:
                exit_px = entry * (1 - stop)          # assume filled at the stop
            elif hit_tgt:
                exit_px = entry * (1 + target)
            elif sig[i - 1] == 0:                      # signal from the PREVIOUS bar
                exit_px = o[i]                         # exit at THIS bar's open
            if exit_px is not None:
                # `entry` already includes the entry-side cost, so only the exit side
                # is charged here. Charging 2*cost would triple-count.
                ret = exit_px / entry - 1 - cost
                equity *= (1 + ret)
                trades.append({"entry_date": dts[entry_i], "exit_date": dts[i],
                               "entry": round(entry, 4), "exit": round(exit_px, 4),
                               "ret_pct": round(ret * 100, 3),
                               "reason": "stop" if hit_stop else "target" if hit_tgt else "signal"})
                in_pos = False
        # 2. enter on the previous bar's signal, at THIS bar's open
        if not in_pos and sig[i - 1] == 1:
            in_pos, entry, entry_i = True, o[i] * (1 + cost), i
            # conservative: a stop can be hit on the entry bar itself (gap down)
            if stop and l[i] <= entry * (1 - stop):
                exit_px = entry * (1 - stop)
                equity *= (1 + (exit_px / entry - 1 - cost))
                trades.append({"entry_date": dts[i], "exit_date": dts[i],
                               "entry": round(entry, 4), "exit": round(exit_px, 4),
                               "ret_pct": round((exit_px / entry - 1 - cost) * 100, 3),
                               "reason": "stop"})
                in_pos = False
        # 3. mark to market at this bar's close
        curve.append(equity * (c[i] / entry) if in_pos else equity)

    # 4. close anything still open at the last bar. Dropping it would bias every
    #    metric towards only the trades that happened to finish.
    if in_pos:
        ret = c[-1] / entry - 1 - cost
        equity *= (1 + ret)
        trades.append({"entry_date": dts[entry_i], "exit_date": dts[-1],
                       "entry": round(entry, 4), "exit": round(float(c[-1]), 4),
                       "ret_pct": round(ret * 100, 3), "reason": "open_at_end"})
        if curve:
            curve[-1] = equity
    return trades, pd.Series(curve)


def metrics(trades: list[dict], eq: pd.Series, years: float) -> dict:
    if not trades:
        return {"trades": 0}
    r = np.array([t["ret_pct"] / 100 for t in trades])
    wins, losses = r[r > 0], r[r <= 0]
    total = float(eq.iloc[-1]) - 1.0
    peak = eq.cummax()
    mdd = float(((eq - peak) / peak).min())
    cagr = float((1 + total) ** (1 / years) - 1) if years > 0 and total > -1 else float("nan")
    daily = eq.pct_change().dropna()
    sharpe = float(daily.mean() / daily.std() * np.sqrt(252)) if len(daily) > 2 and daily.std() else float("nan")
    return {
        "trades": len(trades),
        "win_rate": round(float(len(wins) / len(r)) * 100, 1),
        "avg_win_pct": round(float(wins.mean() * 100), 2) if len(wins) else 0.0,
        "avg_loss_pct": round(float(losses.mean() * 100), 2) if len(losses) else 0.0,
        "profit_factor": round(float(wins.sum() / abs(losses.sum())), 2) if len(losses) and losses.sum() else None,
        "total_return_pct": round(total * 100, 2),
        "cagr_pct": round(cagr * 100, 2) if np.isfinite(cagr) else None,
        "max_drawdown_pct": round(mdd * 100, 2),
        "sharpe": round(sharpe, 2) if np.isfinite(sharpe) else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Walk-forward backtest of rule-based strategies.")
    ap.add_argument("--in", dest="infile", default="")
    add_window_arg(ap, default=0)
    ap.add_argument("--strategy", default="sma_cross", choices=list(STRATS))
    ap.add_argument("--symbols", nargs="*", default=None)
    ap.add_argument("--cost-bps", type=float, default=5.0, help="per side")
    ap.add_argument("--stop", type=float, default=0.0, help="fractional, e.g. 0.08")
    ap.add_argument("--target", type=float, default=0.0, help="fractional, e.g. 0.15")
    ap.add_argument("--windows", type=int, default=3, help="time slices for stability")
    ap.add_argument("--min-history", type=int, default=250)
    ap.add_argument("--out", default="data/backtest")
    # strategy params (defaults come from STRATS)
    ap.add_argument("--fast", type=int, default=20)
    ap.add_argument("--slow", type=int, default=50)
    ap.add_argument("--rsi-n", type=int, default=14)
    ap.add_argument("--rsi-buy", type=float, default=30)
    ap.add_argument("--rsi-exit", type=float, default=55)
    ap.add_argument("--dc-n", type=int, default=20)
    ap.add_argument("--roc-n", type=int, default=20)
    args = ap.parse_args()

    src = args.infile
    if not src:
        src = pick_candles()
    if not src or not Path(src).exists():
        print("no candle archive found - skipping")
        return 0

    df = pd.read_parquet(src)
    need = {"symbol", "open", "high", "low", "close"}
    missing = need - set(df.columns)
    if missing:
        print(f"candles missing columns: {missing} - skipping")
        return 0
    sortcol = "date" if "date" in df.columns else "ts"
    fn, defaults = STRATS[args.strategy]
    params = {"fast": args.fast, "slow": args.slow, "rsi_n": args.rsi_n,
              "rsi_buy": args.rsi_buy, "rsi_exit": args.rsi_exit,
              "dc_n": args.dc_n, "roc_n": args.roc_n}

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"backtest: {args.strategy} {params} | cost {args.cost_bps}bps/side | "
          f"stop {args.stop} target {args.target} | windows {args.windows}")

    all_trades, rows = [], []
    symbols = args.symbols or sorted(df["symbol"].unique())
    for sym in symbols:
        g = df[df["symbol"] == sym].sort_values(sortcol)
        if len(g) < args.min_history:
            continue
        sig = fn(g, params)
        trades, eq = run_symbol(g, sig, cost_bps=args.cost_bps,
                                stop=args.stop, target=args.target, sortcol=sortcol)
        if not trades:
            continue
        d = pd.to_datetime(g[sortcol], errors="coerce")
        years = max((d.max() - d.min()).days / 365.25, 1e-6)
        m = metrics(trades, eq, years)
        m["symbol"] = sym
        rows.append(m)
        for t in trades:
            all_trades.append({"symbol": sym, **t})

        # time-sliced stability
        if args.windows > 1 and len(g) >= args.windows * 60:
            edges = np.linspace(0, len(g), args.windows + 1).astype(int)
            for w in range(args.windows):
                sub = g.iloc[edges[w]:edges[w + 1]]
                s2 = fn(sub, params)
                t2, e2 = run_symbol(sub, s2, cost_bps=args.cost_bps,
                                    stop=args.stop, target=args.target, sortcol=sortcol)
                if t2:
                    dd = pd.to_datetime(sub[sortcol], errors="coerce")
                    y2 = max((dd.max() - dd.min()).days / 365.25, 1e-6)
                    m2 = metrics(t2, e2, y2)
                    rows.append({**m2, "symbol": f"{sym}#w{w+1}"})

    if not rows:
        print("no trades generated (not enough history, or the rule never fired)")
        return 0

    summ = pd.DataFrame(rows)
    summ.to_csv(out / "summary.csv", index=False)
    if all_trades:
        pd.DataFrame(all_trades).to_csv(out / "trades.csv", index=False)

    overall = [r for r in rows if "#w" not in r["symbol"]]
    if overall:
        o = pd.DataFrame(overall)
        pooled = {
            "symbols_traded": len(o),
            "trades": int(o["trades"].sum()),
            "median_total_return_pct": round(float(o["total_return_pct"].median()), 2),
            "median_cagr_pct": round(float(pd.to_numeric(o["cagr_pct"], errors="coerce").median()), 2),
            "median_max_dd_pct": round(float(o["max_drawdown_pct"].median()), 2),
            "median_win_rate": round(float(o["win_rate"].median()), 1),
            "median_sharpe": round(float(pd.to_numeric(o["sharpe"], errors="coerce").median()), 2),
            "pct_profitable": round(float((o["total_return_pct"] > 0).mean() * 100), 1),
        }
        (out / "summary.json").write_text(json.dumps(pooled, indent=2))
        print("\npooled across symbols:")
        for k, v in pooled.items():
            print(f"  {k:26s} {v}")

    print(f"\nWrote {out}/summary.csv, trades.csv" + (", summary.json" if overall else ""))
    print("  NOTE: a positive backtest is a hypothesis, not a result. Check it holds in "
          "the per-window rows before trusting it.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
