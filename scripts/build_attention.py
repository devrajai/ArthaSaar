#!/usr/bin/env python3
"""Wikipedia attention: which companies people are looking up far more than usual.

WHY THIS EXISTS
The Wikimedia pageview API is official, needs no key, and has no rate limit worth worrying
about at this scale. For a listed company it is a free proxy for public attention: a sudden
run of lookups usually means something happened - results, a deal, a scandal, a crash.

WHAT IT IS NOT
Attention is not buying. A company can be searched heavily because it is collapsing. This
file measures interest and nothing else, and says so wherever it appears.

THE MEASURE
For each company: the last N days of daily views, a baseline taken from the median of the
weeks before, and a flag on any day that ran at several times that baseline. A median is used
rather than a mean because one viral day would otherwise raise the baseline and hide itself.
"""
import json, os, statistics, sys, time, urllib.request
from datetime import datetime, timezone, timedelta

OUT = "docs/attention.json"
API = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
       "en.wikipedia/all-access/user/%s/daily/%s/%s")
UA = {"User-Agent": "ArthaSaar/1.0 (market research; contact via github.com/devrajai)"}

DAYS = 60            # how much history to pull
BASE_DAYS = 30       # baseline window, ending where the recent window begins
RECENT_DAYS = 10     # the window being judged
SPIKE_X = 3.0        # a day this many times the baseline is flagged
MIN_BASE = 5         # below this many views a day the ratio is noise, not interest

# Curated, because resolving a company name to the right Wikipedia article automatically is
# unreliable - "Bank of India" and "Bank of Baroda" are different companies, and a wrong
# article would publish a confident number about the wrong firm. These are the liquid names
# where attention is worth measuring; the list can grow.
WIKI = {
    "RELIANCE": "Reliance_Industries",
    "TCS": "Tata_Consultancy_Services",
    "HDFCBANK": "HDFC_Bank",
    "ICICIBANK": "ICICI_Bank",
    "INFY": "Infosys",
    "HINDUNILVR": "Hindustan_Unilever",
    "ITC": "ITC_Limited",
    "SBIN": "State_Bank_of_India",
    "BHARTIARTL": "Bharti_Airtel",
    "KOTAKBANK": "Kotak_Mahindra_Bank",
    "AXISBANK": "Axis_Bank",
    "LT": "Larsen_%26_Toubro",
    "WIPRO": "Wipro",
    "HCLTECH": "HCLTech",
    "TECHM": "Tech_Mahindra",
    "SUNPHARMA": "Sun_Pharma",
    "DRREDDY": "Dr._Reddy%27s_Laboratories",
    "CIPLA": "Cipla",
    "TATAMOTORS": "Tata_Motors",
    "M_M": "Mahindra_%26_Mahindra",
    "MARUTI": "Maruti_Suzuki",
    "BAJAJ_AUTO": "Bajaj_Auto",
    "HEROMOTOCO": "Hero_MotoCorp",
    "EICHERMOT": "Eicher_Motors",
    "TATASTEEL": "Tata_Steel",
    "JSWSTEEL": "JSW_Steel",
    "HINDALCO": "Hindalco_Industries",
    "VEDL": "Vedanta_Limited",
    "ONGC": "Oil_and_Natural_Gas_Corporation",
    "NTPC": "NTPC_Limited",
    "POWERGRID": "Power_Grid_Corporation_of_India",
    "COALINDIA": "Coal_India",
    "ADANIENT": "Adani_Group",
    "ADANIPORTS": "Adani_Ports",
    "DLF": "DLF_(company)",
    "GODREJCP": "Godrej_Consumer_Products",
    "DABUR": "Dabur",
    "BRITANNIA": "Britannia_Industries",
    "NESTLEIND": "Nestlé_India",
    "TITAN": "Titan_Company",
    "ASIANPAINT": "Asian_Paints",
    "ULTRACEMCO": "UltraTech_Cement",
    "ZOMATO": "Zomato",
    "PAYTM": "Paytm",
    "NYKAA": "Nykaa",
    "IRCTC": "Indian_Railway_Catering_and_Tourism_Corporation",
    "YESBANK": "Yes_Bank",
    "IDEA": "Vodafone_Idea",
    "SUZLON": "Suzlon",
}


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch(title, start, end, tries=4):
    """Fetch one article's views, backing off when Wikimedia throttles.

    The first version fired 49 requests 0.1s apart and collected HTTP 429 for two thirds of
    them, which looked exactly like "these article titles are wrong". They were not - the API
    was telling us to slow down. Backoff plus a real pause between calls fixes it; treating a
    429 as a missing article would have quietly dropped the largest companies.
    """
    u = API % (title, start, end)
    delay = 2.0
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                wait = float(ra) if (ra or "").isdigit() else delay
                time.sleep(wait)
                delay *= 2
                continue
            raise
        except Exception as e:
            last = e
            time.sleep(delay)
            delay *= 2
    raise last if last else RuntimeError("fetch failed")


