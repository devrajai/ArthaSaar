#!/usr/bin/env python3
"""
build_indices.py - every index, with its constituents and the move in points.

An index is just a basket, so the useful view is: what is the index doing, and which
of its members are driving that. This joins three free sources:

  data/nse/index_*.csv   NSE's own constituent lists (Nifty 50, Bank, IT, Next 50, 500)
                         - also carries an Industry field per company
  docs/universe.json     today's close / change / volume from the NSE bhavcopy
  docs/data.json         the index level itself (Yahoo), for points and % change

Points: for a stock, points = close - previous close, derived from the % change.
For the index itself we use Yahoo's own level and change where we have the ticker.

Output: docs/indices.json

Usage:
  python scripts/build_indices.py
"""

from __future__ import annotations

import argparse
import glob
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# index id -> (display name, Yahoo ticker for the level, category)
# The ticker is only used for the official level. Yahoo's coverage of NSE sector
# indices is partial, so where there is none we fall back to the equal-weighted
# average of the members - which is always computable from the bhavcopy.
META = {
    # broad market
    "nifty50":            ("Nifty 50", "^NSEI", "Broad"),
    "niftynext50":        ("Nifty Next 50", None, "Broad"),
    "nifty100":           ("Nifty 100", None, "Broad"),
    "nifty200":           ("Nifty 200", None, "Broad"),
    "nifty500":           ("Nifty 500", None, "Broad"),
    "niftymidcap50":      ("Nifty Midcap 50", None, "Broad"),
    "niftymidcap150":     ("Nifty Midcap 150", None, "Broad"),
    "niftysmallcap50":    ("Nifty Smallcap 50", None, "Broad"),
    "niftysmallcap250":   ("Nifty Smallcap 250", None, "Broad"),
    "niftymidsmallcap400":("Nifty MidSmallcap 400", None, "Broad"),
    # sectors
    "niftybank":          ("Nifty Bank", "^NSEBANK", "Sector"),
    "niftyit":            ("Nifty IT", "^CNXIT", "Sector"),
    "niftyauto":          ("Nifty Auto", "^CNXAUTO", "Sector"),
    "niftyfmcg":          ("Nifty FMCG", "^CNXFMCG", "Sector"),
    "niftypharma":        ("Nifty Pharma", "^CNXPHARMA", "Sector"),
    "niftymetal":         ("Nifty Metal", "^CNXMETAL", "Sector"),
    "niftyrealty":        ("Nifty Realty", "^CNXREALTY", "Sector"),
    "niftyenergy":        ("Nifty Energy", "^CNXENERGY", "Sector"),
    "niftyinfra":         ("Nifty Infrastructure", "^CNXINFRA", "Sector"),
    "niftymedia":         ("Nifty Media", "^CNXMEDIA", "Sector"),
    "niftyfinancelist":   ("Nifty Financial Services", None, "Sector"),
    "niftypsubank":       ("Nifty PSU Bank", None, "Sector"),
    "niftyconsumerdur":   ("Nifty Consumer Durables", None, "Sector"),
    "niftyhealthcare":    ("Nifty Healthcare", None, "Sector"),
    "niftyoilgas":        ("Nifty Oil & Gas", None, "Sector"),
    # BSE - constituents are blocked (BSE returns 403 to non-browser clients), so the
    # Sensex is represented through the overlap of its members with Nifty 50.
    "sensex_proxy":       ("Sensex members (via NSE overlap)", "^BSESN", "BSE"),
}

