#!/usr/bin/env python3
"""Screener.in deep-fundamentals collector (free public pages, throttled).
Adds what yfinance lacks: ROCE, promoter/FII/DII holding, pledge, quarterly
sales/profit + YoY growth, market cap, dividend yield.
Runs weekly over tier-1 (Nifty 500) universe. Output: data/screener-fundamentals.json"""
import json
import random
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
SLEEP = (1.0, 2.2)  # min,max seconds between requests — be gentle

def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "ignore")

def num(s):
    s = (s or "").replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return None

def parse_top_ratios(h):
    m = re.search(r'id="top-ratios"(.{0,5000})', h, re.S)
    if not m:
        return {}
    seg = m.group(1)
    items = re.findall(r'class="name">\s*([^<]+?)\s*</span>.*?class="[^"]*number[^"]*">\s*([^<]+?)\s*<', seg, re.S)
    out = {}
    for k, v in items:
        k = k.strip()
        if k == "High / Low":
            parts = v.replace(",", "").split("/")
            out["high_52w"], out["low_52w"] = num(parts[0]), num(parts[-1])
        else:
            out[k] = num(v)
    return out

def parse_quarters(h):
    i = h.find('id="quarters"')
    if i < 0:
        return {}
    end = h.find("</table>", i)
    seg = h[i:end if end > 0 else i + 40000]
    trs = re.findall(r"<tr[^>]*>(.*?)</tr>", seg, re.S)
    table = []
    for tr in trs:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)
        cells = [re.sub(r"<[^>]+>", "", c).replace("&nbsp;", " ").strip() for c in cells]
        if cells:
            table.append(cells)
    if not table:
        return {}
    labels = table[0][1:]
    out = {"quarters": labels[-5:]}
    for row in table[1:]:
        name = row[0].rstrip(" +")
        vals = [num(c) for c in row[1:]]
        out[name] = vals
    for key in ("Sales", "Net Profit"):
        if key in out and len(out[key]) >= 5:
            latest, year_ago = out[key][-1], out[key][-5]
            if latest is not None and year_ago:
                out[key + "_yoy"] = round((latest - year_ago) / abs(year_ago) * 100, 1)
    return out

def parse_shareholding(h):
    i = h.find("Shareholding Pattern")
    if i < 0:
        return {}
    seg = h[i:i + 8000]
    out = {}
    for lbl, key in (("Promoters", "promoters"), ("FIIs", "fii"),
                     ("DIIs", "dii"), ("Public", "public")):
        j = seg.find(lbl + "&nbsp;")
        if j < 0:
            j = seg.find(lbl)
        if j < 0:
            continue
        after = re.findall(r"([\d.]+)%", seg[j:j + 4000])
        if after:
            out[key + "_pct"] = num(after[0])
    return out

def parse_pledge(h):
    m = re.search(r"pledged?[^<>]{0,40}?([\d.]+)\s*%", h, re.I)
    return num(m.group(1)) if m else None

def get_symbol(sym):
    for url in (f"https://www.screener.in/company/{sym}/consolidated/",
                f"https://www.screener.in/company/{sym}/"):
        try:
            return fetch(url), url.endswith("/consolidated/")
        except Exception as e:
            if "404" not in str(e) and "Not Found" not in str(e):
                raise
    return None, False

def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    universe = json.loads((DATA / "universe.json").read_text())
    tier1 = [u["symbol"] for u in universe if u.get("tier") == 1]
    if limit:
        tier1 = tier1[:limit]
    out, fails = {}, []
    for n, sym in enumerate(tier1, 1):
        try:
            h, consolidated = get_symbol(sym)
            if not h:
                fails.append(sym)
                continue
            row = {"consolidated": consolidated}
            row.update(parse_top_ratios(h))
            row.update(parse_quarters(h))
            row.update(parse_shareholding(h))
            pl = parse_pledge(h)
            if pl is not None:
                row["pledge_pct"] = pl
            out[sym] = row
            if n % 50 == 0 or n == len(tier1):
                print(f"{n}/{len(tier1)} done ({len(fails)} failed)", flush=True)
        except Exception as e:
            fails.append(sym)
            print(f"FAIL {sym}: {e}", flush=True)
        time.sleep(random.uniform(*SLEEP))
    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(out),
        "source": "screener.in public pages (weekly, throttled)",
        "stocks": out,
        "failed": fails,
        "note": "Deep fundamentals: mcap, P/E, ROCE, ROE, div yield, book value, "
                "quarterly sales/net profit + YoY, promoters/FII/DII %, pledge. "
                "Screener.in free public pages — personal use only.",
    }
    (DATA / "screener-fundamentals.json").write_text(json.dumps(payload, indent=1))
    print(f"\nwrote data/screener-fundamentals.json — {len(out)} ok, {len(fails)} failed")
    if fails:
        print("failed:", ",".join(fails[:40]))
    if len(out) < min(len(tier1), max(10, len(tier1) // 2)):
        print("ERROR: too many failures", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
