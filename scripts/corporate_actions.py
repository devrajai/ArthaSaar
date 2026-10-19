#!/usr/bin/env python3
"""
corporate_actions.py - fetch NSE corporate actions and back-adjust prices.

WHY THIS MATTERS
----------------
The candle archive is built from the raw bhavcopy, which is NOT adjusted. When a stock
splits 1:10 or pays a bonus, the raw price drops overnight - so a -90% "return" shows
up that never happened. Every indicator, feature and forecast computed on unadjusted
prices is reading a fiction. This script pulls the corporate actions and back-adjusts
the history so returns are real.

Back-adjustment multiplies prices BEFORE an ex-date by the action's factor, leaving the
most recent price untouched (the standard convention).

Usage
-----
  python scripts/corporate_actions.py --fetch                 # NSE -> data/corporate_actions/actions.csv
  python scripts/corporate_actions.py --adjust                # adjust the candle archive
  python scripts/corporate_actions.py --fetch --adjust        # both
  python scripts/corporate_actions.py --adjust --in data/candles/cm_daily.parquet \\
                                       --out data/candles/cm_daily_adj.parquet
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "*/*",
}
CA_URL = "https://www.nseindia.com/api/corporates-corporateActions?index=equities"


# ------------------------------------------------------------------ fetch
def fetch_actions() -> pd.DataFrame:
    import requests
    s = requests.Session()
    s.headers.update(UA)
    # NSE's API needs a session cookie - warm it up on the public pages first
    for warm in ("https://www.nseindia.com/",
                 "https://www.nseindia.com/companies-listing/corporate-filings-actions"):
        try:
            s.get(warm, timeout=25)
        except Exception:
            pass
    r = s.get(CA_URL, timeout=30)
    r.raise_for_status()
    rows = r.json()
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.rename(columns={"symbol": "symbol", "subject": "subject", "exDate": "ex_date",
                            "recDate": "rec_date", "isin": "isin", "series": "series",
                            "comp": "company", "faceVal": "face_value"})
    keep = [c for c in ["symbol", "company", "series", "isin", "subject",
                        "ex_date", "rec_date", "face_value"] if c in df.columns]
    df = df[keep].copy()
    df["ex_date"] = pd.to_datetime(df["ex_date"], format="%d-%b-%Y", errors="coerce")
    df = df.dropna(subset=["ex_date"])
    df["type"], df["factor"] = zip(*df["subject"].map(classify)) if len(df) else ((), ())
    return df.sort_values(["symbol", "ex_date"]).reset_index(drop=True)


# ------------------------------------------------------------------ parsing
def _num(s: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)", s.replace(",", ""))
    return float(m.group(1)) if m else None


def classify(subject: str) -> tuple[str, float | None]:
    """(type, factor) where factor = price_after / price_before. None = no price effect."""
    s = (subject or "").lower()
    if "split" in s:
        # 'Face Value Split From Rs 10 To Rs 2'  -> 2/10
        frm = re.search(r"from\s*(?:rs\.?|re\.?)?\s*([\d.]+)", s)
        to = re.search(r"to\s*(?:rs\.?|re\.?)?\s*([\d.]+)", s)
        if frm and to:
            a, b = float(frm.group(1)), float(to.group(1))
            if a > 0:
                return "split", round(b / a, 6)
        return "split", None
    if "bonus" in s:
        # 'Bonus 1:1' -> price halves -> 0.5 ; 'Bonus 1:2' -> 0.6667
        m = re.search(r"(\d+)\s*:\s*(\d+)", s)
        if m:
            new, held = int(m.group(1)), int(m.group(2))
            if held + new > 0:
                return "bonus", round(held / (held + new), 6)
        return "bonus", None
    if "dividend" in s:
        return "dividend", None      # dividends need the amount, not a share ratio
    if "rights" in s:
        return "rights", None
    return "other", None


# ------------------------------------------------------------------ adjust
def adjust(candles: pd.DataFrame, actions: pd.DataFrame, sortcol: str = "date") -> pd.DataFrame:
    """Back-adjust OHLC for splits/bonuses. Volume is inverse-scaled."""
    df = candles.copy()
    if "date" not in df.columns and "ts" in df.columns:
        df["date"] = pd.to_datetime(df["ts"], unit="s", utc=True).dt.strftime("%Y-%m-%d")
    df["_d"] = pd.to_datetime(df["date"], errors="coerce")

    acts = actions[actions["factor"].notna()].copy()
    if acts.empty:
        df.drop(columns=["_d"], inplace=True)
        df["adj_factor"] = 1.0
        return df

    out = []
    for sym, g in df.groupby("symbol", sort=False):
        a = acts[acts["symbol"] == sym].sort_values("ex_date")
        if a.empty:
            g = g.copy(); g["adj_factor"] = 1.0
            out.append(g); continue
        g = g.copy()
        fac = pd.Series(1.0, index=g.index)
        for _, act in a.iterrows():
            # everything strictly BEFORE the ex-date gets multiplied by the factor
            mask = g["_d"] < act["ex_date"]
            fac.loc[mask] = fac.loc[mask] * float(act["factor"])
        g["adj_factor"] = fac
        for c in ("open", "high", "low", "close"):
            if c in g.columns:
                g[c] = pd.to_numeric(g[c], errors="coerce") * fac
        if "volume" in g.columns:
            g["volume"] = (pd.to_numeric(g["volume"], errors="coerce") / fac).round()
        out.append(g)

    res = pd.concat(out, ignore_index=True).drop(columns=["_d"])
    return res.sort_values(["symbol", sortcol]).reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="NSE corporate actions + price adjustment.")
    ap.add_argument("--fetch", action="store_true")
    ap.add_argument("--adjust", action="store_true")
    ap.add_argument("--in", dest="infile", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--actions", default="data/corporate_actions/actions.csv")
    args = ap.parse_args()
    if not args.fetch and not args.adjust:
        ap.error("give --fetch and/or --adjust")

    apath = Path(args.actions)
    if args.fetch:
        df = fetch_actions()
        apath.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(apath, index=False)
        eff = int(df["factor"].notna().sum()) if not df.empty else 0
        print(f"Wrote {apath}  |  {len(df)} actions, {eff} with a price factor")
        if not df.empty:
            print(df["type"].value_counts().to_string())

    if args.adjust:
        if not apath.exists():
            raise SystemExit(f"no actions at {apath} - run --fetch first")
        actions = pd.read_csv(apath, parse_dates=["ex_date"])
        src = args.infile
        if not src:
            for cand in ("data/candles/daily.parquet", "data/candles/cm_daily.parquet"):
                if Path(cand).exists():
                    src = cand
                    break
        if not src or not Path(src).exists():
            raise SystemExit("no candle archive to adjust")
        candles = pd.read_parquet(src)
        adjusted = adjust(candles, actions)
        dest = Path(args.out or (str(Path(src).with_suffix("")) + "_adj.parquet"))
        dest.parent.mkdir(parents=True, exist_ok=True)
        adjusted.to_parquet(dest, index=False)
        touched = int((adjusted["adj_factor"] != 1.0).sum())
        print(f"Wrote {dest}  |  {len(adjusted):,} rows, {touched:,} back-adjusted")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