def load(p: str):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Indices + constituents + points.")
    ap.add_argument("--nse-dir", default="data/nse")
    ap.add_argument("--universe", default="docs/universe.json")
    ap.add_argument("--data", default="docs/data.json")
    ap.add_argument("--stocks", default="docs/stocks.json")
    ap.add_argument("--out", default="docs/indices.json")
    args = ap.parse_args()

    uni = load(args.universe) or {}
    quotes = {r["symbol"]: r for r in (uni.get("rows") or [])}
    deep = {v.get("symbol") for v in ((load(args.stocks) or {}).get("stocks") or {}).values()}

    # index levels from the markets section (Yahoo)
    levels = {}
    for r in ((load(args.data) or {}).get("markets") or {}).get("rows", []) or []:
        try:
            levels[r[0]] = {"close": float(r[1]), "chg_pct": float(r[2])}
        except Exception:
            continue

    out = []
    for f in sorted(glob.glob(f"{args.nse_dir}/index_*.csv")):
        iid = Path(f).stem.replace("index_", "")
        name, ysym, cat = META.get(iid, (iid.replace("_", " ").title(), None, "Other"))
        try:
            df = pd.read_csv(f, dtype=str)
        except Exception:
            continue
        df.columns = [c.strip() for c in df.columns]
        symcol = next((c for c in ("Symbol", "SYMBOL") if c in df.columns), None)
        namecol = next((c for c in ("Company Name", "NAME OF COMPANY") if c in df.columns), None)
        indcol = next((c for c in ("Industry", "SECTOR") if c in df.columns), None)
        if not symcol:
            continue

        members, adv, dec, unch = [], 0, 0, 0
        for _, r in df.iterrows():
            sym = str(r[symcol]).strip()
            q = quotes.get(sym) or {}
            chg = q.get("chg_pct")
            close = q.get("close")
            pts = None
            if close is not None and chg is not None and (100 + chg) != 0:
                pts = round(close - close / (1 + chg / 100.0), 2)
            if chg is None:
                unch += 1
            elif chg > 0:
                adv += 1
            elif chg < 0:
                dec += 1
            else:
                unch += 1
            members.append({
                "symbol": sym,
                "name": (str(r[namecol]).strip() if namecol else sym),
                "industry": (str(r[indcol]).strip() if indcol else ""),
                "close": close, "chg_pct": chg, "points": pts,
                "volume": q.get("volume"), "deep": sym in deep,
            })

        # equal-weighted average move, as a sanity check next to the official number
        vals = [m["chg_pct"] for m in members if m["chg_pct"] is not None]
        avg = round(sum(vals) / len(vals), 2) if vals else None

        lv = levels.get(ysym) if ysym else None
        members.sort(key=lambda m: -(m["chg_pct"] if m["chg_pct"] is not None else -999))

        out.append({
            "id": iid, "name": name, "yahoo": ysym, "category": cat,
            "level": lv["close"] if lv else None,
            "chg_pct": lv["chg_pct"] if lv else None,
            "points": (round(lv["close"] - lv["close"] / (1 + lv["chg_pct"] / 100.0), 2)
                       if lv and (1 + lv["chg_pct"] / 100.0) else None),
            "avg_chg_pct": avg,
            "count": len(members), "advances": adv, "declines": dec, "unchanged": unch,
            "constituents": members,
        })

    # heat map: every index's move, biggest riser first, so the site can colour tiles
    heat = sorted(
        [{"id": i["id"], "name": i["name"], "category": i["category"],
          "chg_pct": i["chg_pct"] if i["chg_pct"] is not None else i["avg_chg_pct"],
          "points": i["points"], "level": i["level"], "count": i["count"],
          "advances": i["advances"], "declines": i["declines"]} for i in out],
        key=lambda x: -(x["chg_pct"] if x["chg_pct"] is not None else -999))
    payload = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "count": len(out), "categories": sorted({i["category"] for i in out}),
               "heat": heat, "indices": out}
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest}  ({dest.stat().st_size / 1e3:.0f} KB)")
    for i in out:
        lv = f"{i['level']:.2f}" if i.get("level") else "n/a"
        pc = f"{i['chg_pct']:+.2f}%" if i.get("chg_pct") is not None else "n/a"
        pt = f"{i['points']:+.2f}" if i.get("points") is not None else "n/a"
        print(f"  {i['name']:15s} {i['count']:>4} members  level={lv:>10}  {pc:>8}  {pt:>9} pts  "
              f"adv {i['advances']}/dec {i['declines']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
