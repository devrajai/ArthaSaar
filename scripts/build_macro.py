#!/usr/bin/env python3
"""Upcoming macro events, merged with the exchange's own special sessions.

WHY
The site knows corporate events but not the macro calendar. When gold falls 2.7% in a week,
the reason is usually a Fed meeting, a jobs report or an election - and a reader should be
able to see those dates without leaving the page.

SOURCES
  config/macro_events.json   hand-maintained from primary calendars (Fed, BLS, ECI)
  docs/market_status.json    special_sessions, which already carries Muhurat trading

HONEST LIMIT
Macro dates are entered by hand from official calendars, not scraped. A date is only added
after it appears on the primary source, and the page says so - a guessed date would be worse
than no date.
"""
import json, os, sys
from datetime import datetime, timezone, date

OUT = "docs/macro.json"
CFG = "config/macro_events.json"
STATUS = "docs/market_status.json"


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "events": [], "note": ""}
    today = datetime.now(timezone.utc).date()

    try:
        for e in (json.load(open(CFG)).get("events") or []):
            d = e.get("date")
            if not d:
                continue
            try:
                days = (date.fromisoformat(d) - today).days
            except Exception:
                days = None
            out["events"].append({"date": d, "time": e.get("time") or "",
                                  "region": e.get("region") or "", "label": e.get("label") or "",
                                  "note": e.get("note") or "", "days_away": days,
                                  "kind": "macro"})
    except Exception as ex:
        print("  macro config: %s" % type(ex).__name__)

    # the exchange's special sessions belong on the same calendar
    try:
        for s in (json.load(open(STATUS)).get("special_sessions") or []):
            try:
                days = (date.fromisoformat(s["date"]) - today).days
            except Exception:
                days = None
            out["events"].append({"date": s["date"], "time": s.get("open", ""),
                                  "region": "IN", "label": s.get("label") or "Special session",
                                  "note": "Trades %s to %s IST" % (s.get("open"), s.get("close")),
                                  "days_away": days, "kind": "exchange"})
    except Exception:
        pass

    # upcoming first, then most recent past
    out["events"].sort(key=lambda e: (e["days_away"] is None, e["days_away"] if e["days_away"] is not None else 0))
    # STRICTLY UPCOMING. This used to keep events up to three days in the past, and because
    # they sorted by days_away they landed at the TOP of the list - so a card titled "Coming
    # up" led with an election that had already finished. A finished event is history, and
    # the event study covers history properly; this card is only for what is still ahead.
    out["events"] = [e for e in out["events"] if e["days_away"] is None or e["days_away"] >= 0][:25]
    out["count"] = len(out["events"])
    out["note"] = ("Macro dates are entered by hand from official calendars, not scraped. A date "
                   "appears only after it is on the primary source.")

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %d events" % (OUT, out["count"]))
    for e in out["events"]:
        print("   %s %-8s %-38s %s" % (e["date"], e["region"], e["label"][:38],
                                       ("today" if e["days_away"] == 0
                     else ("tomorrow" if e["days_away"] == 1
                           else "in %d days" % e["days_away"]))
                    if e["days_away"] is not None and e["days_away"] >= 0 else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
