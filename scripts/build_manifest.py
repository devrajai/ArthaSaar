#!/usr/bin/env python3
"""Checksum manifest: a SHA-256 for every published data file.

WHY THIS EXISTS
Anyone can fork this repository. Once they do, their copy drifts - a nightly run rewrites
files, a rebuild changes a number, a stray edit lands. Without a hash there is no way to say
"my copy matches yours" without reading every file.

This publishes, for each file, its SHA-256, its size and its last-modified time. A fork can
run the same script and diff the result: identical hashes mean identical data, and a differing
hash points at the exact file that diverged.

It is also the cheapest honesty feature on the site. Every number on the page traces to a file;
this says what that file actually was.
"""
import hashlib, json, os, sys
from datetime import datetime, timezone

DOCS = "docs"
OUT = os.path.join(DOCS, "manifest.json")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    if not os.path.isdir(DOCS):
        print("no docs/")
        return 1
    files = {}
    total = 0
    for name in sorted(os.listdir(DOCS)):
        if not name.endswith(".json") or name == "manifest.json":
            continue
        p = os.path.join(DOCS, name)
        if not os.path.isfile(p):
            continue
        size = os.path.getsize(p)
        total += size
        files[name] = {
            "sha256": sha256(p),
            "bytes": size,
            "mtime": datetime.fromtimestamp(os.path.getmtime(p), timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "count": len(files),
        "total_bytes": total,
        "algorithm": "sha256",
        "files": files,
        "note": ("A SHA-256 for every published JSON file. Run this same script on a fork and "
                 "compare: identical hashes mean identical data, and a differing hash names "
                 "the exact file that diverged."),
        "cautions": {
            "not_signature": ("A hash proves two copies are identical, not that the data is "
                              "correct or authentic. It detects drift, not dishonesty."),
            "changes_daily": ("Every nightly run rewrites these files, so every hash changes. "
                              "Compare two copies taken at the same time, or compare against "
                              "the committed history."),
        },
    }
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %d files hashed, %.1f MB of data" % (len(files), total / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
