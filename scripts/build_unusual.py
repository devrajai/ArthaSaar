#!/usr/bin/env python3
"""Unusual activity: a big order leaves a footprint even when the price barely moves.

WHAT A "BIG ORDER PUNCH" LOOKS LIKE IN FREE DATA
A large institutional order does not have to move the price much, but it cannot hide three
things, all of which NSE publishes every evening:

  volume   contracts traded that day, against the stock's own recent average
  trades   the NUMBER of trades. A single 5,000-lot order is one trade; 5,000 one-lot
           orders are 5,000 trades. A jump in volume with a FALL in trades is one big
           participant. A jump in both is a crowd.
  oi       open interest change. A big fresh position moves OI; a closing trade does not.

This flags days where any of the three sits far outside the stock's own recent range, then
reports what the price and the index actually did.

WHAT IT CANNOT DO
There is no order-level data in the free files, so this cannot name the buyer, the broker or
the size of a single order. It reports that something unusually large happened, not who did it.

HOW THE INDEX EFFECT IS MEASURED
Nifty weights need free-float market caps, which these files do not carry. Rather than invent
weights, this measures the effect EMPIRICALLY: on the days this stock had an unusual session,
what did the Nifty actually do? That is a fact about the past, not a calculated contribution,
and it is labelled that way.

USAGE
  python scripts/build_unusual.py
  python scripts/build_unusual.py --sigma 2.5 --min-days 15
"""
import argparse, glob, json, os, sys
from datetime import datetime, timezone

OUT = "docs/unusual.json"
NIFTY_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=2y"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def nifty_closes():
    import datetime as dt
    try:
        import urllib.request
        j = json.loads(urllib.request.urlopen(
            urllib.request.Request(NIFTY_URL, headers={"User-Agent": "Mozilla/5.0"}),
            timeout=60).read())
        r = j["chart"]["result"][0]
        q = r["indicators"]["quote"][0]
        return {dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d"): c
                for t, c in zip(r["timestamp"], q["close"]) if c is not None}
    except Exception as e:
        print("  nifty fetch failed: %s" % type(e).__name__)
        return {}


def load_fo():
    """Every F&O parquet we have, as one frame."""
    import pandas as pd
    files = sorted(glob.glob("data/parquet/fo/fo_*.parquet"))
    if not files:
        return None, []
    frames = []
    for f in files:
        try:
            frames.append(pd.read_parquet(f))
        except Exception:
            continue
    if not frames:
        return None, files
    return pd.concat(frames, ignore_index=True), files


