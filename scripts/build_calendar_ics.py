#!/usr/bin/env python3
"""
ARTHASAAR - publish corporate actions as a calendar feed (.ics).

WHY
Dividends, splits and ex-dates are dates, and dates belong in a calendar, not in a
table you have to remember to open. This writes docs/arthasaar.ics so the events can
be imported once into Google/Apple Calendar and then update themselves.

Source: docs/calendar.json (NSE corporate-action calendar, with the detail line)
falling back to docs/corp_actions.json.

Design notes
  * All-day events on the action date (DTSTART;VALUE=DATE).
  * A stable UID per (date, symbol, type) so re-importing updates rather than
    duplicating.
  * Lines folded at 75 octets, as RFC 5545 requires.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
OUT = DOCS / "arthasaar.ics"


def load(name):
    p = DOCS / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def fold(line):
    """RFC 5545: no line longer than 75 octets; continuation lines start with a space."""
    out, cur = [], line
    while len(cur.encode("utf-8")) > 74:
        cut = 74
        while len(cur[:cut].encode("utf-8")) > 74:
            cut -= 1
        out.append(cur[:cut])
        cur = " " + cur[cut:]
    out.append(cur)
    return "\r\n".join(out)


def esc(t):
    return (str(t or "").replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def collect():
    """[(date, symbol, type, detail)] deduped."""
    seen, rows = set(), []
    cal = load("calendar.json") or {}
    for day in cal.get("days") or []:
        for ev in day.get("events") or []:
            d = str(ev.get("date") or day.get("date") or "")[:10]
            sym = (ev.get("symbol") or "").strip()
            typ = (ev.get("type") or "corporate action").strip().lower()
            detail = (ev.get("detail") or "").strip()
            key = (d, sym, typ)
            if d and sym and key not in seen:
                seen.add(key)
                rows.append((d, sym, typ, detail))

    ca = load("corp_actions.json") or {}
    for it in ca.get("items") or []:
        d = str(it.get("d") or "")[:10]
        sym = (it.get("s") or "").strip()
        typ = (it.get("k") or "").strip().lower()
        if not (d and sym and typ):
            continue
        if typ == "split":
            detail = "Split 1:%s" % it.get("v")
        elif typ == "dividend":
            detail = "Dividend Rs %s per share" % it.get("v")
        else:
            detail = ""
        key = (d, sym, typ)
        if key not in seen:
            seen.add(key)
            rows.append((d, sym, typ, detail))
    rows.sort()
    return rows


def main():
    rows = collect()
    if not rows:
        print("no corporate actions to publish")
        return 1

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0",
         "PRODID:-//ArthaSaar//Corporate actions//EN", "CALSCALE:GREGORIAN",
         "METHOD:PUBLISH", "X-WR-CALNAME:ArthaSaar - dividends & corporate actions",
         "X-WR-CALDESC:Ex-dates, dividends and splits from the NSE corporate-action calendar."]

    for d, sym, typ, detail in rows:
        try:
            dt = datetime.strptime(d, "%Y-%m-%d")
        except Exception:  # noqa: BLE001
            continue
        end = dt.fromordinal(dt.toordinal() + 1)
        label = {"dividend": "Dividend", "split": "Split"}.get(typ, typ.title())
        desc = detail or label
        L += ["BEGIN:VEVENT",
              f"UID:{d}-{sym}-{typ}@arthasaar",
              f"DTSTAMP:{stamp}",
              f"DTSTART;VALUE=DATE:{dt.strftime('%Y%m%d')}",
              f"DTEND;VALUE=DATE:{end.strftime('%Y%m%d')}",
              f"SUMMARY:{esc(sym + ' - ' + label)}",
              f"DESCRIPTION:{esc(desc + ' (NSE corporate actions, via ArthaSaar)')}",
              "TRANSP:TRANSPARENT",
              "END:VEVENT"]
    L.append("END:VCALENDAR")

    DOCS.mkdir(exist_ok=True)
    OUT.write_text("\r\n".join(fold(x) for x in L) + "\r\n", encoding="utf-8")
    print(f"wrote {OUT} - {len(rows)} events, {OUT.stat().st_size} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
