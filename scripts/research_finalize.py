#!/usr/bin/env python3
"""Finalize Research Radar metadata after the final data-health pass."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

def load(name, default):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:
        return default

def main():
    radar = load("research-radar.json", {})
    health = load("data-health.json", {})
    now = datetime.now(timezone.utc).isoformat()
    ds = radar.setdefault("daily_status", {})
    ds["finalized_at"] = now
    ds["data_health_updated"] = health.get("updated")
    ds["data_health_healthy"] = bool(health.get("healthy"))
    ds["data_health_summary"] = health.get("summary") or {}
    feature = (radar.setdefault("features", {})).setdefault("data_resilience", {})
    feature["health_updated"] = health.get("updated")
    feature["summary"] = health.get("summary") or {}
    detail = radar["features"].setdefault("data_resilience_detail", {})
    detail["health_summary"] = health.get("summary") or {}
    detail["health_updated"] = health.get("updated")
    (DATA / "research-radar.json").write_text(json.dumps(radar, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print("Research Radar finalized:", ds.get("data_health_updated"), ds.get("data_health_summary"))

if __name__ == "__main__":
    main()
