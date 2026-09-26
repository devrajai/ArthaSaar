#!/usr/bin/env python3
"""history_collect.py - ALL NSE stocks + indices ka 1-saal daily candle archive.

- Symbols: NSE EQUITY_L.csv (archives.nseindia.com, ~2000 EQ stocks) + hardcoded indices
- Data: yfinance multi-ticker download (interval=1d, period=5y), 100-symbol batches
- PLUS intraday self-archive (core symbols): 5m/15m (60d window) + 1h (730d) roz
  fetch karke purane intraday.json me MERGE karta hai — Yahoo ka 60-din limit
  apne data se todte hain, roz save karke history khud badhati hai
- Output:
    data-history/daily-00.json ... daily-NN.json  -> GitHub Release "candles" pe (git bloat zero)
    data-history/intraday.json                     -> core symbols ka rolling intraday archive
    data/symbols.json                               -> repo me commit (site search + chunk index)
- Site: https://github.com/devrajai/ArthaSaar/releases/download/candles/daily-00.json (CORS ok)

Run:  python3 scripts/history_collect.py
"""
import datetime as dt
import io
import json
import time
import warnings
from pathlib import Path

import requests

warnings.filterwarnings("ignore")
import yfinance as yf  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUTDIR = ROOT / "data-history"
SYMFILE = ROOT / "data" / "symbols.json"

INDICES = {
    "NIFTY": "^NSEI", "BANKNIFTY": "^NSEBANK", "FINNIFTY": "^CNXFIN",
    "SENSEX": "^BSESN", "NIFTYIT": "^CNXIT", "MIDCPNIFTY": "^NSEMDCP50",
    "INDIAVIX": "^INDIAVIX", "NIFTYAUTO": "^CNXAUTO", "NIFTYPHARMA": "^CNXPHARMA",
    "NIFTYFMCG": "^CNXFMCG", "NIFTYMETAL": "^CNXMETAL", "NIFTYENERGY": "^CNXENERGY",
    "NIFTYPSUBANK": "^CNXPSUBANK", "NIFTYINFRA": "^CNXINFRA", "NIFTYREALTY": "^CNXREALTY",
}
EQUITY_L = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
CHUNK = 100
BATCH = 100
# fallback agar NSE list na mile (kam se kam kuch to ho)
FALLBACK = ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "SBIN",
            "BHARTIARTL", "ITC", "LT", "AXISBANK", "KOTAKBANK", "TATAMOTORS"]


def nse_list():
    """[(SYMBOL, NAME)] - sab EQ-series listed stocks."""
    try:
        r = requests.get(EQUITY_L, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
        r.raise_for_status()
        import pandas as pd
        df = pd.read_csv(io.BytesIO(r.content))
        df.columns = [c.strip() for c in df.columns]
        rows = []
        for _, x in df.iterrows():
            try:
                sym = str(x["SYMBOL"]).strip()
                name = str(x["NAME OF COMPANY"]).strip()
                series = str(x.get("SERIES", "EQ")).strip().upper()
            except Exception:
                continue
            if not sym or series != "EQ":
                continue
            rows.append((sym, name))
        print("NSE EQUITY_L:", len(rows), "EQ stocks")
        return rows
    except Exception as e:  # noqa: BLE001
        print("EQUITY_L fetch fail:", e, "-> fallback", len(FALLBACK))
        return [(s, s) for s in FALLBACK]


def to_bars(sub):
    sub = sub.dropna(subset=["Open", "High", "Low", "Close"])
    t, o, h, l, c, v = [], [], [], [], [], []
    for ts, row in sub.iterrows():
        t.append(int(ts.timestamp()))
        o.append(round(float(row["Open"]), 2))
        h.append(round(float(row["High"]), 2))
        l.append(round(float(row["Low"]), 2))
        c.append(round(float(row["Close"]), 2))
        vol = row.get("Volume")
        v.append(int(vol) if vol == vol and vol else 0)
    if not t:
        return None
    return {"t": t, "o": o, "h": h, "l": l, "c": c, "v": v}


def main():
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=5, minutes=30))).strftime("%Y-%m-%dT%H:%M")

    universe = []  # (display, ysym, name)
    for disp, ys in INDICES.items():
        universe.append((disp, ys, disp + " index"))
    for sym, name in nse_list():
        if sym in INDICES:
            continue
        universe.append((sym, sym + ".NS", name))
    print("universe:", len(universe))

    got = {}  # display -> bars
    names = {}
    i = 0
    while i < len(universe):
        batch = universe[i:i + BATCH]
        tickers = [ys for _, ys, _ in batch]
        try:
            df = yf.download(tickers, interval="1d", period="5y",
                             progress=False, auto_adjust=False, group_by="ticker",
                             threads=True, timeout=60)
        except Exception as e:  # noqa: BLE001
            print("batch fail @", i, e, "- retry once")
            time.sleep(5)
            try:
                df = yf.download(tickers, interval="1d", period="5y",
                                 progress=False, auto_adjust=False, group_by="ticker",
                                 threads=True, timeout=60)
            except Exception:
                df = None
        if df is not None and not df.empty:
            single = len(tickers) == 1
            for disp, ys, name in batch:
                try:
                    sub = df[ys] if not single else df
                except KeyError:
                    continue
                if sub is None:
                    continue
                try:
                    bars = to_bars(sub)
                except Exception:
                    bars = None
                if bars and len(bars["t"]) >= 30:
                    got[disp] = bars
                    names[disp] = name
        print(f"  {min(i + BATCH, len(universe))}/{len(universe)} -> {len(got)} ok", flush=True)
        i += BATCH
        time.sleep(1)

    if not got:
        print("kuch nahi mila - abort")
        return

    # chunk layout: indices chunk 0 me, phir alphabetical stocks
    order = [u[0] for u in universe if u[0] in got]
    chunks = []
    symlist = []
    for j, disp in enumerate(order):
        cid = j // CHUNK
        while len(chunks) <= cid:
            chunks.append({})
        chunks[cid][disp] = got[disp]
        symlist.append({"s": disp, "n": names.get(disp, disp), "c": cid})

    OUTDIR.mkdir(parents=True, exist_ok=True)
    for k, ch in enumerate(chunks):
        p = OUTDIR / f"daily-{k:02d}.json"
        p.write_text(json.dumps({"syms": ch}, separators=(",", ":")), encoding="utf-8")
    symout = {"updated": now, "count": len(symlist), "syms": symlist}
    SYMFILE.parent.mkdir(parents=True, exist_ok=True)
    SYMFILE.write_text(json.dumps(symout, separators=(",", ":")), encoding="utf-8")

    print("symbols:", len(symlist), "| chunks:", len(chunks))
    print("written:", OUTDIR, " + ", SYMFILE)


