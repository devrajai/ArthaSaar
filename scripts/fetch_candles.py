#!/usr/bin/env python3
"""
fetch_candles.py — ArthaSaar Chart Reading data v2 (yfinance, free, no API key).

Why yfinance: Yahoo direct API 429s hard from GH runners; yfinance does the
cookie/crumb dance + retries (same as index_history_collect.py — proven weekly).

Symbols:
  indices  : NIFTY, BANKNIFTY         -> 1m/5m/15m/1h
  F&O big  : RELIANCE, HDFCBANK, ICICIBANK, INFY, TCS,
             SBIN, TATASTEEL, ITC    -> 5m/15m/1h

Output: data/candles.json (column arrays — compact)
  { "updated": "...", "syms": { "NIFTY": { "y":"^NSEI", "pc": 23447.8,
      "5m": {"t":[],"o":[],"h":[],"l":[],"c":[],"v":[]}, ... } } }

Run:  python3 scripts/fetch_candles.py   (from repo root)
"""
import datetime as dt
import json
import os
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")
import yfinance as yf  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "candles.json"

IDX = {"NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK"}
STOCKS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY",
          "TCS", "SBIN", "TATASTEEL", "ITC"]
YMAP = dict(IDX, **{s: s + ".NS" for s in STOCKS})

# interval -> (yfinance period, symbols)
PLAN = {
    "1m":  ("1d",  list(IDX)),                       # 1m sirf indices
    "5m":  ("1d",  list(YMAP)),                     # sab
    "15m": ("5d",  list(YMAP)),
    "1h":  ("1mo", list(YMAP)),
}


def batch(tickers, interval, period):
    """yfinance multi-ticker download -> {name: bars}"""
    df = yf.download(tickers, interval=interval, period=period,
                     progress=False, auto_adjust=False, group_by="ticker",
                     threads=False, timeout=25)
    out = {}
    if df is None or df.empty:
        return out
    single = len(tickers) == 1
    for name in tickers:
        try:
            sub = df[name] if single else df[name]
        except KeyError:
            continue
        if sub is None or sub.empty:
            continue
        sub = sub.dropna(subset=["Open", "High", "Low", "Close"])
        t, o, h, l, c, v = [], [], [], [], [], []
        for ts, row in sub.iterrows():
            t.append(int(ts.timestamp()))
            o.append(round(float(row["Open"]), 2))
            h.append(round(float(row["High"]), 2))
            l.append(round(float(row["Low"]), 2))
            c.append(round(float(row["Close"]), 2))
            vol = row.get("Volume")
            v.append(int(vol) if vol == vol and vol else 0)  # NaN-safe
        out[name] = {"t": t, "o": o, "h": h, "l": l, "c": c, "v": v}
    return out


def prev_closes():
    """sab symbols ka prev close (daily 5d se)"""
    res = {}
    try:
        df = yf.download(list(YMAP.values()), interval="1d", period="5d",
                         progress=False, auto_adjust=False, group_by="ticker",
                         threads=False, timeout=25)
        if df is None or df.empty:
            return res
        for ysym in YMAP.values():
            try:
                sub = df[ysym]
                closes = sub["Close"].dropna().tolist()
                if len(closes) >= 2:
                    res[ysym] = round(float(closes[-2]), 2)
            except Exception:  # noqa: BLE001
                pass
    except Exception as e:  # noqa: BLE001
        print("prevclose batch fail:", e)
    return res


def main():
    data = {}
    try:
        data = json.loads(OUT.read_text(encoding="utf-8")).get("syms", {})
    except Exception:
        pass

    pcs = prev_closes()
    print("prev closes:", len(pcs))

    for iv, (period, names) in PLAN.items():
        tickers = [YMAP[n] for n in names]
        got = {}
        try:
            got = batch(tickers, iv, period)
        except Exception as e:  # noqa: BLE001
            print(f"batch {iv} fail: {e}")
        for ysym, bars in got.items():
            if not bars["t"]:
                continue
            # reverse map ysym -> display name
            for n, ys in YMAP.items():
                if ys == ysym:
                    e = data.setdefault(n, {"y": ys, "pc": None})
                    e[iv] = bars
                    if ys in pcs:
                        e["pc"] = pcs[ys]
                    print(f"OK  {n} {iv}: {len(bars['t'])} bars")
        if not got:
            print(f"NO DATA {iv}")

    if not data:
        print("no data fetched — file not touched")
        return

    out = {"updated": dt.datetime.now(
        dt.timezone(dt.timedelta(hours=5, minutes=30))
    ).strftime("%Y-%m-%dT%H:%M"),
        "syms": data}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print("written", OUT, os.path.getsize(OUT), "bytes")


if __name__ == "__main__":
    main()
