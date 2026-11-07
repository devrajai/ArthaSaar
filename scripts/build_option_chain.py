#!/usr/bin/env python3
"""
build_option_chain.py - publish the option chain with what each strike's change MEANS.

WHY THIS EXISTS
docs/oi_strikes.json only ever published open interest per strike: ce_oi, pe_oi and their
changes. Raw OI cannot tell you whether a strike was written or bought - that needs the
premium change as well, and the premium was never published. The F&O bhavcopy has carried
close and previous close all along, so the missing piece was one join, not one data source.

WHAT IT PUBLISHES
  docs/option_chain.json
    indices / stocks: nearest expiry, spot, lot size, and per strike both legs with
      ltp, premium change, oi, oi change, volume, and an ACTION label
    unusual: contracts where volume exceeds open interest - fresh positions, not old ones
    delivery: for stock options, the cash needed if an in-the-money contract is left to
      expiry, which is what physically-settled stock F&O actually costs

THE ACTION LABEL, AND WHY IT IS THE HONEST ONE
  oi up   + premium down = writing   (someone sold it and is being paid to wait)
  oi up   + premium up   = buying    (new long positions, paying up)
  oi down + premium up   = short covering (sellers buying back)
  oi down + premium down = long unwinding (buyers giving up)
That is the standard reading of a chain, and it is still an inference from two numbers, not
a record of who did what. The card says so.

Input:  data/csv/fo/*.csv   (canonical schema from scripts/nse_source.py)
Output: docs/option_chain.json

Usage:
  python scripts/build_option_chain.py
  python scripts/build_option_chain.py --file data/csv/fo/fo_2026-11-06.csv --top-stocks 40
"""

from __future__ import annotations

import argparse
import glob
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

