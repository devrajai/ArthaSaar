#!/usr/bin/env python3
"""Company Cards collector — data/companies/SYM.json for every Nifty-500 stock.
Sources: screener.in company page (all numbers) + yfinance (sector, officers, story, website).
Polite crawl: 1.5-2.5s delay between screener requests, weekly cadence, personal use.
Run:  python3 scripts/company_cards_collect.py [--limit N] [--symbols A,B,C]
Writes: data/companies/<SYM>.json + data/company-index.json
"""
import html
import json
import os
import random
import re
import sys
import time
from datetime import datetime, timezone

import requests
import yfinance as yf

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/120 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}
DATA = "data"
OUTDIR = os.path.join(DATA, "companies")
FUND = os.path.join(DATA, "screener-fundamentals.json")

NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M UTC")


def clean(txt):
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", txt.replace("&nbsp;", " ")))).strip()


def parse_screener(html):
    d = {}
    m = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S)
    d["name"] = clean(m.group(1)) if m else None

    m = re.search(r'class="sub show-more-box about"[^>]*>(.*?)</div>', html, re.S)
    d["about"] = clean(m.group(1)) if m else None

    m = re.search(r'class="sub commentary always-show-more-box"[^>]*>(.*?)</div>', html, re.S)
    d["key_points"] = clean(m.group(1)) if m else None

    top = {}
    m = re.search(r'<ul id="top-ratios"(.*?)</ul>', html, re.S)
    if m:
        for li in re.findall(r"<li.*?</li>", m.group(1), re.S):
            nm = re.search(r'name">\s*(.*?)\s*</span>', li, re.S)
            if nm:
                val = clean(li[nm.end():]).lstrip("\u20b9").strip()
                top[nm.group(1).strip()] = val
    d["top"] = top

    def table(sec_id, last_cols=None):
        m = re.search(r'<section id="%s".*?</section>' % sec_id, html, re.S)
        if not m:
            return None
        rows = []
        for r in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(0), re.S):
            cells = [clean(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", r, re.S)]
            if any(c != "" for c in cells):
                rows.append(cells)
        if last_cols and rows and len(rows[0]) > last_cols + 1:
            rows = [[r[0]] + r[-last_cols:] for r in rows]
        return rows

    d["quarters"] = table("quarters", last_cols=8)
    pl = table("profit-loss", last_cols=10)
    if pl and len(pl[0]) >= 5:
        w = len(pl[0])
        pl = [r for r in pl if len(r) == w or (len(r) == 2 and r[0] in
               ("Last Year:", "3 Years:", "5 Years:", "10 Years:"))]
    d["profit_loss"] = pl
    d["ratios"] = table("ratios", last_cols=9)

    # shareholding: quarterly block only (cut before the yearly header row)
    sh = table("shareholding")
    if sh:
        cut = None
        for i, r in enumerate(sh[1:], start=1):
            if r[0] == "" and all(re.match(r"^[A-Z][a-z]{2} \d{4}$", c) for c in r[1:3]):
                cut = i
                break
        if cut:
            sh = sh[:cut]
    d["shareholding"] = sh
    return d


def yf_profile(sym):
    p = {}
    try:
        info = yf.Ticker(sym + ".NS").info or {}
    except Exception:
        return p
    p["sector"] = info.get("sector")
    p["industry"] = info.get("industry")
    p["website"] = info.get("website")
    p["employees"] = info.get("fullTimeEmployees")
    p["summary"] = info.get("longBusinessSummary")
    officers = []
    for o in (info.get("companyOfficers") or [])[:8]:
        if o.get("name"):
            officers.append({"name": o.get("name"), "title": o.get("title") or "-",
                             "age": o.get("age"), "pay": o.get("totalPay")})
    p["officers"] = officers
    return p


def fetch_symbol(sym):
    out = None
    for variant in ("consolidated", ""):
        url = "https://www.screener.in/company/%s/%s" % (sym, variant)
        try:
            r = requests.get(url, headers=UA, timeout=30)
        except Exception:
            continue
        if r.status_code == 200 and len(r.text) > 5000:
            out = parse_screener(r.text)
            break
        time.sleep(1.0)
    return out


def main():
    args = sys.argv[1:]
    limit = 0
    symbols = None
    for i, a in enumerate(args):
        if a == "--limit" and i + 1 < len(args):
            limit = int(args[i + 1])
        if a == "--symbols" and i + 1 < len(args):
            symbols = [s.strip().upper() for s in args[i + 1].split(",") if s.strip()]

    if not symbols:
        with open(FUND, encoding="utf-8") as f:
            symbols = sorted(json.load(f).get("stocks", {}).keys())

    if limit:
        symbols = symbols[:limit]
    os.makedirs(OUTDIR, exist_ok=True)

    index = {}
    ok, fail = 0, 0
    for n, sym in enumerate(symbols, 1):
        path = os.path.join(OUTDIR, sym + ".json")
        try:
            with open(path, encoding="utf-8") as f:
                old = json.load(f)
        except Exception:
            old = None

        data = fetch_symbol(sym)
        if not data or not data.get("name"):
            fail += 1
            print("[%d/%d] %s: screener fetch failed" % (n, len(symbols), sym), flush=True)
            time.sleep(2.0)
            continue

        prof = yf_profile(sym)
        rec = {"symbol": sym, "updated": NOW,
               "source": "screener.in + yfinance",
               "url": "https://www.screener.in/company/%s/consolidated/" % sym}
        rec.update(data)
        rec["profile"] = prof

        with open(path, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, separators=(",", ":"))
        index[sym] = {"name": rec["name"],
                     "sector": prof.get("sector") or "",
                     "industry": prof.get("industry") or ""}
        ok += 1
        if n % 25 == 0 or n == len(symbols):
            print("[%d/%d] %s ok" % (n, len(symbols), sym), flush=True)
        time.sleep(random.uniform(1.5, 2.5))

    # merge into index: keep existing entries for symbols not fetched this run
    idx_path = os.path.join(DATA, "company-index.json")
    try:
        with open(idx_path, encoding="utf-8") as f:
            merged = json.load(f)
    except Exception:
        merged = {}
    merged.update(index)
    merged["_updated"] = NOW
    merged["_count"] = len([k for k in merged if not k.startswith("_")])
    with open(idx_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, separators=(",", ":"))

    print("DONE ok=%d fail=%d index=%d companies" % (ok, fail, merged["_count"]))


if __name__ == "__main__":
    main()
