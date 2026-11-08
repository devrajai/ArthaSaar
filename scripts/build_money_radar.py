#!/usr/bin/env python3
"""Big Money Radar: where unusually large money actually showed up, and what it looked like.

WHAT THIS JOINS
Two sources the site already collects, into one ranked feed:

  deals.json      NSE's bulk and block deal disclosures - named clients, quantity and price.
                  A bulk deal is a single client above 0.5% of a company's equity; a block
                  deal is a negotiated trade above roughly Rs 10 crore.
  unusual.json    our own F&O footprint detector - volume, trade count, open interest and
                  shares per trade against each stock's own history.

Either alone is half a picture. A block deal tells you somebody big traded; the F&O footprint
tells you whether the derivatives market was positioned for it. Together they say what the
disclosure does not: whether the money was fresh or closing, and whether it was anticipated.

WHY SHARES PER TRADE, NOT TRADE VALUE
Average trade VALUE is misleading across price levels - a Rs 1,400 share always shows a
bigger trade value than a Rs 50 share with no big order involved. Shares per trade is
scale-free, so a stock is only ever compared with itself.

WHAT THIS CANNOT SAY, AND WHY
Nifty weights. A stock's contribution to the index needs free-float market capitalisation,
which needs promoter holding - and that field is empty in this pipeline. Without it there is
no honest way to convert a deal into index points or into an estimated passive inflow. This
file says so rather than publishing a number that looks precise and is not.

USAGE
  python scripts/build_money_radar.py
"""
import argparse, json, os, sys
from datetime import datetime, timezone

OUT = "docs/money_radar.json"


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def parse_deals(d):
    """Normalise bulk and block rows into one list."""
    out = []
    if not d:
        return out
    for kind in ("bulk", "block"):
        for r in (d.get(kind) or []):
            try:
                out.append({
                    "kind": kind,
                    "date": str(r[0]),
                    "symbol": str(r[1]).upper(),
                    "client": str(r[2]),
                    "side": str(r[3]).upper(),
                    "quantity": int(float(str(r[4]).replace(",", ""))),
                    "price": float(str(r[5]).replace(",", "")),
                })
            except Exception:
                continue
    for x in out:
        x["value_cr"] = round(x["quantity"] * x["price"] / 1e7, 2)
    return out


def main():
    ap = argparse.ArgumentParser(description="Big Money Radar.")
    ap.add_argument("--keep", type=int, default=60)
    args = ap.parse_args()

    deals_doc = load("docs/deals.json")
    unusual = load("docs/unusual.json")

    out = {"updated": now(), "deals": 0, "unusual": 0, "rows": [],
           "note": "", "cautions": {}}

    deals = parse_deals(deals_doc)
    out["deals"] = len(deals)

    # index the F&O footprint by symbol so a deal can be read beside it
    foot = {}
    for f in (unusual or {}).get("flagged") or []:
        s = str(f.get("symbol", "")).upper()
        if not s:
            continue
        prev = foot.get(s)
        score = max(f.get("volume_z") or 0, f.get("trades_z") or 0,
                    f.get("oi_z") or 0, f.get("spt_z") or 0)
        if prev is None or score > prev["score"]:
            foot[s] = {"score": round(score, 1), "date": f.get("date"),
                       "spt": f.get("shares_per_trade"),
                       "vol_z": f.get("volume_z"), "spt_z": f.get("spt_z"),
                       "oi_z": f.get("oi_z"),
                       "price_chg_pct": f.get("price_chg_pct")}
    out["unusual"] = len(foot)

    rows = []
    for d in deals:
        f = foot.get(d["symbol"])
        rows.append({
            "symbol": d["symbol"],
            "date": d["date"],
            "kind": d["kind"],
            "client": d["client"][:44],
            "side": d["side"],
            "quantity": d["quantity"],
            "price": d["price"],
            "value_cr": d["value_cr"],
            # the footprint, when the derivatives market also noticed
            "fno_score": (f or {}).get("score"),
            "fno_spt": (f or {}).get("spt"),
            "fno_price_chg_pct": (f or {}).get("price_chg_pct"),
            "also_unusual": bool(f),
        })

    # rank by deal value, but lift anything the derivatives market also flagged
    rows.sort(key=lambda r: (-(r["value_cr"] * (1.5 if r["also_unusual"] else 1.0))))
    out["rows"] = rows[: args.keep]
    out["total_deal_value_cr"] = round(sum(r["value_cr"] for r in rows), 1)
    out["with_footprint"] = sum(1 for r in rows if r["also_unusual"])

    if rows:
        out["note"] = ("%d bulk and block deals worth Rs %.0f crore, ranked by size, with the "
                       "F&O footprint beside each. %d of them also showed unusual derivatives "
                       "activity." % (len(rows), out["total_deal_value_cr"],
                                      out["with_footprint"]))
    else:
        out["note"] = ("No deal disclosures in docs/deals.json. The radar fills once "
                       "fetch_deals.py has run.")

    out["cautions"] = {
        "disclosure_not_signal": ("A bulk or block deal is a disclosure, not a recommendation. "
                                  "A large buy can be an index fund rebalancing, a promoter "
                                  "raising cash, or a short seller covering."),
        "no_index_weights": ("Nifty weights, points contributed and estimated passive inflows "
                             "are NOT published. They need free-float market capitalisation, "
                             "which needs promoter holding, and that field is empty here. An "
                             "invented weight would look precise and be wrong."),
        "shares_per_trade": ("Shares per trade is used instead of average trade value, because "
                             "value is not comparable across price levels."),
        "lag": ("Deals are published after the close, so this describes what already happened."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %d deals (Rs %.0f cr) | %d symbols with an F&O footprint | %d overlap"
          % (len(rows), out["total_deal_value_cr"], len(foot), out["with_footprint"]))
    for r in out["rows"][:8]:
        flag = " +F&O" if r["also_unusual"] else ""
        print("     %s %-12s %-5s %-6s Rs %8.2f cr  %s%s"
              % (r["date"], r["symbol"], r["kind"], r["side"], r["value_cr"],
                 r["client"][:26], flag))
    return 0


if __name__ == "__main__":
    sys.exit(main())
