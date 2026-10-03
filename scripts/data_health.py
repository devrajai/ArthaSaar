#!/usr/bin/env python3
"""
Validate ArthaSaar hosted data snapshots.

This never calls paid APIs. It only checks the repository's committed JSON
snapshots against data/source-registry.json and writes data/data-health.json.
"""
import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REG = DATA / "source-registry.json"
OUT = DATA / "data-health.json"


def parse_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def ts_of(obj):
    if not isinstance(obj, dict):
        return None
    for k in ("updated", "timestamp", "asof", "generated_at"):
        if obj.get(k):
            return str(obj[k])
    return None


def parse_ts(v):
    if not v:
        return None
    s = " ".join(str(v).strip().split())
    s = s.replace(" IST", "+05:30").replace(" IST.", "+05:30").replace("Z", "+00:00")
    m = re.match(r"^(\d{1,2}) ([A-Za-z]{3}) (\d{4}), (\d{1,2}):(\d{2})(?::(\d{2}))? \+05:30$", s)
    if m:
        try:
            base = datetime.strptime("%s %s %s %s %s %s" % (m.group(1),m.group(2),m.group(3),m.group(4),m.group(5),m.group(6) or "00"), "%d %b %Y %H %M %S")
            return base.replace(tzinfo=timezone(timedelta(hours=5, minutes=30)))
        except Exception:
            pass
    for fmt in ("%d %b %Y, %H:%M %z", "%d %b %Y, %H:%M:%S %z"):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            pass
    try:
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None

def inspect_feed(path):
    items = [x.strip() for x in str(path or "").split(" + ") if x.strip()]
    found = []
    for item in items:
        p = ROOT / item if item.startswith("data/") else ROOT / "data" / item
        if p.is_dir():
            files = list(p.glob("*.json"))
            if files:
                latest = max(fp.stat().st_mtime for fp in files)
                found.append((True, datetime.fromtimestamp(latest, tz=timezone.utc).isoformat(), f"{len(files)} files"))
            continue
        if p.exists():
            obj = parse_json(p)
            found.append((True, ts_of(obj), "file"))
    if not found:
        return False, None, "missing"
    explicit = [x for x in found if x[1]]
    latest = max(explicit, key=lambda x: str(x[1]))[1] if explicit else None
    coverage = ", ".join(sorted(set(x[2] for x in found)))
    return True, latest, coverage

def main():
    reg = parse_json(REG) or {"feeds": []}
    now = datetime.now(timezone.utc)
    results = []

    for f in reg.get("feeds", []):
        fid = f.get("id", "")
        path = f.get("file", "")
        if "<SYMBOL>" in path:
            path = "data/history-index.json"
        exists, updated, inferred_coverage = inspect_feed(path)
        dt = parse_ts(updated)
        age_h = round((now - dt).total_seconds() / 3600, 1) if dt else None
        max_age = float(f.get("max_age_hours", 72))
        if not exists:
            status = "missing"
        elif dt is None and "history" not in fid:
            status = "unknown"
        elif age_h is not None and age_h > max_age:
            status = "stale"
        else:
            status = "ok"

        coverage = f.get("coverage", "—")
        if inferred_coverage not in ("file", "missing") and coverage == "—":
            coverage = inferred_coverage
        if fid == "nse-index-history":
            obj = parse_json(ROOT / "data" / "index-history.json") or {}
            if isinstance(obj, dict):
                val = obj.get("indices", obj.get("history", {}))
                coverage = f"{len(val)} indices" if isinstance(val, dict) else coverage
        if fid == "yahoo-history":
            hp = DATA / "history"
            coverage = f"{sum(1 for _ in hp.glob("*.json"))} symbol history files" if hp.exists() else "missing"
        results.append({
            "id": fid,
            "label": f.get("label", fid),
            "source": f.get("source", ""),
            "file": path,
            "status": status,
            "updated": updated,
            "age_hours": age_h,
            "max_age_hours": max_age,
            "coverage": coverage,
        })

    ok = sum(1 for x in results if x["status"] == "ok")
    problems = [x for x in results if x["status"] in ("missing", "invalid", "stale")]
    out = {
        "updated": now.isoformat(),
        "healthy": not problems,
        "summary": {"total": len(results), "ok": ok, "problems": len(problems)},
        "feeds": results,
    }
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print("data health:", out["summary"])


if __name__ == "__main__":
    main()