def main():
    ap = argparse.ArgumentParser(description="Unusual F&O activity.")
    ap.add_argument("--sigma", type=float, default=3.0, help="how far from normal counts")
    ap.add_argument("--min-days", type=int, default=15, help="baseline sessions needed")
    ap.add_argument("--keep", type=int, default=40)
    args = ap.parse_args()

    df, files = load_fo()
    out = {"updated": now(), "sessions": 0, "flagged": [], "note": "", "cautions": {}}

    if df is None or df.empty:
        out["note"] = "No F&O parquet found. The detector needs data/parquet/fo/."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
        print("unusual: no F&O data")
        return 0

    import pandas as pd
    # Aggregate every contract of a symbol per day. Summing across expiries is the right
    # thing here: a big participant may work across several expiries, and the footprint we
    # want is the whole symbol's activity, not one contract's.
    for c in ("volume", "oi", "oi_change", "trades", "turnover"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
        else:
            df[c] = 0.0
    if "close" in df.columns:
        df["close"] = pd.to_numeric(df["close"], errors="coerce")

    # Activity is SUMMED across every contract - a large participant may work across
    # several expiries, and the footprint we want is the symbol's whole activity.
    daily = (df.groupby(["symbol", "date"], as_index=False)
               .agg(volume=("volume", "sum"), trades=("trades", "sum"),
                    oi=("oi", "sum"), oi_change=("oi_change", "sum"),
                    turnover=("turnover", "sum")))

    # PRICE must come from one contract only. Taking the last close across all rows made the
    # series jump between a Rs 0.50 option and a Rs 3,000 future, which produced "moves" of
    # -98% and +1022%. The stock future with the most volume is the near-month contract and
    # is the honest price proxy available here.
    stf = df[df.get("instrm_type").astype(str).str.upper().isin(["STF", "FUTSTK"])] \
        if "instrm_type" in df.columns else df.iloc[0:0]
    if not stf.empty:
        idx = stf.groupby(["symbol", "date"])["volume"].idxmax()
        px = stf.loc[idx, ["symbol", "date", "close"]].rename(columns={"close": "px"})
    else:
        px = df.groupby(["symbol", "date"], as_index=False)["close"].median()
        px = px.rename(columns={"close": "px"})
        print("  [warn] no stock-futures rows; using the median contract price instead")
    daily = daily.merge(px, on=["symbol", "date"], how="left")
    daily = daily.rename(columns={"px": "close"})
    sessions = sorted(daily["date"].unique())
    out["sessions"] = len(sessions)
    print("  %d sessions, %d symbols" % (len(sessions), daily["symbol"].nunique()))

    nif = nifty_closes()
    nif_dates = sorted(nif)
    nif_ret = {nif_dates[i]: (nif[nif_dates[i]] / nif[nif_dates[i - 1]] - 1) * 100
               for i in range(1, len(nif_dates))}

    flagged = []
    thin = 0
    for sym, g in daily.groupby("symbol"):
        g = g.sort_values("date").reset_index(drop=True)
        if len(g) < args.min_days + 1:
            thin += 1
            continue
        g["ret"] = g["close"].pct_change() * 100
        # a single-session move beyond 50% is a contract roll or a bad row, not a price move
        g.loc[g["ret"].abs() > 50, "ret"] = pd.NA
        # trailing baseline, never including the day being judged
        for col, label in (("volume", "volume"), ("trades", "trades"),
                           ("oi_change", "open interest")):
            base = g[col].shift(1).rolling(args.min_days, min_periods=max(5, args.min_days // 2))
            mu, sd = base.mean(), base.std()
            z = (g[col] - mu) / sd.replace(0, pd.NA)
            g["z_" + col] = z
        hits = g[(g["z_volume"] > args.sigma) | (g["z_trades"] > args.sigma) |
                 (g["z_oi_change"] > args.sigma)]
        for _, r in hits.iterrows():
            d = str(r["date"])
            flagged.append({
                "date": d, "symbol": sym,
                "volume_z": round(float(r["z_volume"]), 1) if pd.notna(r["z_volume"]) else None,
                "trades_z": round(float(r["z_trades"]), 1) if pd.notna(r["z_trades"]) else None,
                "oi_z": round(float(r["z_oi_change"]), 1) if pd.notna(r["z_oi_change"]) else None,
                "volume": int(r["volume"]), "trades": int(r["trades"]),
                "oi_change": int(r["oi_change"]),
                "price_chg_pct": round(float(r["ret"]), 2) if pd.notna(r["ret"]) else None,
                "price_ok": bool(pd.notna(r["ret"])),
                "nifty_chg_pct": round(nif_ret[d], 2) if d in nif_ret else None,
            })

    # per symbol: what the Nifty typically did on this stock's unusual days
    impact = {}
    for f in flagged:
        if f["nifty_chg_pct"] is None:
            continue
        s = impact.setdefault(f["symbol"], {"n": 0, "sum": 0.0, "moves": []})
        s["n"] += 1
        s["sum"] += f["nifty_chg_pct"]
        s["moves"].append(f["nifty_chg_pct"])
    for sym, s in impact.items():
        s["avg_nifty_pct"] = round(s.pop("sum") / s["n"], 2)
        s["max_abs_nifty_pct"] = round(max(abs(x) for x in s["moves"]), 2)
        s.pop("moves", None)

    flagged.sort(key=lambda x: -(max(x["volume_z"] or 0, x["trades_z"] or 0, x["oi_z"] or 0)))
    out["flagged"] = flagged[: args.keep]
    out["total_flagged"] = len(flagged)
    out["symbols_impact"] = dict(sorted(impact.items(),
                                        key=lambda kv: -kv[1]["n"])[:40])

    if flagged:
        out["note"] = ("%d unusual sessions across %d symbols: volume, trade count or open "
                       "interest far outside the stock's own recent range. These are facts "
                       "about what happened, not signals." % (len(flagged), len(impact)))
    else:
        out["note"] = ("No session exceeded %.1f standard deviations. Either the market was "
                       "quiet or the baseline is still too short." % args.sigma)
    if thin:
        out["note"] += (" %d symbols were skipped for having under %d sessions of history."
                        % (thin, args.min_days + 1))

    out["cautions"] = {
        "no_order_data": ("Free files carry no order-level detail. This cannot name the "
                          "buyer, the broker, or the size of any single order."),
        "summed_expiries": ("Volume and open interest are summed across every expiry and "
                            "strike of the symbol, because a large participant may work "
                            "across several at once."),
        "index_effect": ("The Nifty figure is the EMPIRICAL move on that stock's unusual "
                         "days, not a calculated contribution. Nifty weights need "
                         "free-float market caps, which these files do not carry."),
        "baseline": ("A z-score against a short baseline is noisy. The session count is "
                     "published so a thin result can be discounted."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %d unusual sessions across %d symbols (of %d symbols scanned)"
          % (len(flagged), len(impact), daily["symbol"].nunique()))
    for f in out["flagged"][:8]:
        print("     %s %-12s vol z=%-6s trades z=%-6s price %s%% nifty %s%%"
              % (f["date"], f["symbol"], f["volume_z"], f["trades_z"],
                 f["price_chg_pct"], f["nifty_chg_pct"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
