#!/usr/bin/env python3
"""bullish_scan.py - Composite Bullish Scanner.
Fundamental score (PE/ROE/ROCE/profit growth/promoter) + Technical score
(delivery %, price, 52w position, GTI zones) -> week/month/year/long-term verdicts.
Inputs: data/screener-fundamentals.json, data/radar.json, data/gti.json, data/fii-dii.json
Output: data/bullish.json"""
import json
import os
from datetime import datetime


def load(p, default):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default


def clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def fund_score(s):
    """0-100 fundamental quality."""
    roe = s.get("ROE") or 0
    roce = s.get("ROCE") or 0
    pe = s.get("Stock P/E") or 0
    npf = s.get("Net Profit") or []
    sc = clamp(roe * 1.25, 0, 25)                   # ROE 20%+ = full 25
    sc += clamp(roce * 1.33, 0, 20)                 # ROCE 15%+ = full
    # profit growth: last 4 quarters vs previous 4
    if len(npf) >= 8:
        recent, prior = sum(npf[-4:]), sum(npf[-8:-4])
        if prior > 0:
            g = (recent - prior) / prior * 100
            sc += clamp(g / 5.0, 0, 20)   # 100% growth = full
        else:
            sc += 5
    else:
        sc += 4
    sc += clamp((s.get("Net Profit_yoy") or 0) / 3.0, 0, 15)   # YoY 45%+ = full
    # valuation: PE sweet spot, bubble penalize
    if 0 < pe <= 30:
        sc += 12
    elif pe <= 50:
        sc += 7
    elif pe > 0:
        sc += 2
    pr = s.get("promoters_pct") or 0
    sc += clamp((pr - 30) / 4.0, 0, 8)               # promoter 62%+ = full
    return round(clamp(sc), 1)


def tech_score(s, radar, gti):
    """0-100 technical strength (EOD based)."""
    sym = s.get("_sym", "")
    r = radar.get(sym, {})
    price = s.get("Current Price") or 0
    hi, lo = s.get("high_52w") or 0, s.get("low_52w") or 0
    sc = 0.0
    # 52-week position (30)
    if hi and lo and hi > lo and price:
        sc += clamp((price - lo) / (hi - lo) * 40.0, 0, 30)
    else:
        sc += 15
    # delivery + price action from radar (40)
    chg = r.get("chg")
    deliv = r.get("deliv")
    if chg is not None:
        sc += clamp(20 + chg * 4.0, 0, 20)
    else:
        sc += 10
    if deliv is not None:
        sc += clamp(deliv / 2.0, 0, 20)              # delivery 40%+ = full
    else:
        sc += 10
    # GTI zone (30)
    g = gti.get(sym)
    if g:
        rsi = g.get("rsi") or 50
        zone = (g.get("zone") or "").lower()
        z = 10
        if "sd" in zone:
            z = 26
        elif "ss" in zone:
            z = 4
        if 45 <= rsi <= 65:
            z += 4
        sc += clamp(z, 0, 30)
    else:
        sc += 15
    return round(clamp(sc), 1)


def verdict(w, m, y, d):
    if w >= 62 and m >= 58:
        return "STRONG BULLISH", "#77f37b"
    if w >= 50 and m >= 50 and y >= 50:
        return "BULLISH", "#a8e6a1"
    if w <= 40 or m <= 38:
        return "BEARISH", "#ff8b8b"
    return "NEUTRAL", "#9fb0c4"


def main():
    fund = load("data/screener-fundamentals.json", {})
    stocks = fund.get("stocks", {})
    radar = {}
    try:
        with open("data/radar.json") as f:
            rd = json.load(f)
        for row in rd.get("accumulation", []) + rd.get("hidden_selling", []) + rd.get("volume_blast", []):
            radar[row["sym"]] = row
    except Exception:
        pass
    gti = {}
    try:
        with open("data/gti.json") as f:
            gd = json.load(f)
        for sym, g in (gd.get("symbols") or {}).items():
            key = sym.split(":")[0].strip().upper()
            if "NIFTY" in key or "SENSEX" in key or "BANKNIFTY" in key:
                continue
            gti[key] = g
    except Exception:
        pass
    fii = load("data/fii-dii.json", {})
    bias = fii.get("bias") or fii.get("verdict") or "neutral"
    out = {}
    for sym, s in stocks.items():
        if not isinstance(s, dict):
            continue
        s["_sym"] = sym
        f = fund_score(s)
        t = tech_score(s, radar, gti)
        bias_bonus = 3 if "bull" in str(bias).lower() else (-3 if "bear" in str(bias).lower() else 0)
        w = clamp(t * 0.8 + f * 0.2 + bias_bonus)
        m = clamp(t * 0.5 + f * 0.5 + bias_bonus)
        y = clamp(f * 0.7 + t * 0.3)
        d = clamp(f)
        v, col = verdict(w, m, y, d)
        out[sym] = {"f": f, "t": t, "w": round(w, 1), "m": round(m, 1),
                    "y": round(y, 1), "d": round(d, 1), "v": v, "c": col,
                    "pe": s.get("Stock P/E"), "roe": s.get("ROE"),
                    "np_yoy": s.get("Net Profit_yoy"), "price": s.get("Current Price")}
    def top(key, n=12):
        return sorted(out.items(), key=lambda kv: kv[1][key], reverse=True)[:n]
    res = {
        "updated": datetime.now().isoformat(),
        "bias": bias,
        "count": len(out),
        "week": [{"s": k, **v} for k, v in top("w")],
        "month": [{"s": k, **v} for k, v in top("m")],
        "year": [{"s": k, **v} for k, v in top("y")],
        "decade": [{"s": k, **v} for k, v in top("d")],
        "bearish": [{"s": k, **v} for k, v in sorted(out.items(), key=lambda kv: kv[1]["m"])[:6]],
        "note": ("Week = technical (delivery/momentum/zones) | Month = 50-50 | Year = fundamentals-heavy | "
                 "Long-term = pure quality score (ROE/ROCE/growth). Ye scores hain, guarantee nahi - "
                 "koi bhi stock girta-sidharta rehta hai. SL hamesha."),
    }
    os.makedirs("data", exist_ok=True)
    with open("data/bullish.json", "w") as f:
        json.dump(res, f, separators=(",", ":"))
    print("bullish.json:", len(out), "stocks | top week:",
          res["week"][0]["s"], res["week"][0]["w"], "| top long-term:", res["decade"][0]["s"], res["decade"][0]["d"])


if __name__ == "__main__":
    main()
