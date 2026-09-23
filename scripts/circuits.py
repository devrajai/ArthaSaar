#!/usr/bin/env python3
"""circuits.py v2 - Upper/Lower Circuit Scanner + 7-day history:
- Roz ka UC/LC list (close=high/low, 1-20% bands)
- Har stock ka past 7 trading day ka % change (d7)
- 7 din me kitni baar same-side circuit laga (h)
- Roz ka UC/LC count trend (tr)
Source (free): nsearchives.nseindia.com bhavcopy (UDiFF). Output: data/circuits.json"""
import csv, io, json, os, sys, urllib.request, zipfile
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).date()
SERIES = {"EQ", "BE", "BZ", "SM", "ST"}
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def bhav_for(d):
    url = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_%s_F_0000.csv.zip" % d.strftime("%Y%m%d")
    try:
        req = urllib.request.Request(url, headers=UA)
        raw = urllib.request.urlopen(req, timeout=40).read()
    except Exception:
        return None
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
        rows = list(csv.DictReader(io.StringIO(zf.read(zf.namelist()[0]).decode("utf-8", "ignore"))))
    except Exception:
        return None
    st = {}
    for r in rows:
        if r.get("SctySrs") not in SERIES or r.get("FinInstrmTp") != "STK":
            continue
        try:
            c, h, l, p = float(r["ClsPric"]), float(r["HghPric"]), float(r["LwPric"]), float(r["PrvsClsgPric"])
            if p <= 0 or c <= 0:
                continue
            st[r.get("TckrSymb") or ""] = {"c": c, "h": h, "l": l, "p": p, "v": float(r.get("TtlTrfVal") or 0) / 1e7}
        except (ValueError, KeyError, ZeroDivisionError):
            continue
    return st if st else None

def classify(st):
    """return {sym: pct} for circuit-hit stocks + uc/lc sets"""
    uc, lc = set(), set()
    pct = {}
    for sym, x in st.items():
        if not sym:
            continue
        ch = (x["c"] - x["p"]) / x["p"] * 100.0
        pct[sym] = ch
        if x["c"] == x["h"] and ch >= 0.9:
            uc.add(sym)
        elif x["c"] == x["l"] and ch <= -0.9:
            lc.add(sym)
    return pct, uc, lc

def main():
    # 7 trading days ikkatha karo (aaj/latest se peeche)
    days = []
    d = TODAY
    tries = 0
    while len(days) < 7 and tries < 13:
        st = bhav_for(d)
        if st:
            days.append((d, st))
        d -= timedelta(days=1)
        tries += 1
    if not days:
        print("FAIL: bhavcopy nahi mila")
        sys.exit(1)
    days.reverse()  # purana -> naya
    used = days[-1][0]

    # per-day: pct map + circuit sets
    hist = []
    for dt, st in days:
        pct, uc, lc = classify(st)
        hist.append({"d": dt, "pct": pct, "uc": uc, "lc": lc, "st": st})

    st = hist[-1]["st"]
    pct, uc_set, lc_set = hist[-1]["pct"], hist[-1]["uc"], hist[-1]["lc"]

    def hits(sym, side):
        n = 0
        for hd in hist:
            if sym in (hd["uc"] if side == "uc" else hd["lc"]):
                n += 1
        return n

    def d7(sym):
        out = []
        for hd in hist:
            p = hd["pct"].get(sym)
            out.append(round(p, 1) if p is not None else None)
        return out

    uc, lc = {}, {}
    for sym in uc_set:
        x = st[sym]
        ch = pct[sym]
        b = min(20, max(1, round(abs(ch))))
        uc.setdefault(b, []).append({"s": sym, "c": round(x["c"], 2), "p": round(ch, 2), "v": round(x["v"], 1),
                                     "h": hits(sym, "uc"), "d7": d7(sym)})
    for sym in lc_set:
        x = st[sym]
        ch = pct[sym]
        b = min(20, max(1, round(abs(ch))))
        lc.setdefault(b, []).append({"s": sym, "c": round(x["c"], 2), "p": round(ch, 2), "v": round(x["v"], 1),
                                     "h": hits(sym, "lc"), "d7": d7(sym)})

    def pack(dd):
        out = []
        for b in sorted(dd.keys(), reverse=True):
            lst = sorted(dd[b], key=lambda x: -x["v"])[:50]
            out.append({"b": b, "n": len(dd[b]), "top": lst})
        return out

    tr = [{"d": hd["d"].strftime("%d %b"), "uc": len(hd["uc"]), "lc": len(hd["lc"])} for hd in hist]

    data = {
        "updated": used.strftime("%d %b %Y"),
        "note": "Upper circuit = close high pe lock (sellers khatam). Lower = close low pe lock. 1-20% band-wise. Bars = past 7 din ka daily %. 7d = us din me kitni baar circuit laga. NSE bhavcopy se. Indicative only.",
        "n_uc": len(uc_set), "n_lc": len(lc_set),
        "tr": tr,
        "uc": pack(uc), "lc": pack(lc),
    }
    os.makedirs("data", exist_ok=True)
    with open("data/circuits.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("OK wrote data/circuits.json -", used, "- UC:", len(uc_set), "LC:", len(lc_set),
          "| 7d trend:", [(t["d"], t["uc"], t["lc"]) for t in tr])

if __name__ == "__main__":
    main()
