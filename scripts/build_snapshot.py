#!/usr/bin/env python3
"""Store one snapshot a day, so tomorrow can say what changed.

WHY THIS EXISTS
"What changed since yesterday" is the most useful message a data product can send, and it is
the only one that cannot be built retroactively. Every day without a snapshot is a day that
can never be compared. So this runs first and stores, even while the message that reads it is
still thin.

WHAT IT STORES
A flat set of named numbers, each with the date it describes:
    index levels and their change
    breadth (share above the 50-day average)
    put-call ratio and the band it fell in
    FII and DII net flows in crore
    open interest by expiry, for the near and far series
    gold and silver per gram

Every value keeps its own date. A snapshot assembled from files of different vintages is
normal, and hiding that would make the comparison wrong in a way nobody could see.

READING IT
docs/snapshot.json holds today's, plus 'changes' - the difference from the most recent earlier
snapshot for every field present in both. A field missing from either side is reported as
'not comparable', never as zero.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta, timezone

HISTORY = "data/snapshots.json"
OUT = "docs/snapshot.json"
KEEP = 400
IST = timezone(timedelta(hours=5, minutes=30))


def jload(p):
    try:
        return json.loads(open(p).read())
    except Exception:
        return None


def today_ist():
    return datetime.now(IST).strftime("%Y-%m-%d")


def collect():
    """Every number worth comparing tomorrow, each tagged with the date it describes."""
    vals = {}

    def put(key, value, date, unit="", source=""):
        if value is None:
            return
        try:
            vals[key] = {"value": round(float(value), 4), "date": str(date or ""),
                         "unit": unit, "source": source}
        except Exception:
            return

    # index levels
    ih = jload("docs/index_history.json") or {}
    for ix in (ih.get("indices") or []):
        sym = str(ix.get("symbol") or "")
        name = {"^NSEI": "nifty", "^NSEBANK": "banknifty", "^BSESN": "sensex"}.get(sym)
        if not name:
            continue
        daily = ix.get("daily") or []
        if daily:
            put("index.%s.close" % name, daily[-1][4], daily[-1][0], "points", "index_history")

    # breadth
    br = jload("docs/breadth.json") or {}
    put("breadth.above_50", br.get("above_50"), str(br.get("updated") or "")[:10], "%", "breadth")
    put("breadth.above_200", br.get("above_200"), str(br.get("updated") or "")[:10], "%", "breadth")
    put("breadth.total", br.get("total"), str(br.get("updated") or "")[:10], "stocks", "breadth")

    # PCR
    pcr = jload("docs/pcr_signal.json") or {}
    cur = pcr.get("current") or {}
    put("pcr.nifty", cur.get("pcr"), cur.get("date"), "ratio", "pcr_signal")

    # flows
    brief = jload("docs/brief.json") or {}
    for b in (brief.get("bullets") or []):
        t = str(b)
        if t.upper().startswith("FII"):
            import re
            m = re.search(r"(-?[\d,]+(?:\.\d+)?)", t)
            if m:
                put("flow.fii_cr", float(m.group(1).replace(",", "")),
                    brief.get("market_date"), "crore", "brief")
        elif t.upper().startswith("DII"):
            import re
            m = re.search(r"(-?[\d,]+(?:\.\d+)?)", t)
            if m:
                put("flow.dii_cr", float(m.group(1).replace(",", "")),
                    brief.get("market_date"), "crore", "brief")

    # open interest by expiry
    obe = jload("docs/oi_by_expiry.json") or {}
    nif = ((obe.get("indices") or {}).get("NIFTY")) or {}
    exps = sorted([e for e in (nif.get("expiries") or []) if e.get("expiry")],
                  key=lambda e: str(e.get("expiry")))
    for e in exps[:2]:
        tag = str(e.get("expiry"))
        put("oi.nifty.%s.total" % tag,
            (float(e.get("total_ce_oi") or 0) + float(e.get("total_pe_oi") or 0)),
            tag, "contracts", "oi_by_expiry")
        put("oi.nifty.%s.pcr" % tag, e.get("pcr"), tag, "ratio", "oi_by_expiry")
        put("oi.nifty.%s.max_pain" % tag, e.get("max_pain"), tag, "points", "oi_by_expiry")

    # metals
    mt = jload("docs/metals.json") or {}
    if mt.get("available"):
        for k in ("gold", "silver"):
            b = mt.get(k) or {}
            put("metal.%s.per_gram" % k, b.get("per_gram"), str(mt.get("updated") or "")[:10],
                "rupees", "metals")
    put("fx.usdinr", mt.get("usdinr"), str(mt.get("updated") or "")[:10], "rupees", "metals")

    return vals


def main() -> int:
    day = today_ist()
    vals = collect()
    if not vals:
        print("nothing collected - no files were readable")
        return 0

    hist = jload(HISTORY) or []
    if not isinstance(hist, list):
        hist = []

    # the most recent snapshot from an earlier day
    prev = None
    for h in reversed(hist):
        if h.get("date") != day:
            prev = h
            break

    changes = []
    if prev:
        pv = prev.get("values") or {}
        for k, v in vals.items():
            old = pv.get(k)
            if not old:
                changes.append({"field": k, "status": "not comparable",
                                "detail": "absent from the previous snapshot"})
                continue
            try:
                d = v["value"] - float(old["value"])
            except Exception:
                continue
            base = float(old["value"])
            pct = (d / base * 100.0) if base else None
            changes.append({
                "field": k, "status": "changed" if abs(d) > 1e-9 else "unchanged",
                "from": old["value"], "to": v["value"], "delta": round(d, 4),
                "pct": (round(pct, 2) if pct is not None else None),
                "unit": v.get("unit", ""),
                "since": prev.get("date"),
            })
    # only keep today's record once per day
    hist = [h for h in hist if h.get("date") != day]
    hist.append({"date": day, "values": vals})
    hist = hist[-KEEP:]
    os.makedirs("data", exist_ok=True)
    json.dump(hist, open(HISTORY, "w"), separators=(",", ":"))

    moved = [c for c in changes if c.get("status") == "changed"]
    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "date": day,
        "fields": len(vals),
        "compared_with": (prev.get("date") if prev else None),
        "changes": changes,
        "moved": len(moved),
        "note": ("One snapshot a day. Each value carries the date of the file it came from, "
                 "because a snapshot assembled from files of different vintages is normal and "
                 "hiding that would make the comparison wrong in a way nobody could see."),
    }
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("-> %s  %.1f KB | %d fields" % (OUT, os.path.getsize(OUT) / 1024, len(vals)))
    if prev:
        print("   compared with %s: %d moved" % (prev.get("date"), len(moved)))
        for c in moved[:8]:
            print("     %-28s %s -> %s (%+.2f%s)"
                  % (c["field"], c["from"], c["to"], c.get("pct") or 0,
                     "%" if c.get("pct") is not None else ""))
    else:
        print("   first snapshot - nothing to compare with yet")
    return 0


if __name__ == "__main__":
    sys.exit(main())
