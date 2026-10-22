#!/usr/bin/env python3
"""
build_sectors.py - the sector heat map, and which stocks are moving it.

Groups the listed universe by industry and works out, for each sector: the average
move, how many stocks are up versus down, and the individual names with their move in
percent and in points. That is what a heat map needs.

Industry comes from NSE's own index constituent files (they carry an Industry column
per company), which is more reliable for Indian stocks than Yahoo's sector labels.
Yahoo's sector is used as a fallback.

Output: docs/sectors.json
  {"updated","count","sectors":[{"name","count","avg_chg","advances","declines",
     "best","worst","stocks":[{symbol,name,close,chg_pct,points,deep}]}]}

Usage:
  python scripts/build_sectors.py
"""

from __future__ import annotations

import argparse
import glob
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd


def load(p: str):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def nse_industries(nse_dir: str) -> dict:
    """symbol -> industry, from NSE's index constituent files."""
    out = {}
    for f in sorted(glob.glob(f"{nse_dir}/index_*.csv")):
        try:
            df = pd.read_csv(f, dtype=str)
        except Exception:
            continue
        df.columns = [c.strip() for c in df.columns]
        if "Symbol" not in df.columns or "Industry" not in df.columns:
            continue
        for _, r in df.iterrows():
            sym = str(r["Symbol"]).strip()
            ind = str(r["Industry"]).strip()
            if sym and ind and ind.lower() != "nan":
                out.setdefault(sym, ind)   # Nifty 500 first alphabetically; good enough
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Sector heat map from the listed universe.")
    ap.add_argument("--nse-dir", default="data/nse")
    ap.add_argument("--universe", default="docs/universe.json")
    ap.add_argument("--stocks", default="docs/stocks.json")
    ap.add_argument("--out", default="docs/sectors.json")
    ap.add_argument("--min-stocks", type=int, default=3, help="hide tiny sectors")
    args = ap.parse_args()

    uni = load(args.universe) or {}
    rows = uni.get("rows") or []
    ind_map = nse_industries(args.nse_dir)

    stocks = (load(args.stocks) or {}).get("stocks") or {}
    deep = {v.get("symbol"): v for v in stocks.values()}
    yahoo_sector = {}
    for v in stocks.values():
        if v.get("sector"):
            yahoo_sector[v["symbol"]] = v["sector"]

    groups: dict[str, list] = {}
    for r in rows:
        sym = r.get("symbol")
        chg = r.get("chg_pct")
        close = r.get("close")
        if chg is None or close is None:
            continue
        ind = ind_map.get(sym) or yahoo_sector.get(sym) or "Unclassified"
        pts = round(close - close / (1 + chg / 100.0), 2) if (1 + chg / 100.0) else None
        groups.setdefault(ind, []).append({
            "symbol": sym, "name": (r.get("name") or "")[:30],
            "close": close, "chg_pct": chg, "points": pts,
            "volume": r.get("volume"), "deep": sym in deep,
        })

    sectors = []
    for name, members in groups.items():
        if len(members) < args.min_stocks:
            continue
        vals = [m["chg_pct"] for m in members]
        adv = sum(1 for v in vals if v > 0)
        dec = sum(1 for v in vals if v < 0)
        members.sort(key=lambda m: -m["chg_pct"])
        sectors.append({
            "name": name, "count": len(members),
            "avg_chg": round(sum(vals) / len(vals), 2),
            "advances": adv, "declines": dec,
            "best": members[0]["symbol"], "worst": members[-1]["symbol"],
            "stocks": members,
        })
    sectors.sort(key=lambda s: -s["avg_chg"])

    payload = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
               "count": len(sectors), "sectors": sectors}
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    print(f"Wrote {dest}  ({dest.stat().st_size / 1e3:.0f} KB)  |  {len(sectors)} sectors")
    for s in sectors[:8]:
        print(f"  {s['name'][:34]:34s} {s['avg_chg']:+6.2f}%  {s['count']:>4} stocks  "
              f"up {s['advances']}/down {s['declines']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
