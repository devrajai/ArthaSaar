#!/usr/bin/env python3
"""Parse the 'IpoBodh Daily' Google Doc into the site's IPO section.

WHY: the IPO tab shows open 0 / closed 0 / listed 0 because NSE's IPO endpoints return
nothing usable. Meanwhile a doc in Drive carries the same information in prose, updated
daily. This reads it.

IT IS PROSE, SO THIS PARSES CONSERVATIVELY. Only patterns that are unambiguous get
extracted, and every row records that it came from the doc rather than from NSE. Anything
the regexes cannot read is dropped, not guessed - a wrong subscription multiple is worse
than a missing one.

Input: reference/ipobodh_daily.txt  (the doc's plain text, newest entry LAST)
Output: docs/ipo_doc.json
"""
import json, os, re, sys
from datetime import datetime, timezone

SRC = "reference/ipobodh_daily.txt"
OUT = "docs/ipo_doc.json"

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def latest_entry(text):
    """The doc appends newest last. Entries start with a line like '25 Oct 2026 — IpoBodh Daily'."""
    marks = list(re.finditer(r"^(\d{1,2})\s+([A-Z][a-z]{2})\s+(\d{4})\s*[—-]\s*IpoBodh Daily\s*$",
                             text, re.M))
    if not marks:
        return None, ""
    m = marks[-1]
    body = text[m.end():]
    # cut at the next entry heading if one follows
    nxt = re.search(r"^\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}\s*[—-]\s*IpoBodh Daily\s*$", body, re.M)
    if nxt:
        body = body[:nxt.start()]
    d = "%s-%02d-%02d" % (m.group(3), MONTHS.get(m.group(2), 1), int(m.group(1)))
    return d, body


def band(m):
    """'₹70–75' -> ('70', '75')"""
    if not m:
        return "", ""
    a = m.group(1).replace(",", "")
    b = (m.group(2) or a).replace(",", "")
    return a, b


# Name (₹70–75; 0.69x, GMP ₹3)   |   Name (₹186–196; 1.97x, GMP ₹25)   |   Name (0.86x)
RE_FULL = re.compile(r"([A-Z][A-Za-z&.\- ]{2,44}?)\s*\(\s*₹\s*([\d,]+)\s*[–-]\s*([\d,]+)\s*;\s*"
                     r"([\d.]+)x\s*(?:,\s*GMP\s*₹\s*([\d,]+))?\s*\)")
RE_SUB = re.compile(r"([A-Z][A-Za-z&.\- ]{2,44}?)\s*\(\s*([\d.]+)x\s*\)")
RE_GMP = re.compile(r"([A-Z][A-Za-z&.\- ]{2,44}?)\s*\+\s*([\d.]+)\s*%")
RE_SIZE = re.compile(r"([A-Z][A-Za-z&.\- ]{2,44}?)\s*\(\s*₹\s*([\d,]+)\s*(Cr|crore)\s*\)", re.I)


def parse(body, as_of):
    out = {"as_of": as_of, "open": [], "upcoming": [], "movers": [], "note": ""}
    seen = set()

    def add(bucket, name, **kw):
        name = re.sub(r"\s+", " ", name).strip(" ,.;:")
        # "Safex Chemicals (Rs 450 Cr) and Allied Engineering (Rs 400 Cr)" - the conjunction
        # sits between two names and the regex captures it as part of the second
        name = re.sub(r"^(?:and|with|alongside|plus)\s+", "", name, flags=re.I).strip()
        if not name or len(name) < 3:
            return
        key = (bucket, name.lower())
        if key in seen:
            return
        seen.add(key)
        row = {"name": name}
        row.update({k: v for k, v in kw.items() if v})
        out[bucket].append(row)

    # ---- open issues: name + price band + subscription + GMP ----
    for m in RE_FULL.finditer(body):
        add("open", m.group(1), lo=m.group(2).replace(",", ""), hi=m.group(3).replace(",", ""),
            subs=float(m.group(4)), gmp=(m.group(5).replace(",", "") if m.group(5) else ""))
    for m in RE_SUB.finditer(body):
        add("open", m.group(1), subs=float(m.group(2)))

    # ---- upcoming: name + issue size in crore ----
    up = re.search(r"Upcoming:(.*?)(?:\n|Closed-issue|$)", body, re.S)
    if up:
        for m in RE_SIZE.finditer(up.group(1)):
            add("upcoming", m.group(1), size_cr=m.group(2).replace(",", ""))

    # ---- GMP movers and recent listings: name + percent ----
    for seg_key, label in (("closed-issue", "closed GMP"), ("recent listings", "recent listing")):
        seg = re.search(seg_key + r"(.*?)(?:\n\n|$)", body, re.S | re.I)
        if seg:
            for m in RE_GMP.finditer(seg.group(1)):
                add("movers", m.group(1), pct=float(m.group(2)), kind=label)

    out["counts"] = {k: len(out[k]) for k in ("open", "upcoming", "movers")}
    out["note"] = ("Read from the IpoBodh Daily doc in Google Drive, not from NSE. The doc is "
                   "written in prose, so only clearly-stated figures are extracted - anything "
                   "ambiguous is left out rather than guessed. Subscription multiples and GMP "
                   "are as at the doc's entry date (%s)." % as_of)
    return out


def main():
    if not os.path.exists(SRC):
        print("missing", SRC)
        return 1
    text = open(SRC, encoding="utf-8").read()
    as_of, body = latest_entry(text)
    if not body:
        print("could not find an entry heading in the doc")
        return 1
    data = parse(body, as_of)
    print("as of %s | open %d, upcoming %d, movers %d"
          % (as_of, len(data["open"]), len(data["upcoming"]), len(data["movers"])))
    for r in data["open"][:4]:
        print("   open  ", r)
    for r in data["upcoming"][:3]:
        print("   upcoming", r)
    for r in data["movers"][:3]:
        print("   mover ", r)
    if not data["open"] and not data["upcoming"]:
        print("REFUSING TO WRITE: nothing parsed - the doc wording probably changed.")
        return 1
    os.makedirs("docs", exist_ok=True)
    json.dump(data, open(OUT, "w"), ensure_ascii=False)
    print("->", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
