#!/usr/bin/env python3
"""What an option actually costs to trade, and what usually happens to the cheap ones.

WHY THIS IS NOT A "SMALL CAPITAL STRATEGY"
The premium is not the cost of an option; premium x LOT SIZE is. A Rs 2 option on a
lot of 3,000 costs Rs 6,000, not Rs 2. This screen shows the real number, because that is
the figure that decides whether a contract is reachable at all.

And the cheap ones are cheap for a reason. An option trading at Rs 1 is priced that way
because the market thinks it will probably expire worthless. That is not a discount, it is
the odds. So this file publishes, beside every affordable contract, the honest base rate
measured from our own F&O history: of options that traded under Rs 2 in their final week,
what share ever doubled, and what share expired worthless.

WHAT IT READS
  data/parquet/fo/fo_*.parquet   strikes, premiums, volume, open interest
  fo_mktlots.csv (NSE)           lot size per underlying, fetched live

WHAT IT WRITES
  docs/affordable.json           contracts bucketed by cost per lot, ranked by liquidity,
                                 with the base rates attached

WHAT IT CANNOT SAY YET
The stored F&O parquet has no expiry column (the collector dropped it; fixed, but the
history needs rebuilding). Without expiry a contract cannot be labelled by its expiry date,
so each row shows the nearest expiry from NSE's lot file and is marked expiry_known=false.
When the rebuilt data lands, the same script labels rows exactly.
"""
import argparse, csv, glob, io, json, os, sys, urllib.request
from datetime import datetime, timezone

