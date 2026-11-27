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

import sys as _sys
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from _archive import pick_candles  # noqa: E402

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


Z80 = 1.2816   # two-sided 80% normal quantile


def _err(actual: np.ndarray, pred: np.ndarray, last_train: float | None = None,
         sigma: float | None = None) -> dict:
    """Error, direction hit rate and 80% band coverage.

    hit     - did the model get the SIGN of the move right, against the last training close.
              A model that is always slightly wrong in the right direction scores 100 here while
              its MAPE stays poor; that is the point of reporting both.
    cover80 - did the outcome land inside a band built from the training volatility. A band that
              covers far less than 80% of outcomes is too narrow to be honest about.
    """
    a, p = np.asarray(actual, float), np.asarray(pred, float)
    n = min(len(a), len(p))
    a, p = a[:n], p[:n]
    if n == 0:
        return {"mae": float("nan"), "rmse": float("nan"), "mape": float("nan"),
                "hit": float("nan"), "cover80": float("nan")}
    mae = float(np.mean(np.abs(a - p)))
    rmse = float(np.sqrt(np.mean((a - p) ** 2)))
    denom = np.where(np.abs(a) < 1e-9, np.nan, np.abs(a))
    mape = float(np.nanmean(np.abs((a - p) / denom)) * 100) if np.isfinite(denom).any() else float("nan")

    hit = float("nan")
    if last_train is not None and np.isfinite(last_train) and n > 0:
        want = np.sign(a[-1] - last_train)
        got = np.sign(p[-1] - last_train)
        if want != 0:
            hit = 100.0 if want == got else 0.0

    cover = float("nan")
    if sigma is not None and np.isfinite(sigma) and sigma > 0:
        steps = np.arange(1, n + 1)
        # sigma is the standard deviation of LOG returns - a fraction, not rupees. The band has to
        # be scaled by the predicted price or it is compared against the wrong units and covers
        # nothing, which is what happened on the first run: cover80 read 0% for every model.
        half = np.abs(p) * Z80 * sigma * np.sqrt(steps)
        cover = float(np.mean(np.abs(a - p) <= half) * 100)

    return {"mae": mae, "rmse": rmse, "mape": mape, "hit": hit, "cover80": cover}


