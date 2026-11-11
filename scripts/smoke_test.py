#!/usr/bin/env python3
"""
ARTHASAAR - smoke test for the published data.

Catches the failures a reader actually notices: a card with nothing in it, a home
page whose numbers come from different days, and a trading session that never
landed. Runs in CI; exits non-zero so the build is flagged.

Checks
  1. home_facts.json exists, has a session date, and carries every headline fact.
  2. No fact is older than the session (home page mixing days).
  3. The price data reaches the newest session the gap checker knows about.
  4. No *weekday* session is missing (weekends can be Muhurat and are listed
     separately, so they warn rather than fail).

Usage: python3 scripts/smoke_test.py [--warn-only]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
REQUIRED = ("nifty", "vix", "breadth", "fii", "dii", "pcr", "max_pain")


def load(name):
    p = DOCS / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def main():
    warn_only = "--warn-only" in sys.argv
    fails, warns = [], []

    hf = load("home_facts.json")
    if not hf:
        fails.append("home_facts.json missing - the home page has no single snapshot")
    else:
        if not hf.get("asof"):
            fails.append("home_facts.json has no session date")
        facts = hf.get("facts") or {}
        for k in REQUIRED:
            v = facts.get(k)
            if not v or v.get("v") in (None, ""):
                fails.append(f"home fact '{k}' is empty")
        if hf.get("stale"):
            names = ", ".join(s.get("fact", "?") for s in hf["stale"])
            fails.append(f"home page mixes dates - older than the session: {names}")
        cov = hf.get("coverage") or {}
        if cov.get("behind"):
            warns.append("price history is behind the recap session")
        if cov.get("history_last") and cov.get("recap_last") and cov["history_last"] < cov["recap_last"]:
            warns.append(f"history.json stops at {cov['history_last']} but the recap reaches {cov['recap_last']}")

    g = load("data_gaps.json")
    if not g:
        warns.append("data_gaps.json missing - run scripts/gap_detector.py")
    else:
        for gap in g.get("gaps") or []:
            d = gap.get("date", "")
            wd = gap.get("weekday", "")
            if wd in ("Sat", "Sun"):
                warns.append(f"special session missing: {d} ({wd})")
            else:
                fails.append(f"trading day missing: {d} ({wd})")

    for f in fails:
        print("FAIL:", f)
    for w in warns:
        print("WARN:", w)
    if not fails and not warns:
        print("smoke: all good")

    if fails and not warn_only:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
