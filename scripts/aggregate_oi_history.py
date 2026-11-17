#!/usr/bin/env python3
"""Rebuild data/oi/oi_history.parquet from the F&O bhavcopy files already on disk.

WHY THIS EXISTS
Everything downstream of open interest was frozen at 28 October while the pipeline kept
fetching fresh bhavcopy every night:

    data/parquet/fo/fo_2026-11-16.parquet   <- fetched daily, current
    data/oi/oi_history.parquet              <- read by build_oi_history.py, stuck at 28 Oct
    docs/oi_history.json                    <- rebuilt daily, so it LOOKS fresh
    docs/pcr_signal.json                    <- reports the stale date honestly

Nothing converted the first into the second, so build_oi_history.py kept faithfully reading a
file nobody was updating. The visible symptom was a put-call ratio 20 days old on the site and
in the Telegram brief. The cause was this missing step.

WHAT IT COMPUTES, per index per date
    pcr            total put OI / total call OI
    max_pain       the strike where option buyers collectively lose least - that is, where
                   the sum of (call OI x distance above strike) and (put OI x distance below
                   strike) is smallest. It is arithmetic on open interest, not a forecast.
    call_wall      strike with the largest call open interest
    put_wall       strike with the largest put open interest
    atm_strike     strike nearest the spot

It only ever APPENDS. Existing rows are never rewritten - a history that silently changes
underneath the studies reading it is worse than a short one.
"""
from __future__ import annotations

import glob
import os
import sys

import pandas as pd

SRC_GLOB = "data/parquet/fo/fo_*.parquet"
HIST = "data/oi/oi_history.parquet"

INDEXES = {"NIFTY": "NIFTY", "BANKNIFTY": "BANKNIFTY"}

COLS = ["date", "index", "spot", "spot_source", "total_ce_oi", "total_pe_oi", "pcr",
        "max_pain", "call_wall", "put_wall", "atm_strike", "strikes_listed"]


def max_pain(ce: pd.Series, pe: pd.Series) -> float | None:
    """Strike where total option-buyer payout is lowest, i.e. writers hurt least."""
    strikes = sorted(set(ce.index) | set(pe.index))
    if not strikes:
        return None
    best, best_val = None, None
    for k in strikes:
        # calls above k expire worthless to the buyer; puts below k likewise
        loss = 0.0
        for s in strikes:
            c = float(ce.get(s, 0) or 0)
            p = float(pe.get(s, 0) or 0)
            if c and s < k:
                loss += c * (k - s)
            if p and s > k:
                loss += p * (s - k)
        if best_val is None or loss < best_val:
            best, best_val = k, loss
    return float(best) if best is not None else None


def main() -> int:
    files = sorted(glob.glob(SRC_GLOB))
    if not files:
        print("no fo_*.parquet files - nothing to aggregate")
        return 0

    have = None
    known = set()
    if os.path.exists(HIST):
        have = pd.read_parquet(HIST)
        have["date"] = pd.to_datetime(have["date"]).dt.strftime("%Y-%m-%d")
        known = set(have["date"].unique())
        print("history: %d rows, through %s" % (len(have), max(known) if known else "-"))
    else:
        print("history: none yet, building from scratch")

    rows = []
    for path in files:
        try:
            df = pd.read_parquet(path)
        except Exception as e:
            print("  skip %s (%s)" % (os.path.basename(path), type(e).__name__))
            continue
        if df.empty or "symbol" not in df.columns:
            continue
        day = str(pd.to_datetime(df["date"].iloc[0]).date())
        if day in known:
            continue

        # INDEX options are IDO, not STO - STO is a stock option. Filtering on "STO" alone
        # found zero Nifty rows and the aggregator silently added nothing, which is exactly
        # the kind of empty-success this repo keeps producing. Accept both, and require a
        # CE/PE label so futures rows are excluded.
        opt = df[df["instrm_type"].astype(str).isin(["STO", "IDO"])]
        opt = opt[opt["opt_type"].astype(str).isin(["CE", "PE"])]
        made = []
        for sym, label in INDEXES.items():
            sub = opt[opt["symbol"].astype(str) == sym]
            if sub.empty:
                continue
            sub = sub[sub["strike"].notna()]
            if sub.empty:
                continue
            ce = sub[sub["opt_type"].astype(str) == "CE"].groupby("strike")["oi"].sum()
            pe = sub[sub["opt_type"].astype(str) == "PE"].groupby("strike")["oi"].sum()
            total_ce, total_pe = float(ce.sum()), float(pe.sum())
            if total_ce <= 0:
                continue                       # a PCR off zero call OI is not a number
            try:
                spot = float(sub["underlying"].dropna().iloc[0])
            except Exception:
                spot = None
            strikes = sorted(set(ce.index) | set(pe.index))
            atm = min(strikes, key=lambda s: abs(s - spot)) if (spot and strikes) else None
            rows.append({
                "date": day, "index": label, "spot": spot, "spot_source": "underlying",
                "total_ce_oi": total_ce, "total_pe_oi": total_pe,
                "pcr": round(total_pe / total_ce, 4),
                "max_pain": max_pain(ce, pe),
                "call_wall": float(ce.idxmax()) if not ce.empty else None,
                "put_wall": float(pe.idxmax()) if not pe.empty else None,
                "atm_strike": float(atm) if atm else None,
                "strikes_listed": len(strikes),
            })
            made.append("%s pcr %.3f mp %s" % (label, total_pe / total_ce, rows[-1]["max_pain"]))
        if made:
            print("  %s -> %s" % (day, "; ".join(made)))

    if not rows:
        print("nothing new to add - history is already current")
        return 0

    add = pd.DataFrame(rows)
    out = pd.concat([have, add], ignore_index=True) if have is not None else add
    for c in COLS:
        if c not in out.columns:
            out[c] = None
    out = out[COLS]
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out = out.drop_duplicates(subset=["date", "index"], keep="first").sort_values(["date", "index"])

    os.makedirs(os.path.dirname(HIST), exist_ok=True)
    out.to_parquet(HIST, index=False)
    print("\n-> %s  |  %d rows, %s through %s  (+%d new)"
          % (HIST, len(out), out["index"].nunique(), out["date"].max(), len(add)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
