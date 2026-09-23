#!/usr/bin/env python3
"""stages.py - STOCK STAGE DETECTOR (Dev ke notebook ke 4-Stage rules):
Stage 1 = Base (sab kuch flat, taiyari) | Stage 2 = Uptrend (20 upar 40, dancing area, 200 SMA ke upar)
Stage 3 = Topping (20 neeche 40 upar wale se) | Stage 4 = Downtrend (20 neeche 40, 200 SMA ke neeche)
Weekly closes bhavcopy se banate hain (incremental, pehli baar ~10 mahine ka history laata hai)"""
import io, json, csv, zipfile, urllib.request, os
from datetime import date, datetime, timedelta

IST = datetime.utcnow() + timedelta(hours=5, minutes=30)
TODAY = IST.date()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
SERIES = {"EQ", "BE", "BZ", "SM", "ST"}
BOOTSTRAP_DAYS = 300    # calendar days lookback on first run
MAX_DOWNLOADS = 215     # per run download cap

def bhav(d):
    url = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_%s_F_0000.csv.zip" % d.strftime("%Y%m%d")
    try:
        req = urllib.request.Request(url, headers=UA)
        raw = urllib.request.urlopen(req, timeout=40).read()
        zf = zipfile.ZipFile(io.BytesIO(raw))
        rd = csv.DictReader(io.TextIOWrapper(zf.open(zf.namelist()[0]), encoding="utf-8", errors="ignore"))
        out = {}
        for r in rd:
            if r.get("SctySrs") in SERIES and r.get("TckrSymb"):
                try:
                    c = float(r.get("ClsPric") or 0)
                except Exception:
                    continue
                if c > 0:
                    out[r["TckrSymb"]] = c
        return out
    except Exception:
        return None

def main():
    state = {"last": None, "wl": [], "w": {}}
    if os.path.exists("data/stages.json"):
        try:
            with open("data/stages.json") as f:
                old = json.load(f)
            state["last"] = old.get("last")
            state["wl"] = old.get("wl") or []
            state["w"] = old.get("w") or {}
        except Exception:
            pass
    # trading days to fetch
    if state["last"]:
        start = datetime.strptime(state["last"], "%Y-%m-%d").date() + timedelta(days=1)
    else:
        start = TODAY - timedelta(days=BOOTSTRAP_DAYS)
    days = []
    d = start
    while d <= TODAY:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    if len(days) > MAX_DOWNLOADS:
        days = days[-MAX_DOWNLOADS:]
    ndl = 0
    last_ok = state["last"]
    for d in days:
        cl = bhav(d)
        if cl is None:
            continue
        ndl += 1
        last_ok = d.isoformat()
        wk = (d - timedelta(days=d.weekday())).isoformat()  # Monday
        if wk not in state["wl"]:
            state["wl"].append(wk)
        idx = state["wl"].index(wk)
        for sym, c in cl.items():
            arr = state["w"].setdefault(sym, [])
            while len(arr) <= idx:
                arr.append(None)
            if len(arr) > idx:
                arr[idx] = round(c, 1)
        if ndl % 25 == 0:
            print("...", ndl, "files,", d)
    print("downloaded:", ndl, "days; weeks:", len(state["wl"]), "stocks:", len(state["w"]))
    # compute stages
    allst = {}
    counts = {1: 0, 2: 0, 3: 0, 4: 0, 0: 0}
    top2 = []
    for sym, arr in state["w"].items():
        vals = [x for x in arr if x is not None]
        if len(vals) < 12:
            counts[0] += 1
            continue
        c = vals[-1]
        w4 = sum(vals[-4:]) / min(4, len(vals))
        w8 = sum(vals[-8:]) / min(8, len(vals))
        w40 = sum(vals[-40:]) / min(40, len(vals))
        if c > w40 and w4 > w8:
            st = 2
        elif c < w40 and w4 < w8:
            st = 4
        elif c > w40 and w4 <= w8:
            st = 3
        else:
            st = 1
        hi = max(vals)
        dist = round(100 * (c - hi) / hi, 1) if hi > 0 else 0
        counts[st] += 1
        allst[sym] = [st, dist]
        if st == 2:
            top2.append([sym, c, dist])
    top2.sort(key=lambda x: -x[2])
    out = {
        "updated": TODAY.strftime("%d %b %Y"),
        "last": last_ok,
        "wl": state["wl"],
        "w": state["w"],
        "counts": counts,
        "all": allst,
        "top2": top2[:40],
    }
    with open("data/stages.json", "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("OK stages:", counts, "| top2 sample:", [t[0] for t in top2[:5]])

if __name__ == "__main__":
    main()
