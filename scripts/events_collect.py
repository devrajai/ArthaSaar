#!/usr/bin/env python3
"""
MARKET BRAIN — global economic event calendar collector.

Builds data/events.json every day:
  1. This week + next week of market-moving events for ALL countries
     (US GDP / jobs / CPI, Fed, ECB, BoJ, China data, India data...)
     from ForexFactory's free public weekly JSON feed.
  2. Curated fixed dates: FOMC meetings, RBI MPC meetings, India Union
     Budget, US elections, quarterly-results seasons.
  3. Upcoming quarterly-result dates for top Indian stocks + US mega caps
     (yfinance).

All sources free. Runs on GitHub Actions (full internet).
"""
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
IST = timezone(timedelta(hours=5, minutes=30), name="IST")

FF_URLS = [
    ("this week", "https://nfs.faireconomy.media/ff_calendar_thisweek.json"),
    ("next week", "https://nfs.faireconomy.media/ff_calendar_nextweek.json"),
]

# --- curated fixed dates (verified Sep 2026) -------------------------------
# FOMC 2026: Jan27-28 Mar17-18 Apr28-29 Jun16-17 Jul28-29 Sep15-16 done;
# remaining Oct 27-28, Dec 8-9  (federalreserve.gov)
# RBI MPC 2026-27 (rbi.org.in press release, Mar 2026):
# Apr6-8 Jun3-5 Aug3-5 done; remaining Oct5-7, Dec2-4, Feb3-5(2027)
STATIC_EVENTS = [
    {"date": "2026-10-05", "date_end": "2026-10-07", "country": "IND",
     "impact": "High",
     "title": "RBI Monetary Policy Committee meeting — repo rate decision on Oct 7, 10 AM IST"},
    {"date": "2026-10-27", "date_end": "2026-10-28", "country": "USD",
     "impact": "High",
     "title": "FOMC meeting — Fed rate decision on Oct 28, ~11:30 PM IST"},
    {"date": "2026-11-03", "date_end": "", "country": "USD",
     "impact": "High",
     "title": "US mid-term elections — Congress control, market-moving"},
    {"date": "2026-12-02", "date_end": "2026-12-04", "country": "IND",
     "impact": "High",
     "title": "RBI Monetary Policy Committee meeting — repo rate decision on Dec 4, 10 AM IST"},
    {"date": "2026-12-08", "date_end": "2026-12-09", "country": "USD",
     "impact": "High",
     "title": "FOMC meeting — Fed rate decision on Dec 9, ~12 AM IST (with SEP projections)"},
    {"date": "2027-02-01", "date_end": "", "country": "IND",
     "impact": "High",
     "title": "India Union Budget 2027-28 presentation — ~11 AM IST"},
    {"date": "2027-02-03", "date_end": "2027-02-05", "country": "IND",
     "impact": "High",
     "title": "RBI Monetary Policy Committee meeting — repo rate decision on Feb 5, 10 AM IST"},
    {"date": "2026-10-15", "date_end": "2026-11-10", "country": "USD",
     "impact": "Medium",
     "title": "US Q3 quarterly-results season — mega-cap results move world markets"},
    {"date": "2026-10-20", "date_end": "2026-11-15", "country": "IND",
     "impact": "Medium",
     "title": "India Q2 FY27 quarterly-results season (Sep quarter)"},
    {"date": "2027-01-05", "date_end": "2027-02-10", "country": "IND",
     "impact": "Medium",
     "title": "India Q3 FY27 quarterly-results season (Dec quarter)"},
]

US_MEGA = ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA"]
IN_TOP = 30


def ff_week():
    """Fetch ForexFactory this+next week events for all countries."""
    out = []
    for label, url in FF_URLS:
        try:
            r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            items = r.json()
            print(f"ff {label}: {len(items)} events")
            for it in items:
                try:
                    when = datetime.fromisoformat(it["date"])
                except Exception:
                    continue
                ist = when.astimezone(IST)
                if ist < datetime.now(IST) - timedelta(days=1):
                    continue  # drop fully past events
                title = (it.get("title") or "").strip()
                if not title:
                    continue
                out.append({
                    "title": title,
                    "country": (it.get("country") or "").strip(),
                    "date_ist": ist.strftime("%Y-%m-%d"),
                    "time_ist": ist.strftime("%H:%M"),
                    "impact": (it.get("impact") or "").strip() or "Low",
                    "forecast": (it.get("forecast") or "").strip(),
                    "previous": (it.get("previous") or "").strip(),
                })
        except Exception as e:  # noqa: BLE001
            print(f"ff {label} FAILED: {e}")
    # dedupe + sort
    seen, ded = set(), []
    for e in out:
        k = (e["date_ist"], e["time_ist"], e["title"], e["country"])
        if k not in seen:
            seen.add(k)
            ded.append(e)
    ded.sort(key=lambda x: (x["date_ist"], x["time_ist"]))
    return ded


