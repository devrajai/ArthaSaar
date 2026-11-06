#!/usr/bin/env python3
"""
ARTHASAAR - data checks (keep the last good version).

Why: the site has twice shown a broken page because one generated file was
missing or bad. This validates every file the app actually loads, and if a file
fails, restores the previously committed copy instead of publishing the bad one.

How it decides what to check: it reads docs/index.html and pulls the CORE and
HEAVY file lists out of it, so the checks stay in sync with the app by
construction - no second list to forget to update.

Output: docs/data_health.json  (what the site can show as "as of" + per-file state)

Usage:  python3 scripts/check_data.py [--revert]
        --revert : git checkout -- docs/<file> for files that fail (default on in CI)
"""
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
INDEX = DOCS / "index.html"

# Files where a small row count is normal, and files where it is a red flag.
MIN_ROWS = {
    "universe.json": 1000, "stocks.json": 500, "screener.json": 200,
    "indices.json": 20, "sectors.json": 8, "data.json": 1,
    "history.json": 500, "charts.json": 20, "series.json": 100,
    "delivery.json": 200, "rollover.json": 20, "circuits.json": 1,
    "fo_ban.json": 0, "sebi.json": 1, "news.json": 5, "events.json": 1,
    "sector_rotation.json": 5, "corp_actions.json": 5, "rebalance.json": 10,
    "circulars.json": 10, "filings.json": 10,
}
# Hours before a file counts as stale. Weekends make this generous on purpose.
MAX_AGE_H = {
    "data.json": 96, "universe.json": 96, "stocks.json": 96, "screener.json": 96,
    "history.json": 96, "delivery.json": 96, "rollover.json": 96, "circuits.json": 96,
    "fo_ban.json": 96, "sebi.json": 120, "news.json": 48, "events.json": 120,
}
STATIC = {"charges.json","learn.json","config.json","patterns_reference.json"}
DEFAULT_MIN_ROWS = 1
DEFAULT_MAX_AGE_H = 96
# Files that are allowed to be absent (optional extras).
OPTIONAL = {"ipo_doc.json", "patterns_reference.json", "whatif.json", "cases.json",
            "muhurat.json", "weekday.json", "scenarios.json", "presentations.json"}


def app_file_lists():
    """Pull CORE and HEAVY arrays straight out of the app."""
    try:
        s = INDEX.read_text(encoding="utf-8", errors="replace")
    except Exception as e:  # noqa: BLE001
        print("cannot read index.html:", e)
        return []
    names = set()
    for arr in ("CORE", "HEAVY"):
        m = re.search(arr + r"\s*=\s*\[([^\]]{0,6000})\]", s)
        if m:
            names.update(re.findall(r'"([a-z0-9_]+\.json)"', m.group(1)))
    if not names:  # fallback: every .json the page mentions
        names.update(re.findall(r'"([a-z0-9_]+\.json)"', s))
    return sorted(names)


def row_count(v):
    if isinstance(v, list):
        return len(v)
    if isinstance(v, dict):
        if isinstance(v.get("count"), int):
            return v["count"]
        for k in ("rows", "items", "data", "filings", "symbols", "stocks", "orders", "funds"):
            if isinstance(v.get(k), (list, dict)):
                return len(v[k])
        return 1 if v else 0
    return 0


def stamp(v):
    """Best-effort timestamp from the file's own fields."""
    if not isinstance(v, dict):
        return None
    for k in ("updated", "generated_utc", "u", "date", "as_of", "built_at"):
        t = v.get(k)
        if isinstance(t, str) and t:
            for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z",
                        "%Y-%m-%dT%H:%M:%S", "%d-%m-%Y", "%d %b %Y, %H:%M IST", "%Y-%m-%d"):
                try:
                    d = datetime.strptime(t.replace("Z", "Z"), fmt)
                    return d.replace(tzinfo=d.tzinfo or timezone.utc)
                except Exception:  # noqa: BLE001
                    continue
            try:
                d = datetime.fromisoformat(t.replace("Z", "+00:00"))
                return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
            except Exception:  # noqa: BLE001
                pass
    return None


def check(name):
    p = DOCS / name
    rec = {"file": name, "ok": False, "state": "", "rows": None, "age_h": None}
    if not p.exists():
        rec["state"] = "missing"
        return rec
    try:
        v = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:  # noqa: BLE001
        rec["state"] = "bad json: " + str(e)[:60]
        return rec
    rows = row_count(v)
    rec["rows"] = rows
    need = MIN_ROWS.get(name, DEFAULT_MIN_ROWS)
    if rows < need:
        rec["state"] = f"too few rows ({rows} < {need})"
        return rec
    st = stamp(v)
    if st and name not in STATIC:
        age = (datetime.now(timezone.utc) - st).total_seconds() / 3600
        rec["age_h"] = round(age, 1)
        lim = MAX_AGE_H.get(name, DEFAULT_MAX_AGE_H)
        if age > lim:
            rec["state"] = f"stale ({age:.0f}h > {lim}h)"
            return rec
    rec["ok"] = True
    rec["state"] = "ok"
    return rec


def revert(name):
    try:
        subprocess.run(["git", "checkout", "--", f"docs/{name}"], cwd=ROOT,
                       check=True, capture_output=True)
        return True
    except Exception:  # noqa: BLE001
        return False


def main():
    do_revert = "--revert" in sys.argv
    names = app_file_lists()
    print(f"checking {len(names)} files the app loads")
    out, bad = [], []
    for n in names:
        r = check(n)
        if not r["ok"]:
            if n in OPTIONAL and r["state"] == "missing":
                r["state"] = "optional, absent"
                r["ok"] = True
            else:
                bad.append(r)
                if do_revert:
                    r["reverted"] = revert(n)
        out.append(r)
    health = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "checked": len(out),
        "failed": len(bad),
        "files": out,
        "note": ("Every file the app loads, checked for presence, JSON validity, a minimum "
                 "row count and a maximum age. A file that fails is restored from the last "
                 "committed copy rather than published, so a bad pipeline run cannot take the "
                 "site down."),
    }
    (DOCS / "data_health.json").write_text(json.dumps(health, separators=(",", ":")), encoding="utf-8")
    for r in bad:
        print(f"  FAIL {r['file']}: {r['state']}" + (" (reverted)" if r.get("reverted") else ""))
    print(f"done: {len(out)-len(bad)}/{len(out)} ok")


if __name__ == "__main__":
    main()
