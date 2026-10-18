"""
indicators.py - a small, dependency-light technical-indicator library.

Pure pandas/numpy, no TA package required. Every function takes plain Series (or a
DataFrame with open/high/low/close/volume) and returns Series/DataFrame, so it works
on any of the hub's candle archives.

Included: SMA, EMA, WMA, RSI (Wilder), MACD, Bollinger, True Range, ATR, Stochastic,
ADX/DI, OBV, VWAP, Donchian, CCI, ROC, Williams %R, Supertrend, plus `add_all()`.

Conventions, stated so there are no surprises:
  * EMA uses adjust=False and seeds from the first value (the trading convention, not
    pandas' default adjust=True) - so ema(x, n).iloc[0] == x.iloc[0].
  * RSI/ATR/ADX use Wilder smoothing (alpha = 1/n), which is what charting platforms show.
  * Rolling windows are trailing and include the current bar - no look-ahead.
  * NaN while a window is still filling, never a silent zero.

Verify with: python scripts/test_indicators.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd


# ------------------------------------------------------------------ moving averages
def sma(s: pd.Series, n: int = 20) -> pd.Series:
    return s.rolling(n).mean()


def ema(s: pd.Series, n: int = 20) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def wma(s: pd.Series, n: int = 20) -> pd.Series:
    w = np.arange(1, n + 1)
    return s.rolling(n).apply(lambda x: float(np.dot(x, w) / w.sum()), raw=True)


def _wilder(s: pd.Series, n: int) -> pd.Series:
    """Wilder's smoothing == EMA with alpha = 1/n."""
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


# ------------------------------------------------------------------ momentum
def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    delta = close.diff()
    up = delta.clip(lower=0.0)
    down = (-delta).clip(lower=0.0)
    rs = _wilder(up, n) / _wilder(down, n).replace(0.0, np.nan)
    out = 100.0 - (100.0 / (1.0 + rs))
    # all-gains window -> RSI 100, all-losses -> 0 (avoid NaN from a zero denominator)
    out = out.where(~((_wilder(down, n) == 0) & (_wilder(up, n) > 0)), 100.0)
    return out


def macd(close: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    line = ema(close, fast) - ema(close, slow)
    sig = ema(line, signal)
    return pd.DataFrame({"macd": line, "macd_signal": sig, "macd_hist": line - sig})


def roc(close: pd.Series, n: int = 10) -> pd.Series:
    return close.pct_change(n) * 100.0


def cci(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 20) -> pd.Series:
    tp = (high + low + close) / 3.0
    ma = tp.rolling(n).mean()
    md = (tp - ma).abs().rolling(n).mean()
    return (tp - ma) / (0.015 * md.replace(0.0, np.nan))


def williams_r(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    hh, ll = high.rolling(n).max(), low.rolling(n).min()
    return -100.0 * (hh - close) / (hh - ll).replace(0.0, np.nan)


def stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
               k: int = 14, d: int = 3) -> pd.DataFrame:
    hh, ll = high.rolling(k).max(), low.rolling(k).min()
    kk = 100.0 * (close - ll) / (hh - ll).replace(0.0, np.nan)
    return pd.DataFrame({"stoch_k": kk, "stoch_d": kk.rolling(d).mean()})


# ------------------------------------------------------------------ volatility
def bollinger(close: pd.Series, n: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = close.rolling(n).mean()
    sd = close.rolling(n).std(ddof=0)          # population sd - charting convention
    upper, lower = mid + k * sd, mid - k * sd
    return pd.DataFrame({
        "bb_mid": mid, "bb_upper": upper, "bb_lower": lower,
        "bb_bandwidth": (upper - lower) / mid.replace(0.0, np.nan),
        "bb_pctb": (close - lower) / (upper - lower).replace(0.0, np.nan),
    })


def true_range(high: pd.Series, low: pd.Series, close: pd.Series) -> pd.Series:
    pc = close.shift(1)
    return pd.concat([(high - low).abs(), (high - pc).abs(), (low - pc).abs()], axis=1).max(axis=1)


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    return _wilder(true_range(high, low, close), n)


def donchian(high: pd.Series, low: pd.Series, n: int = 20) -> pd.DataFrame:
    return pd.DataFrame({"dc_upper": high.rolling(n).max(),
                         "dc_lower": low.rolling(n).min()})


# ------------------------------------------------------------------ trend strength
def adx(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.DataFrame:
    up, dn = high.diff(), -low.diff()
    plus_dm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=high.index)
    minus_dm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=high.index)
    tr_s = _wilder(true_range(high, low, close), n).replace(0.0, np.nan)
    plus_di = 100.0 * _wilder(plus_dm, n) / tr_s
    minus_di = 100.0 * _wilder(minus_dm, n) / tr_s
    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, np.nan)
    return pd.DataFrame({"adx": _wilder(dx, n), "plus_di": plus_di, "minus_di": minus_di})


