#!/usr/bin/env python3
"""Pull ArthaSaar's published market data into this repo before the Telegram jobs run.

Why this exists
---------------
The Telegram scripts (telegram_brain.py, telegram_alert.py, morning_unified.py) were
written for the ArthaSaar repo and read ArthaSaar's own market data files. This repo
does not produce those files, so without this step the Telegram messages would go out
nearly empty.

This script fetches the published copies from ArthaSaar's public main branch
(raw.githubusercontent.com - no token, no auth) into this repo's data/ directory,
then the Telegram scripts read them exactly as before. Nothing is written back to
ArthaSaar.

Behaviour
---------
* each file is fetched independently; one failure never aborts the run
* if a fetch fails and a local copy already exists, the local copy is kept
* exits 0 either way, so it can never block the Telegram job

Usage: python3 scripts/fetch_arthasaar_data.py
"""
import os
import sys
import urllib.request

# Source repo (override with ARTHASAAR_REPO=owner/name if it moves).
# If the repo is PRIVATE, set ARTHASAAR_TOKEN (a PAT with repo read) and the API
# fallback below will pull it; without a token a private repo 404s.
REPO = os.environ.get("ARTHASAAR_REPO", "devrajai/ArthaSaar")
BRANCH = os.environ.get("ARTHASAAR_BRANCH", "main")
TOKEN = (os.environ.get("ARTHASAAR_TOKEN")
         or os.environ.get("GH_PAT")
         or os.environ.get("GITHUB_TOKEN"))
SRC = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/data/{{}}.json"
API = f"https://api.github.com/repos/{REPO}/contents/data/{{}}.json"

# every data file the ported Telegram scripts read
FILES = [
    "brain-screener", "breadth", "events", "fii-dii", "fii-history", "futures",
    "global", "gti", "indices-all", "mf-top", "mood", "oi-gti", "preopen",
    "radar", "smart-brain", "timesfm_forecasts",
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")


def _headers(accept=None):
    h = {"User-Agent": "market-data-hub-fetch"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    if accept:
        h["Accept"] = accept
    return h


def fetch(name):
    """Try the raw URL first, then the GitHub contents API (needed for private repos)."""
    try:
        req = urllib.request.Request(SRC.format(name), headers=_headers())
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()
    except Exception:
        req = urllib.request.Request(API.format(name),
                                     headers=_headers("application/vnd.github.raw"))
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read()


def main():
    os.makedirs(DATA, exist_ok=True)
    ok = fresh = kept = 0
    for name in FILES:
        dest = os.path.join(DATA, name + ".json")
        try:
            body = fetch(name)
            with open(dest, "wb") as f:
                f.write(body)
            ok += 1
            fresh += 1
            print("  fetched %-20s %6d bytes" % (name, len(body)))
        except Exception as e:
            if os.path.exists(dest):
                kept += 1
                print("  kept local %-18s (%s)" % (name, type(e).__name__))
            else:
                print("  MISSING %-20s (%s)" % (name, type(e).__name__))
    print("arthasaar data: %d fetched, %d kept local, of %d" % (fresh, kept, len(FILES)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
