#!/usr/bin/env python3
"""
build_site_data.py - aggregate every output into one small JSON for the website.

Most of the hub's outputs are git-ignored (indicators, screens, forecasts, quality) so
the site cannot fetch them from the repo directly. This runs inside the pipeline, where
those files DO exist, and folds the useful parts into `docs/data.json` - one committed
file the static site reads.

Everything is defensive: a missing section is simply omitted, never an error.

Usage
-----
  python scripts/build_site_data.py
  python scripts/build_site_data.py --out docs/data.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

try:
    import pyarrow as _pa
    _pa.set_cpu_count(1)
    _pa.set_io_thread_count(1)
except Exception:
    pass

MAX_ROWS = 25


def _read_json(p: Path):
    try:
        return json.loads(p.read_text()) if p.exists() else None
    except Exception:
        return None


def _read_csv(p: Path, rows: int = MAX_ROWS):
    try:
        if not p.exists():
            return None
        df = pd.read_csv(p, dtype=str)
        return {
            "columns": list(df.columns)[:12],
            "rows": df.head(rows).fillna("").astype(str).values.tolist(),
            "total": int(len(df)),
        }
    except Exception:
        return None


def build() -> dict:
    out: dict = {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

    # ---- F&O / market
    fut = _read_json(Path("data/futures.json"))
    if fut:
        stocks = fut.get("stocks", [])[:20]
        out["fno"] = {
            "date": fut.get("date"),
            "pcr": fut.get("pcr", {}),
            "index_futures": fut.get("index_futures", [])[:8],
            "top_oi": [{"symbol": s.get("symbol"), "oi": s.get("oi"),
                        "oi_chg": s.get("oi_chg"), "chg": s.get("change_pct")}
                       for s in stocks],
            "stock_futures": len(fut.get("stocks", [])),
        }

    # ---- archive (bhavcopy manifest)
    man = _read_csv(Path("data/manifest.csv"), rows=MAX_ROWS)
    if man:
        try:
            df = pd.read_csv("data/manifest.csv", dtype=str)
            out["archive"] = {
                "files": int(len(df)),
                "dates": int(df["date"].nunique()) if "date" in df.columns else None,
                "symbols_max": int(pd.to_numeric(df["symbols"], errors="coerce").max())
                if "symbols" in df.columns else None,
                "first": df["date"].min() if "date" in df.columns else None,
                "last": df["date"].max() if "date" in df.columns else None,
                "recent": df.sort_values("date").tail(12).to_dict("records"),
            }
        except Exception:
            pass

    # ---- YouTube brain
    brain = _read_json(Path("data/analysis/brain_summary.json"))
    if brain:
        out["brain"] = {
            "channels": brain.get("channels"),
            "videos": brain.get("videos"),
            "window": [brain.get("window_start"), brain.get("window_end")],
            "total_views": brain.get("total_views"),
            "net_sentiment": brain.get("net_sentiment"),
            "top_symbols": brain.get("top_symbols", [])[:12],
            "top_themes": brain.get("top_themes", [])[:10],
        }
    ch = _read_csv(Path("data/analysis/channel_stats.csv"), rows=15)
    if ch:
        out["channels"] = ch
    vids = _read_csv(Path("data/youtube/videos.csv"), rows=15)
    if vids:
        out["videos"] = vids

    # ---- indicators snapshot (git-ignored, so folded in here)
    ind = _read_csv(Path("data/indicators/latest.csv"), rows=30)
    if ind:
        out["indicators"] = ind

    # ---- screens
    screens = {}
    for p in sorted(Path("data/screens").glob("*.csv")) if Path("data/screens").exists() else []:
        r = _read_csv(p, rows=15)
        if r:
            screens[p.stem] = r
    if screens:
        out["screens"] = screens

    # ---- relative strength
    rs = _read_csv(Path("data/rs/latest.csv"), rows=20)
    if rs:
        out["relative_strength"] = rs

    # ---- patterns
    pat = _read_csv(Path("data/patterns/detected.csv"), rows=25)
    if pat:
        out["patterns"] = pat

    # ---- forecast accuracy
    acc = _read_csv(Path("data/forecast/accuracy.csv"), rows=40)
    if acc:
        try:
            df = pd.read_csv("data/forecast/accuracy.csv")
            df = df[~df["symbol"].astype(str).str.contains("#w", na=False)]
            med = (df.groupby("model")["mape"].median().sort_values()
                   .reset_index().round(2).values.tolist())
            out["forecast"] = {"median_mape_by_model": med, "rows": int(len(df))}
        except Exception:
            pass

    # ---- data quality
    q = _read_json(Path("data/quality/report.json"))
    if q:
        out["quality"] = {"rows": q.get("rows"), "symbols": q.get("symbols"),
                          "window": q.get("window"),
                          "errors": [e.get("check") for e in q.get("errors", [])],
                          "warnings": [w.get("check") for w in q.get("warnings", [])]}

    # ---- NSE reference
    fii = _read_csv(Path("data/nse/fii_dii.csv"), rows=5)
    if fii:
        out["fii_dii"] = fii
    cons = {}
    for p in sorted(Path("data/nse").glob("index_*.csv")) if Path("data/nse").exists() else []:
        try:
            cons[p.stem.replace("index_", "")] = int(len(pd.read_csv(p)))
        except Exception:
            pass
    if cons:
        out["index_constituents"] = cons

    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate outputs into docs/data.json.")
    ap.add_argument("--out", default="docs/data.json")
    args = ap.parse_args()

    data = build()
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=2, default=str))

    sections = [k for k in data if k != "generated_utc"]
    size = dest.stat().st_size
    print(f"Wrote {dest}  ({size:,} bytes)")
    print(f"  sections: {', '.join(sections) if sections else '(none - no data yet)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
