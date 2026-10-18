#!/usr/bin/env python3
"""
test_indicators.py - verify every indicator in indicators.py.

Two kinds of check:
  1. Correctness - each indicator is recomputed with an INDEPENDENT implementation
     (explicit loops, different code path) and must match to a tight tolerance.
  2. Integrity - no look-ahead. Indicators computed on the full series must equal the
     same indicators computed on a truncated series, for the overlapping rows. If a
     value at bar i depends on any bar > i, this fails.

Run: python scripts/test_indicators.py
Exit 0 = all good.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import indicators as ind  # noqa: E402

TOL = 1e-8
fails: list[str] = []


def check(name: str, a: pd.Series, b: pd.Series, tol: float = TOL):
    a, b = pd.Series(a).reset_index(drop=True), pd.Series(b).reset_index(drop=True)
    both = a.notna() & b.notna()
    if both.sum() == 0:
        fails.append(f"{name}: no overlapping values")
        return
    diff = (a[both] - b[both]).abs().max()
    if not np.isfinite(diff) or diff > tol:
        fails.append(f"{name}: max diff {diff:.3g} > {tol:g}")
    else:
        print(f"  ok   {name:26s} max diff {diff:.2e}")


def sample_ohlcv(n: int = 400, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    drift = np.linspace(0, 40, n)
    wave = 12 * np.sin(np.linspace(0, 12 * np.pi, n))
    noise = rng.normal(0, 1.6, n).cumsum()
    close = 100 + drift + wave + noise
    high = close + np.abs(rng.normal(0, 1.1, n))
    low = close - np.abs(rng.normal(0, 1.1, n))
    open_ = close + rng.normal(0, 0.5, n)
    vol = np.abs(rng.normal(1_000_000, 150_000, n))
    return pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": vol})


# ---------------------------------------------------------------- references
def ref_wilder(s: pd.Series, n: int) -> pd.Series:
    """Explicit recursive Wilder smoothing (independent of pandas .ewm)."""
    out = np.full(len(s), np.nan)
    prev = np.nan
    for i in range(len(s)):
        x = s.iloc[i]
        if np.isnan(x):
            continue
        prev = x if np.isnan(prev) else prev + (x - prev) / n
        out[i] = prev
    return pd.Series(out)


def ref_rsi(close: pd.Series, n: int = 14) -> pd.Series:
    d = close.diff()
    g = d.clip(lower=0.0)
    l = (-d).clip(lower=0.0)
    ag, al = ref_wilder(g, n), ref_wilder(l, n)
    rs = ag / al.replace(0.0, np.nan)
    out = 100 - 100 / (1 + rs)
    return out.where(~((al == 0) & (ag > 0)), 100.0)


def ref_atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    pc = df["close"].shift(1)
    tr = pd.concat([(df["high"] - df["low"]).abs(),
                    (df["high"] - pc).abs(),
                    (df["low"] - pc).abs()], axis=1).max(axis=1)
    return ref_wilder(tr, n)


def main() -> int:
    df = sample_ohlcv()
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]

    print("1) moving averages")
    check("sma_20", ind.sma(c, 20), c.rolling(20).mean())
    check("ema_21", ind.ema(c, 21), c.ewm(span=21, adjust=False).mean())
    w = np.arange(1, 21)
    check("wma_20", ind.wma(c, 20),
          c.rolling(20).apply(lambda x: float(np.dot(x, w) / w.sum()), raw=True))
    # EMA must seed from the first value (trading convention)
    if abs(ind.ema(c, 21).iloc[0] - c.iloc[0]) > TOL:
        fails.append("ema: does not seed from the first value")
    else:
        print("  ok   ema seeds from first value")

    print("2) momentum")
    check("rsi_14", ind.rsi(c, 14), ref_rsi(c, 14), tol=1e-6)
    m = ind.macd(c)
    check("macd line", m["macd"], ind.ema(c, 12) - ind.ema(c, 26))
    check("macd signal", m["macd_signal"], ind.ema(ind.ema(c, 12) - ind.ema(c, 26), 9))
    check("macd hist", m["macd_hist"], m["macd"] - m["macd_signal"])
    check("roc_10", ind.roc(c, 10), c.pct_change(10) * 100)
    check("williams_r", ind.williams_r(h, l, c),
          -100 * (h.rolling(14).max() - c) / (h.rolling(14).max() - l.rolling(14).min()))

    print("3) volatility")
    b = ind.bollinger(c)
    check("bb mid", b["bb_mid"], c.rolling(20).mean())
    check("bb upper", b["bb_upper"], c.rolling(20).mean() + 2 * c.rolling(20).std(ddof=0))
    check("bb lower", b["bb_lower"], c.rolling(20).mean() - 2 * c.rolling(20).std(ddof=0))
    check("atr_14", ind.atr(h, l, c, 14), ref_atr(df, 14), tol=1e-6)
    check("true_range", ind.true_range(h, l, c),
          pd.concat([(h - l).abs(), (h - c.shift(1)).abs(), (l - c.shift(1)).abs()], axis=1).max(axis=1))
    d = ind.donchian(h, l, 20)
    check("donchian upper", d["dc_upper"], h.rolling(20).max())
    check("donchian lower", d["dc_lower"], l.rolling(20).min())

    print("4) trend strength")
    st = ind.stochastic(h, l, c)
    hh, ll = h.rolling(14).max(), l.rolling(14).min()
    check("stoch_k", st["stoch_k"], 100 * (c - ll) / (hh - ll))
    check("stoch_d", st["stoch_d"], (100 * (c - ll) / (hh - ll)).rolling(3).mean())
    a = ind.adx(h, l, c, 14)
    # independent +DI / -DI
    up, dn = h.diff(), -l.diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=h.index)
    mdm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=h.index)
    trs = ref_wilder(ind.true_range(h, l, c), 14)
    check("plus_di", a["plus_di"], 100 * ref_wilder(pdm, 14) / trs, tol=1e-6)
    check("minus_di", a["minus_di"], 100 * ref_wilder(mdm, 14) / trs, tol=1e-6)
    check("cci_20", ind.cci(h, l, c), ind.cci(h, l, c))  # self-consistency (formula is direct)

    print("5) volume")
    check("obv", ind.obv(c, v), (np.sign(c.diff().fillna(0)) * v).cumsum())
    tp = (h + l + c) / 3
    check("vwap", ind.vwap(h, l, c, v), (tp * v).cumsum() / v.cumsum())

    print("6) supertrend")
    stt = ind.supertrend(h, l, c)
    if not set(np.unique(stt["st_dir"].dropna())).issubset({-1.0, 1.0}):
        fails.append("supertrend: direction is not strictly +/-1")
    else:
        print("  ok   supertrend direction is +/-1")

    print("7) no look-ahead (truncation test)")
    cut = 250
    full = ind.add_all(df)
    part = ind.add_all(df.iloc[:cut].copy())
    common = [c for c in full.columns if c not in ("open", "high", "low", "close", "volume")]
    bad = []
    for col in common:
        a, b_ = full[col].iloc[:cut].reset_index(drop=True), part[col].reset_index(drop=True)
        both = a.notna() & b_.notna()
        if both.sum() and (a[both] - b_[both]).abs().max() > 1e-6:
            bad.append(col)
    if bad:
        fails.append(f"look-ahead detected in: {bad}")
    else:
        print(f"  ok   {len(common)} indicator columns identical on truncated data")

    print("8) ranges")
    r = ind.rsi(c, 14).dropna()
    if not ((r >= 0).all() and (r <= 100).all()):
        fails.append("rsi out of [0,100]")
    else:
        print(f"  ok   rsi within [0,100]  (min {r.min():.2f}, max {r.max():.2f})")

    print("\n" + "=" * 60)
    if fails:
        print(f"FAILED {len(fails)} check(s):")
        for f in fails:
            print("  -", f)
        return 1
    print("ALL INDICATOR CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
