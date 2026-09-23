#!/usr/bin/env python3
"""bigplayer.py - BIG PLAYER RADAR (Whale / Shark / Pig - Dev ka idea, Manish podcast framework):
WHALE = bulk + block deals (client-wise names milte hain!)
SHARK  = futures OI buildup (long/short buildup = bade players position bana rahe)
OPTION SHARK = options contracts me sabse bada OI change
PIG = sabse zyada traded stocks (jahan bheed khelti hai - "pigs get slaughtered")
Data: NSE free files - bulk.csv, block.csv, FO bhavcopy, CM bhavcopy"""
import io, json, csv, zipfile, urllib.request
from datetime import datetime, timedelta

IST = datetime.utcnow() + timedelta(hours=5, minutes=30)
TODAY = IST
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get_csv_text(path):
    url = "https://nsearchives.nseindia.com/content/equities/" + path
    try:
        req = urllib.request.Request(url, headers=UA)
        return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    except Exception:
        return None

def bhav_fo():
    url = "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_%s_F_0000.csv.zip" % TODAY.strftime("%Y%m%d")
    try:
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
        zf = zipfile.ZipFile(io.BytesIO(raw))
        return list(csv.DictReader(io.TextIOWrapper(zf.open(zf.namelist()[0]), encoding="utf-8", errors="ignore")))
    except Exception:
        return None

def main():
    out = {"updated": TODAY.strftime("%d %b %Y"), "bulk": [], "block": [], "fut": [], "idxfut": [], "opts": [], "active": []}
    # ---- WHALE: bulk + block deals
    for key, fname in (("bulk", "bulk.csv"), ("block", "block.csv")):
        txt = get_csv_text(fname)
        if not txt or not txt.startswith("Date"):
            continue
        agg = {}
        for r in csv.DictReader(io.StringIO(txt)):
            sym = (r.get("Symbol") or "").strip()
            if not sym:
                continue
            try:
                qty = float(r.get("Quantity Traded") or 0)
                px = float(r.get("Trade Price / Wght. Avg. Price") or 0)
            except Exception:
                continue
            side = (r.get("Buy/Sell") or "").strip().upper()
            cli = (r.get("Client Name") or "").strip()
            val = qty * px
            a = agg.setdefault(sym, {"name": (r.get("Security Name") or sym)[:28], "bv": 0.0, "sv": 0.0, "cli": {}, "n": 0})
            a["n"] += 1
            if side == "BUY":
                a["bv"] += val
            else:
                a["sv"] += val
            if cli:
                cv = a["cli"].get(cli, [0.0, ""])[0] + val
                a["cli"][cli] = [cv, side]
        rows = []
        for sym, a in agg.items():
            clis = sorted(a["cli"].items(), key=lambda x: -x[1][0])[:3]
            rows.append({"s": sym, "n": a["name"], "bv": round(a["bv"] / 1e7, 1), "sv": round(a["sv"] / 1e7, 1),
                         "t": round((a["bv"] + a["sv"]) / 1e7, 1), "d": a["n"],
                         "c": [c[0][:26] + (" (" + c[1][1] + ")" if c[1][1] else "") for c in clis]})
        rows.sort(key=lambda x: -x["t"])
        out[key] = rows[:25]
    # ---- SHARK: FO bhavcopy
    fo = bhav_fo()
    if fo:
        stf, idf, opt = {}, {}, []
        for r in fo:
            t = r.get("FinInstrmTp")
            try:
                oi = float(r.get("OpnIntrst") or 0)
                coi = float(r.get("ChngInOpnIntrst") or 0)
                cls = float(r.get("ClsPric") or 0)
                prev = float(r.get("PrvsClsgPric") or 0)
                stl = float(r.get("SttlmPric") or cls)
            except Exception:
                continue
            sym = (r.get("TckrSymb") or "").strip()
            if not sym:
                continue
            if t == "STF" or t == "IDF":
                tgt = stf if t == "STF" else idf
                cur = tgt.get(sym)
                if cur is None or oi > cur[0]:
                    pchg = round(100 * (cls / prev - 1), 2) if prev else 0.0
                    tgt[sym] = [oi, coi, pchg, cls]
            elif t in ("STO", "IDO"):
                if abs(coi) > 0:
                    opt.append([sym, r.get("XpryDt", "")[2:7], r.get("StrkPric", "").replace(".00", ""), r.get("OptnTp", ""), int(coi), stl])
        def classify(pchg, coi):
            if pchg >= 0 and coi > 0: return "LONG BUILDUP"
            if pchg < 0 and coi > 0: return "SHORT BUILDUP"
            if pchg >= 0 and coi < 0: return "SHORT COVER"
            return "LONG UNWIND"
        for key, tgt, cap in (("fut", stf, 20), ("idxfut", idf, 8)):
            rows = []
            for sym, (oi, coi, pchg, cls) in tgt.items():
                val = coi * cls
                rows.append({"s": sym, "oi": int(oi), "coi": int(coi), "p": pchg, "k": classify(pchg, coi), "v": round(abs(val) / 1e7, 1)})
            rows.sort(key=lambda x: -x["v"])
            out[key] = rows[:cap]
        opt.sort(key=lambda x: -abs(x[4] * x[5]))
        out["opts"] = [{"s": o[0], "e": o[1], "k": o[2], "t": o[3], "coi": o[4]} for o in opt[:15]]
    # ---- PIG: most traded stocks from CM bhavcopy (turnover Cr)
    try:
        url = "https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_%s_F_0000.csv.zip" % TODAY.strftime("%Y%m%d")
        raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read()
        zf = zipfile.ZipFile(io.BytesIO(raw))
        rd = csv.DictReader(io.TextIOWrapper(zf.open(zf.namelist()[0]), encoding="utf-8", errors="ignore"))
        acts = []
        for r in rd:
            if r.get("SctySrs") not in ("EQ", "BE", "BZ", "SM", "ST"):
                continue
            try:
                trf = float(r.get("TtlTrfVal") or 0)
            except Exception:
                continue
            if trf > 0:
                acts.append([r.get("TckrSymb"), round(trf / 1e7, 0)])
        acts.sort(key=lambda x: -x[1])
        out["active"] = acts[:15]
    except Exception as e:
        print("active skip:", e)
    with open("data/bigplayer.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    print("OK bigplayer: bulk=%d block=%d fut=%d idxfut=%d opts=%d" % (len(out["bulk"]), len(out["block"]), len(out["fut"]), len(out["idxfut"]), len(out["opts"])))

if __name__ == "__main__":
    main()
