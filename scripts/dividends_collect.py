#!/usr/bin/env python3
"""dividends_collect.py - Dividend/Bonus/Split calendar (v3: many fallbacks).
GitHub runner IPs ko NSE/BSE APIs 403 dete hain, isliye relay chain:
  1. direct NSE + BSE (kabhi chal jaye to)
  2. codetabs proxy relay (BSE)
  3. r.jina.ai reader relay (BSE)
  4. Yahoo dividend calendar (query1 - Actions se reachable)
Merge + dedupe. Output: data/dividends.json (powerpack.js card reads it).
"""
import http.cookiejar
import json
import os
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

UA = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}
CATS = {"Dividend": "DIV", "Bonus": "BON", "Stock Split": "SPL"}


def bse_url(cat, f, t, page):
    return (
        "https://api.bseindia.com/BseIndiaAPI/api/AnnSubCategoryGetData/w?pageno=" + str(page)
        + "&strCat=" + urllib.parse.quote(cat)
        + "&strSrc=market&strSearch=&FromDate=" + f.strftime("%d-%m-%Y")
        + "&ToDate=" + t.strftime("%d-%m-%Y") + "&Type=null"
    )


def http_json(url, headers=None, timeout=25):
    req = urllib.request.Request(url, headers=headers or UA)
    raw = urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s[:4].lower() == "json":
            s = s[4:]
        s = s.strip()
    if not s.startswith("{"):
        i = s.find("{")
        if i > 0:
            s = s[i:]
    return json.loads(s)


def parse_bse_rows(d, typ):
    out = []
    for x in d.get("Table") or []:
        out.append(
            {
                "sym": (x.get("scrip_name") or "").upper(),
                "code": x.get("scrip") or "",
                "date": x.get("ex_dt") or x.get("ann_dt") or "",
                "type": typ,
                "detail": (x.get("subject") or "")[:110],
            }
        )
    return out


def bse_direct(cat, f, t):
    out = []
    for page in (1, 2):
        try:
            out += parse_bse_rows(http_json(bse_url(cat, f, t, page)), CATS.get(cat, "OTH"))
        except Exception as e:
            print("BSE direct", cat, "p" + str(page), "fail:", str(e)[:60])
    return out


def bse_relay(cat, f, t):
    out = []
    for page in (1, 2):
        u = bse_url(cat, f, t, page)
        for relay, name in (
            ("https://api.codetabs.com/v1/proxy?quest=" + urllib.parse.quote(u, safe=""), "codetabs"),
            ("https://r.jina.ai/" + u, "jina"),
        ):
            try:
                rows = parse_bse_rows(http_json(relay), CATS.get(cat, "OTH"))
                if rows:
                    print("BSE", cat, "via", name, "p" + str(page), ":", len(rows), "rows")
                    out += rows
                    break
            except Exception as e:
                print("BSE", name, cat, "p" + str(page), "fail:", str(e)[:60])
    return out


def yahoo_dividends():
    out = []
    for off in range(0, 22):
        day = date.today() + timedelta(days=off)
        url = (
            "https://query1.finance.yahoo.com/v1/finance/calendar/dividends?day="
            + day.strftime("%Y-%m-%d") + "&formatted=false"
        )
        try:
            d = http_json(url, headers={**UA, "Referer": "https://finance.yahoo.com/"}, timeout=15)
            fin = (d or {}).get("finance") or {}
            res = fin.get("result")
            if not res:
                continue
            rows = res[0] if isinstance(res, list) else res
            if isinstance(rows, dict):
                rows = rows.get("rows") or []
            for x in rows or []:
                sym = (x.get("symbol") or "").replace(".NS", "").replace(".BO", "").upper()
                amt = x.get("amount") or x.get("dividend") or ""
                ex = x.get("exDate") or x.get("ex-date") or day.strftime("%d-%b-%Y")
                if not sym:
                    continue
                out.append(
                    {
                        "sym": sym,
                        "code": "",
                        "date": str(ex),
                        "type": "DIV",
                        "detail": ("DIVIDEND - RS " + str(amt) + " PER SHARE") if amt else "DIVIDEND DECLARED",
                    }
                )
        except Exception as e:
            print("Yahoo", day, "fail:", str(e)[:50])
    return out


def nse_actions(f, t):
    try:
        cj = http.cookiejar.CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
        op.open(urllib.request.Request("https://www.nseindia.com/", headers=UA), timeout=25).read(102400)
        url = (
            "https://www.nseindia.com/api/corporates-corporate-actions?index=equities&from_date="
            + f.strftime("%d-%m-%Y") + "&to_date=" + t.strftime("%d-%m-%Y")
        )
        d = json.loads(op.open(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "ignore"))
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
        out.append({"sym": sym, "code": "", "date": ex, "type": typ, "detail": (x.get("purpose") or "")[:110]})
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
        b = bse_direct(cat, today, till)
        if not b:
            b = bse_relay(cat, today, till)
        print("BSE", cat, "rows:", len(b))
        rows += b
    y = yahoo_dividends()
    print("Yahoo rows:", len(y))
    rows += y
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
        "note": "NSE + BSE + Yahoo se - aane wale 3 hafte ke dividend/bonus/split.",
    }
    os.makedirs("data", exist_ok=True)
    with open("data/dividends.json", "w") as f:
        json.dump(out, f, indent=1)
    print("dividends.json:", len(uniq), "items (merged)")


if __name__ == "__main__":
    main()