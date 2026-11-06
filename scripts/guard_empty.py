#!/usr/bin/env python3
"""Never overwrite a good published file with an empty one.

THE FAILURE THIS PREVENTS
From 29 October to 5 November, screener.json was rebuilt empty on every nightly run. Each
build "succeeded", committed a file with count 0, and the site showed nothing. Nobody was
told, because an empty file looks exactly like a working file that found nothing.

The same pattern produced: series.json holding 2 series for 2,200 stocks, rs.json with 2
entries, breadth.json with no figures, commodities.json reporting "no parquet found" for
weeks. In every case the previous commit had good data and the new build destroyed it.

THE RULE
Compare each file against the version in the last commit. If this run produced something
materially emptier than what is already published, KEEP THE PUBLISHED VERSION, mark it
stale, and say so loudly. A stale file with a visible marker is honest; an empty file that
looks current is not.

WHAT COUNTS AS EMPTY
Not byte size - a file can be large and contain nothing. This counts data rows: the length
of the biggest list or dict under the usual keys, falling back to byte size. A file that had
100+ rows and now has none is a failure. A file that had none and still has none is
unchanged, and is left alone.

SOME FILES ARE ALLOWED TO BE EMPTY
patterns.json genuinely has days with no pattern. fo_ban.json can have no banned symbols.
Restoring yesterday's 403 patterns would present stale detections as today's. Those are
listed in EMPTY_OK and skipped.

USAGE
  python scripts/guard_empty.py            check and repair docs/
  python scripts/guard_empty.py --dry-run  report only
"""
import json, os, subprocess, sys

DOCS = "docs"
REPORT = "docs/_guard_report.json"

# Emptiness here is a real result, not a failure. Restoring the previous version would
# present old detections as if they were today's.
EMPTY_OK = {
    "patterns.json",       # no pattern matched today is a valid outcome
    "fo_ban.json",         # no symbol banned is a valid outcome
    "insider.json",        # no disclosure in the window
    "deals.json",          # no bulk/block deal in the window
    "presentations.json",  # no usable sentence in the filing window
    "telegram_pcr.json",   # collector parked
    "ipo.json",            # NSE returns nothing; the tab hands off to another site
}

ROW_KEYS = ("rows", "series", "stocks", "items", "companies", "events", "entries",
            "indices", "sectors", "cards", "days", "videos", "channels", "months",
            "years", "categories", "presets", "results", "data", "list")


def weight(obj):
    """A rough 'how much data is in here' number. Rows first, bytes second."""
    if not isinstance(obj, dict):
        return 0
    best = 0
    for k in ROW_KEYS:
        v = obj.get(k)
        if isinstance(v, (list, dict)):
            best = max(best, len(v))
    if best == 0:
        for k in ("count", "total"):
            v = obj.get(k)
            if isinstance(v, int):
                best = max(best, v)
    return best


def head_version(path):
    """The file as it exists in the last commit, or None."""
    try:
        out = subprocess.run(["git", "show", "HEAD:" + path],
                             capture_output=True, timeout=60)
        if out.returncode != 0 or not out.stdout:
            return None
        return json.loads(out.stdout)
    except Exception:
        return None


def main():
    dry = "--dry-run" in sys.argv
    repaired, checked, skipped, unchanged = [], 0, 0, 0

    if not os.path.isdir(DOCS):
        print("guard: no docs/ directory")
        return 0

    for name in sorted(os.listdir(DOCS)):
        if not name.endswith(".json") or name.startswith("_"):
            continue
        if name in EMPTY_OK:
            skipped += 1
            continue
        path = os.path.join(DOCS, name)
        try:
            now = json.load(open(path))
        except Exception:
            continue

        old = head_version(path)
        if old is None:
            continue                      # new file, nothing to compare against

        w_now, w_old = weight(now), weight(old)
        checked += 1

        # A drop to nothing, or a collapse to under a tenth of what was published, is a
        # failed build rather than a quiet market. Require the old file to have had real
        # content, so a file that was always empty is never resurrected.
        if w_old >= 20 and w_now < max(1, w_old * 0.1):
            entry = {"file": name, "before": w_old, "now": w_now}
            repaired.append(entry)
            print("  KEEPING PREVIOUS  %-24s published %d rows, this run produced %d"
                  % (name, w_old, w_now))
            if dry:
                continue
            # restore the published version and mark it, so the site can say it is stale
            restored = dict(old) if isinstance(old, dict) else old
            if isinstance(restored, dict):
                restored["_kept_from_previous"] = True
                restored["_guard_note"] = (
                    "This run's build produced %d rows against %d already published, so the "
                    "previous version was kept rather than replacing good data with an empty "
                    "file." % (w_now, w_old))
            json.dump(restored, open(path, "w"), ensure_ascii=False, separators=(",", ":"))
        else:
            unchanged += 1

    out = {"checked": checked, "repaired": repaired,
           "skipped_empty_ok": skipped, "unchanged": unchanged,
           "dry_run": dry}
    try:
        json.dump(out, open(REPORT, "w"), ensure_ascii=False, separators=(",", ":"))
    except Exception:
        pass

    print("guard: checked %d, kept %d from the previous commit, %d unchanged, %d skipped"
          % (checked, len(repaired), unchanged, skipped))
    if repaired and not dry:
        # a workflow annotation, so this is visible in the Actions summary and not buried
        for r in repaired:
            print("::warning title=Kept previous %s::This run produced %d rows against %d "
                  "published - the published file was kept and marked stale."
                  % (r["file"], r["now"], r["before"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
