#!/usr/bin/env python3
"""
forecast.py - forecasting with free models, and an honest accuracy number for each.

This is deliberately model-agnostic. It runs whatever is available and reports how
each one actually did on a held-out slice, so you can see whether a fancy model beats
a dumb baseline instead of assuming it.

Models, cheapest first:
  naive           last value carried forward
  drift           last value + average slope
  mean            the training mean
  seasonal_naive  repeat the last `season` points (default 5 = a trading week)
  ets             statsmodels Holt-Winters / exponential smoothing
  arima           statsmodels ARIMA(1,1,1)
  timesfm         Google TimesFM 3.0  (only if `timesfm` is installed - heavy)
  chronos         Amazon Chronos     (only if `chronos` is installed)

Validation is WALK-FORWARD, never a random split: the last `horizon` points are held
out, each model is fit only on the earlier data, and the error is measured against the
held-out truth. Markets are time-ordered - a random split leaks the future and makes
every model look good.

Honest note: none of these know about news, earnings or policy. A model beating naive
on one symbol is a lead, not a result. Check it across many symbols before believing it.

Usage
-----
  python scripts/forecast.py                                  # all symbols, all models
  python scripts/forecast.py --models naive,ets --horizon 21
  python scripts/forecast.py --symbols RELIANCE TCS --in data/candles/cm_daily.parquet
"""

from __future__ import annotations

# Set thread caps BEFORE numpy/statsmodels load: some containers (and this sandbox)
# have a low thread/memory ceiling and OpenBLAS aborts with "Memory allocation failed"
# if it tries to spin up one worker per core.
import os
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
    os.environ.setdefault(_v, "1")

import argparse
import gc
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

# ---------------------------------------------------------------- models
def m_naive(tr: np.ndarray, h: int, season: int) -> np.ndarray:
    return np.repeat(tr[-1], h)


def m_drift(tr: np.ndarray, h: int, season: int) -> np.ndarray:
    slope = (tr[-1] - tr[0]) / max(len(tr) - 1, 1)
    return tr[-1] + slope * np.arange(1, h + 1)


def m_mean(tr: np.ndarray, h: int, season: int) -> np.ndarray:
    return np.repeat(tr.mean(), h)


def m_seasonal_naive(tr: np.ndarray, h: int, season: int) -> np.ndarray:
    if len(tr) < season:
        return m_naive(tr, h, season)
    reps = int(np.ceil(h / season))
    return np.tile(tr[-season:], reps)[:h]


def m_ets(tr: np.ndarray, h: int, season: int) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing
    fit = ExponentialSmoothing(tr, trend="add", seasonal=None,
                               initialization_method="estimated").fit()
    return np.asarray(fit.forecast(h), dtype=float)


def m_arima(tr: np.ndarray, h: int, season: int) -> np.ndarray:
    from statsmodels.tsa.arima.model import ARIMA
    fit = ARIMA(tr, order=(1, 1, 1)).fit()
    return np.asarray(fit.forecast(h), dtype=float)


def m_timesfm(tr: np.ndarray, h: int, season: int) -> np.ndarray:
    from timesfm3 import ModelConfig, TimesFM3Forecaster  # heavy optional dep
    cfg = ModelConfig(checkpoint_path="google/timesfm-3.0-pytorch",
                      per_core_batch_size=8, device="cpu")
    f = TimesFM3Forecaster(cfg)
    out = list(f.predict_batch(contexts=[tr.astype(np.float32)], horizon=h))[0]
    return np.asarray(out.forecast, dtype=float)


def m_chronos(tr: np.ndarray, h: int, season: int) -> np.ndarray:
    from chronos import ChronosPipeline  # heavy optional dep
    import torch
    pipe = ChronosPipeline.from_pretrained("amazon/chronos-t5-small",
                                           device_map="cpu", torch_dtype=torch.float32)
    ctx = torch.tensor(tr, dtype=torch.float32).unsqueeze(0)
    q, _ = pipe.predict(ctx, h)          # (1, n_quantiles, h)
    return np.asarray(q[0].median(dim=0).values, dtype=float)


MODELS = {
    "naive": m_naive, "drift": m_drift, "mean": m_mean,
    "seasonal_naive": m_seasonal_naive, "ets": m_ets, "arima": m_arima,
    "timesfm": m_timesfm, "chronos": m_chronos,
}
CHEAP = ["naive", "drift", "mean", "seasonal_naive"]


