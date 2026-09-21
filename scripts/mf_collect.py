#!/usr/bin/env python3
"""mf_collect.py — AMFI se saare Indian mutual funds ka daily NAV data.
Source: https://amfiindia.com/spages/NAVAll.txt (free, no key).
Output: data/mf.json  — compact list for the MF Tracker section.
Runs on GitHub Actions daily. Prev NAV from yesterday's mf.json -> day change.
"""
import json, datetime as dt, urllib.request, os, re

URL = "https://amfiindia.com/spages/NAVAll.txt"

def cat_short(sec):
    # "Open Ended Schemes(Equity Scheme - Large Cap Fund)" -> "Equity - Large Cap"
    m = re.match(r"\w+ Ended Schemes\((.+?)\)", sec)
    if not m:
        return sec[:24]
    c = m.group(1)
    c = c.replace("Schemes", "").replace("Scheme", "")
    if "-" in c:
        parts = [p.strip() for p in c.split("-", 1)]
        head = parts[0].split()[0] if parts[0].split() else ""
        return (head + " - " + parts[1])[:28]
    return c.strip()[:28]

def fetch():
    try:
        raw = open("NAVAll.txt", encoding="utf-8", errors="ignore").read()
        if ";" in raw:
            print("using pre-downloaded NAVAll.txt")
            return raw
    except Exception:
        pass
    for url in ("https://www.amfiindia.com/spages/NAVAll.txt", "https://amfiindia.com/spages/NAVAll.txt"):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
                "Accept": "text/plain,*/*", "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.amfiindia.com/"})
            raw = urllib.request.urlopen(req, timeout=120).read().decode("utf-8", "ignore")
            if ";" in raw:
                return raw
            print("WARN bad response from %s: %r" % (url, raw[:120]))
        except Exception as e:
            print("WARN %s: %s" % (url, e))
    raise SystemExit("AMFI download failed")

raw = fetch()

prev = {}
if os.path.exists("data/mf.json"):
    try:
        for f in json.load(open("data/mf.json")).get("funds", []):
            prev[str(f["c"])] = f["v"]
    except Exception:
        pass

funds, seen, cat, house = [], set(), "", ""
def pdate(x):
    try:
        return dt.datetime.strptime(x.strip(), "%d-%b-%Y").date()
    except Exception:
        return None
today = dt.date.today()
for line in raw.splitlines():
    line = line.strip()
    if not line:
        continue
    if ";" not in line:
        if "Schemes" in line and "(" in line:
            cat = cat_short(line)
        elif "Mutual Fund" in line or "Asset Management" in line or line.endswith("Trust") or line.endswith("Trustees"):
            house = line[:30]
        continue
    p = [x.strip() for x in line.split(";")]
    if len(p) < 8 or not p[0].isdigit():
        continue
    d = pdate(p[7]) if len(p) > 7 else None
    if d is None or (today - d).days > 30:
        continue  # stale/dead option
    try:
        nav = round(float(p[6]), 4)
    except ValueError:
        continue
    name = (p[3] + " \u00b7 " + p[4] + " \u00b7 " + p[5]).strip(" \u00b7")[:60] if p[3] else ""
    code = p[0]
    if not code or not name or code in seen or not nav:
        continue
    if "Close" in (cat or ""):
        continue
    seen.add(code)
    chg = None
    pv = prev.get(code)
    if pv and pv > 0:
        chg = round((nav / pv - 1) * 100, 2)
    funds.append({"c": code, "n": name, "v": nav, "h": house, "k": cat, "p": chg})

out = {"updated": dt.datetime.now(dt.timezone.utc).isoformat(),
       "count": len(funds), "funds": funds,
       "note": "Source: AMFI NAVAll (free). Fund-manager details free mein nahi milte — sirf house/category."}
with open("data/mf.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
print("mf.json written: %d funds" % len(funds))
