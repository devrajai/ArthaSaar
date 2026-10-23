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
from datetime import datetime, timezone

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
    """Return (should_run, reason).

    There is no docs/quality.json. The pipeline writes its quality block INSIDE
    docs/data.json as {"rows":..,"symbols":..,"errors":..,"warnings":..}, and the first
    version of this looked for a file that does not exist - so the gate never found
    anything and defaulted to RUN, which would have fired a task every day whether or not
    anything was wrong. This reads what is actually there.

    Only checks feeds that should ALWAYS carry data. Seasonality, deals and shareholding
    are legitimately empty when their sources are unavailable, and flagging those would
    fire a task every day forever.
    """
    problems = []
    try:
        d = json.load(open("docs/data.json"))
    except Exception:
        return True, "docs/data.json is missing - the pipeline may not be running at all"

    # 1. is the pipeline itself fresh?
    gen = str(d.get("generated_utc") or "")
    if not gen:
        problems.append("data.json has no timestamp")
    else:
        try:
            t = datetime.strptime(gen, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            age_h = (datetime.now(timezone.utc) - t).total_seconds() / 3600.0
            if age_h > 26:
                problems.append("data.json is %.0f hours old" % age_h)
        except Exception:
            problems.append("data.json timestamp is unreadable")

    # 2. the pipeline's own quality block
    q = d.get("quality")
    if isinstance(q, dict):
        errs = q.get("errors") or 0
        if errs:
            problems.append("%d quality error(s)" % errs)

    # 3. feeds that should always have rows
    ALWAYS = [("docs/stocks.json", "count"), ("docs/indices.json", "count"),
              ("docs/mf.json", "count"), ("docs/rs.json", "count"),
              ("docs/correlation.json", "count"), ("docs/calendar.json", "count")]
    for path, key in ALWAYS:
        try:
            j = json.load(open(path))
        except Exception:
            problems.append("%s is missing" % path.split("/")[-1])
            continue
        if (j.get(key) or 0) == 0:
            problems.append("%s has 0 rows" % path.split("/")[-1])

    if problems:
        return True, "; ".join(problems[:6])
    return False, "data.json is fresh, no quality errors, and every always-on feed has rows"


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
