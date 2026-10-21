#!/usr/bin/env python3
"""
timesfm_forecast.py - Google TimesFM zero-shot forecasts (FM3).

Runs the 2.5-200M checkpoint on CPU and writes one JSON the site reads.

WHY THIS IS A SEPARATE WORKFLOW
  Loading the model needs roughly 3-4 GB of RAM. That is fine on a GitHub Actions
  runner (~7 GB) but not on a small container. It is therefore NOT part of the daily
  pipeline - see .github/workflows/timesfm.yml.

MODEL CACHE ON DRIVE
  The checkpoint is ~1 GB. Instead of re-downloading it on every run, the workflow
  pulls it from a Google Drive folder (scripts/timesfm_drive.py) and pushes it back
  if it had to download fresh.

API NOTE
  The `timesfm` package ships TimesFM 2.5 as `timesfm.timesfm_2p5.*`. An earlier
  version of this script imported `from timesfm3 import ...`, which does not exist in
  the package at all - which is why it had never actually run. The calls below were
  read off the installed package, not guessed:
      TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
      model.compile(ForecastConfig(max_context=..., max_horizon=...))
      points, quantiles = model.forecast(horizon=H, inputs=[series, ...])

Output: data/timesfm_forecasts.json
  {
    "model": "...", "updated": "...", "horizon_days": 21,
    "nifty": {...},                       # kept for the old site's report card
    "forecasts": [ {symbol,name,last,median_chg_pct,low10_chg_pct,high90_chg_pct,confidence}, ... ]
  }

Usage:
  python scripts/timesfm_forecast.py
  python scripts/timesfm_forecast.py --max-series 40 --context 512
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

# keep CPU memory tight before torch/numpy import
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
    os.environ.setdefault(_v, "2")
os.environ.setdefault("HF_HOME", os.environ.get("HF_HOME", "/tmp/hf"))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

MODEL_ID = "google/timesfm-2.5-200m-pytorch"
OUT = Path("data/timesfm_forecasts.json")

# index/asset series to forecast even if they are not in the stock config
EXTRA = {
    "^NSEI": "Nifty 50",
    "^NSEBANK": "Bank Nifty",
    "^INDIAVIX": "India VIX",
    "^GSPC": "S&P 500",
    "^IXIC": "Nasdaq",
    "^DJI": "Dow Jones",
    "^N225": "Nikkei 225",
    "^HSI": "Hang Seng",
    "^FTSE": "FTSE 100",
    "GC=F": "Gold",
    "CL=F": "Crude Oil",
    "BTC-USD": "Bitcoin",
    "INR=X": "USD/INR",
}


def load_series(max_series: int, years: int) -> dict[str, pd.Series]:
    """Close series per symbol: watched stocks from the candle archive, plus indices."""
    out: dict[str, pd.Series] = {}

    # 1. local candle archive (already back-adjusted)
    for cand in ("data/candles/daily_adj.parquet", "data/candles/cm_daily_adj.parquet"):
        p = Path(cand)
        if p.exists():
            try:
                df = pd.read_parquet(p)
                sortcol = "ts" if "ts" in df.columns else "date"
                df = df.sort_values(["symbol", sortcol])
                counts = df.groupby("symbol").size().sort_values(ascending=False)
                keep = list(counts[counts >= 120].index)[:max_series]
                for s in keep:
                    g = df[df["symbol"] == s]
                    out[str(s)] = pd.Series(g["close"].astype(float).values)
            except Exception as e:
                print(f"  [warn] could not read {cand}: {e}")
            break

    # 2. indices / global / crypto via Yahoo
    try:
        import yfinance as yf
        for sym, name in EXTRA.items():
            try:
                d = yf.download(sym, period=f"{years}y", interval="1d",
                                progress=False, auto_adjust=True)
                if d is None or len(d) < 120:
                    continue
                col = "Close"
                if isinstance(d.columns, pd.MultiIndex):
                    d.columns = d.columns.get_level_values(0)
                s = d[col].dropna().astype(float)
                if len(s) >= 120:
                    out[sym] = pd.Series(s.values)
            except Exception as e:
                print(f"  [warn] yahoo {sym}: {type(e).__name__}")
    except ImportError:
        print("  [warn] yfinance not installed - forecasting local series only")

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="TimesFM forecasts -> data/timesfm_forecasts.json")
    ap.add_argument("--context", type=int, default=512, help="lookback window fed to the model")
    ap.add_argument("--horizon", type=int, default=63, help="steps forecast; 21d slice is reported")
    ap.add_argument("--report-days", type=int, default=21, help="horizon the site reports")
    ap.add_argument("--max-series", type=int, default=60)
    ap.add_argument("--years", type=int, default=2)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    series = load_series(args.max_series, args.years)
    print(f"series to forecast: {len(series)}")
    if not series:
        print("nothing to forecast - no series with enough history")
        return 0

    # ---- load the model (the memory-heavy step) ----
    from timesfm.timesfm_2p5.timesfm_2p5_torch import TimesFM_2p5_200M_torch
    from timesfm.configs import ForecastConfig

    print(f"loading {MODEL_ID} on CPU ...")
    try:
        model = TimesFM_2p5_200M_torch.from_pretrained(MODEL_ID)
        model.compile(ForecastConfig(max_context=args.context,
                                     max_horizon=args.horizon,
                                     per_core_batch_size=1))
    except Exception as e:  # noqa: BLE001
        print(f"FATAL: could not load TimesFM ({type(e).__name__}: {str(e)[:140]})")
        print("  The 200M checkpoint plus torch needs about 3-4 GB of RAM.")
        print("  Run this on a runner with more memory (see .github/workflows/timesfm.yml).")
        return 1

    # ---- forecast ----
    syms = list(series)
    inputs = [np.asarray(series[s], dtype=float)[-args.context:] for s in syms]
    points, quantiles = model.forecast(horizon=args.horizon, inputs=inputs)
    points = np.asarray(points, dtype=float)
    quantiles = np.asarray(quantiles, dtype=float)

    k = args.report_days - 1
    rows = []
    for i, sym in enumerate(syms):
        hist = inputs[i]
        last = float(hist[-1])
        med_abs = float(points[i][k])
        if not last or not np.isfinite(med_abs):
            continue
        q = quantiles[i][k] if quantiles.ndim == 3 else quantiles[i]
        q = np.asarray(q, dtype=float)
        low_abs, high_abs = float(np.min(q)), float(np.max(q))
        median_chg = (med_abs / last - 1) * 100
        low_chg = (low_abs / last - 1) * 100
        high_chg = (high_abs / last - 1) * 100
        # confidence: how tight the 10-90 band is, as a share of the price.
        # a wide band means the model is unsure. 100 = tight, 0 = very wide.
        band_pct = abs(high_chg - low_chg)
        confidence = int(max(0, min(100, round(100 - band_pct * 4))))
        rows.append({
            "symbol": sym,
            "name": EXTRA.get(sym, sym),
            "last": round(last, 2),
            "median_chg_pct": round(median_chg, 2),
            "low10_chg_pct": round(low_chg, 2),
            "high90_chg_pct": round(high_chg, 2),
            "confidence": confidence,
            "direction": "up" if median_chg > 0.25 else ("down" if median_chg < -0.25 else "flat"),
        })

    rows.sort(key=lambda r: -r["median_chg_pct"])
    payload = {
        "model": "TimesFM 2.5 200M (zero-shot)",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "horizon_days": args.report_days,
        "series": len(rows),
        "forecasts": rows,
    }
    nif = next((r for r in rows if r["symbol"] == "^NSEI"), None)
    if nif:
        payload["nifty"] = nif

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, indent=2))
    print(f"Wrote {dest}  |  {len(rows)} series, {args.report_days}d horizon")
    if nif:
        print(f"  Nifty {args.report_days}d: {nif['median_chg_pct']:+.2f}%  "
              f"(band {nif['low10_chg_pct']:+.2f} to {nif['high90_chg_pct']:+.2f}, "
              f"confidence {nif['confidence']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
