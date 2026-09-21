#!/usr/bin/env python3
"""MARKET BRAIN — TimesFM 3.0 daily forecasts (multi-horizon).

Google Research's TimesFM 3.0 (330M params) zero-shot forecaster.

Features in this version (Dev's TimesFM 3.0 wishlist):
  1. multi-horizon: 7d / 14d / 21d / 30d / 3m from one 63-step forecast
  2. confidence % — share of the model's 9 quantile bands that agree
     with the median direction (rough conviction, not a probability)
  3. all major + sectoral Indian indices, global & FX, crypto top 10,
     top-50 stocks, India VIX
  4. sector rotation ranking — sectors ranked by 30-day median forecast
  5. expected big movers — widest 21-day bands (volatility ranking)
  6. accuracy tracker — past forecasts vs what actually happened
     (data/timesfm_history.json accumulates one entry per series per day)
  7. batched yfinance downloads + retry pass (fixes sectoral rate-limits)

Honest limits: TimesFM extrapolates statistical patterns in price. It does
NOT know news, earnings or policy. The free checkpoint is univariate —
price+VIX+volume cannot be fed together. Treat output as scenario bands,
never as buy/sell signals. Non-commercial personal use.

Output: data/timesfm_forecasts.json + data/timesfm_history.json
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

HORIZON = 63          # trading days ~ 3 months
CONTEXT = 512         # last N daily closes fed to the model
TOP_STOCKS = 50       # top N stocks by market cap
POINTS = [(7, "7"), (14, "14"), (21, "21"), (30, "30"), (63, "3m")]

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
    # -- anchor stocks (rest come from top-50) --
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

SECTOR_KEYS = {"^CNXIT", "^CNXAUTO", "^CNXPHARMA", "^CNXFMCG", "^CNXMETAL",
               "^CNXENERGY", "^CNXPSUBANK", "^CNXREALTY", "^NSEBANK"}


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


def fetch_one(sym, period="2y"):
    """Single-symbol fetch with retries."""
    for attempt in range(4):
        try:
            df = yf.download(sym, period=period, interval="1d",
                             progress=False, auto_adjust=True)
            sub = df["Close"].dropna()
            if len(sub) >= 100:
                return sub
        except Exception as e:  # noqa: BLE001
            print(f"  {sym} retry {attempt + 1}: {str(e)[:60]}")
        time.sleep(8 * (attempt + 1))
    return None


def fetch_all(symbols):
    """Chunked batch download + per-symbol retry pass. Returns {sym: Series}."""
    out, failed = {}, []
    syms = list(symbols)
    for i in range(0, len(syms), 15):
        chunk = syms[i:i + 15]
        try:
            df = yf.download(chunk, period="2y", interval="1d",
                             group_by="ticker", auto_adjust=True,
                             progress=False, threads=True)
            for sym in chunk:
                try:
                    sub = (df[sym]["Close"] if len(chunk) > 1 else df["Close"]).dropna()
                    if len(sub) >= 100:
                        out[sym] = sub
                        continue
                except Exception:  # noqa: BLE001
                    pass
                failed.append(sym)
        except Exception as e:  # noqa: BLE001
            print("chunk failed:", str(e)[:60])
            failed.extend(chunk)
        time.sleep(2.5)
    # retry pass (the old sectoral failures were rate-limits)
    still = []
    for sym in failed:
        sub = fetch_one(sym) or fetch_one(sym, "1y")
        if sub is not None:
            out[sym] = sub
            print("  retry OK:", sym)
        else:
            still.append(sym)
        time.sleep(1.5)
    return out, still


def horizon_block(med, qs, last, n):
    """Stats at trading-day n. qs is (H, 9) q10..q90."""
    m = float(med[n - 1])
    lo, hi = float(qs[n - 1, 0]), float(qs[n - 1, -1])
    qrow = qs[n - 1]
    n_up = int(sum(1 for q in qrow if q > last))
    n_dn = 9 - n_up
    med_up = m > last
    conf = (n_up if med_up else n_dn) / 9.0 * 100

    def pct(x):
        return round((x / last - 1.0) * 100, 2) if last else None

    return {
        "p": pct(m),                       # median % change
        "lo": pct(lo), "hi": pct(hi),      # bear / bull band %
        "conf": round(conf),               # quantile agreement 0-100
    }


def main():
    from timesfm3 import ModelConfig, TimesFM3Forecaster

    DATA.mkdir(exist_ok=True)
    add_top_stocks()
    print(f"series to forecast: {len(SERIES)}")

    # 1. fetch history (closes + dates)
    raw, failed = fetch_all(SERIES)
    if not raw:
        print("FATAL: no series fetched")
        return
    print(f"fetched {len(raw)} series, {len(failed)} failed")

    hist = {s: np.asarray(raw[s].values, dtype=np.float32)[-CONTEXT:]
            for s in raw}
    dates = {s: [d.strftime("%Y-%m-%d") for d in raw[s].index[-CONTEXT:]]
             for s in raw}

    # 2. load TimesFM 3.0 (CPU)
    print("loading google/timesfm-3.0-pytorch on CPU ...")
    cfg = ModelConfig(checkpoint_path="google/timesfm-3.0-pytorch",
                      per_core_batch_size=8, device="cpu")
    forecaster = TimesFM3Forecaster(cfg)

    # 3. forecast (batched, 63-step horizon)
    syms = list(hist)
    outs = list(forecaster.predict_batch(
        contexts=[hist[s] for s in syms],
        horizon=HORIZON, return_quantiles=True, use_symmetric_averaging=False))

    results = []
    for sym, out in zip(syms, outs):
        med = np.asarray(out.forecast, dtype=float)
        qs = np.asarray(out.quantiles, dtype=float)
        last = float(hist[sym][-1])

        # legacy fields stay 21-day so the website keeps working
        b21 = horizon_block(med, qs, last, 21)
        med_end = round(float(med[20]), 2)
        results.append({
            "symbol": sym,
            "name": SERIES[sym],
            "cat": categorize(sym),
            "as_of_last_close": round(last, 2),
            "horizon_days": 21,
            "median_end": med_end,
            "median_chg_pct": b21["p"],
            "low10_end": round(float(qs[20, 0]), 2),
            "low10_chg_pct": b21["lo"],
            "high90_end": round(float(qs[20, -1]), 2),
            "high90_chg_pct": b21["hi"],
            "median_path": [round(float(v), 2) for v in med],
            "direction": ("up" if (b21["p"] or 0) > 1
                          else "down" if (b21["p"] or 0) < -1 else "flat"),
            "confidence": b21["conf"],
            "horizons": {k: horizon_block(med, qs, last, n) for n, k in POINTS},
        })

    results.sort(key=lambda r: (r["cat"], -(r["median_chg_pct"] or 0)))

    # 4. sector rotation (ranked by 30-day median)
    rotation = sorted(
        ({"name": r["name"], "sym": r["symbol"],
          "chg30": r["horizons"]["30"]["p"], "conf": r["horizons"]["30"]["conf"]}
         for r in results if r["symbol"] in SECTOR_KEYS),
        key=lambda x: -(x["chg30"] or -999))

    # 5. expected big movers (widest 21d bands)
    movers = sorted(
        ({"name": r["name"], "sym": r["symbol"], "cat": r["cat"],
          "band": round((r["high90_chg_pct"] or 0) - (r["low10_chg_pct"] or 0), 1),
          "median": r["median_chg_pct"]}
         for r in results),
        key=lambda x: -(x["band"]))[:15]

    # 6. accuracy tracker — score old forecasts, store today's
    accuracy = update_history(results, hist, dates)

    payload = {
        "model": "google/timesfm-3.0-pytorch",
        "updated": datetime.now(timezone.utc).isoformat(),
        "horizon_days": 21,
        "max_horizon": "3 months (63 trading days)",
        "context_days": CONTEXT,
        "accuracy": accuracy,
        "rotation": rotation,
        "movers": movers,
        "disclaimer": ("TimesFM is a statistical pattern model. It does not "
                       "know news, earnings or events. Confidence = quantile "
                       "agreement, not a probability. Use as scenario bands "
                       "only, not trading signals."),
        "forecasts": results,
        "failed_symbols": failed,
    }
    (DATA / "timesfm_forecasts.json").write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    print(f"timesfm_forecasts.json written: {len(results)} series, "
          f"{len(failed)} failed, accuracy={accuracy}")


def update_history(results, hist, dates):
    """Append today's h21 forecasts, score matured ones, return stats."""
    HFILE = DATA / "timesfm_history.json"
    try:
        entries = json.loads(HFILE.read_text())
    except Exception:  # noqa: BLE001
        entries = []
    by = {(e["d"], e["s"]): e for e in entries}

    today = None
    for r in results:
        d = dates[r["symbol"]][-1]
        today = max(today or d, d)
        key = (d, r["symbol"])
        e = by.get(key)
        if e is None:
            e = {"d": d, "s": r["symbol"]}
            entries.append(e)
            by[key] = e
        e["l"] = r["as_of_last_close"]     # last close at forecast time
        e["m"] = r["median_end"]            # h21 median price forecast

    # score matured entries once
    hits = tracked = 0
    for e in entries:
        if "r" in e:
            hits += e["r"]
            tracked += 1
            continue
        s = e["s"]
        if s not in dates:
            continue
        dl = dates[s]
        try:
            idx = dl.index(e["d"])
        except ValueError:
            continue
        if idx + 21 >= len(dl):
            continue  # not matured yet
        actual = float(hist[s][idx + 21])
        pred_chg = (e["m"] / e["l"] - 1) if e["l"] else 0
        act_chg = (actual / e["l"] - 1) if e["l"] else 0
        e["r"] = 1 if (pred_chg > 0) == (act_chg > 0) else 0
        hits += e["r"]
        tracked += 1

    # prune: keep last ~300 days of entries
    from datetime import date as _date, timedelta as _td
    cutoff = (_date.today() - _td(days=300)).isoformat()
    entries = [e for e in entries if e["d"] >= cutoff]
    entries.sort(key=lambda x: x["d"])
    HFILE.write_text(json.dumps(entries, separators=(",", ":")))
    return {"tracked": tracked, "hits": hits,
            "rate": round(hits / tracked * 100, 1) if tracked else None}


if __name__ == "__main__":
    main()