def walk_forward(y: np.ndarray, fn, horizon: int, season: int,
                 origins: int = 6, min_train: int = 60) -> list[dict]:
    """Rolling origins, oldest first.

    One train/test split tells you how a model did on one particular week. Six origins spread
    back through the series tell you whether it was luck. The returned list is what the caller
    splits into an earlier half for choosing the model and a later half for reporting it.
    """
    n = len(y)
    if n < min_train + horizon:
        return []
    span = n - horizon - min_train
    if span <= 0:
        return []
    step = max(1, span // max(1, origins - 1))
    cuts, o = [], n - horizon
    while o >= min_train and len(cuts) < origins:
        cuts.append(o)
        o -= step
    cuts.reverse()

    out = []
    for cut in cuts:
        tr, te = y[:cut], y[cut:cut + horizon]
        if len(tr) < min_train or len(te) < horizon:
            continue
        try:
            pred = np.asarray(fn(tr, horizon, season), float)
        except Exception:
            continue
        if not np.all(np.isfinite(pred)):
            continue
        # volatility of the training window, used for the band
        r = np.diff(np.log(np.maximum(tr, 1e-9)))
        sigma = float(np.std(r)) if len(r) > 2 else float("nan")
        e = _err(te, pred, last_train=float(tr[-1]), sigma=sigma)
        e["origin"] = int(cut)
        e["n_train"] = int(len(tr))
        e["sigma"] = sigma
        e["pred"] = pred
        e["actual"] = te
        out.append(e)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Forecast with free models + walk-forward accuracy.")
    ap.add_argument("--in", dest="infile", default="")
    ap.add_argument("--symbols", nargs="*", default=None)
    ap.add_argument("--models", default="naive,drift,mean,seasonal_naive,ets,arima")
    ap.add_argument("--horizon", type=int, default=21)
    ap.add_argument("--season", type=int, default=5)
    ap.add_argument("--min-history", type=int, default=120)
    ap.add_argument("--origins", type=int, default=6,
                    help="walk-forward origins per symbol (spec asks for at least 6)")
    ap.add_argument("--min-train", type=int, default=60,
                    help="shortest training window an origin may use")
    ap.add_argument("--out", default="data/forecast")
    args = ap.parse_args()

    if not args.infile:
        args.infile = pick_candles()
    src = Path(args.infile) if args.infile else None

    # FALLBACK WHEN THE CANDLE ARCHIVE IS ABSENT.
    # cm_daily_adj.parquet lives on Google Drive and is not in the repository, so this step
    # produced nothing on every run for two weeks. It exited 0, build_forecast_page.py then
    # wrote "skipped (no accuracy.csv)", and the site check kept the previous forecast.json -
    # so the forecast tab showed 13-day-old numbers while every run reported success.
    # docs/series.json holds 120 daily closes for ~2,200 symbols and IS committed, which is
    # enough history for every model here.
    if src is None or not src.exists():
        sj = Path("docs/series.json")
        if not sj.exists():
            print("no candle archive and no docs/series.json - skipping")
            return 0
        raw = json.loads(sj.read_text())
        ser = raw.get("series") or raw
        rows = []
        for sym, vals in ser.items():
            if not isinstance(vals, list):
                continue
            for i, v in enumerate(vals):
                if v is None:
                    continue
                rows.append({"symbol": str(sym).split(".")[0], "close": float(v), "date": i})
        if not rows:
            print("docs/series.json held no usable closes - skipping")
            return 0
        df = pd.DataFrame(rows)
        sortcol = "date"
        print(f"forecast from {sj} (candle archive absent) | {len(ser)} symbols")
    else:
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

        per_model = {}
        for name in wanted:
            fn = MODELS[name]
            runs = walk_forward(y, fn, args.horizon, args.season,
                                origins=args.origins, min_train=args.min_train)
            if runs:
                per_model[name] = runs
            gc.collect()
        if not per_model:
            continue

        # Split the origins: choose on the earlier half, report on the later half. Picking a
        # model on the same scores it is then presented with is how a backtest flatters itself.
        for name, runs in per_model.items():
            half = max(1, len(runs) // 2)
            select_runs = runs[:half]
            report_runs = runs[half:] or runs[-1:]

            def agg(rs, key):
                vals = [r[key] for r in rs if np.isfinite(r.get(key, np.nan))]
                return float(np.mean(vals)) if vals else float("nan")

            acc_rows.append({
                "symbol": sym, "model": name,
                "origins": len(report_runs),
                "n_train": int(report_runs[-1]["n_train"]),
                "mape": agg(report_runs, "mape"),
                "mae": agg(report_runs, "mae"),
                "rmse": agg(report_runs, "rmse"),
                "hit": agg(report_runs, "hit"),
                "cover80": agg(report_runs, "cover80"),
                # what the model was chosen on - kept so the choice can be audited
                "select_mape": agg(select_runs, "mape"),
                "mape_spread": float(np.nanstd([r["mape"] for r in report_runs
                                                if np.isfinite(r.get("mape", np.nan))]))
                                  if report_runs else float("nan"),
            })

            try:
                fut = np.asarray(MODELS[name](y, args.horizon, args.season), float)
                sig = float(np.std(np.diff(np.log(np.maximum(y, 1e-9)))))
                for step, val in enumerate(fut, 1):
                    # scale by the price, same reason as in _err
                    half_band = abs(float(val)) * Z80 * sig * float(np.sqrt(step))
                    fc_rows.append({"symbol": sym, "model": name, "step": step,
                                    "yhat": float(val),
                                    "lo80": float(val - half_band),
                                    "hi80": float(val + half_band)})
            except Exception:
                pass

    # naive is the baseline every other model has to beat
    naive_by_sym = {}
    for r in acc_rows:
        if r["model"] == "naive" and np.isfinite(r["mape"]):
            naive_by_sym[r["symbol"]] = r["mape"]
    for r in acc_rows:
        nv = naive_by_sym.get(r["symbol"])
        r["beats_naive_pp"] = (float(nv) - r["mape"]) if (nv is not None and np.isfinite(r["mape"])) else float("nan")

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

    print("\nmedian by model over the reported origins (lower MAPE is better):")
    med = acc.groupby("model")[["mape", "hit", "cover80", "origins"]].median().sort_values("mape")
    base = med["mape"].get("naive", np.nan)
    print(f"  {'model':16s} {'MAPE':>8s} {'hit':>7s} {'cover80':>8s} {'origins':>8s}  vs naive")
    for m, row in med.iterrows():
        gap = (base - row["mape"]) if (m != "naive" and np.isfinite(base)) else np.nan
        tag = ""
        if np.isfinite(gap):
            tag = f"{gap:+6.2f} pp" + ("" if gap >= 0.5 else "  no clear gain")
        print(f"  {m:16s} {row['mape']:7.2f}% {row['hit']:6.0f}% {row['cover80']:7.0f}% "
              f"{row['origins']:8.0f}  {tag}")
    print("\nA hit rate near 50% means the sign of the move is a coin toss. Cover80 well below 80% "
          "means the band is too narrow to be honest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
