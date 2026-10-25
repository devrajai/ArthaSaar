#!/usr/bin/env python3
"""Turn the 'Chart Patterns - reference' Google Doc into structured JSON for the site.

WHY THIS IS A SCRIPT AND NOT A HAND-WRITTEN JSON: the doc is the source of truth and it
gets edited. Parsing it means the next edit flows through instead of drifting.

The doc's shape is consistent: numbered sections, each introduced by a heading line, then
a tab-separated table whose first row is the column names. We parse that rather than
hard-coding the patterns, so adding a row to the doc adds a row to the site.
"""
import json, os, re, sys
from datetime import datetime, timezone

SRC = "reference/patterns_ref.txt"
OUT = "docs/patterns_reference.json"


def clean(s):
    return re.sub(r"\s+", " ", (s or "")).strip()


def parse(text):
    lines = [l.rstrip() for l in text.split("\n")]
    out = {"updated": "", "source": "Google Doc: Chart Patterns - reference (ArthaSaar)",
           "intro": "", "groups": [], "detection": [], "discipline": [], "note": ""}

    # "Last checked: 2026-10-17"
    m = re.search(r"Last checked:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", text)
    out["updated"] = m.group(1) if m else ""

    # the intro is the paragraph after the Last checked line, before the first section
    body = [l for l in lines if l.strip()]
    for i, l in enumerate(body):
        if l.lower().startswith("last checked"):
            if i + 1 < len(body):
                out["intro"] = clean(body[i + 1])
            break

    section = None
    header = None
    rows = []
    in_detection = False
    in_discipline = False

    def flush():
        nonlocal section, header, rows
        if section and header and rows:
            out["groups"].append({"title": section, "columns": header, "rows": rows})
        section, header, rows = None, None, []

    for raw in lines:
        line = raw.strip()
        if not line or set(line) <= {"_", "-"}:
            continue
        # numbered section heading, e.g. "1. Reversal patterns (trend is ending)"
        m = re.match(r"^(\d+)\.\s+(.*)$", line)
        if m and "\t" not in line and len(line) < 90:
            flush()
            title = clean(m.group(2))
            low = title.lower()
            in_detection = "reading them from data" in low
            in_discipline = "discipline" in low
            if not in_detection and not in_discipline:
                section = title
            continue
        if line.startswith("\u25cf") or line.startswith("•"):
            out["discipline"].append(clean(line.lstrip("\u25cf• ")))
            continue
        if "\t" in line:
            cells = [clean(c) for c in line.split("\t")]
            if in_detection:
                if cells[0].lower() != "pattern":
                    out["detection"].append({"pattern": cells[0],
                                             "hint": cells[1] if len(cells) > 1 else ""})
                continue
            if header is None:
                header = cells
            else:
                rows.append(cells)
            continue
    flush()
    return out


def main():
    if not os.path.exists(SRC):
        print("missing", SRC)
        return 1
    text = open(SRC, encoding="utf-8").read()
    data = parse(text)
    total = sum(len(g["rows"]) for g in data["groups"])
    print("groups:", len(data["groups"]), "| pattern rows:", total,
          "| detection rules:", len(data["detection"]),
          "| discipline points:", len(data["discipline"]))
    for g in data["groups"]:
        print("  %-46s %d rows, cols=%s" % (g["title"][:46], len(g["rows"]), g["columns"]))
    if total < 15:
        print("REFUSING TO WRITE: only %d pattern rows parsed - the doc shape probably "
              "changed. Fix the parser rather than shipping a thin reference." % total)
        return 1
    os.makedirs("docs", exist_ok=True)
    json.dump(data, open(OUT, "w"), ensure_ascii=False)
    print("->", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