def gen_india_events():
    """India data releases follow fixed monthly patterns (MoSPI/CBIC/DGFT).
    Dates are the usual release days - marked 'expected' to stay honest."""
    from datetime import date
    out = []
    today = date.today()
    months = [0, 1, 2]  # this + next 2 months

    def add(y, m, d, title, impact, note="expected date"):
        try:
            dt = date(y, m, d)
        except ValueError:
            return
        if dt < today or (dt - today).days > 60:
            return
        out.append({"title": title + " (" + note + ")",
                    "country": "INR",
                    "date_ist": dt.isoformat(),
                    "time_ist": "17:30" if "17:30" else "",
                    "impact": impact, "forecast": "", "previous": ""})

    y, m = today.year, today.month
    for off in months:
        mm, yy = m + off, y
        while mm > 12:
            mm -= 12
            yy += 1
        # monthly releases around the 12th (CPI + IIP)
        add(yy, mm, 12, "India CPI inflation (MoSPI)", "High")
        add(yy, mm, 12, "India IIP industrial production", "Medium")
        # trade data ~15th
        add(yy, mm, 15, "India trade balance / exports-imports", "Medium")
        # auto sales on the 1st
        nm, ny = mm + 1, yy
        if nm > 12:
            nm, ny = 1, ny + 1
        add(ny, nm, 1, "India monthly auto sales numbers", "Medium")
        # quarterly GDP: last working day of Feb, May, Aug, Nov
        if mm in (2, 5, 8, 11):
            if mm == 2:
                last = 28
            elif mm in (5, 8, 11):
                import calendar
                last = calendar.monthrange(yy, mm)[1]
            add(yy, mm, last, "India quarterly GDP release", "High")
    return out


def earnings():
    """Upcoming quarterly-result dates: top Indian stocks + US mega caps."""
    out = []
    today = datetime.now(timezone.utc).date()

    def grab(symbol, name, country):
        try:
            import yfinance as yf
            t = yf.Ticker(symbol)
            ed = t.earnings_dates
            if ed is None or len(ed) == 0:
                return
            for ts, _row in ed.iterrows():
                d = ts.date() if hasattr(ts, "date") else ts
                if d >= today:
                    out.append({"symbol": name, "ticker": symbol, "country": country,
                                "date": d.isoformat()})
                    break
        except Exception as e:  # noqa: BLE001
            print(f"  earnings {symbol}: {e}")

    try:
        fund = json.loads((DATA / "screener-fundamentals.json").read_text())
        stocks = fund.get("stocks", {})
        ranked = sorted(stocks.items(),
                        key=lambda kv: (kv[1].get("Market Cap") or 0), reverse=True)
        for sym, _v in ranked[:IN_TOP]:
            grab(sym + ".NS", sym, "IN")
            time.sleep(1.0)
    except Exception as e:  # noqa: BLE001
        print("india earnings list failed:", e)

    for sym in US_MEGA:
        grab(sym, sym, "US")
        time.sleep(1.0)

    out.sort(key=lambda x: (x["date"], x["symbol"]))
    return out


def main():
    DATA.mkdir(exist_ok=True)
    print("=== events collect ===")
    week = ff_week()
    week.extend(gen_india_events())
    week.sort(key=lambda x: (x["date_ist"], x["time_ist"]))
    print(f"week events total (this+next+india): {len(week)}")
    print("sample:", week[:3] if week else "none")

    print("=== earnings ===")
    ear = earnings()
    print(f"upcoming earnings: {len(ear)}")

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "week": week,
        "key_dates": STATIC_EVENTS,
        "earnings": ear,
    }
    (DATA / "events.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1))
    print("events.json written:", len(week), "week events,", len(ear), "earnings")


if __name__ == "__main__":
    main()
