#!/usr/bin/env python3
"""oi_gti.py - Option chain OI (NSE F&O bhavcopy IDO rows) + GTI zones combo.
WAY2LAABH-style OI analysis (put/call walls, PCR, max pain) + Manish GTI zones.
Output: data/oi-gti.json -> GTI section ka combo card."""
import csv
import io
import json
import os
import sys
import urllib.request
import zipfile
from datetime import date, datetime, timedelta

DATA = "data"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}
SYMS = {"NIFTY": "NIFTY 50", "BANKNIFTY": "BANKNIFTY"}

def fetch_rows():
    for back in range(0, 5):
        d = date.today() - timedelta(days=back)
        if d.weekday() >= 5 and back == 0:
            continue
        try:
            url = (f"https://nsearchives.nseindia.com/content/fo/"
                   f"BhavCopy_NSE_FO_0_0_0_{d:%Y%m%d}_F_0000.csv.zip")
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                z = zipfile.ZipFile(io.BytesIO(r.read()))
            with z.open(z.namelist()[0]) as f:
                text = f.read().decode("utf-8", "ignore")
            return d, list(csv.DictReader(io.StringIO(text)))
        except Exception as e:
            print(f"no bhavcopy {d}: {e}")
    return None, None

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return 0.0

def pdt(s):
    for f in ("%d-%m-%Y", "%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, f).date()
        except (ValueError, TypeError):
            pass
    return date.max

def combo_logic(sym, oistrikes, spot, gti_sym):
    """GTI zones + OI walls ka combo verdict (Hinglish)."""
    ks = sorted(oistrikes)
    if not ks or not gti_sym or not gti_sym.get("day_zones"):
        return {"support": "", "resistance": "", "verdict": "GTI zones nahi mile"}
    sd, ss = gti_sym["day_zones"]["SD"], gti_sym["day_zones"]["SS"]
    sd_mid = (sd[0] + sd[1]) / 2
    ss_mid = (ss[0] + ss[1]) / 2
    put_wall = max(ks, key=lambda k: oistrikes[k]["pe"])
    call_wall = max(ks, key=lambda k: oistrikes[k]["ce"])
    tol = 0.8 if sym == "NIFTY" else 300

    if abs(put_wall - sd_mid) <= tol:
        sup_note = ("GTI SD zone " + str(int(sd[0])) + "-" + str(int(sd[1]))
                    + " + PUT wall " + str(int(put_wall)) + " = DOUBLE support (strong base)")
    else:
        sup_note = "PUT wall " + str(int(put_wall)) + " (GTI SD " + str(int(sd_mid)) + " se alag)"
    if abs(call_wall - ss_mid) <= tol:
        res_note = ("GTI SS zone " + str(int(ss[0])) + "-" + str(int(ss[1]))
                    + " + CALL wall " + str(int(call_wall)) + " = DOUBLE resistance (wall)")
    else:
        res_note = "CALL wall " + str(int(call_wall)) + " (GTI SS " + str(int(ss_mid)) + " se alag)"

    tot_pe = sum(v["pe"] for v in oistrikes.values())
    tot_ce = sum(v["ce"] for v in oistrikes.values())
    pcr = round(tot_pe / tot_ce, 2) if tot_ce else 0
    if pcr > 1.1:
        bias = "PCR " + str(pcr) + " > 1 - put writers hawaldaar, bullish bias"
    elif pcr < 0.85:
        bias = "PCR " + str(pcr) + " < 0.85 - call writers dominant, bearish bias"
    else:
        bias = "PCR " + str(pcr) + " - neutral range (put vs call barabar)"
    if put_wall < spot < call_wall:
        rng = ("Spot " + str(int(spot)) + " walls ke beech mein (" + str(int(put_wall))
               + " - " + str(int(call_wall)) + ") - rangebound")
    elif spot <= put_wall:
        rng = "Spot PUT wall " + str(int(put_wall)) + " ke neeche/par - support test ho raha"
    else:
        rng = "Spot CALL wall " + str(int(call_wall)) + " ke upar - breakout mode"
    return {"support": sup_note, "resistance": res_note, "verdict": bias + ". " + rng}

def max_pain(oistrikes):
    ks = sorted(oistrikes)
    best, best_pain = None, None
    for s in ks:
        pain = sum(oistrikes[k]["ce"] * max(0, s - k) + oistrikes[k]["pe"] * max(0, k - s) for k in ks)
        if best_pain is None or pain < best_pain:
            best, best_pain = s, pain
    return best

def main():
    d, rows = fetch_rows()
    if not rows:
        print("ERROR: no bhavcopy", file=sys.stderr)
        sys.exit(1)
    try:
        gti = json.load(open(DATA + "/gti.json"))
    except Exception:
        gti = {"symbols": {}}
    out = {"updated": datetime.now().isoformat(), "date": d.strftime("%d-%m-%Y"),
           "source": "NSE F&O bhavcopy (EOD)", "symbols": {}}
    for nse_sym, gti_key in SYMS.items():
        opts = [r for r in rows if r.get("FinInstrmTp") == "IDO" and r.get("TckrSymb") == nse_sym]
        if not opts:
            print("no IDO rows for", nse_sym)
            continue
        exp = min(set(r["XpryDt"] for r in opts), key=pdt)
        rowset = [r for r in opts if r["XpryDt"] == exp]
        strikes = {}
        spot = 0
        for r in rowset:
            k = int(num(r.get("StrkPric")))
            o = strikes.setdefault(k, {"ce": 0, "ce_chg": 0, "pe": 0, "pe_chg": 0})
            spot = num(r.get("UndrlygPric")) or spot
            if r.get("OptnTp") == "CE":
                o["ce"] += int(num(r.get("OpnIntrst")))
                o["ce_chg"] += int(num(r.get("ChngInOpnIntrst")))
            else:
                o["pe"] += int(num(r.get("OpnIntrst")))
                o["pe_chg"] += int(num(r.get("ChngInOpnIntrst")))
        if not spot:
            spot = num(rowset[0].get("UndrlygPric"))
        put_wall = max(strikes, key=lambda k: strikes[k]["pe"])
        call_wall = max(strikes, key=lambda k: strikes[k]["ce"])
        tot_pe = sum(v["pe"] for v in strikes.values())
        tot_ce = sum(v["ce"] for v in strikes.values())
        near = sorted(strikes, key=lambda k: abs(k - spot))[:7]
        near.sort()
        gti_sym = gti.get("symbols", {}).get(gti_key, {})
        entry = {
            "spot": round(spot, 1), "expiry": pdt(exp).strftime("%d %b"),
            "put_wall": put_wall, "put_wall_oi": strikes[put_wall]["pe"],
            "call_wall": call_wall, "call_wall_oi": strikes[call_wall]["ce"],
            "pcr": round(tot_pe / tot_ce, 2) if tot_ce else 0,
            "max_pain": max_pain(strikes),
            "total_oi": tot_pe + tot_ce,
            "chain": [{"strike": k, "ce": strikes[k]["ce"], "ce_chg": strikes[k]["ce_chg"],
                       "pe": strikes[k]["pe"], "pe_chg": strikes[k]["pe_chg"]} for k in near],
            "gti": {"day_poc": gti_sym.get("day_poc"),
                    "SD": gti_sym.get("day_zones", {}).get("SD"),
                    "SS": gti_sym.get("day_zones", {}).get("SS"),
                    "golden": gti_sym.get("week_poc")},
            "combo": combo_logic(nse_sym, strikes, spot, gti_sym),
        }
        out["symbols"][gti_key] = entry
        print(nse_sym, "OK: put", put_wall, "call", call_wall, "pcr", entry["pcr"],
              "maxpain", entry["max_pain"])
    os.makedirs(DATA, exist_ok=True)
    with open(DATA + "/oi-gti.json", "w") as f:
        json.dump(out, f, indent=1)
    print("oi-gti.json written:", len(out["symbols"]), "symbols")

if __name__ == "__main__":
    main()
