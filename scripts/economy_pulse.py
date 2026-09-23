#!/usr/bin/env python3
"""Economy Pulse - 6 govt/economy indicators (GST, Rail freight, Ports, Auto, EPFO, Power).
Google News RSS se latest headlines roz fetch karta hai; values manually verified (sources noted).
data/economy-pulse.json"""
import json, time, re, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import os

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime.now(IST)
OUT = "data/economy-pulse.json"

# search query per indicator (Google News RSS, 30d window) + required keywords to filter noise
QUERIES = {
    "gst": ("monthly GST collections crore", ["gst"]),
    "rail": ("Indian Railways freight loading", ["rail", "freight"]),
    "port": ("India port cargo traffic Mundra JNPT", ["port", "teu", "cargo", "mundra", "jnpt", "shipping"]),
    "auto": ("India monthly car sales Maruti Tata Mahindra", ["sales", "units", "maruti", "tata", "mahindra", "hyundai"]),
    "epfo": ("EPFO payroll data net member addition", ["epfo", "provident"]),
    "power": ("India power demand peak electricity", ["power", "electricity", "gigawatt", " demand"]),
}

# value regex kept for future use (currently values are manually verified)
RX = {
    "gst": re.compile(r"(?:rs\.|₹)\s*([\d.]+)\s*(lakh crore|trillion)", re.I),
    "rail": re.compile(r"([\d.]+)\s*(?:million tonnes|mt)\b", re.I),
    "port": re.compile(r"([\d,.]+)\s*(?:mmt|teus?)\b", re.I),
    "auto": re.compile(r"([\d,.]+)\s*units", re.I),
    "epfo": re.compile(r"([\d.]+)\s*lakh\s*(?:members?|subscribers?|net)", re.I),
    "power": re.compile(r"([\d.]+)\s*(?:gigawatts?|gw)\b", re.I),
}
YOY = re.compile(r"([+\-]?\d+(?:\.\d+)?)\s*%", re.I)

def fetch_rss(q, retries=2):
    url = "https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:30d") + "&hl=en-IN&gl=IN&ceid=IN:en"
    for a in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64)"})
            with urllib.request.urlopen(req, timeout=25) as r:
                return ET.fromstring(r.read())
        except Exception:
            if a >= retries: return None
            time.sleep(3)
    return None

def main():
    cur = {}
    if os.path.exists(OUT):
        try: cur = json.load(open(OUT))
        except Exception: cur = {}
    byid = {i.get("id"): i for i in cur.get("ind", [])}

    for iid, (q, kw) in QUERIES.items():
        it = byid.get(iid, {})
        hl = []
        root = fetch_rss(q)
        items = []
        if root is not None:
            for el in root.iter("item"):
                try:
                    t = (el.findtext("title") or "").strip()
                    pd = el.findtext("pubDate") or ""
                    if not t or not pd: continue
                    dt = parsedate_to_datetime(pd).astimezone(IST)
                    s = (el.findtext("source") or "").strip()
                    items.append((t, dt, s))
                except Exception: continue
        seen = set()
        for t, dt, s in sorted(items, key=lambda x: x[1], reverse=True):
            k = t[:60].lower()
            if k in seen: continue
            seen.add(k)
            if " - " in t: body, ds = t.rsplit(" - ", 1)
            else: body, ds = t, s
            low = body.lower()
            if not any(k in low for k in kw): continue
            hl.append({"t": body[:150], "s": ds[:40], "d": dt.strftime("%d %b")})
            # NOTE: val/yoy manually verified only (auto-regex galat figure pakad leta tha). Sirf headlines auto-update.
            if len(hl) >= 4: break
        it["hl"] = hl
        byid[iid] = it
        time.sleep(1.0)

    order = ["gst", "rail", "port", "auto", "epfo", "power"]
    ind = [byid.get(k, {}) for k in order]
    out = {
        "updated": NOW.strftime("%d %b %Y, %H:%M IST"),
        "note": "Govt monthly/weekly releases. Main figures sources se verified; headlines roz auto-update (Google News). Indicative only - not advice.",
        "ind": ind,
    }
    os.makedirs("data", exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("OK wrote", OUT)
    for i in ind:
        print(" ", i.get("id"), "|", i.get("val"), "|", i.get("yoy"), "|", len(i.get("hl", [])), "hl")

if __name__ == "__main__":
    main()