def supertrend(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 10, mult: float = 3.0) -> pd.DataFrame:
    a = atr(high, low, close, period)
    hl2 = (high + low) / 2.0
    upper, lower = hl2 + mult * a, hl2 - mult * a
    fu, fl = upper.copy(), lower.copy()
    for i in range(1, len(close)):
        fu.iloc[i] = min(upper.iloc[i], fu.iloc[i - 1]) if (close.iloc[i - 1] <= fu.iloc[i - 1]) else upper.iloc[i]
        fl.iloc[i] = max(lower.iloc[i], fl.iloc[i - 1]) if (close.iloc[i - 1] >= fl.iloc[i - 1]) else lower.iloc[i]
    direction = pd.Series(np.nan, index=close.index)
    line = pd.Series(np.nan, index=close.index)
    for i in range(1, len(close)):
        if close.iloc[i] > fu.iloc[i - 1]:
            direction.iloc[i] = 1.0
        elif close.iloc[i] < fl.iloc[i - 1]:
            direction.iloc[i] = -1.0
        else:
            direction.iloc[i] = direction.iloc[i - 1] if not np.isnan(direction.iloc[i - 1]) else 1.0
        line.iloc[i] = fl.iloc[i] if direction.iloc[i] > 0 else fu.iloc[i]
    return pd.DataFrame({"supertrend": line, "st_dir": direction})


# ------------------------------------------------------------------ volume
def obv(close: pd.Series, volume: pd.Series) -> pd.Series:
    sign = np.sign(close.diff().fillna(0.0))
    return (sign * volume).cumsum()


def vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    tp = (high + low + close) / 3.0
    return (tp * volume).cumsum() / volume.cumsum().replace(0.0, np.nan)


# ------------------------------------------------------------------ convenience
def add_all(df: pd.DataFrame) -> pd.DataFrame:
    """Attach the full indicator set to an OHLCV frame (columns lower-case)."""
    out = df.copy()
    c, h, l, v = out["close"], out["high"], out["low"], out["volume"]

    for n in (20, 50, 200):
        out[f"sma_{n}"] = sma(c, n)
    for n in (9, 21):
        out[f"ema_{n}"] = ema(c, n)
    out["wma_20"] = wma(c, 20)
    out["rsi_14"] = rsi(c, 14)
    out = out.join(macd(c))
    out = out.join(bollinger(c))
    out["atr_14"] = atr(h, l, c, 14)
    out["atr_pct"] = out["atr_14"] / c.replace(0.0, np.nan)
    out = out.join(stochastic(h, l, c))
    out = out.join(adx(h, l, c))
    out = out.join(donchian(h, l))
    out = out.join(supertrend(h, l, c))
    out["cci_20"] = cci(h, l, c)
    out["williams_r"] = williams_r(h, l, c)
    out["roc_10"] = roc(c, 10)
    out["obv"] = obv(c, v)
    out["vwap"] = vwap(h, l, c, v)
    return out


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Compute indicators for one CSV of OHLCV.")
    ap.add_argument("csv")
    ap.add_argument("--tail", type=int, default=5)
    args = ap.parse_args()
    df = pd.read_csv(args.csv)
    df.columns = [c.lower() for c in df.columns]
    out = add_all(df)
    cols = ["close", "sma_20", "ema_21", "rsi_14", "macd", "atr_14", "adx", "supertrend", "st_dir"]
    print(out[cols].tail(args.tail).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
