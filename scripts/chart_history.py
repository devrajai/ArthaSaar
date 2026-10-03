#!/usr/bin/env python3
"""
ARTHASAAR - per-symbol daily chart history collector.

Why: the site's Charts tab only had 15 symbols of intraday candles. This writes a
small per-symbol DAILY file (5 years by default) so any stock/index can draw a real
chart, fast, on a phone.

Output
  data/history/<SYM>.json   {"sym","rows","from","to","d":[YYYYMMDD..],"o":[],"h":[],"l":[],"c":[],"v":[]}
  data/history-index.json   {"updated","count","years","symbols":{SYM:{"rows","from","to"}}}
  
Coverage note:
  - Stock history now uses data/universe.json (full active stock universe).
  - Index history remains on the verified Yahoo mapping in INDICES; the site
    separately tracks 139 NSE index snapshots in data/indices-all.json.


Source: Yahoo Finance via yfinance (free). Runs daily after market close.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "history"
YEARS = "5y"          # repo copy = 5 years (small, fast). Full history lives in the release archive.
CHUNK = 20            # tickers per batch call
SLEEP = 2

INDICES = ["^NSEI", "^NSEBANK", "^BSESN", "^CNXIT", "^CNXPHARMA", "^CNXAUTO", "^CNXFMCG", "^CNXMETAL", "^CNXENERGY", "^CNXREALTY", "^CNXFIN"]


def load_symbols():
    """
    Prefer the full exchange universe so the chart archive does not silently
    shrink to index constituents. Fall back to constituents.json only if the
    broader universe is unavailable.
    """
    syms = []
    seen = set()

    try:
        universe = json.loads((DATA / "universe.json").read_text())
        for it in universe if isinstance(universe, list) else []:
            s = (it.get("symbol") or "").strip().upper() if isinstance(it, dict) else ""
            if s and s not in seen:
                seen.add(s)
                syms.append(s)
        if syms:
            print(f"universe.json: {len(syms)} symbols")
            return syms
    except Exception as e:  # noqa: BLE001
        print("universe.json load failed:", e)

    try:
        c = json.loads((DATA / "constituents.json").read_text())
        for lst in (c.get("lists") or {}).values():
            for it in lst:
                s = (it.get("symbol") or "").strip().upper()
                if s and s not in seen:
                    seen.add(s)
                    syms.append(s)
    except Exception as e:  # noqa: BLE001
        print("constituents load failed:", e)

    print(f"fallback chart universe: {len(syms)} symbols")
    return syms


def pack(sym, df):
    d, o, h, l, c, v = [], [], [], [], [], []
    for idx, row in df.iterrows():
        try:
            cl = float(row["Close"])
            if cl != cl:  # NaN
                continue
            d.append(int(idx.strftime("%Y%m%d")))
            o.append(round(float(row["Open"]), 2))
            h.append(round(float(row["High"]), 2))
            l.append(round(float(row["Low"]), 2))
            c.append(round(cl, 2))
            v.append(int(row["Volume"]) if row["Volume"] == row["Volume"] else 0)
        except Exception:  # noqa: BLE001
            continue
    if len(d) < 30:
        return None
    return {"sym": sym, "rows": len(d), "from": str(d[0]), "to": str(d[-1]),
            "d": d, "o": o, "h": h, "l": l, "c": c, "v": v}


def fetch(tickers):
    got = {}
    for i in range(0, len(tickers), CHUNK):
        batch = tickers[i:i + CHUNK]
        try:
            df = yf.download(batch, period=YEARS, interval="1d", group_by="ticker",
                             threads=True, progress=False, auto_adjust=False)
        except Exception as e:  # noqa: BLE001
            print("  batch fail:", e)
            df = None
        for t in batch:
            try:
                sub = df[t].dropna(how="all") if df is not None and t in df.columns.get_level_values(0) else None
                if sub is not None and len(sub):
                    got[t] = sub
            except Exception:  # noqa: BLE001
                pass
        # retry the ones that failed, one by one
        miss = [t for t in batch if t not in got]
        for t in miss:
            try:
                sub = yf.Ticker(t).history(period=YEARS, interval="1d")
                if sub is not None and len(sub):
                    got[t] = sub
            except Exception:  # noqa: BLE001
                pass
        print(f"  {min(i + CHUNK, len(tickers))}/{len(tickers)} done")
        time.sleep(SLEEP)
    return got


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    syms = load_symbols()
    tickers = [(s + ".NS", s) for s in syms] + [(ix, ix) for ix in INDICES]
    print(f"symbols: {len(tickers)}")
    dfmap = fetch([t for t, _ in tickers])
    index, n = {}, 0
    for tk, sym in tickers:
        sub = dfmap.get(tk)
        if sub is None:
            continue
        p = pack(sym, sub)
        if not p:
            continue
        (OUT / f"{sym}.json").write_text(json.dumps(p, separators=(",", ":")))
        index[sym] = {"rows": p["rows"], "from": p["from"], "to": p["to"]}
        n += 1
    (DATA / "history-index.json").write_text(json.dumps({
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": n, "years": YEARS, "source": "yfinance daily", "symbols": index,
    }, separators=(",", ":")))
    print(f"wrote {n} symbol files")


if __name__ == "__main__":
    main()