OUT = "docs/option_chain.json"
INDEX_NAMES = ("NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "NIFTYNXT50")
MAX_STRIKES = 25
BAND = 0.10              # only strikes within +/-10% of spot
MIN_VOL_UNUSUAL = 500    # contracts, so a single lot does not look unusual


def latest_file(pattern: str) -> str | None:
    files = sorted(glob.glob(pattern))
    return files[-1] if files else None


def load(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, low_memory=False)
    need = {"symbol", "expiry", "strike", "opt_type", "close", "oi"}
    if not need.issubset(df.columns):
        raise SystemExit(f"{path} is missing {sorted(need - set(df.columns))}")
    for c in ("strike", "close", "prevclose", "oi", "oi_change", "volume", "lot", "underlying"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        else:
            df[c] = np.nan
    df = df[df["opt_type"].astype(str).str.upper().isin(["CE", "PE"])]
    df = df[df["expiry"].notna() & df["strike"].notna()]
    return df


def action(oi_chg: float, prem_chg: float, prem: float, oi: float) -> str:
    """What the change in this leg most likely was."""
    if not np.isfinite(oi_chg) or not np.isfinite(prem_chg):
        return "flat"
    oi_base = max(abs(oi - oi_chg), 1.0)
    oi_pct = oi_chg / oi_base
    prem_pct = prem_chg / prem if prem else 0.0
    # Anything inside a rounding error of both numbers is noise, not a signal.
    if abs(oi_pct) < 0.01 or abs(prem_pct) < 0.02:
        return "flat"
    if oi_chg > 0:
        return "writing" if prem_chg < 0 else "buying"
    return "short covering" if prem_chg > 0 else "long unwinding"


def leg(r) -> dict:
    prem = float(r["close"]) if np.isfinite(r["close"]) else None
    prev = float(r["prevclose"]) if np.isfinite(r["prevclose"]) else None
    chg = (prem - prev) if (prem is not None and prev is not None) else None
    return {
        "ltp": round(prem, 2) if prem is not None else None,
        "chg": round(chg, 2) if chg is not None else None,
        "oi": int(r["oi"]) if np.isfinite(r["oi"]) else 0,
        "oi_chg": int(r["oi_change"]) if np.isfinite(r["oi_change"]) else 0,
        "vol": int(r["volume"]) if np.isfinite(r["volume"]) else 0,
        "action": action(r["oi_change"], chg, prem, r["oi"]) if chg is not None else "flat",
    }


def chain_for(g: pd.DataFrame, expiry, spot: float, lot: float) -> dict:
    """One underlying, one expiry, strikes near the money."""
    rows = []
    for strike, sg in g.groupby("strike"):
        if spot and np.isfinite(spot) and abs(strike / spot - 1) > BAND:
            continue
        ce = sg[sg["opt_type"].astype(str).str.upper() == "CE"]
        pe = sg[sg["opt_type"].astype(str).str.upper() == "PE"]
        rows.append({
            "strike": float(strike),
            "ce": leg(ce.iloc[0]) if len(ce) else None,
            "pe": leg(pe.iloc[0]) if len(pe) else None,
        })
    rows.sort(key=lambda x: x["strike"])
    if len(rows) > MAX_STRIKES:
        if spot and np.isfinite(spot):
            rows.sort(key=lambda x: abs(x["strike"] - spot))
            rows = sorted(rows[:MAX_STRIKES], key=lambda x: x["strike"])
        else:
            rows = rows[:MAX_STRIKES]
    ce_oi = sum((r["ce"] or {}).get("oi", 0) for r in rows)
    pe_oi = sum((r["pe"] or {}).get("oi", 0) for r in rows)
    return {
        "expiry": str(expiry)[:10],
        "spot": round(float(spot), 2) if spot and np.isfinite(spot) else None,
        "lot": int(lot) if lot and np.isfinite(lot) else None,
        "pcr": round(pe_oi / ce_oi, 2) if ce_oi else None,
        "strikes": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish the option chain with OI action labels.")
    ap.add_argument("--file", default=None, help="a canonical F&O csv; default = latest on disk")
    ap.add_argument("--top-stocks", type=int, default=30)
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    path = args.file or latest_file("data/csv/fo/*.csv")
    if not path or not Path(path).exists():
        print("no F&O csv on disk - nothing to publish")
        return 0

    df = load(path)
    if df.empty:
        print("no option rows in that file")
        return 0

    # nearest expiry per symbol, so the file describes the chain people are trading
    df["expiry"] = df["expiry"].astype(str)
    nearest = df.groupby("symbol")["expiry"].min().to_dict()
    df = df[df.apply(lambda r: r["expiry"] == nearest.get(r["symbol"]), axis=1)]

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": str(df["date"].iloc[0])[:10] if "date" in df.columns else None,
        "source": Path(path).name,
        "indices": {},
        "stocks": {},
        "unusual": [],
        "note": ("Open interest alone cannot say whether a strike was written or bought. "
                 "The label here combines the change in open interest with the change in "
                 "premium, which is the standard reading of a chain - an inference from two "
                 "numbers, not a record of who traded."),
    }

    # ---- indices ----
    for name in INDEX_NAMES:
        g = df[df["symbol"].astype(str).str.upper() == name]
        if g.empty:
            continue
        exp = nearest.get(name) or g["expiry"].min()
        g = g[g["expiry"] == exp]
        spot = float(g["underlying"].dropna().iloc[0]) if g["underlying"].notna().any() else None
        lot = float(g["lot"].dropna().iloc[0]) if g["lot"].notna().any() else None
        out["indices"][name] = chain_for(g, exp, spot, lot)

    # ---- stocks, by option volume ----
    vol = df.groupby("symbol")["volume"].sum().sort_values(ascending=False)
    picks = [s for s in vol.index if str(s).upper() not in INDEX_NAMES][:args.top_stocks]
    for name in picks:
        g = df[df["symbol"] == name]
        exp = nearest.get(name) or g["expiry"].min()
        g = g[g["expiry"] == exp]
        spot = float(g["underlying"].dropna().iloc[0]) if g["underlying"].notna().any() else None
        lot = float(g["lot"].dropna().iloc[0]) if g["lot"].notna().any() else None
        ch = chain_for(g, exp, spot, lot)
        # physically settled: an ITM contract left to expiry means taking delivery
        if ch["lot"] and ch["spot"]:
            itm = []
            for r in ch["strikes"]:
                if r["ce"] and ch["spot"] > r["strike"]:
                    itm.append({"type": "CE", "strike": r["strike"],
                                "cash": round(r["strike"] * ch["lot"])})
                if r["pe"] and ch["spot"] < r["strike"]:
                    itm.append({"type": "PE", "strike": r["strike"],
                                "cash": round(r["strike"] * ch["lot"])})
            ch["delivery_cash"] = min(itm, key=lambda x: x["cash"]) if itm else None
        out["stocks"][name] = ch

    # ---- unusual: more volume than open interest means fresh positions ----
    un = df[(df["volume"] >= MIN_VOL_UNUSUAL) & (df["volume"] > df["oi"])].copy()
    if len(un):
        un["ratio"] = un["volume"] / un["oi"].replace(0, np.nan)
        un = un.sort_values("volume", ascending=False).head(40)
        for _, r in un.iterrows():
            out["unusual"].append({
                "symbol": str(r["symbol"]), "expiry": str(r["expiry"])[:10],
                "strike": float(r["strike"]), "type": str(r["opt_type"]).upper(),
                "ltp": round(float(r["close"]), 2) if np.isfinite(r["close"]) else None,
                "vol": int(r["volume"]), "oi": int(r["oi"]),
                "ratio": round(float(r["ratio"]), 2) if np.isfinite(r["ratio"]) else None,
                "action": leg(r)["action"],
            })

    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, separators=(",", ":")))
    print(f"Wrote {dest} ({dest.stat().st_size / 1e3:.0f} KB) | "
          f"{len(out['indices'])} indices, {len(out['stocks'])} stocks, "
          f"{len(out['unusual'])} unusual")
    for name, ch in list(out["indices"].items())[:2]:
        labs = {}
        for r in ch["strikes"]:
            for side in ("ce", "pe"):
                if r[side]:
                    labs[r[side]["action"]] = labs.get(r[side]["action"], 0) + 1
        print(f"  {name}: spot {ch['spot']} lot {ch['lot']} pcr {ch['pcr']} "
              f"strikes {len(ch['strikes'])} labels {labs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
