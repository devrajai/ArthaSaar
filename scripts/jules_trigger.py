#!/usr/bin/env python3
"""Start a Jules session from CI (the Jules API, alpha).

WHY THIS EXISTS
---------------
Jules can be triggered from a GitHub Action instead of only from its web UI. That buys one
thing the UI cannot do: a CONDITION. The UI fires on a calendar; this fires when there is
actually something to do.

The intended use is the daily quality pass - read docs/quality.json, and only wake Jules if
a feed is amber or red. A task that runs every day whether or not anything is wrong is just
a daily PR to review.

THE KEY
-------
JULES_API_KEY must be a repository secret. It is NEVER read from a file and never printed.
Google disables any Jules key it finds publicly exposed, and this repo is public - so an
inlined key would be scraped and dead within hours.

Exit codes: 0 = fine (including "nothing to do" and "no key configured").
A missing key is a configuration step, not a failure, so the workflow must not go red.
"""
import json, os, sys, urllib.request, urllib.error

API = "https://jules.googleapis.com/v1alpha"
OWNER = os.environ.get("REPO_OWNER", "devrajai")
REPO = os.environ.get("REPO_NAME", "ArthaSaar")
BRANCH = os.environ.get("BASE_BRANCH", "main")
KEY = os.environ.get("JULES_API_KEY", "").strip()
DRY = "--dry" in sys.argv


def call(path, payload=None, method="GET"):
    url = API + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    # The docs use X-Goog-Api-Key; accept either spelling on the way in, send this one.
    req.add_header("X-Goog-Api-Key", KEY)
    if data:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=60) as r:
        body = r.read().decode("utf-8", "replace")
    return json.loads(body) if body.strip() else {}


def quality_gate():
    """Return (should_run, reason). Only wake Jules when something is actually wrong."""
    try:
        q = json.load(open("docs/quality.json"))
    except Exception:
        return True, "no quality report found, so running unconditionally"
    rows = q.get("rows") or q.get("feeds") or []
    bad = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        status = str(r.get("status") or r.get("state") or "").lower()
        if status in ("red", "amber", "fail", "failed", "stale"):
            bad.append(str(r.get("feed") or r.get("name") or "?"))
    if bad:
        return True, "quality report flags: " + ", ".join(bad[:6])
    if rows:
        return False, "every feed in the quality report is green"
    return True, "quality report carried no feed rows"


PROMPT = """Read docs/quality.json and docs/quality.md, and the pipeline logs for the most
recent run.

A feed is flagged as: {reason}

Your job is to fix THAT SPECIFIC FEED.

1. Find why it stopped working - run the fetcher locally and read the error.
2. Find a working FREE alternative endpoint or a more robust parse.
3. Update only that fetcher and its pipeline step.
4. If no free source can be found, make the fetcher fail honestly: it must write its JSON
   with a `note` field explaining the source is unavailable, and the tab must display that
   note. Never substitute a guessed or stale value.

Constraints, which are not negotiable:
- Free data sources only. No API keys. No paid services.
- The script must keep the `os._exit(rc)` guard if it imports pandas or pyarrow.
- Its pipeline step in .github/workflows/pipeline.yml and scripts/run_pipeline.sh must end
  with `|| true`.
- Plain CSS only in docs/index.html. No color-mix, no backdrop-filter, no CSS nesting.
- If a new JSON file is produced it must be registered in BOTH the CORE/HEAVY loader array
  and the assign() switch in docs/index.html. A file that is generated but never fetched
  shows an empty card with no error - that has already happened here once.

Do the work now and open the PR. Do not stop to ask for plan approval, and do not reply with
a plan alone. If something in this brief is genuinely ambiguous, make the honest choice, say
which choice you made in the PR description, and continue.
"""


def main():
    should, reason = quality_gate()
    print("gate: %s (%s)" % ("RUN" if should else "SKIP", reason))
    if not should:
        print("nothing to fix - not starting a session")
        return 0

    if not KEY:
        # A clean skip. The owner has not added the secret yet; that is a setup step.
        print("JULES_API_KEY is not set - skipping.")
        print("Add it in Settings > Secrets and variables > Actions, then re-run this workflow.")
        return 0

    payload = {
        "prompt": PROMPT.format(reason=reason),
        "title": "Daily quality fix: %s" % reason[:60],
        "sourceContext": {
            "source": "sources/github/%s/%s" % (OWNER, REPO),
            "githubRepoContext": {"startingBranch": BRANCH},
        },
        # Auto-create the PR, and do NOT gate on plan approval. Jules stopped for approval
        # on an earlier batch and never resumed - an unattended trigger cannot afford that.
        "automationMode": "AUTO_CREATE_PR",
        "requirePlanApproval": False,
    }
    if DRY:
        print("[dry run] would POST /sessions with title:", payload["title"])
        print("  source:", payload["sourceContext"]["source"])
        return 0

    try:
        out = call("/sessions", payload, "POST")
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        print("Jules API HTTP %s: %s" % (e.code, detail))
        # 401/403 means the key is wrong or the GitHub app is not installed on this repo -
        # both are setup problems the owner has to fix, not something to fail the cron over.
        return 0
    except Exception as e:
        print("Jules API error: %s" % type(e).__name__)
        return 0

    print("session started:", out.get("id"))
    print("  state:", out.get("state"))
    print("  view:", out.get("url"))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
