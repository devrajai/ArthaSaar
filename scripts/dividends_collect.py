#!/usr/bin/env python3
"""dividends_collect.py - Dividend/Bonus/Split calendar (v2: NSE + BSE merge).
Two free sources, merged + deduped - ek fail ho to doosra chalta hai:
  1. NSE corporate-actions API (cookie bootstrap) - upcoming ex-dates
  2. BSE AnnSubCategoryGetData API - announcements window
Output: data/dividends.json (same shape as before - powerpack.js card reads it).
"""
import http.cookiejar
import json
import os
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
}
CATS = {"Dividend": "DIV", "Bonus": "BON", "Stock Split": "SPL"}


def bse_cat(cat, f, t):
    out = []
    for page in (1, 2):
        api = (
            "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno=" + str(page)
            + "&strCat=" + urllib.parse.quote(cat)
            + "&strSrc=market&strSearch=&FromDate=" + f.strftime("%d-%m-%Y")
            + "&ToDate=" + t.strftime("%d-%m-%Y") + "&Type=null"
        )
        try:
            req = urllib.request.Request(
                api,
                headers={
                    **UA,
                    "Referer": "https://www.bseindia.com/corporates/ann.html",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )
            r = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "ignore")
            d = json.loads(r)
            for x in d.get("Table") or []:
                out.append(
                    {
                        "sym": (x.get("scrip_name") or "").upper(),
                        "code": x.get("scrip") or "",
                        "date": x.get("ex_dt") or x.get("ann_dt") or "",
                        "type": CATS.get(cat, "OTH"),
                        "detail": (x.get("subject") or "")[:110],
                    }
                )
        except Exception as e:
            print("BSE", cat, "p" + str(page), "fail:", str(e)[:60])
    return out


def nse_actions(f, t):
    try:
        cj = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        op.open(
            urllib.request.Request("https://www.nseindia.com/", headers=UA), timeout=25
        ).read(102400)
        url = (
            "https://www.nseindia.com/api/corporates-corporate-actions?index=equities&from_date="
            + f.strftime("%d-%m-%Y")
            + "&to_date="
            + t.strftime("%d-%m-%Y")
        )
        r = op.open(urllib.request.Request(url, headers=UA), timeout=30).read().decode(
            "utf-8", "ignore"
        )
        d = json.loads(r)
    except Exception as e:
        print("NSE corp actions fail:", str(e)[:80])
        return []
    out = []
    for x in d.get("data") or []:
        sym = (x.get("symbol") or "").upper()
        ex = x.get("exDate") or ""
        p = (x.get("purpose") or "").upper()
        if not sym or not ex:
            continue
        typ = None
        if "DIVIDEND" in p:
            typ = "DIV"
        elif "BONUS" in p:
            typ = "BON"
        elif "SPLIT" in p or "FACE VALUE" in p:
            typ = "SPL"
        if not typ:
            continue
        out.append(
            {
                "sym": sym,
                "code": "",
                "date": ex,
                "type": typ,
                "detail": (x.get("purpose") or "")[:110],
            }
        )
    return out


def norm_date(s):
    s = (s or "").strip()
    for fmt in ("%d-%b-%Y", "%d-%m-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).strftime("%Y%m%d")
        except ValueError:
            pass
    return ""


def main():
    today = date.today()
    till = today + timedelta(days=21)
    rows = nse_actions(today, till)
    print("NSE rows:", len(rows))
    for cat in CATS:
        b = bse_cat(cat, today, till)
        print("BSE", cat, "rows:", len(b))
        rows += b
    seen = set()
    uniq = []
    for x in rows:
        if not x["sym"] or not x["detail"]:
            continue
        k = (x["sym"], x["type"], norm_date(x["date"]))
        if k in seen:
            continue
        seen.add(k)
        uniq.append(x)
    uniq.sort(key=lambda x: (norm_date(x["date"]) or "99999999", x["sym"]))
    out = {
        "updated": datetime.now().isoformat(),
        "from": today.strftime("%d-%m-%Y"),
        "to": till.strftime("%d-%m-%Y"),
        "items": uniq[:80],
        "note": "NSE + BSE se - aane wale 3 hafte ke dividend/bonus/split.",
    }
    os.makedirs("data", exist_ok=True)
    with open("data/dividends.json", "w") as f:
        json.dump(out, f, indent=1)
    print("dividends.json:", len(uniq), "items (merged NSE+BSE)")


if __name__ == "__main__":
    main()