CORE = dict(INDICES)
CORE.update({s: s + ".NS" for s in ["RELIANCE", "HDFCBANK", "ICICIBANK", "INFY",
                                    "TCS", "SBIN", "TATASTEEL", "ITC"]})
INTRADAY_PLAN = {"5m": ("60d", 16000), "15m": ("60d", 16000), "1h": ("730d", 6000)}


def intraday():
    """core symbols ka rolling intraday archive — purana merge, naya append."""
    path = OUTDIR / "intraday.json"
    old = {}
    try:
        old = json.loads(path.read_text(encoding="utf-8"))
        print("old intraday:", {k: {iv: len(b["t"]) for iv, b in v.items() if iv != "y"}
                                for k, v in list(old.items())[:3]})
    except Exception:
        old = {}
    out = {k: v for k, v in old.items()}
    for iv, (period, cap) in INTRADAY_PLAN.items():
        tickers = list(CORE.values())
        try:
            df = yf.download(tickers, interval=iv, period=period,
                             progress=False, auto_adjust=False, group_by="ticker",
                             threads=True, timeout=60)
        except Exception as e:  # noqa: BLE001
            print("intraday", iv, "fail:", e)
            continue
        if df is None or df.empty:
            continue
        for disp, ys in CORE.items():
            try:
                sub = df[ys]
            except KeyError:
                continue
            if sub is None or sub.empty:
                continue
            bars = to_bars(sub)
            if not bars or not bars["t"]:
                continue
            e = out.setdefault(disp, {"y": ys})
            prev = e.get(iv)
            merged = {t: i for i, t in enumerate(prev["t"])} if prev else {}
            for i, t in enumerate(bars["t"]):
                merged[t] = i
            keys = sorted(merged.keys())[-cap:]
            e[iv] = {
                "t": keys,
                "o": [], "h": [], "l": [], "c": [], "v": [],
            }
            # rebuild arrays from new bars, fallback old
            src_new = {t: i for i, t in enumerate(bars["t"])}
            src_old = {t: i for i, t in enumerate(prev["t"])} if prev else {}
            for t in keys:
                if t in src_new:
                    i = src_new[t]
                    e[iv]["o"].append(bars["o"][i]); e[iv]["h"].append(bars["h"][i])
                    e[iv]["l"].append(bars["l"][i]); e[iv]["c"].append(bars["c"][i])
                    e[iv]["v"].append(bars["v"][i])
                else:
                    i = src_old[t]
                    e[iv]["o"].append(prev["o"][i]); e[iv]["h"].append(prev["h"][i])
                    e[iv]["l"].append(prev["l"][i]); e[iv]["c"].append(prev["c"][i])
                    e[iv]["v"].append(prev["v"][i])
            print(f"intraday {disp} {iv}: {len(keys)} bars (cap {cap})")
    if out:
        path.write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
        print("written", path, path.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
    intraday()
