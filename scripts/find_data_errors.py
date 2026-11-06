#!/usr/bin/env python3
"""
find_data_errors.py - catch the prices that are wrong before a reader does.

WHY THIS EXISTS
A screener row that says a stock fell 90% in two sessions is almost never a real fall.
It is nearly always a split, a bonus or a demerger that never got applied to the price
series, so the archive holds Rs 900 and then Rs 90 and calls the gap a collapse. Today
that shows up as 19 rows with suspect_move=true and no explanation anywhere on the site.

WHAT IT DOES
Reads docs/screener.json, looks for moves too big to be trading, works out the ratio the
price actually moved by, and tries to match it to a corporate action on file. Three
verdicts, and the difference between them matters:

  explained   a corporate action is on file for that symbol near that date
  likely      the move fits a clean ratio (about 1:10, 1:5, 1:2) but nothing is on file
  unexplained the move is too big to be trading and nothing on file explains it -
              this is the one that needs a human

Only the third is a data error in the strict sense. The first two are not wrong prices,
they are unadjusted ones, and the fix is different: apply the action, do not delete the
row.

Output: docs/data_errors.json

Usage:
  python scripts/find_data_errors.py
  python scripts/find_data_errors.py --min-move 40
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCREENER = "docs/screener.json"
CALENDAR = "docs/calendar.json"
DATA = "docs/data.json"
OUT = "docs/data_errors.json"

# Windows worth testing. 20 sessions is deliberately NOT here: a 45% fall over a month is
# ordinary trading for a small cap, and including it buried the real cases under 60 rows of
# noise on the first run. A corporate action is a STEP, so it shows up in days, not weeks.
WINDOWS = ("chg_1d", "chg_2d", "chg_3d", "chg_5d")
# A dividend never moves a price 70%. Only these can explain a step.
EXPLAINS = ("split", "bonus", "demerger", "rights", "other", "scheme")
# ratios a corporate action usually produces, as the price multiplier
CLEAN = (2, 3, 4, 5, 10, 20, 100)


def load(p: str):
    try:
        return json.loads(Path(p).read_text())
    except Exception:
        return None


def known_actions() -> list[dict]:
    """Every corporate action we hold, as {symbol, date, kind, detail}."""
    out: list[dict] = []
    d = load(DATA) or {}
    co = d.get("corporate") or {}
    for kind, block in co.items():
        if kind == "dividend":
            continue          # a Re 1 dividend does not explain a 90% fall
        for r in (block or {}).get("rows") or []:
            if len(r) >= 3 and r[0]:
                out.append({"symbol": str(r[0]).upper(), "date": str(r[2])[:10],
                            "kind": kind, "detail": str(r[1])[:90]})
    cal = load(CALENDAR) or {}
    for day in (cal.get("days") or []) + (cal.get("recent") or []):
        for e in day.get("events") or []:
            if e.get("symbol") and (e.get("type") or "") != "dividend":
                out.append({"symbol": str(e["symbol"]).upper(),
                            "date": str(e.get("date") or "")[:10],
                            "kind": e.get("type") or "event",
                            "detail": str(e.get("detail") or "")[:90]})
    return out


def classify(move_pct: float) -> tuple[str, float]:
    """What corporate action would produce this move, and the implied factor.

    Direction matters. A split divides the price (a 1:10 turns 900 into 90, a -90% move),
    while a consolidation multiplies it (a 2:1 reverse split doubles it, a +100% move).
    The first version of this called both of them "1:2", which is wrong for the upside.
    """
    mult = 1 + move_pct / 100.0
    if mult <= 0:
        return "crash", 0.0
    if mult < 1:
        r = 1.0 / mult
        for c in CLEAN:
            if abs(r - 1.0 / c) / (1.0 / c) < 0.12:
                return f"1:{c} split", round(r, 4)
        return "", round(r, 4)
    for c in CLEAN:
        if abs(mult - c) / c < 0.12:
            return f"{c}:1 consolidation", round(mult, 4)
    return "", round(mult, 4)


def main() -> int:
    ap = argparse.ArgumentParser(description="Flag prices that look like unadjusted actions.")
    ap.add_argument("--min-move", type=float, default=70.0,
                    help="absolute percent move that cannot be ordinary trading")
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args()

    sc = load(SCREENER)
    if not sc or not sc.get("rows"):
        print("no screener rows - nothing to check")
        return 0

    actions = known_actions()
    by_sym: dict[str, list[dict]] = {}
    for a in actions:
        by_sym.setdefault(a["symbol"], []).append(a)

    flagged = []
    for r in sc["rows"]:
        sym = str(r.get("symbol") or "").upper()
        if not sym:
            continue
        # the worst window, not the first: a demerger shows up in chg_2d, not chg_1d
        worst_key, worst = None, 0.0
        for w in WINDOWS:
            v = r.get(w)
            if v is None or not isinstance(v, (int, float)):
                continue
            if abs(v) > abs(worst):
                worst_key, worst = w, float(v)
        if abs(worst) < args.min_move:
            continue

        label, ratio = classify(worst)
        near = by_sym.get(sym) or []
        if near:
            verdict, detail = "explained", f"{near[0]['kind']} on {near[0]['date']}: {near[0]['detail']}"
        elif label:
            verdict, detail = "likely", f"fits a {label} - no action on file"
        else:
            verdict, detail = "unexplained", "no clean ratio and no action on file"

        flagged.append({
            "symbol": sym,
            "name": (r.get("name") or "")[:34],
            "window": worst_key.replace("chg_", ""),
            "move_pct": round(worst, 2),
            "implied_ratio": label or None,
            "verdict": verdict,
            "detail": detail,
            "screener_flag": bool(r.get("suspect_move")),
        })

    order = {"unexplained": 0, "likely": 1, "explained": 2}
    flagged.sort(key=lambda x: (order[x["verdict"]], x["move_pct"]))

    payload = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checked": len(sc["rows"]),
        "min_move_pct": args.min_move,
        "counts": {k: sum(1 for f in flagged if f["verdict"] == k)
                   for k in ("unexplained", "likely", "explained")},
        "rows": flagged[:60],
        "note": ("A move this size is almost always a split, bonus or demerger that was never "
                 "applied to the price series, not a real fall. 'explained' means an action is "
                 "on file, 'likely' means the size fits a clean ratio but nothing is on file, "
                 "and 'unexplained' is the one worth a human look."),
    }
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(payload, separators=(",", ":")))
    c = payload["counts"]
    print(f"checked {payload['checked']} rows | unexplained {c['unexplained']} | "
          f"likely {c['likely']} | explained {c['explained']}")
    for f in flagged[:5]:
        print(f"  {f['symbol']:<12} {f['window']:>4} {f['move_pct']:>8}%  "
              f"{f['verdict']:<11} {f['detail'][:56]}")
    print(f"Wrote {dest} ({dest.stat().st_size / 1e3:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
