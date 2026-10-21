#!/usr/bin/env python3
"""
build_site_data.py - aggregate every output into one small JSON for the website.

Most of the hub's outputs are git-ignored (indicators, screens, forecasts, quality), so
the site cannot fetch them from the repo directly. This runs inside the pipeline, where
those files DO exist, and folds the useful parts into `docs/data.json` - one committed
file the static site reads.

Sections produced (only when the data exists):
  daily        headline of the day: what updated, PCR, max pain, spike counts
  fno          stock-futures OI, index futures, PCR / max pain
  spikes       OI spikes and volume spikes
  corporate    dividends, splits and bonuses (from NSE corporate actions)
  markets      global indices
  commodities  gold, crude, and friends
  fx           currency pairs
  crypto       crypto pairs
  news         headlines from RSS
  archive      bhavcopy manifest summary
  brain        YouTube channel analysis
  channels / videos
  indicators / screens / relative_strength / patterns / forecast / quality
  fii_dii / index_constituents

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


def _json(p: Path):
    try:
        return json.loads(p.read_text()) if p.exists() else None
    except Exception:
        return None


def _csv(p: Path, rows: int = MAX_ROWS):
    try:
        if not p.exists():
            return None
        df = pd.read_csv(p, dtype=str)
        if df.empty:
            return None
        return {"columns": list(df.columns)[:12],
                "rows": df.head(rows).fillna("").astype(str).values.tolist(),
                "total": int(len(df))}
    except Exception:
        return None


def _movers(path: str, kinds: dict) -> dict:
    """Last close + % change per symbol, split into groups by symbol pattern."""
    p = Path(path)
    if not p.exists():
        return {}
    try:
        df = pd.read_parquet(p)
    except Exception:
        return {}
    if not {"symbol", "close"}.issubset(df.columns):
        return {}
    sortcol = "date" if "date" in df.columns else ("ts" if "ts" in df.columns else None)
    if sortcol is None:
        return {}
    out: dict[str, list] = {}
    for sym, g in df.groupby("symbol", sort=False):
        g = g.sort_values(sortcol)
        if len(g) < 2:
            continue
        last = float(g["close"].iloc[-1]); prev = float(g["close"].iloc[-2])
        if not prev:
            continue
        grp = "other"
        for name, test in kinds.items():
            if test(sym):
                grp = name
                break
        out.setdefault(grp, []).append({
            "symbol": sym, "close": round(last, 4),
            "chg_pct": round((last / prev - 1) * 100, 2),
            "date": str(g[sortcol].iloc[-1])[:10],
        })
    for g in out.values():
        g.sort(key=lambda r: -abs(r["chg_pct"]))
    return out


def build() -> dict:
    d: dict = {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}

    # ---------------- F&O ----------------
    fut = _json(Path("data/futures.json"))
    if fut:
        d["fno"] = {
            "date": fut.get("date"),
            "pcr": fut.get("pcr", {}),
            "index_futures": fut.get("index_futures", [])[:8],
            "top_oi": [{"symbol": s.get("symbol"), "oi": s.get("oi"),
                        "oi_chg": s.get("oi_chg"), "chg": s.get("change_pct")}
                       for s in fut.get("stocks", [])[:20]],
            "stock_futures": len(fut.get("stocks", [])),
        }

    # ---------------- spikes ----------------
    oi = _csv(Path("data/spikes/oi_spikes.csv"), 20)
    vol = _csv(Path("data/spikes/volume_spikes.csv"), 20)
    if oi or vol:
        d["spikes"] = {}
        if oi:
            d["spikes"]["oi"] = oi
        if vol:
            d["spikes"]["volume"] = vol

    # ---------------- corporate actions ----------------
    ca_path = Path("data/corporate_actions/actions.csv")
    if ca_path.exists():
        try:
            ca = pd.read_csv(ca_path, dtype=str)
            ca["type"] = ca["type"].fillna("other")
            grp = {}
            for t in ("dividend", "split", "bonus", "rights", "other"):
                sub = ca[ca["type"] == t]
                if len(sub):
                    grp[t] = {"columns": ["symbol", "subject", "ex_date", "company"],
                              "rows": sub[["symbol", "subject", "ex_date", "company"]]
                                      .fillna("").head(30).astype(str).values.tolist(),
                              "total": int(len(sub))}
            if grp:
                d["corporate"] = grp
        except Exception:
            pass

    # ---------------- markets / commodities / fx ----------------
    kinds = {
        "fx": lambda s: s.endswith("=X"),
        "commodity": lambda s: s.endswith("=F"),
        "crypto": lambda s: s.endswith("-USD"),
        "index": lambda s: s.startswith("^"),
    }
    m = _movers("data/yahoo/_all.parquet", kinds)
    if m.get("index"):
        d["markets"] = {"columns": ["symbol", "close", "chg_pct", "date"], "rows":
                        [[r["symbol"], r["close"], r["chg_pct"], r["date"]] for r in m["index"]],
                        "total": len(m["index"])}
    if m.get("commodity"):
        d["commodities"] = {"columns": ["symbol", "close", "chg_pct", "date"], "rows":
                            [[r["symbol"], r["close"], r["chg_pct"], r["date"]] for r in m["commodity"]],
                            "total": len(m["commodity"])}
    if m.get("fx"):
        d["fx"] = {"columns": ["symbol", "close", "chg_pct", "date"], "rows":
                   [[r["symbol"], r["close"], r["chg_pct"], r["date"]] for r in m["fx"]],
                   "total": len(m["fx"])}

    # ---------------- crypto ----------------
    cm = _movers("data/crypto/_all.parquet", {})
    if cm.get("other"):
        d["crypto"] = {"columns": ["symbol", "close", "chg_pct", "date"], "rows":
                       [[r["symbol"], r["close"], r["chg_pct"], r["date"]] for r in cm["other"]],
                       "total": len(cm["other"])}
    elif m.get("crypto"):
        d["crypto"] = {"columns": ["symbol", "close", "chg_pct", "date"], "rows":
                       [[r["symbol"], r["close"], r["chg_pct"], r["date"]] for r in m["crypto"]],
                       "total": len(m["crypto"])}

    # ---------------- news ----------------
    nw = _csv(Path("data/news/headlines.csv"), 30)
    if nw:
        d["news"] = nw

    # ---------------- archive ----------------
    if Path("data/manifest.csv").exists():
        try:
            df = pd.read_csv("data/manifest.csv", dtype=str)
            d["archive"] = {
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

    # ---------------- YouTube ----------------
    brain = _json(Path("data/analysis/brain_summary.json"))
    if brain:
        d["brain"] = {"channels": brain.get("channels"), "videos": brain.get("videos"),
                      "window": [brain.get("window_start"), brain.get("window_end")],
                      "total_views": brain.get("total_views"),
                      "net_sentiment": brain.get("net_sentiment"),
                      "top_symbols": brain.get("top_symbols", [])[:12],
                      "top_themes": brain.get("top_themes", [])[:10]}
    ch = _csv(Path("data/analysis/channel_stats.csv"), 15)
    if ch:
        d["channels"] = ch
    vids = _csv(Path("data/youtube/videos.csv"), 15)
    if vids:
        d["videos"] = vids

    # ---------------- analysis ----------------
    for key, path in (("indicators", "data/indicators/latest.csv"),
                      ("relative_strength", "data/rs/latest.csv"),
                      ("patterns", "data/patterns/detected.csv")):
        r = _csv(Path(path), 30)
        if r:
            d[key] = r
    screens = {}
    sp = Path("data/screens")
    if sp.exists():
        for p in sorted(sp.glob("*.csv")):
            r = _csv(p, 15)
            if r:
                screens[p.stem] = r
    if screens:
        d["screens"] = screens

    acc = Path("data/forecast/accuracy.csv")
    if acc.exists():
        try:
            df = pd.read_csv(acc)
            df = df[~df["symbol"].astype(str).str.contains("#w", na=False)]
            med = (df.groupby("model")["mape"].median().sort_values()
                   .reset_index().round(2).values.tolist())
            d["forecast"] = {"median_mape_by_model": med, "rows": int(len(df))}
        except Exception:
            pass

    # TimesFM (FM3) - only present when the RUN_TIMESFM job has been enabled
    tf = _json(Path("data/timesfm_forecasts.json"))
    if tf:
        rows = tf if isinstance(tf, list) else tf.get("forecasts", [])
        if rows:
            d["fm3"] = {"columns": ["symbol", "median_chg_pct", "direction", "confidence"],
                        "rows": [[r.get("symbol"), r.get("median_chg_pct"),
                                  r.get("direction"), r.get("confidence")] for r in rows[:25]],
                        "total": len(rows)}

    q = _json(Path("data/quality/report.json"))
    if q:
        d["quality"] = {"rows": q.get("rows"), "symbols": q.get("symbols"),
                        "window": q.get("window"),
                        "errors": [e.get("check") for e in q.get("errors", [])],
                        "warnings": [w.get("check") for w in q.get("warnings", [])]}

    fii = _csv(Path("data/nse/fii_dii.csv"), 5)
    if fii:
        d["fii_dii"] = fii
    cons = {}
    nse = Path("data/nse")
    if nse.exists():
        for p in sorted(nse.glob("index_*.csv")):
            try:
                cons[p.stem.replace("index_", "")] = int(len(pd.read_csv(p)))
            except Exception:
                pass
    if cons:
        d["index_constituents"] = cons

    # ---------------- daily headline ----------------
    upd = {"as_of": d.get("generated_utc"), "items": []}
    if d.get("archive", {}).get("last"):
        upd["items"].append(f"Bhavcopy archive through {d['archive']['last']} "
                            f"({d['archive'].get('files')} files, {d['archive'].get('dates')} days)")
    if d.get("fno", {}).get("pcr"):
        p = d["fno"]["pcr"]
        if p.get("nifty_pcr_oi") is not None:
            upd["items"].append(f"Nifty PCR {p['nifty_pcr_oi']} · max pain {p.get('nifty_max_pain')}")
    if d.get("spikes", {}).get("oi"):
        upd["items"].append(f"{d['spikes']['oi']['total']} OI spikes in stock futures")
    if d.get("spikes", {}).get("volume"):
        upd["items"].append(f"{d['spikes']['volume']['total']} volume spikes vs their own average")
    if d.get("corporate"):
        c = d["corporate"]
        bits = []
        for t in ("dividend", "split", "bonus"):
            if t in c:
                bits.append(f"{c[t]['total']} {t}{'s' if c[t]['total'] != 1 else ''}")
        if bits:
            upd["items"].append("Corporate actions: " + ", ".join(bits))
    if d.get("brain"):
        upd["items"].append(f"{d['brain'].get('videos')} videos across "
                            f"{d['brain'].get('channels')} channels")
    if d.get("news"):
        upd["items"].append(f"{d['news']['total']} news headlines")
    d["daily"] = upd

    return d


def main() -> int:
    ap = argparse.ArgumentParser(description="Aggregate outputs into docs/data.json.")
    ap.add_argument("--out", default="docs/data.json")
    args = ap.parse_args()

    data = build()
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(data, indent=2, default=str))

    sections = [k for k in data if k not in ("generated_utc", "daily")]
    print(f"Wrote {dest}  ({dest.stat().st_size:,} bytes)")
    print(f"  sections: {', '.join(sections) if sections else '(none - no data yet)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
