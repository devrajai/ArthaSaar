#!/usr/bin/env python3
"""F&O futures collector — NSE UDiFF bhavcopy (free, no key).
Gives the full monthly contract chain for index futures (NIFTY, BANKNIFTY, ...)
and the near-month contract for top stock futures by open interest.
Also computes NIFTY Put/Call Ratio (OI + volume) and max pain from the
options (IDO) rows in the same file.
Output: data/futures.json — feeds the website Futures tab + Dashboard.

Note: NSE lists only 3 monthly expiries at a time (near/next/far) — there are
no yearly-dated futures in India; this file captures every active expiry.
"""
import csv
import io
import json
import sys
import urllib.request
import zipfile
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

def fetch_zip(d):
    url = (f"https://nsearchives.nseindia.com/content/fo/"
           f"BhavCopy_NSE_FO_0_0_0_{d:%Y%m%d}_F_0000.csv.zip")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        return zipfile.ZipFile(io.BytesIO(r.read()))

def rows_for(d):
    z = fetch_zip(d)
    with z.open(z.namelist()[0]) as f:
        text = f.read().decode("utf-8", "ignore")
    return list(csv.DictReader(io.StringIO(text)))

def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None

def main():
    rows = None
    used = None
    for back in range(0, 5):  # today, then step back over weekends/holidays
        d = date.today() - timedelta(days=back)
        if d.weekday() >= 5 and back == 0:
            continue
        try:
            rows = rows_for(d)
            used = d
            break
        except Exception as e:
            print(f"no bhavcopy for {d}: {e}")
    if not rows:
        print("ERROR: no bhavcopy found in last 5 days", file=sys.stderr)
        sys.exit(1)

    def fnum(r, k):
        return num(r.get(k))

    # index futures (IDF) — full expiry chain per symbol
    indices = {}
    for r in rows:
        if r["FinInstrmTp"] != "IDF":
            continue
        sym = r["TckrSymb"]
        indices.setdefault(sym, {"underlying": fnum(r, "UndrlygPric"),
                                 "contracts": []})
        indices[sym]["contracts"].append({
            "expiry": r["XpryDt"],
            "close": fnum(r, "ClsPric"),
            "oi": int(num(r["OpnIntrst"]) or 0),
            "oi_chg": int(num(r["ChngInOpnIntrst"]) or 0),
            "volume": int(num(r["TtlTradgVol"]) or 0),
        })
    for v in indices.values():
        v["contracts"].sort(key=lambda c: c["expiry"])

    # stock futures (STF) — near-month contract, ranked by open interest
    best = {}
    for r in rows:
        if r["FinInstrmTp"] != "STF":
            continue
        if int(num(r["OpnIntrst"]) or 0) <= 0:
            continue  # skip dead series
        sym = r["TckrSymb"]
        exp = r["XpryDt"]
        cur = best.get(sym)
        if cur is None or exp < cur["expiry"]:
            best[sym] = {"symbol": sym, "expiry": exp,
                         "close": fnum(r, "ClsPric"),
                         "underlying": fnum(r, "UndrlygPric"),
                         "oi": int(num(r["OpnIntrst"]) or 0),
                         "oi_chg": int(num(r["ChngInOpnIntrst"]) or 0)}
    stocks = sorted(best.values(), key=lambda s: -s["oi"])
    for s in stocks:
        if s["close"] and s["underlying"]:
            s["basis_pct"] = round((s["close"] - s["underlying"])
                                   / s["underlying"] * 100, 2)

    # ---- options analytics (IDO rows): Nifty PCR + max pain ----
    ido = [r for r in rows if r["FinInstrmTp"] == "IDO"]
    oint = lambda r: int(num(r["OpnIntrst"]) or 0)
    ovat = lambda r: int(num(r["TtlTradgVol"]) or 0)
    pcr = {}
    try:
        nifty = [r for r in ido if r["TckrSymb"] == "NIFTY"]
        ce_oi = sum(oint(r) for r in nifty if r["OptnTp"] == "CE")
        pe_oi = sum(oint(r) for r in nifty if r["OptnTp"] == "PE")
        ce_v = sum(ovat(r) for r in nifty if r["OptnTp"] == "CE")
        pe_v = sum(ovat(r) for r in nifty if r["OptnTp"] == "PE")
        all_ce = sum(oint(r) for r in ido if r["OptnTp"] == "CE")
        all_pe = sum(oint(r) for r in ido if r["OptnTp"] == "PE")
        # max pain on nearest expiry
        from collections import defaultdict
        nearest = min(set(r["XpryDt"] for r in nifty))
        near = [r for r in nifty if r["XpryDt"] == nearest]
        ois = defaultdict(lambda: {"CE": 0, "PE": 0})
        for r in near:
            ois[num(r["StrkPric"])][r["OptnTp"]] += oint(r)
        strikes = sorted(ois)
        max_pain = None
        if strikes:
            max_pain = int(min(strikes, key=lambda S: sum(
                o["CE"] * max(0, S - K) + o["PE"] * max(0, K - S)
                for K, o in ois.items())))
        pcr = {
            "nifty_pcr_oi": round(pe_oi / ce_oi, 3) if ce_oi else None,
            "nifty_pcr_vol": round(pe_v / ce_v, 3) if ce_v else None,
            "nifty_call_oi": ce_oi, "nifty_put_oi": pe_oi,
            "all_index_pcr_oi": round(all_pe / all_ce, 3) if all_ce else None,
            "nifty_max_pain": max_pain,
            "nifty_expiry": nearest,
            "nifty_spot": fnum(nifty[0], "UndrlygPric") if nifty else None,
        }
        print("PCR:", pcr)
    except Exception as e:  # noqa: BLE001
        print("PCR computation failed:", e)

    payload = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "date": used.strftime("%d-%m-%Y"),
        "note": ("NSE F&O futures (EOD bhavcopy). Index futures show every "
                 "active monthly expiry. India has no yearly-dated futures — "
                 "3 monthly contracts exist at a time."),
        "indices": [{"symbol": k, **v} for k, v in sorted(indices.items())],
        "pcr": pcr,
        "stocks": stocks[:80],
        "stock_count": len(stocks),
    }
    (DATA / "futures.json").write_text(json.dumps(payload, indent=1))
    print(f"wrote data/futures.json — {len(indices)} index futures chains, "
          f"{len(stocks)} stock futures ({used})")

if __name__ == "__main__":
    main()