OUT = "docs/affordable.json"
LOTS_URL = "https://nsearchives.nseindia.com/content/fo/fo_mktlots.csv"
BUCKETS = [500, 1000, 2000, 5000]
CHEAP_PREMIUM = 2.0        # "cheap option" definition used for the base rate
MIN_SESSIONS_FOR_RATES = 60   # below this the base rate is noise, not a measurement


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_lots():
    """symbol -> lot size for the nearest expiry NSE lists."""
    try:
        raw = urllib.request.urlopen(urllib.request.Request(
            LOTS_URL, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.nseindia.com/"}),
            timeout=60).read().decode("utf-8", "replace")
    except Exception as e:
        print("  lot sizes unavailable: %s" % type(e).__name__)
        return {}, None
    rows = list(csv.reader(io.StringIO(raw)))
    if not rows:
        return {}, None
    header = [h.strip() for h in rows[0]]
    # columns after UNDERLYING and SYMBOL are expiry months, nearest first
    exp_cols = [(i, h) for i, h in enumerate(header) if i >= 2 and h]
    lots = {}
    nearest = None
    for r in rows[1:]:
        if len(r) < 3:
            continue
        sym = r[1].strip().upper()
        if not sym:
            continue
        for i, label in exp_cols:
            if i < len(r):
                v = r[i].strip().replace(",", "")
                if v.isdigit() and int(v) > 0:
                    lots[sym] = int(v)
                    nearest = nearest or label
                    break
    return lots, nearest


def load_fo():
    import pandas as pd
    files = sorted(glob.glob("data/parquet/fo/fo_*.parquet"))
    if not files:
        return None
    frames = []
    for f in files:
        try:
            frames.append(pd.read_parquet(f))
        except Exception:
            continue
    return pd.concat(frames, ignore_index=True) if frames else None


def base_rates(df, sessions):
    """Of cheap options, how many doubled, and how many went to nearly nothing.

    Without expiry this cannot restrict to the final week, so it measures options whose
    premium was under the cheap threshold on any day we hold, and follows that same
    strike-and-type contract forward through the sessions we have.
    """
    import pandas as pd
    # A base rate over a handful of sessions is not a measurement. With six sessions an
    # option can swing either way and "ever doubled" says nothing about what happens to a
    # cheap option by expiry. Publishing it would encourage exactly the wrong conclusion.
    if sessions < MIN_SESSIONS_FOR_RATES:
        return {"insufficient_history": True, "sessions": sessions,
                "needed": MIN_SESSIONS_FOR_RATES,
                "note": ("Only %d sessions of F&O history are stored. A base rate needs at "
                         "least %d to mean anything - a cheap option's whole life is the "
                         "question, and these files cover a few days."
                         % (sessions, MIN_SESSIONS_FOR_RATES))}
    if "opt_type" not in df.columns or "close" not in df.columns:
        return None
    o = df[df["opt_type"].astype(str).str.upper().isin(["CE", "PE"])].copy()
    if o.empty:
        return None
    o["close"] = pd.to_numeric(o["close"], errors="coerce")
    o = o[o["close"] > 0]
    key = ["symbol", "strike", "opt_type"]
    if "expiry" in o.columns and o["expiry"].notna().any():
        key = key + ["expiry"]
    o = o.sort_values(key + ["date"])
    doubled = zeroed = total = 0
    for _, g in o.groupby(key):
        if len(g) < 2:
            continue
        start = g["close"].iloc[0]
        if start > CHEAP_PREMIUM:
            continue
        total += 1
        peak = g["close"].max()
        end = g["close"].iloc[-1]
        if peak >= start * 2:
            doubled += 1
        if end <= start * 0.25:
            zeroed += 1
    if not total:
        return None
    return {"cheap_contracts_followed": total,
            "doubled_pct": round(doubled / total * 100, 1),
            "fell_to_a_quarter_pct": round(zeroed / total * 100, 1),
            "premium_under": CHEAP_PREMIUM}


def main():
    ap = argparse.ArgumentParser(description="Affordability of option contracts.")
    ap.add_argument("--per-bucket", type=int, default=40)
    args = ap.parse_args()

    out = {"updated": now(), "nearest_expiry": None, "buckets": [],
           "base_rates": None, "note": "", "cautions": {}}

    lots, nearest = fetch_lots()
    out["nearest_expiry"] = nearest
    print("  lot sizes for %d underlyings (nearest expiry %s)" % (len(lots), nearest))

    df = load_fo()
    if df is None or df.empty:
        out["note"] = "No F&O parquet found; run fetch_bhavcopy first."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
        print("affordable: no F&O data")
        return 0

    import pandas as pd
    sessions_held = int(df["date"].nunique()) if "date" in df.columns else 0
    out["sessions_held"] = sessions_held
    out["base_rates"] = base_rates(df, sessions_held)

    if "opt_type" not in df.columns:
        out["note"] = "F&O file has no option-type column."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
        return 0

    o = df[df["opt_type"].astype(str).str.upper().isin(["CE", "PE"])].copy()
    for c in ("close", "volume", "oi", "strike"):
        if c in o.columns:
            o[c] = pd.to_numeric(o[c], errors="coerce")
    o = o[(o["close"] > 0) & o["strike"].notna()]
    if o.empty:
        out["note"] = "No priced option contracts in the files."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
        return 0

    # the latest session only - a stale premium would misstate the cost
    latest = str(o["date"].max())
    o = o[o["date"].astype(str) == latest]
    out["session"] = latest

    has_expiry = "expiry" in o.columns and o["expiry"].notna().any()

    recs = []
    for _, r in o.iterrows():
        sym = str(r["symbol"]).upper()
        lot = lots.get(sym)
        if not lot:
            continue
        cost = float(r["close"]) * lot
        recs.append({
            "symbol": sym,
            "strike": float(r["strike"]),
            "type": str(r["opt_type"]).upper(),
            "premium": round(float(r["close"]), 2),
            "lot": lot,
            "cost_per_lot": int(round(cost)),
            "volume": int(r["volume"]) if pd.notna(r.get("volume")) else 0,
            "oi": int(r["oi"]) if pd.notna(r.get("oi")) else 0,
            "expiry": str(r["expiry"])[:10] if has_expiry else nearest,
            "expiry_known": bool(has_expiry),
        })

    # Require TRADED VOLUME, not just open interest. A strike with OI but no volume on the
    # day cannot be entered or exited at a fair price - listing it as "affordable" would be
    # misleading, because the cost is not the obstacle, the liquidity is.
    recs = [x for x in recs if x["volume"] > 0]
    recs.sort(key=lambda x: (x["cost_per_lot"], -x["volume"]))

    # RANGES, not cumulative caps. With "under 500 / under 1000 / under 2000" every bucket
    # showed the same cheapest rows and told the reader nothing new.
    floor = 0
    for cap in BUCKETS:
        sel = [x for x in recs if floor < x["cost_per_lot"] <= cap]
        out["buckets"].append({
            "min_cost": floor, "max_cost": cap,
            "count": len(sel),
            # within a range, most-traded first: liquidity is the real constraint
            "rows": sorted(sel, key=lambda x: -x["volume"])[: args.per_bucket],
        })
        floor = cap
    above = [x for x in recs if x["cost_per_lot"] > BUCKETS[-1]]
    out["above_top_bucket"] = {"count": len(above)}

    out["total_contracts"] = len(recs)
    out["note"] = ("Cost per lot is premium x lot size, on the %s session. Only contracts with "
                   "traded volume or open interest are listed - a cheap strike nobody trades "
                   "cannot be exited." % latest)
    if not has_expiry:
        out["note"] += (" The stored files carry no expiry, so rows are labelled with the "
                        "nearest expiry from NSE's lot file rather than the contract's own.")
    if out["base_rates"] and out["base_rates"].get("insufficient_history"):
        out["note"] += (" No doubling or expiry base rate is published: %d sessions of "
                        "history is not enough to measure what happens to a cheap option over "
                        "its life." % out["sessions_held"])
    out["cautions"] = {
        "cheap_is_the_odds": ("An option at a low premium is priced that way because the "
                              "market expects it to expire worthless. The premium is not a "
                              "discount."),
        "premium_is_not_cost": ("Premium x lot size is what leaves your account. A Rs 2 "
                                "option on a 3,000 lot costs Rs 6,000."),
        "charges_not_included": ("Brokerage, STT, exchange and GST charges are not included. "
                                 "On a small premium they can be a large share of the stake."),
        "not_a_recommendation": ("Nothing here is advice or a signal. It is the arithmetic of "
                                 "what a contract costs and how cheap contracts have behaved."),
        "sebi": ("SEBI's own studies have found that most individual F&O traders lose money "
                 "over time. Read this beside that finding, not instead of it."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   session %s | %d tradeable contracts with a known lot size"
          % (latest, out["total_contracts"]))
    for b in out["buckets"]:
        print("   Rs %-5d - %-5d  %5d contracts" % (b["min_cost"], b["max_cost"], b["count"]))
    print("   above Rs %-5d     %5d contracts" % (BUCKETS[-1], out["above_top_bucket"]["count"]))
    br = out["base_rates"]
    if br and br.get("insufficient_history"):
        print("   base rates WITHHELD: %d sessions stored, %d needed"
              % (br["sessions"], br["needed"]))
    elif br:
        print("   cheap options (under Rs %.0f): %d followed, %.1f%% ever doubled, "
              "%.1f%% fell to a quarter"
              % (br["premium_under"], br["cheap_contracts_followed"],
                 br["doubled_pct"], br["fell_to_a_quarter_pct"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
