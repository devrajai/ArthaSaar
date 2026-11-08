#!/usr/bin/env python3
"""
ARTHASAAR - make the published price history split-adjusted.

THE BUG THIS FIXES
docs/charts.json holds monthly closes per symbol. When a stock splits, the raw
series steps down by the split ratio and every chart, momentum figure and
backtest that crosses that date is wrong. Measured on the live file before this
existed: HDFCBANK -52.8% in 2025-08 (a 1:2 split) and KOTAKBANK -81.5% in
2026-01 (a 1:5 split) - both the largest month-on-month moves in their own
histories, and both entirely fake.

WHAT IT DOES
For every split in docs/corp_actions.json, divide every monthly close BEFORE the
split month by the ratio, so the series is continuous. Points from the split
month onward are already post-split and are left alone.

IDEMPOTENT
Applied splits are recorded in charts.json under "splits_applied". A rerun skips
them, so the pipeline can run this daily without dividing twice. If build_charts
regenerates the file from scratch the marker disappears and the adjustment is
reapplied - which is correct, because fresh data is unadjusted.

Dividends are NOT applied (that is a total-return series, a different question).
Only splits, which are a pure unit change.

Usage: python3 scripts/adjust_charts.py [--dry-run]
"""
import json
import sys
from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs"
CHARTS = DOCS / "charts.json"
CORP = DOCS / "corp_actions.json"


def max_jump(series):
    """Largest absolute month-on-month move, as a percentage."""
    worst = 0.0
    for i in range(1, len(series)):
        a, b = series[i - 1][1], series[i][1]
        if a and b:
            worst = max(worst, abs(b / a - 1) * 100)
    return worst


def main():
    dry = "--dry-run" in sys.argv
    if not CHARTS.exists():
        print("no charts.json"); return 1
    charts = json.loads(CHARTS.read_text(encoding="utf-8"))
    series = charts.get("series") or {}
    applied = {tuple(x) for x in charts.get("splits_applied", [])}

    splits = []
    if CORP.exists():
        try:
            for it in json.loads(CORP.read_text(encoding="utf-8")).get("items", []):
                if it.get("k") == "split" and it.get("v"):
                    splits.append((it["s"], str(it["d"])[:10], float(it["v"])))
        except Exception as e:  # noqa: BLE001
            print("corp_actions unreadable:", e)

    todo = [s for s in splits if (s[0], s[1], s[2]) not in applied]
    print(f"{len(splits)} splits known, {len(todo)} not yet applied")
    if not todo:
        print("nothing to do")
        return 0

    changed = []
    for sym, date, ratio in todo:
        pts = series.get(sym)
        if not pts or ratio <= 1:
            continue
        month = date[:7]
        before = max_jump(pts)
        n = 0
        for p in pts:
            if p[0] < month:            # strictly before the split month
                p[1] = round(p[1] / ratio, 2)
                n += 1
        after = max_jump(pts)
        changed.append((sym, date, ratio, n, before, after))
        print(f"  {sym:12} 1:{ratio:g} on {date}: {n} months adjusted | "
              f"largest move {before:.1f}% -> {after:.1f}%")

    if dry:
        print("dry run - not writing"); return 0

    charts["splits_applied"] = sorted(applied | {(s[0], s[1], s[2]) for s in todo})
    note = charts.get("note", "")
    add = (" Prices before a split are divided by the split ratio so the series is "
           "continuous; points from the split month on are already post-split. Dividends "
           "are not applied.")
    if "split-adjusted" not in note:
        charts["note"] = (note + add).strip()
    CHARTS.write_text(json.dumps(charts, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {CHARTS} ({CHARTS.stat().st_size/1e6:.2f} MB), {len(changed)} symbols adjusted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
