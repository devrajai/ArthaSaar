#!/usr/bin/env python3
"""
fetch_youtube.py - poll every channel in config/channels.json and record new uploads.

The feed only carries the ~15 latest uploads per channel, so this is a "what's new"
log: on each run it appends any video IDs it hasn't seen before. Run it often (the
daily job does) and you build a complete history over time without an API key.

Usage
-----
  python scripts/fetch_youtube.py
  python scripts/fetch_youtube.py --config config/channels.json --outdir data

Outputs:
  data/youtube/videos.csv              all channels, one row per video (deduped)
  data/youtube/<channel-slug>.csv      per-channel view
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from youtube_source import as_dicts, fetch_channel  # noqa: E402

COLS = ["video_id", "channel_name", "channel_id", "title",
        "published", "updated", "url", "thumbnail", "views", "description", "first_seen"]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "channel"


def _load(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str) if path.exists() else pd.DataFrame(columns=COLS)


def main() -> int:
    ap = argparse.ArgumentParser(description="Poll YouTube channels for new uploads.")
    ap.add_argument("--config", default="config/channels.json")
    ap.add_argument("--outdir", default="data")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text())
    channels = [c for c in cfg.get("channels", []) if c.get("active", True)]
    if not channels:
        print("No active channels in config."); return 0

    outdir = Path(args.outdir) / "youtube"
    outdir.mkdir(parents=True, exist_ok=True)
    combined_path = outdir / "videos.csv"
    combined = _load(combined_path)
    seen = set(combined["video_id"]) if not combined.empty else set()

    total_new = 0
    per_channel: dict[str, int] = {}
    for ch in channels:
        cid = ch["channel_id"]
        name = ch.get("name", cid)
        try:
            title, videos = fetch_channel(cid)
        except Exception as exc:  # noqa: BLE001
            print(f"  {name}: ERROR {type(exc).__name__}: {exc}")
            continue
        rows = as_dicts(videos)
        new = [r for r in rows if r["video_id"] not in seen]
        for r in new:
            r["first_seen"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if new:
            combined = pd.concat([combined, pd.DataFrame(new, columns=COLS)], ignore_index=True)
            seen.update(r["video_id"] for r in new)
        # per-channel snapshot
        pd.DataFrame(rows, columns=[c for c in COLS if c != "first_seen"]).to_csv(
            outdir / f"{_slug(name)}.csv", index=False)
        newest = max((r["published"] for r in rows), default="-")
        print(f"  {name}: {len(rows)} in feed, {len(new)} new  (newest {newest[:10]})")
        total_new += len(new)
        per_channel[name] = len(new)

    if not combined.empty:
        combined = combined.drop_duplicates(subset=["video_id"], keep="first")
        combined = combined.sort_values(["channel_name", "published"], ascending=[True, False])
        combined.to_csv(combined_path, index=False)
    # Machine-readable run summary. The hourly workflow reads `new` and, when it is
    # above zero, triggers the full pipeline - that is the "new video -> collect" link.
    summary = {
        "checked_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "new": int(total_new),
        "total": int(len(combined)),
        "channels_checked": len(channels),
        "new_by_channel": {k: v for k, v in per_channel.items() if v},
    }
    (outdir / "last_run.json").write_text(json.dumps(summary, indent=2))

    print(f"Done. {total_new} new video(s); {len(combined)} total on record.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
