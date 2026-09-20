#!/usr/bin/env python3
"""
MARKET BRAIN — TimesFM 3.0 weekly forecasts (expanded coverage).

Google Research's TimesFM 3.0 (330M params) is a zero-shot time-series
foundation model. This script:

  1. Downloads ~2 years of daily closes (Yahoo Finance) for:
     - all major Indian indices + sectoral indices
     - global (S&P 500, Nasdaq, gold, crude) + USD-INR
     - crypto top 10
     - top 50 Indian stocks by market cap (from screener-fundamentals.json)
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
TOP_STOCKS = 50       # top N stocks by market cap

SERIES = {
    # -- Indian indices --
    "^NSEI": "Nifty 50",
    "^NSEBANK": "Bank Nifty",
    "^BSESN": "Sensex",
    "^CNXIT": "Nifty IT",
    "^CNXAUTO": "Nifty Auto",
    "^CNXPHARMA": "Nifty Pharma",
    "^CNXFMCG": "Nifty FMCG",
    "^CNXMETAL": "Nifty Metal",
    "^CNXENERGY": "Nifty Energy",
    "^CNXPSUBANK": "Nifty PSU Bank",
    "^CNXREALTY": "Nifty Realty",
    "^NSEMDCP50": "Nifty Midcap 50",
    "^INDIAVIX": "India VIX",
    # -- global & FX --
    "^GSPC": "S&P 500",
    "^NDX": "Nasdaq 100",
    "GC=F": "Gold (COMEX)",
    "CL=F": "Crude Oil WTI",
    "INR=X": "USD-INR",
    # -- crypto top 10 --
    "BTC-USD": "Bitcoin",
    "ETH-USD": "Ethereum",
    "BNB-USD": "BNB",
    "XRP-USD": "XRP",
    "SOL-USD": "Solana",
    "ADA-USD": "Cardano",
    "DOGE-USD": "Dogecoin",
    "TRX-USD": "TRON",
    "LINK-USD": "Chainlink",
    "AVAX-USD": "Avalanche",
    # -- anchor stocks (names for the biggest, rest come from top-50) --
    "RELIANCE.NS": "Reliance Industries",
    "TCS.NS": "TCS",
    "HDFCBANK.NS": "HDFC Bank",
    "ICICIBANK.NS": "ICICI Bank",
    "INFY.NS": "Infosys",
    "BHARTIARTL.NS": "Bharti Airtel",
    "LT.NS": "Larsen & Toubro",
    "SBIN.NS": "State Bank of India",
    "ITC.NS": "ITC",
    "HINDUNILVR.NS": "Hindustan Unilever",
}


def categorize(sym):
    if "-USD" in sym:
        return "crypto"
    if sym == "INR=X" or sym in ("^GSPC", "^NDX", "GC=F", "CL=F"):
        return "global"
    if sym.startswith("^"):
        return "index"
    return "stock"


def add_top_stocks():
    """Merge top-N stocks by market cap from screener-fundamentals.json."""
    try:
        fund = json.loads((DATA / "screener-fundamentals.json").read_text())
        stocks = fund.get("stocks", {})
        ranked = sorted(stocks.items(),
                        key=lambda kv: (kv[1].get("Market Cap") or 0),
                        reverse=True)
        added = 0
        for sym, _v in ranked:
            if added >= TOP_STOCKS:
                break
            key = sym + ".NS"
            if key not in SERIES:
                SERIES[key] = sym
                added += 1
    except Exception as e:  # noqa: BLE001
        print("top-50 stocks load failed:", e)


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
    add_top_stocks()
    print(f"series to forecast: {len(SERIES)}")

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
    print(f"fetched {len(hist)} series, {len(failed)} failed")

    # 2. load TimesFM 3.0 (CPU)
    print("loading google/timesfm-3.0-pytorch on CPU ...")
    cfg = ModelConfig(checkpoint_path="google/timesfm-3.0-pytorch",
                      per_core_batch_size=8, device="cpu")
    forecaster = TimesFM3Forecaster(cfg)

    # 3. forecast (batched)
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
            "cat": categorize(sym),
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

    results.sort(key=lambda r: (r["cat"], -(r["median_chg_pct"] or 0)))
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
