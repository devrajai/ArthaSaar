#!/usr/bin/env python3
"""greeks.py - OPTION GREEKS + LTP CALCULATOR (EOD, free NSE FO bhavcopy se):
- Har F&O underlying ka option chain: price, IV (Black-Scholes se reverse-engineer),
  Delta, Gamma, Theta (per day), Vega + theoretical price vs market price
- Interactive LTP calculator front-end me hai (greeks.js)
Note: EOD close se compute hota hai - live Greeks nahi, indicative hai."""
import io, json, csv, zipfile, urllib.request, math
from datetime import datetime, timedelta

IST = datetime.utcnow() + timedelta(hours=5, minutes=30)
TODAY = IST
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
R = 0.065  # risk-free rate approx (RBI)

def N(x): return 0.5 * math.erfc(-x / math.sqrt(2.0))
def phi(x): return math.exp(-x * x / 2.0) / math.sqrt(2.0 * math.pi)

def bs(S, K, T, r, sig, typ):
    if T <= 0 or sig <= 0: return 0.0
    d1 = (math.log(S / K) + (r + sig * sig / 2.0) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    if typ == "c":
        return S * N(d1) - K * math.exp(-r * T) * N(d2)
    return K * math.exp(-r * T) * N(-d2) - S * N(-d1)

def greeks(S, K, T, r, sig, typ):
    if T <= 0 or sig <= 0:
        return [0.0, 0.0, 0.0, 0.0]
    d1 = (math.log(S / K) + (r + sig * sig / 2.0) * T) / (sig * math.sqrt(T))
    d2 = d1 - sig * math.sqrt(T)
    if typ == "c":
        delta = N(d1)
        theta = (-S * phi(d1) * sig / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * N(d2)) / 365.0
    else:
        delta = N(d1) - 1.0
        theta = (-S * phi(d1) * sig / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * N(-d2)) / 365.0
    gamma = phi(d1) / (S * sig * math.sqrt(T))
    vega = S * phi(d1) * math.sqrt(T) / 100.0
    return [delta, gamma, theta, vega]

def iv_solve(S, K, T, r, mkt, typ):
    if mkt <= 0 or T <= 0:
        return None
    intr = max(0.0, S - K) if typ == "c" else max(0.0, K - S)
    if mkt <= intr * 1.0005:  # intrinsic ke bahar premium nahi -> IV unstable
        return None
    lo, hi = 0.005, 4.0
    for _ in range(60):
        mid = (lo + hi) / 2.0
        p = bs(S, K, T, r, mid, typ)
        if p > mkt: hi = mid
        else: lo = mid
    return mid

def main():
    url = "https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_%s_F_0000.csv.zip" % TODAY.strftime("%Y%m%d")
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read()
    zf = zipfile.ZipFile(io.BytesIO(raw))
    rows = list(csv.DictReader(io.TextIOWrapper(zf.open(zf.namelist()[0]), encoding="utf-8", errors="ignore")))
    data = {}
    for r in rows:
        if r.get("FinInstrmTp") not in ("STO", "IDO"):
            continue
        sym = (r.get("TckrSymb") or "").strip()
        try:
            K = float(r.get("StrkPric") or 0)
            px = float(r.get("ClsPric") or 0)
            oi = float(r.get("OpnIntrst") or 0)
            spot = float(r.get("UndrlygPric") or 0)
        except Exception:
            continue
        if not sym or K <= 0 or px <= 0 or spot <= 0:
            continue
        exp = (r.get("XpryDt") or "")[:10]
        d = data.setdefault(sym, {"s": spot, "e": {}})
        e = d["e"].setdefault(exp, {"c": {}, "p": {}})
        typ = "c" if r.get("OptnTp") == "CE" else "p"
        m = e[typ]
        if K not in m or oi > m[K][1]:
            m[K] = (px, oi)
    def tdays(exp):
        try:
            ed = datetime.strptime(exp, "%Y-%m-%d")
            return max(0.25, (ed - TODAY).total_seconds() / 86400.0) / 365.0
        except Exception:
            return None
    res = {}
    for sym, d in data.items():
        exps = sorted(d["e"].keys())[:2]
        if not exps:
            continue
        S = d["s"]
        chains = []
        for exp in exps:
            T = tdays(exp)
            if not T or (not d["e"][exp]["c"] and not d["e"][exp]["p"]):
                continue
            ks = sorted(set(list(d["e"][exp]["c"].keys()) + list(d["e"][exp]["p"].keys())))
            ks = sorted(sorted(ks, key=lambda k: abs(math.log(k / S)))[:18])
            rows3 = []
            for K in ks:
                row = [K]
                for typ in ("c", "p"):
                    m = d["e"][exp][typ].get(K)
                    if m:
                        px, oi = m
                        iv = iv_solve(S, K, T, R, px, typ)
                        if iv:
                            g = greeks(S, K, T, R, iv, typ)
                            row += [round(px, 2), round(iv * 100, 1), round(g[0], 2), round(g[2], 1)]
                        else:
                            row += [round(px, 2), None, None, None]
                    else:
                        row += [None, None, None, None]
                rows3.append(row)
            chains.append({"d": exp, "r": rows3})
        if chains:
            res[sym] = {"s": S, "c": chains}
    o = {"updated": TODAY.strftime("%d %b %Y"), "r": R, "u": res}
    with open("data/greeks.json", "w") as f:
        json.dump(o, f, separators=(",", ":"))
    print("OK greeks: underlyings =", len(res), "| sample:", list(res)[:8])

if __name__ == "__main__":
    main()