def main():
    out = {"updated": now(), "available": False, "rows": [], "count": 0,
           "spike_x": SPIKE_X, "window_days": DAYS, "note": "", "cautions": {}}

    end = datetime.now(timezone.utc).date() - timedelta(days=1)
    start = end - timedelta(days=DAYS)
    s, e = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

    rows = []
    failed = []
    for sym, title in WIKI.items():
        try:
            d = fetch(title, s, e)
        except Exception:
            failed.append(sym)
            continue
        views = []
        for it in (d.get("items") or []):
            ts = it.get("timestamp") or ""
            if len(ts) >= 8:
                views.append((ts[:8], it.get("views") or 0))
        if len(views) < BASE_DAYS + 5:
            failed.append(sym)
            continue

        recent = views[-RECENT_DAYS:]
        base_window = views[-(BASE_DAYS + RECENT_DAYS):-RECENT_DAYS] or views[:-RECENT_DAYS]
        base_vals = [v for _, v in base_window] or [v for _, v in views]
        base = statistics.median(base_vals)
        if base < MIN_BASE:
            failed.append(sym)
            continue

        peak_day, peak_views = max(recent, key=lambda x: x[1])
        peak_x = peak_views / base if base else 0
        last_views = recent[-1][1]
        last_x = last_views / base if base else 0
        rows.append({
            "symbol": sym,
            "article": title.replace("%26", "&").replace("%27", "'"),
            "baseline": int(base),
            "last_day": int(last_views),
            "last_x": round(last_x, 2),
            "peak_day": peak_day,
            "peak_views": int(peak_views),
            "peak_x": round(peak_x, 2),
            "spiking": peak_x >= SPIKE_X,
            "days": len(views),
        })
        time.sleep(0.8)   # Wikimedia throttles fast bursts; be a good citizen

    rows.sort(key=lambda r: -r["peak_x"])
    out["rows"] = rows
    out["count"] = len(rows)
    out["available"] = bool(rows)
    out["failed"] = failed

    spiking = [r for r in rows if r["spiking"]]
    if rows:
        top = rows[0]
        out["note"] = (
            "%d companies measured over %d days of English Wikipedia views. %d are running at "
            "%.0fx or more of their own baseline in the last %d days; the highest is %s at %.1fx "
            "on %s." % (len(rows), DAYS, len(spiking), SPIKE_X, RECENT_DAYS,
                        top["symbol"], top["peak_x"], top["peak_day"]))
    out["cautions"] = {
        "not_buying": ("Attention is not buying. A company is often looked up hardest while it "
                       "is falling - this measures interest, never money or intent."),
        "english_only": ("English Wikipedia only. Regional-language editions carry a different "
                         "and possibly larger audience, which this does not see."),
        "baseline": ("The baseline is the median of the previous 30 days, so one viral day "
                     "cannot inflate the bar it is judged against."),
        "coverage": ("%d companies are tracked, chosen because their Wikipedia article is "
                     "unambiguous. A wrong article would publish a confident number about the "
                     "wrong firm, so the list is curated rather than guessed." % len(WIKI)),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %d companies, %d spiking, %d failed" % (len(rows), len(spiking), len(failed)))
    for r in rows[:6]:
        print("     %-12s peak %5.1fx (%s)  baseline %5d  last %5d (%.1fx)"
              % (r["symbol"], r["peak_x"], r["peak_day"], r["baseline"], r["last_day"], r["last_x"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
