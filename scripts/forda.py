#!/usr/bin/env python3
"""forda.py - F&O RADAR: NSE F&O bhavcopy (UDiFF, free) se:
PCR, Max Pain (Nifty), futures basis, Long/Short Buildup, Short Covering,
Long Unwinding scanners + India VIX + Nifty PE (ind_close_all CSV).
Output: data/forda.json"""
import csv, io, json, os, sys, urllib.request, zipfile
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
TODAY = datetime.now(IST).date()
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def fetch(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        return urllib.request.urlopen(req, timeout=40).read()
    except Exception:
        return None

def fo_for(d):
    raw = fetch("https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_%s_F_0000.csv.zip" % d.strftime("%Y%m%d"))
    if not raw:
        return None, None
    try:
        zf = zipfile.ZipFile(io.BytesIO(raw))
        return list(csv.DictReader(io.StringIO(zf.read(zf.namelist()[0]).decode("utf-8", "ignore")))), d
    except Exception:
        return None, None

def idx_for(d):
    raw = fetch("https://nsearchives.nseindia.com/content/indices/ind_close_all_%s.csv" % d.strftime("%d%m%Y"))
    if not raw:
        return {}
    out = {}
    try:
        for r in csv.DictReader(io.StringIO(raw.decode("utf-8", "ignore"))):
            n = (r.get("Index Name") or "").strip().lower()
            if n in ("nifty 50", "india vix"):
                out[n] = r
    except Exception:
        pass
    return out

def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

def main():
    rows, used = None, None
    d = TODAY
    for _ in range(6):
        rows, used = fo_for(d)
        if rows:
            break
        d -= timedelta(days=1)
    if not rows:
        print("FAIL: F&O bhavcopy nahi mila")
        sys.exit(1)
    idx = idx_for(used)
    nifty_spot = fnum(idx.get("nifty 50", {}).get("Closing Index Value"))
    nifty_pe = fnum(idx.get("nifty 50", {}).get("P/E"))
    vix = fnum(idx.get("india vix", {}).get("Closing Index Value"))

    # --- Nifty options: nearest expiry, PCR + Max Pain ---
    calls, puts = {}, {}
    for r in rows:
        if r.get("FinInstrmTp") != "IDO" or (r.get("TckrSymb") or "").upper() != "NIFTY":
            continue
        try:
            exp = datetime.strptime(r["XpryDt"][:10], "%Y-%m-%d").date()
            k, oi = fnum(r["StrkPric"]), fnum(r["OpnIntrst"]) or 0.0
        except (KeyError, ValueError, TypeError):
            continue
        if not k or exp < used:
            continue
        tgt = calls if r["OptnTp"] == "CE" else puts
        tgt.setdefault(exp, {})[k] = tgt.setdefault(exp, {}).get(k, 0.0) + oi
    # futures (index): nearest expiry
    fut = None
    for r in rows:
        if r.get("FinInstrmTp") != "IDF" or (r.get("TckrSymb") or "").upper() != "NIFTY":
            continue
        try:
            exp = datetime.strptime(r["XpryDt"][:10], "%Y-%m-%d").date()
            c = fnum(r["ClsPric"])
        except (KeyError, ValueError, TypeError):
            continue
        if exp < used or not c:
            continue
        if fut is None or exp < fut[0]:
            fut = (exp, c)

    pcr = max_pain = None
    exp_dates = sorted(set(list(calls.keys()) + list(puts.keys())))
    if exp_dates:
        ex = exp_dates[0]
        ce, pe = calls.get(ex, {}), puts.get(ex, {})
        oi_ce = sum(ce.values())
        oi_pe = sum(pe.values())
        if oi_ce:
            pcr = round(oi_pe / oi_ce, 2)
        # max pain: strike jahan option writers ka total payout minimum
        strikes = sorted(set(list(ce.keys()) + list(pe.keys())))
        best, best_pain = None, None
        for s in strikes:
            pain = 0.0
            for k, v in ce.items():
                if s > k:
                    pain += (s - k) * v
            for k, v in pe.items():
                if s < k:
                    pain += (k - s) * v
            if best_pain is None or pain < best_pain:
                best_pain, best = pain, s
        max_pain = best

    basis = basis_pct = None
    if fut and nifty_spot:
        basis = round(fut[1] - nifty_spot, 1)
        basis_pct = round((fut[1] - nifty_spot) / nifty_spot * 100.0, 3)

    # --- Stock futures: buildup classification (per symbol, saari expiries ka OI jod ke) ---
    lb, sb, sc, lu = [], [], [], []
    agg = {}
    for r in rows:
        if r.get("FinInstrmTp") != "STF" or r.get("OptnTp"):
            continue
        sym = r.get("TckrSymb") or ""
        c, p = fnum(r.get("ClsPric")), fnum(r.get("PrvsClsgPric"))
        oi, chg = fnum(r.get("OpnIntrst")) or 0.0, fnum(r.get("ChngInOpnIntrst")) or 0.0
        val = (fnum(r.get("TtlTrfVal")) or 0.0) / 1e7
        try:
            exp = datetime.strptime(r["XpryDt"][:10], "%Y-%m-%d").date()
        except (KeyError, ValueError, TypeError):
            exp = used
        if not sym or not c or not p or p <= 0:
            continue
        a = agg.setdefault(sym, {"v": 0.0, "oi": 0.0, "chg": 0.0, "pct": None, "exp": used + timedelta(days=9999)})
        a["v"] += val
        a["oi"] += oi
        a["chg"] += chg
        if exp >= used and exp < a["exp"]:
            a["exp"] = exp
            a["pct"] = (c - p) / p * 100.0
    for sym, a in agg.items():
        if a["pct"] is None:
            continue
        poi = a["oi"] - a["chg"]
        if poi <= 0:
            continue
        oip = a["chg"] / poi * 100.0
        item = {"s": sym, "p": round(a["pct"], 2), "o": round(oip, 1), "v": round(a["v"], 1)}
        if a["pct"] > 0.2 and oip > 3:
            lb.append(item)
        elif a["pct"] < -0.2 and oip > 3:
            sb.append(item)
        elif a["pct"] > 0.2 and oip < -3:
            sc.append(item)
        elif a["pct"] < -0.2 and oip < -3:
            lu.append(item)

    def top(lst, n=12):
        return sorted(lst, key=lambda x: -x["v"])[:n]

    data = {
        "updated": used.strftime("%d %b %Y"),
        "note": "F&O bhavcopy (NSE) se EOD analysis. Max Pain = jahan option writers ko sabse kam loss (price wahi jhukta hai). PCR > 1.2 bullish-ish, < 0.8 bearish-ish. Basis+ = premium (bullish), basis- = discount. Indicative, advice nahi.",
        "spot": nifty_spot, "fut": fut[1] if fut else None, "fut_exp": fut[0].strftime("%d %b") if fut else "",
        "basis": basis, "basis_pct": basis_pct,
        "pcr": pcr, "max_pain": max_pain, "vix": vix, "nifty_pe": nifty_pe,
        "lb": top(lb), "sb": top(sb), "sc": top(sc), "lu": top(lu),
        "n_lb": len(lb), "n_sb": len(sb), "n_sc": len(sc), "n_lu": len(lu),
    }
    os.makedirs("data", exist_ok=True)
    with open("data/forda.json", "w") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print("OK wrote data/forda.json -", used, "- PCR:", pcr, "MaxPain:", max_pain, "Basis:", basis, "VIX:", vix, "PE:", nifty_pe,
          "| LB:", len(lb), "SB:", len(sb), "SC:", len(sc), "LU:", len(lu))

if __name__ == "__main__":
    main()
