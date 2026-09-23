#!/usr/bin/env python3
"""circuits.py - Upper/Lower Circuit Scanner: NSE daily bhavcopy (UDiFF) se
stocks jo upper circuit (close=high, +1-20%) ya lower circuit (close=low) pe
band hue. Free source: nsearchives.nseindia.com. Output: data/circuits.json"""
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
        raw = urllib.request.urlopen(req, timeout=30).read()
    except Exception:
        return None, None
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
        name = zf.namelist()[0]
        return list(csv.DictReader(io.StringIO(zf.read(name).decode("utf-8", "ignore")))), d
    except Exception:
        return None, None

def main():
    rows, used = None, None
    d = TODAY
    for _ in range(6):  # aaj se peeche 6 din try karo (weekend/holiday fallback)
        rows, used = bhav_for(d)
        if rows:
            break
        d -= timedelta(days=1)
    if not rows:
        print("FAIL: bhavcopy nahi mila (6 din try kiya)")
        sys.exit(1)

    uc, lc = {}, {}
    n_uc = n_lc = 0
    for r in rows:
        if r.get("SctySrs") not in SERIES or r.get("FinInstrmTp") != "STK":
            continue
        try:
            c, h, l, p = float(r["ClsPric"]), float(r["HghPric"]), float(r["LwPric"]), float(r["PrvsClsgPric"])
            if p <= 0 or c <= 0:
                continue
            pct = (c - p) / p * 100.0
            val_cr = float(r.get("TtlTrfVal") or 0) / 1e7
        except (ValueError, KeyError, ZeroDivisionError):
            continue
        sym = r.get("TckrSymb") or r.get("FinInstrmId") or ""
        if not sym:
            continue
        item = {"s": sym, "c": round(c, 2), "p": round(pct, 2), "v": round(val_cr, 1)}
        hit = None
        if c == h and pct >= 0.9:
            hit, n_uc = "uc", n_uc + 1
        elif c == l and pct <= -0.9:
            hit, n_lc = "lc", n_lc + 1
        if hit:
            b = min(20, max(1, round(abs(pct))))
            (uc if hit == "uc" else lc).setdefault(b, []).append(item)

    def pack(dd):
        out = []
        for b in sorted(dd.keys(), reverse=True):
            lst = sorted(dd[b], key=lambda x: -x["v"])[:50]
            out.append({"b": b, "n": len(dd[b]), "top": lst})
        return out

    data = {
        "updated": used.strftime("%d %b %Y"),
        "note": "Upper circuit = close high pe lock (sellers khatam). Lower = close low pe lock (buyers khatam). 1-20% band-wise. NSE bhavcopy se. Indicative only.",
        "n_uc": n_uc, "n_lc": n_lc,
        "uc": pack(uc), "lc": pack(lc),
    }
    os.makedirs("data", exist_ok=True)
    with open("data/circuits.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("OK wrote data/circuits.json -", used, "- UC:", n_uc, "LC:", n_lc, "- bands:", [x["b"] for x in data["uc"]])

if __name__ == "__main__":
    main()
