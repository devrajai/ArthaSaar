#!/usr/bin/env python3
"""dividends_collect.py - Dividend/Bonus/Split calendar (BSE announcements API).
Best-effort free source - kai din 0 rows aate hain, tab card 'no data' dikhata hai.
Output: data/dividends.json"""
import json
import os
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
      "Accept": "application/json",
      "Referer": "https://www.bseindia.com/corporates/ann.html",
      "X-Requested-With": "XMLHttpRequest"}
CATS = {"Dividend": "DIV", "Bonus": "BON", "Stock Split": "SPL"}

def fetch_cat(cat, f, t):
    api = ("https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno=1"
           f"&strCat={urllib.parse.quote(cat)}&strSrc=market&strSearch=&FromDate={f:%d-%m-%Y}&ToDate={t:%d-%m-%Y}&Type=null")
    try:
        req = urllib.request.Request(api, headers=UA)
        r = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
        d = json.loads(r)
        rows = d.get("Table") or []
        if d.get("Status") is False and not rows:
            return []
        out = []
        for x in rows:
            sub = (x.get("subject") or "")[:110]
            out.append({"sym": x.get("scrip_name") or x.get("News_submission_id") or "",
                        "code": x.get("scrip") or "", "date": x.get("ex_dt") or x.get("ann_dt") or "",
                        "type": CATS.get(cat, "OTH"), "detail": sub})
        return out
    except Exception as e:
        print(cat, "fail:", str(e)[:60])
        return []

def main():
    today = date.today()
    till = today + timedelta(days=21)
    all_rows = []
    for cat in CATS:
        all_rows += fetch_cat(cat, today, till)
    out = {"updated": datetime.now().isoformat(),
           "from": today.strftime("%d-%m-%Y"), "to": till.strftime("%d-%m-%Y"),
           "items": all_rows[:60],
           "note": "BSE announcements se - aane wale 3 hafte ke dividend/bonus/split."}
    os.makedirs("data", exist_ok=True)
    with open("data/dividends.json", "w") as f:
        json.dump(out, f, indent=1)
    print("dividends.json:", len(all_rows), "items")

if __name__ == "__main__":
    main()
