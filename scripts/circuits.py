#!/usr/bin/env python3
"""circuits.py v4 - Circuit Scanner + 7-day history + all-stock search + NSE band changes:
- Roz ka UC/LC list (close=high/low, 1-20% bands)
- Har stock ka past 7 trading day ka % change (d7) + circuit flags
- Roz ka UC/LC count trend (tr)
- 'all' dict: sab NSE stocks ka 7-din data + current circuit band (search ke liye)
- 'bands': NSE roz ka circuit band change list (surveillance decisions) + 7-din history
Sources (free): nsearchives.nseindia.com bhavcopy UDiFF + eq_band_changes + sec_list. Output: data/circuits.json"""
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

def band_changes_for(d):
    """NSE roz ka eq_band_changes file: kaunsa stock kis % se kis % me gaya"""
    url = "https://nsearchives.nseindia.com/content/equities/eq_band_changes_%s.csv" % d.strftime("%d%m%Y")
    try:
        req = urllib.request.Request(url, headers=UA)
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        rows = list(csv.DictReader(io.StringIO(raw)))
    except Exception:
        return None
    out = []
    for r in rows:
        s, f, t = (r.get("Symbol") or "").strip(), (r.get("From") or "").strip(), (r.get("To") or "").strip()
        if not s:
            continue
        try:
            out.append({"s": s, "n": (r.get("Security Name") or "")[:28], "f": f, "t": t})
        except (ValueError, KeyError):
            continue
    return out

def sec_bands_for(d):
    """NSE sec_list file: har stock ka current circuit band"""
    url = "https://nsearchives.nseindia.com/content/equities/sec_list_%s.csv" % d.strftime("%d%m%Y")
    try:
        req = urllib.request.Request(url, headers=UA)
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        rows = list(csv.DictReader(io.StringIO(raw)))
    except Exception:
        return None
    m = {}
    for r in rows:
        s = (r.get("Symbol") or "").strip()
        if not s:
            continue
        b = (r.get("Band") or "").strip()
        m[s] = "nb" if "no band" in b.lower() else b
    return m or None

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

    # sab stocks ka 7-din history (search ke liye): sym -> [d1..d7, flags"012", uc_hits, lc_hits, last_close, band]
    bands_map = sec_bands_for(used)
    all_stocks = {}
    for sym, x in st.items():
        if not sym:
            continue
        vals = []
        flags = []
        for hd in hist:
            p = hd["pct"].get(sym)
            vals.append(round(p, 1) if p is not None else None)
            flags.append("1" if sym in hd["uc"] else ("2" if sym in hd["lc"] else "0"))
        u = sum(1 for c in flags if c == "1")
        l = sum(1 for c in flags if c == "2")
        all_stocks[sym] = vals + ["".join(flags), u, l, round(x["c"], 1), (bands_map or {}).get(sym, "?")]

    # NSE circuit band changes (roz ka + 7-din history)
    bhist = []
    for dt, _x in days:
        ch = band_changes_for(dt)
        if ch is not None:
            bhist.append({"d": dt.strftime("%d %b"), "n": len(ch), "list": ch})
    today_ch = bhist[-1]["list"] if bhist else []
    bands = {
        "updated": used.strftime("%d %b %Y"),
        "ch": today_ch,
        "hist": bhist,
    }

    data = {
        "all": all_stocks,
        "bands": bands,
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
          "| all stocks:", len(all_stocks),
          "| band changes aaj:", len(today_ch), "| bands map:", len(bands_map) if bands_map else 0,
          "| 7d trend:", [(t["d"], t["uc"], t["lc"]) for t in tr])

if __name__ == "__main__":
    main()
