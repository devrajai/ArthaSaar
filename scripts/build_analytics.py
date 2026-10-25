#!/usr/bin/env python3
"""
build_analytics.py - regenerate the derivable Telegram analytics from the hub's own data.

The Telegram jobs read 16 derived JSONs that used to come from the ArthaSaar repo.
That repo is gone, so those files have to come from somewhere. This script produces
the ones the hub can honestly derive itself:

  futures.json   from the NSE F&O bhavcopy  -> stock-futures OI, OI change, and Nifty PCR / max-pain
  breadth.json   from a candle archive      -> % of symbols trading above their 200-day EMA

The rest (smart-brain, mood, gti, oi-gti, radar, events, global, fii-dii, mf-top,
preopen, brain-screener, index-changes) are model/news/flow outputs that need the
old pipeline or another source. timesfm_forecasts.json is produced by
timesfm_forecast.py. See README for the full status table.

Usage
-----
  python scripts/build_analytics.py
  python scripts/build_analytics.py --out data
"""

from __future__ import annotations

import argparse
import glob
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# Cap Arrow's thread pool. Some containers (CI, sandboxes) have a low thread limit and
# pyarrow's default pool can fail with "Failed to launch worker thread".
try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

INDEX_FOR_PCR = "NIFTY"

# UDiFF F&O instrument codes: STF stock futures, IDF index futures,
# STO stock options, IDO index options. Older sources used FUTSTK/OPTIDX names.
FUT_STOCK = {"STF", "FUTSTK"}
FUT_INDEX = {"IDF", "FUTIDX"}
OPT_INDEX = {"IDO", "OPTIDX"}


def _latest_fo(csv_dir: Path, parquet_dir: Path) -> pd.DataFrame | None:
    """Prefer the PARQUET. The csv was preferred before, but data/csv/fo/ is now gitignored -
    it is the intermediate step, roughly 3.5 MB per day and about 900 MB a year, while the
    parquet holds the same rows at a fraction of the size. The csv branch stays as a fallback
    for a local run that has not produced parquet yet."""
    pq = sorted(glob.glob(str(parquet_dir / "fo_*.parquet")))
    if pq:
        return pd.read_parquet(pq[-1])
    csvs = sorted(glob.glob(str(csv_dir / "fo_*.csv")))
    if csvs:
        return pd.read_csv(csvs[-1], dtype=str)
    return None


