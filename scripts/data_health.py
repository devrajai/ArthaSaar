#!/usr/bin/env python3
"""
Validate ArthaSaar hosted data snapshots.

This never calls paid APIs. It only checks the repository's committed JSON
snapshots against data/source-registry.json and writes data/data-health.json.
"""
import json
from datetime import datetime, timezone
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
    s = str(v).replace("Z", "+00:00")
    try:
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d
    except Exception:
        return None


def main():
    reg = parse_json(REG) or {"feeds": []}
    now = datetime.now(timezone.utc)
    results = []

    for f in reg.get("feeds", []):
        fid = f.get("id", "")
        path = f.get("file", "")
        if "<SYMBOL>" in path:
            path = "data/history-index.json"
        rel = path[5:] if path.startswith("data/") else path
        p = ROOT / "data" / rel if not path.startswith("data/") else ROOT / path
        obj = parse_json(p) if p.exists() else None
        updated = ts_of(obj)
        dt = parse_ts(updated)
        age_h = round((now - dt).total_seconds() / 3600, 1) if dt else None
        max_age = float(f.get("max_age_hours", 72))
        if not p.exists():
            status = "missing"
        elif obj is None:
            status = "invalid"
        elif dt is None and "history" not in fid:
            status = "unknown"
        elif age_h is not None and age_h > max_age:
            status = "stale"
        else:
            status = "ok"

        coverage = f.get("coverage", "—")
        if fid == "nse-index-history" and isinstance(obj, dict):
            coverage = f'{len(obj.get("indices", {}))} indices'
        if fid == "yahoo-history" and isinstance(obj, dict):
            coverage = f'{obj.get("count", 0)} symbol histories'
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