def _err(actual: np.ndarray, pred: np.ndarray) -> dict:
    a, p = np.asarray(actual, float), np.asarray(pred, float)
    n = min(len(a), len(p))
    a, p = a[:n], p[:n]
    mae = float(np.mean(np.abs(a - p)))
    rmse = float(np.sqrt(np.mean((a - p) ** 2)))
    denom = np.where(np.abs(a) < 1e-9, np.nan, np.abs(a))
    mape = float(np.nanmean(np.abs((a - p) / denom)) * 100) if np.isfinite(denom).any() else float("nan")
    # direction hit-rate on step 1 vs the last training value
    return {"mae": mae, "rmse": rmse, "mape": mape}


def main() -> int:
    ap = argparse.ArgumentParser(description="Forecast with free models + walk-forward accuracy.")
    ap.add_argument("--in", dest="infile", default="")
    ap.add_argument("--symbols", nargs="*", default=None)
    ap.add_argument("--models", default="naive,drift,mean,seasonal_naive,ets,arima")
    ap.add_argument("--horizon", type=int, default=21)
    ap.add_argument("--season", type=int, default=5)
    ap.add_argument("--min-history", type=int, default=120)
    ap.add_argument("--out", default="data/forecast")
    args = ap.parse_args()

    if not args.infile:
        for cand in ("data/candles/daily.parquet", "data/candles/cm_daily.parquet"):
            if Path(cand).exists():
                args.infile = cand
                break
    src = Path(args.infile) if args.infile else None
    if src is None or not src.exists():
        print("no candle archive found - skipping")
        return 0

    df = pd.read_parquet(src)
    if not {"symbol", "close"}.issubset(df.columns):
        print("candles need symbol + close - skipping")
        return 0
    sortcol = "ts" if "ts" in df.columns else "date"
    wanted = [m.strip() for m in args.models.split(",") if m.strip() in MODELS]

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    print(f"forecast from {src} | horizon={args.horizon} | models={','.join(wanted)}")

    acc_rows, fc_rows = [], []
    symbols = args.symbols or sorted(df["symbol"].unique())
    for sym in symbols:
        g = df[df["symbol"] == sym].sort_values(sortcol)
        y = pd.to_numeric(g["close"], errors="coerce").dropna().to_numpy(float)
        if len(y) < args.min_history:
            continue
        tr, te = y[: -args.horizon], y[-args.horizon:]

        for name in wanted:
            fn = MODELS[name]
            try:
                pred = np.asarray(fn(tr, args.horizon, args.season), float)
            except Exception as e:  # noqa: BLE001 - a missing heavy dep must not kill the run
                if name not in CHEAP:
                    print(f"  {sym:12s} {name:15s} unavailable "
                          f"({type(e).__name__}: {str(e)[:70]})")
                gc.collect()   # a failed heavy fit can leave memory fragmented
                continue
            e = _err(te, pred)
            gc.collect()
            acc_rows.append({"symbol": sym, "model": name, "n_train": len(tr), **e})
            try:
                fut = np.asarray(fn(y, args.horizon, args.season), float)
                for step, val in enumerate(fut, 1):
                    fc_rows.append({"symbol": sym, "model": name, "step": step, "yhat": float(val)})
            except Exception:
                pass

    if not acc_rows:
        print("no model produced a forecast - see the errors above "
              "(either not enough history, or the model deps failed to load)")
        return 0

    acc = pd.DataFrame(acc_rows)
    try:
        acc.to_csv(out / "accuracy.csv", index=False)
        if fc_rows:
            pd.DataFrame(fc_rows).to_parquet(out / "forecasts.parquet", index=False)
    except MemoryError:
        gc.collect()
        acc.to_csv(out / "accuracy.csv", index=False)   # retry once after cleanup

    print(f"\nWrote {out}/accuracy.csv  ({acc['symbol'].nunique()} symbols x {acc['model'].nunique()} models)")
    if fc_rows:
        print(f"  + {out}/forecasts.parquet ({len(fc_rows)} forward points)")

    print("\nmedian MAPE by model (lower is better):")
    med = (acc.groupby("model")["mape"].median().sort_values())
    base = med.get("naive", np.nan)
    for m, v in med.items():
        tag = ""
        if m != "naive" and np.isfinite(base):
            tag = f"  ({'better' if v < base else 'worse'} than naive)"
        print(f"  {m:16s} {v:7.2f}%{tag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
