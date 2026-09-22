#!/usr/bin/env python3
"""stock_scores.py - Danelfin-style AI Score 1-10 per stock (technical + fundamental + combined).
Reads brain-screener.json + fundamentals.json. Writes data/stock-scores.json."""
import sys, json, datetime
sys.path.insert(0, "scripts")
from tghelp import jload, IST

sc = jload("data/brain-screener.json")
fu = jload("data/fundamentals.json")

def clamp(v, lo=0.0, hi=10.0):
    return max(lo, min(hi, v))

def tech_score(s):
    t = 0.0; r = []
    rsi = s.get("rsi14")
    if rsi is not None:
        if 40 <= rsi <= 65: t += 2.0; r.append("RSI healthy")
        elif 65 < rsi <= 75: t += 1.0; r.append("RSI garam")
        elif rsi > 75: t += 0.0; r.append("RSI overbought")
        elif rsi < 30: t += 0.5; r.append("RSI oversold bounce zone")
        else: t += 1.0
    if s.get("above_ema200"): t += 2.0; r.append("EMA200 ke upar")
    else: r.append("EMA200 ke neeche")
    if (s.get("macd_hist") or 0) > 0: t += 1.5; r.append("MACD positive")
    else: r.append("MACD negative")
    if (s.get("price") or 0) > (s.get("ema20") or 1e9): t += 1.5; r.append("EMA20 ke upar")
    v = s.get("vol_vs_avg20") or 1
    if 1.5 <= v <= 15: t += 1.5; r.append("volume %.1fx" % v)
    elif v > 15: t += 0.5; r.append("volume spike %.1fx" % v)
    if (s.get("consec_days") or 0) >= 3: t += 1.0; r.append("%d-din streak" % s["consec_days"])
    fp = s.get("from_52w_high_pct")
    if fp is not None:
        if -10 <= fp <= -1: t += 0.5; r.append("52w high ke paas")
    return clamp(t), r

def num(v):
    try:
        return float(v)
    except Exception:
        return None

def fund_score(sym):
    f = fu.get(sym)
    if not f: return None, []
    t = 5.0; r = []
    pe = num(f.get("trailingPE"))
    if pe is not None:
        if pe < 20: t += 2.0; r.append("PE %.1f sasta" % pe)
        elif pe < 35: t += 1.0; r.append("PE %.1f theek" % pe)
        else: t -= 1.5; r.append("PE %.1f mehenga" % pe)
    roe = num(f.get("returnOnEquity"))
    if roe is not None:
        if roe > 0.20: t += 1.5; r.append("ROE %.0f%% strong" % (roe * 100))
        elif roe > 0.12: t += 0.75; r.append("ROE %.0f%%" % (roe * 100))
        elif roe < 0.05: t -= 1.0; r.append("ROE kam %.0f%%" % (roe * 100))
    de = num(f.get("debtToEquity"))
    if de is not None:
        if de < 0.3: t += 1.0; r.append("karza kam")
        elif de > 1.0: t -= 1.0; r.append("karza zyada")
    pm = num(f.get("profitMargins"))
    if pm is not None and pm > 0.12: t += 1.0; r.append("margin %.0f%%" % (pm * 100))
    rg = num(f.get("revenueGrowth"))
    if rg is not None and rg > 0.10: t += 1.0; r.append("sales +%.0f%%" % (rg * 100))
    eg = num(f.get("earningsGrowth"))
    if eg is not None and eg > 0.10: t += 1.0; r.append("profit +%.0f%%" % (eg * 100))
    elif eg is not None and eg < 0: t -= 0.5; r.append("profit gira")
    return clamp(t), r

rows = []
for s in (sc.get("stocks") or []):
    if (s.get("tier") or 9) > 2: continue
    sym = s.get("symbol")
    if not sym: continue
    tec, tr = tech_score(s)
    fnd, fr = fund_score(sym)
    if fnd is None:
        total = tec * 0.7
        fr = ["fundamentals data nahi"]
    else:
        total = tec * 0.6 + fnd * 0.4
    rows.append({"sym": sym, "t": round(tec, 1), "f": (round(fnd, 1) if fnd is not None else None),
                 "total": round(total, 1), "r": (tr + fr)[:6]})
rows.sort(key=lambda x: -x["total"])
out = {"updated": datetime.datetime.now(IST).isoformat(),
       "scale": "1-10, higher = better. Technical 60% + Fundamental 40%. Gyaan nahi, hisaab.",
       "top": rows[:40]}
json.dump(out, open("data/stock-scores.json", "w"), indent=1)
print("scores:", len(rows), "| top:", [(r["sym"], r["total"]) for r in rows[:5]])