def build_futures(fo: pd.DataFrame) -> dict:
    for c in ["instrm_type", "strike", "opt_type", "oi", "oi_change", "close", "prevclose", "symbol"]:
        if c not in fo.columns:
            fo[c] = pd.NA
    for c in ["strike", "oi", "oi_change", "close", "prevclose"]:
        fo[c] = pd.to_numeric(fo[c], errors="coerce")
    fo["instrm_type"] = fo["instrm_type"].astype(str).str.upper()
    fo["symbol"] = fo["symbol"].astype(str).str.upper()

    stocks = []
    fut = fo[fo["instrm_type"].isin(FUT_STOCK)]
    for sym, g in fut.groupby("symbol"):
        oi = g["oi"].sum()
        oic = g["oi_change"].sum()
        c, pc = g["close"].iloc[-1], g["prevclose"].iloc[-1]
        chg = round((c / pc - 1) * 100, 2) if pc and pd.notna(pc) and pd.notna(c) else None
        # ---- long / short buildup ----------------------------------------------------
        # This costs nothing extra: open interest and price are already stored. The classic
        # four-way read of OI against price:
        #   price up   + OI up   -> long buildup     (new longs, conviction)
        #   price down + OI up   -> short buildup    (new shorts, conviction)
        #   price up   + OI down -> short covering   (shorts closing, can fade)
        #   price down + OI down -> long unwinding   (longs bailing out)
        # Thresholds keep noise out: a 0.05% price tick with 0.1% OI drift is not a signal.
        oi_prev = (oi - oic) if (pd.notna(oi) and pd.notna(oic)) else None
        oi_pct = None
        if oi_prev and oi_prev > 0:
            oi_pct = round(float(oic) / float(oi_prev) * 100, 2)
        buildup = None
        if chg is not None and oi_pct is not None and abs(chg) >= 0.5 and abs(oi_pct) >= 1.0:
            if chg > 0 and oi_pct > 0:
                buildup = "Long buildup"
            elif chg < 0 and oi_pct > 0:
                buildup = "Short buildup"
            elif chg > 0 and oi_pct < 0:
                buildup = "Short covering"
            else:
                buildup = "Long unwinding"
        stocks.append({"symbol": sym, "oi": None if pd.isna(oi) else int(oi),
                       "oi_chg": None if pd.isna(oic) else int(oic), "change_pct": chg,
                       "oi_pct": oi_pct, "buildup": buildup})
    stocks.sort(key=lambda s: -(s["oi"] or 0))

    index_futures = []
    for sym, g in fo[fo["instrm_type"].isin(FUT_INDEX)].groupby("symbol"):
        oi = g["oi"].sum()
        index_futures.append({"symbol": sym, "oi": None if pd.isna(oi) else int(oi)})

    pcr = {}
    opt = fo[fo["instrm_type"].isin(OPT_INDEX) & fo["symbol"].eq(INDEX_FOR_PCR)]
    if not opt.empty:
        ce = opt[opt["opt_type"].astype(str).str.upper().eq("CE")]
        pe = opt[opt["opt_type"].astype(str).str.upper().eq("PE")]
        ce_oi, pe_oi = ce["oi"].sum(), pe["oi"].sum()
        if ce_oi and ce_oi > 0:
            pcr["nifty_pcr_oi"] = round(float(pe_oi) / float(ce_oi), 2)
        # max pain ~ strike with the largest total option OI
        tot = pd.concat([ce, pe]).groupby("strike")["oi"].sum()
        if not tot.empty:
            pcr["nifty_max_pain"] = float(tot.idxmax())

    return {"date": str(fo["date"].iloc[0]) if "date" in fo.columns and len(fo) else None,
            "source": "nse-bhavcopy-fo", "stocks": stocks,
            "index_futures": index_futures, "pcr": pcr}


def build_breadth(candle_candidates: list[Path]) -> dict | None:
    path = next((p for p in candle_candidates if p.exists()), None)
    if path is None:
        return None
    df = pd.read_parquet(path)
    if not {"symbol", "date", "close"}.issubset(df.columns):
        return None
    above = total = 0
    as_of = df["date"].max()
    for _, g in df.groupby("symbol", sort=False):
        g = g.sort_values("date")
        if len(g) < 200:
            continue
        ema = g["close"].ewm(span=200, adjust=False).mean().iloc[-1]
        last = g["close"].iloc[-1]
        total += 1
        if pd.notna(ema) and last > ema:
            above += 1
    if not total:
        return None
    return {"above_ema200_pct": round(above / total * 100, 1),
            "as_of": str(as_of), "symbols": total, "source": path.name}


def main() -> int:
    ap = argparse.ArgumentParser(description="Regenerate derivable Telegram analytics JSONs.")
    ap.add_argument("--out", default="data")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    written = []

    fo = _latest_fo(Path("data/csv/fo"), Path("data/parquet/fo"))
    if fo is not None and not fo.empty:
        fut = build_futures(fo)
        (out / "futures.json").write_text(json.dumps(fut, indent=2))
        written.append(f"futures.json  ({len(fut['stocks'])} stock futures, pcr={fut['pcr']})")
    else:
        print("no F&O bhavcopy found - skipping futures.json")

    br = build_breadth([Path("data/candles/daily.parquet"), Path("data/candles/cm_daily.parquet")])
    if br:
        (out / "breadth.json").write_text(json.dumps(br, indent=2))
        written.append(f"breadth.json  ({br['above_ema200_pct']}% above EMA200 of {br['symbols']} symbols)")
    else:
        print("no candle archive with >=200 days - skipping breadth.json")

    print(f"\nanalytics @ {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
    for w in written:
        print("  wrote", w)
    if not written:
        print("  nothing written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
