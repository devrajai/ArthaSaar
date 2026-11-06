#!/usr/bin/env python3
"""
timesfm_forecast.py - Google TimesFM 2.5 zero-shot forecasts.

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
PKG_VERSION = "2.5"            # written into the output so a run can be traced
# Only forecast series a model can say something useful about. A stock with 130 sessions of
# history and no volume produces the kind of output that made VINNY show +1,157%.
MIN_HISTORY = 750              # ~3 years of sessions
MIN_AVG_VOLUME = 50_000        # shares a day, applied to archive stocks only
MAX_ABS_MEDIAN_PCT = 60.0      # a 21-day median beyond this is not a forecast, it is a bug
OUT = Path("data/timesfm_forecasts.json")
LOG = Path("data/forecast_log.jsonl")
LOG_KEEP = 30          # runs kept for the scorer; ~30 x 2,225 rows is a few MB

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


def log_forecasts(rows: list[dict], as_of: str, horizon_days: int) -> None:
    """Append this run to the log that timesfm_score.py reads.

    Only the four numbers needed to settle a forecast are stored. A full copy of every row
    would be tens of MB after a month of runs, and the scorer does not need names or
    confidence to answer whether the call was right.
    """
    keep: list[str] = []
    if LOG.exists():
        try:
            keep = [ln for ln in LOG.read_text().splitlines() if ln.strip()][-(LOG_KEEP - 1):]
        except Exception:
            keep = []
    entry = {
        "as_of": as_of,
        "horizon_days": horizon_days,
        "n": len(rows),
        "rows": [{"symbol": r["symbol"], "last": r["last"],
                  "median_chg_pct": r["median_chg_pct"],
                  "low10_chg_pct": r["low10_chg_pct"],
                  "high90_chg_pct": r["high90_chg_pct"]} for r in rows],
    }
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text("\n".join(keep + [json.dumps(entry, separators=(",", ":"))]) + "\n")
    print(f"  logged {len(rows)} forecasts to {LOG} ({len(keep) + 1} runs kept)")


def load_series(max_series: int, years: int) -> dict[str, pd.Series]:
    """Close series per symbol: watched stocks from the candle archive, plus indices."""
    out: dict[str, pd.Series] = {}

    # 1. local candle archive (already back-adjusted)
    # Adjusted prices first: a split makes an unadjusted series look like a 50% crash and
    # TimesFM will happily forecast the crash. The unadjusted files are the fallback, because
    # no series at all is worse than an approximate one - but say so when it happens.
    for cand in ("data/candles/daily_adj.parquet", "data/candles/cm_daily_adj.parquet",
                 "data/candles/daily.parquet", "data/candles/cm_daily.parquet"):
        p = Path(cand)
        if p.exists():
            if "adj" not in p.name:
                print(f"  [warn] {p.name} is not split-adjusted - "
                      f"corporate actions will distort these forecasts")
            try:
                df = pd.read_parquet(p)
                sortcol = "ts" if "ts" in df.columns else "date"
                df = df.sort_values(["symbol", sortcol])
                counts = df.groupby("symbol").size()
                keep = list(counts[counts >= MIN_HISTORY].index)
                # Most-traded first. With 2,225 symbols a run can hit its time budget, and
                # when it does the names people actually look at must already be done.
                vol: dict = {}
                if "volume" in df.columns:
                    try:
                        tail = df.groupby("symbol").tail(20)
                        vol = tail.groupby("symbol")["volume"].mean().to_dict()
                    except Exception:
                        vol = {}
                keep.sort(key=lambda x: -(vol.get(x) or 0))
                # drop the untradeable ones - they were the source of the absurd rows
                keep = [k for k in keep if (vol.get(k) or 0) >= MIN_AVG_VOLUME]
                keep = keep[:max_series]
                print(f"  {len(keep)} series pass the {MIN_HISTORY}-session and "
                      f"{MIN_AVG_VOLUME:,}-share floor")
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
    ap.add_argument("--all", action="store_true",
                    help="every symbol in the archive with enough history (ignores --max-series)")
    ap.add_argument("--chunk", type=int, default=250, help="series per model call")
    ap.add_argument("--budget-min", type=float, default=70.0,
                    help="stop forecasting after this many minutes so the run finishes cleanly")
    ap.add_argument("--years", type=int, default=2)
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args()

    series = load_series(10 ** 9 if args.all else args.max_series, args.years)
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

    # ---- forecast, in chunks ----
    # This used to hand every series to a single forecast() call. That is fine for 60 and
    # falls over on 2,225: the model returns points AND quantiles per series, so the result
    # arrays alone run to hundreds of MB. Chunking keeps memory flat and lets a slow runner
    # stop at a time budget instead of being killed halfway through writing the file.
    import time
    syms = list(series)
    k = args.report_days - 1
    rows = []
    chunk = max(1, args.chunk)
    t0 = time.time()
    for start in range(0, len(syms), chunk):
        if (time.time() - t0) / 60.0 > args.budget_min:
            print(f"  time budget of {args.budget_min:.0f} min reached after {len(rows)} "
                  f"series - the rest waits for the next run")
            break
        part = syms[start:start + chunk]
        # FORECAST LOG RETURNS, NOT PRICES.
        # Feeding raw prices let the model extrapolate a trend indefinitely: a stock at 0.96
        # was projected to 12, publishing a +1,157% median and a -100% floor. Log returns are
        # stationary and small, so a path cannot invent a thousand percent, and converting
        # back with exp() keeps every price positive.
        raw = [np.asarray(series[s], dtype=float)[-args.context:] for s in part]
        inputs = [np.diff(np.log(np.clip(r, 1e-9, None))) for r in raw]
        points, quantiles = model.forecast(horizon=args.horizon, inputs=inputs)
        points = np.asarray(points, dtype=float)
        quantiles = np.asarray(quantiles, dtype=float)

        dropped = 0
        for i, sym in enumerate(part):
            hist = raw[i]                      # prices, for the conversion back
            last = float(hist[-1])
            if not last or not np.isfinite(last):
                continue
            # cumulative log return at step k, converted back to a price
            rmed = np.asarray(points[i], dtype=float)
            cum_med = float(np.sum(rmed[:k + 1]))
            if not np.isfinite(cum_med):
                continue
            q = quantiles[i] if quantiles.ndim == 3 else quantiles[i][None, :]
            q = np.asarray(q, dtype=float)
            try:
                qs = q[:k + 1, :] if q.ndim == 2 else q[:k + 1]
                cum_q = np.cumsum(qs, axis=0)[-1] if q.ndim == 2 else np.cumsum(qs)
            except Exception:
                continue
            cum_q = np.asarray(cum_q, dtype=float)
            cum_q = cum_q[np.isfinite(cum_q)]
            if cum_q.size == 0:
                continue
            median_chg = (np.exp(cum_med) - 1) * 100
            low_chg = (np.exp(float(np.min(cum_q))) - 1) * 100
            high_chg = (np.exp(float(np.max(cum_q))) - 1) * 100
            # A 21-day median beyond +/-60% is a model failure, not information. Publishing
            # it would put a four-digit number on the page next to a real stock.
            if not np.isfinite(median_chg) or abs(median_chg) > MAX_ABS_MEDIAN_PCT:
                dropped += 1
                continue
            band_pct = round(high_chg - low_chg, 2)     # width of the 10-90 band, % of price
            rows.append({
                "symbol": sym,
                "name": EXTRA.get(sym, sym),
                "last": round(last, 2),
                "median_chg_pct": round(median_chg, 2),
                "low10_chg_pct": round(low_chg, 2),
                "high90_chg_pct": round(high_chg, 2),
                # band width replaces "confidence". The old score was 100 - 4*band, which
                # read as a probability and was 0 for two thirds of rows. This is what it
                # actually is: how wide the band is, as a percentage of the price.
                "band_pct": band_pct,
                # direction is only meaningful for an index, where the level is a market
                # view rather than a single company's price
                "direction": ("up" if median_chg > 0.25 else ("down" if median_chg < -0.25 else "flat"))
                             if sym in EXTRA else None,
            })
        if dropped:
            print(f"  dropped {dropped} series whose forecast exceeded "
                  f"+/-{MAX_ABS_MEDIAN_PCT:.0f}% over {args.report_days} sessions")
        print(f"  {min(start + chunk, len(syms))}/{len(syms)} forecast, {len(rows)} rows")

    # Sort by symbol, NOT by median. Sorting by median descending put the twenty-five most
    # absurd rows at the top of the published file, so the card led with VINNY +1,157%.
    rows.sort(key=lambda r: r["symbol"])
    payload = {
        "model": "TimesFM 2.5 200M (zero-shot)",
        "model_id": MODEL_ID,
        "package_version": PKG_VERSION,
        "input": "log returns (converted back with exp)",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "horizon_days": args.report_days,
        "series": len(rows),
        "forecasts": rows,
    }
    nif = next((r for r in rows if r["symbol"] == "^NSEI"), None)
    if nif:
        payload["nifty"] = nif

    log_forecasts(rows, payload["updated"][:10], args.report_days)

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
