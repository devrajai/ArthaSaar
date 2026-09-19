#!/usr/bin/env python3
"""
MARKET BRAIN — TimesFM 3.0 weekly forecasts (Phase 5).

Google Research's TimesFM 3.0 (330M params, released Aug 2026) is a zero-shot
time-series foundation model. This script:

  1. Downloads ~2 years of daily closes (Yahoo Finance) for key indices,
     top stocks and crypto.
  2. Runs TimesFM 3.0 on CPU (free GitHub Actions runner) to forecast the
     next 21 daily steps (~1 month) with 10th-90th percentile bands.
  3. Saves data/timesfm_forecasts.json for the daily digest + website.

Model weights (~1.3 GB) download on each run from HuggingFace — weekly
schedule keeps this cheap. License: non-commercial (fine for personal use).

IMPORTANT: TimesFM extrapolates statistical patterns in price history.
It does NOT know news, earnings, or policy. Treat output as scenario
bands, never as buy/sell signals.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

HORIZON = 21          # ~1 month of trading days
CONTEXT = 512         # last N daily closes fed to the model

SERIES = {
    "^NSEI": "Nifty 50",
    "^NSEBANK": "Bank Nifty",
    "^BSESN": "Sensex",
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "TCS",
    "HDFCBANK.NS": "HDFC Bank",
    "ICICIBANK.NS": "ICICI Bank",
    "INFY.NS": "Infosys",
    "ITC.NS": "ITC",
    "LT.NS": "Larsen & Toubro",
    "SBIN.NS": "State Bank of India",
    "BHARTIARTL.NS": "Bharti Airtel",
    "HINDUNILVR.NS": "Hindustan Unilever",
}


def fetch_closes(symbol, period="2y"):
    for attempt in range(3):
        try:
            df = yf.download(symbol, period=period, interval="1d",
                             progress=False, auto_adjust=True)
            closes = df["Close"].dropna().values.flatten()
            if len(closes) >= 100:
                return closes[-CONTEXT:]
        except Exception as e:  # noqa: BLE001
            print(f"  {symbol} fetch attempt {attempt+1}: {e}")
        time.sleep(5 * (attempt + 1))
    return None


def main():
    from timesfm3 import ModelConfig, TimesFM3Forecaster

    DATA.mkdir(exist_ok=True)

    # 1. fetch history
    hist, failed = {}, []
    for sym, name in SERIES.items():
        c = fetch_closes(sym)
        if c is None:
            failed.append(sym)
        else:
            hist[sym] = c
            print(f"  {name:<22} {len(c):>4} days, last={c[-1]:,.2f}")
    if not hist:
        print("FATAL: no series fetched")
        return

    # 2. load TimesFM 3.0 (CPU)
    print("loading google/timesfm-3.0-pytorch on CPU ...")
    cfg = ModelConfig(checkpoint_path="google/timesfm-3.0-pytorch",
                      per_core_batch_size=8, device="cpu")
    forecaster = TimesFM3Forecaster(cfg)

    # 3. forecast
    syms = list(hist)
    outs = list(forecaster.predict_batch(
        contexts=[np.asarray(hist[s], dtype=np.float32) for s in syms],
        horizon=HORIZON, return_quantiles=True, use_symmetric_averaging=False))

    results = []
    for sym, out in zip(syms, outs):
        med = np.asarray(out.forecast, dtype=float)     # (H,) median path
        qs = np.asarray(out.quantiles, dtype=float)     # (H, 9) q10..q90
        last = float(hist[sym][-1])
        med_end, q10_end, q90_end = float(med[-1]), float(qs[-1, 0]), float(qs[-1, -1])

        def pct(x):
            return round((x / last - 1.0) * 100, 2) if last else None

        results.append({
            "symbol": sym,
            "name": SERIES[sym],
            "as_of_last_close": round(last, 2),
            "horizon_days": HORIZON,
            "median_end": round(med_end, 2),
            "median_chg_pct": pct(med_end),
            "low10_end": round(q10_end, 2),
            "low10_chg_pct": pct(q10_end),
            "high90_end": round(q90_end, 2),
            "high90_chg_pct": pct(q90_end),
            "median_path": [round(float(v), 2) for v in med],
            "direction": ("up" if pct(med_end) and pct(med_end) > 1
                          else "down" if pct(med_end) and pct(med_end) < -1
                          else "flat"),
        })
        print(f"  {SERIES[sym]:<22} 21d median {pct(med_end):+.1f}% "
              f"(10-90% band {pct(q10_end):+.1f}% .. {pct(q90_end):+.1f}%)")

    results.sort(key=lambda r: (r["median_chg_pct"] or 0), reverse=True)
    payload = {
        "model": "google/timesfm-3.0-pytorch",
        "updated": datetime.now(timezone.utc).isoformat(),
        "horizon_days": HORIZON,
        "context_days": CONTEXT,
        "disclaimer": ("TimesFM is a statistical pattern model. It does not "
                       "know news, earnings or events. Use as scenario "
                       "bands only, not trading signals."),
        "forecasts": results,
        "failed_symbols": failed,
    }
    (DATA / "timesfm_forecasts.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=1))
    print(f"timesfm_forecasts.json written: {len(results)} series, "
          f"{len(failed)} failed")


if __name__ == "__main__":
    main()
