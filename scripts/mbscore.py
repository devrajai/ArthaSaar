#!/usr/bin/env python3
"""ArthaSaar Score (TM) - per-stock 100-point combo:
Fundamentals 25 + Technicals 25 + News Sentiment 25 + Trend AI 25.
Plus Smart Money Score 0-10 (FII/DII/promoter/pledge/accumulation) + red flags.
Inputs (free, existing): screener-fundamentals.json, brain-screener.json,
news-volume.json, radar.json. Output: data/mb-score.json"""
import json, os
from datetime import datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime.now(IST)

def jload(p):
    if os.path.exists(p):
        try: return json.load(open(p))
        except Exception: return {}
    return {}

def num(v, d=None):
    try:
        if v is None: return d
        return float(v)
    except Exception: return d

def f_score(e):
    """Fundamentals /25"""
    s = 0
    pe = num(e.get("Stock P/E"))
    if pe is None: s += 2
    elif pe <= 15: s += 5
    elif pe <= 25: s += 4
    elif pe <= 40: s += 2
    roe = num(e.get("ROE"))
    if roe is None: s += 2
    elif roe >= 20: s += 6
    elif roe >= 15: s += 5
    elif roe >= 10: s += 3
    elif roe >= 5: s += 2
    roce = num(e.get("ROCE"))
    if roce is None: s += 1
    elif roce >= 20: s += 4
    elif roce >= 12: s += 3
    elif roce >= 8: s += 2
    sy = num(e.get("Sales_yoy"))
    if sy is None: s += 2
    elif sy >= 20: s += 5
    elif sy >= 10: s += 4
    elif sy >= 5: s += 3
    elif sy >= 0: s += 2
    py = num(e.get("Net Profit_yoy"))
    if py is None: s += 1
    elif py >= 25: s += 5
    elif py >= 10: s += 4
    elif py >= 0: s += 3
    return min(25, max(0, s))

def t_score(t):
    """Technicals /25"""
    s = 0
    if t.get("above_ema200"): s += 8
    f52 = num(t.get("from_52w_high_pct"))
    if f52 is None: s += 3
    elif f52 <= 5: s += 8
    elif f52 <= 15: s += 6
    elif f52 <= 30: s += 4
    elif f52 <= 50: s += 2
    rsi = num(t.get("rsi14"))
    if rsi is None: s += 3
    elif 50 <= rsi <= 70: s += 6
    elif 40 <= rsi < 50: s += 4
    elif 70 < rsi <= 80: s += 4
    elif 30 <= rsi < 40: s += 3
    elif rsi > 80: s += 1
    else: s += 2
    va = num(t.get("vol_vs_avg20"))
    if va is None: s += 1
    elif va >= 2: s += 3
    elif va >= 1.2: s += 2
    else: s += 1
    return min(25, max(0, s))

def s_score(sym, nv):
    """News sentiment /25 (news-volume.json 41 Nifty stocks; else neutral 12.5)"""
    c = None
    for x in nv.get("companies", []):
        if x.get("sym") == sym: c = x; break
    if not c: return 12.5, False
    v = 12.5 + c.get("sent", 0) * 0.1
    sp = c.get("spike", 1.0) or 1.0
    if sp >= 1.5: v += 2.5 if c.get("sent", 0) >= 0 else -2.5
    return min(25, max(0, round(v, 1))), True

def ai_score(t):
    """Trend AI /25 - MACD + EMA20 + streak + volume (machine signals)"""
    s = 0
    mh = num(t.get("macd_hist"))
    if mh is None: s += 4
    elif mh > 0: s += 8
    ema20 = num(t.get("ema20")); px = num(t.get("price"))
    if ema20 is None or px is None: s += 4
    elif px > ema20: s += 8
    cd = num(t.get("consec_days"), 0) or 0; chg = num(t.get("change_pct"), 0) or 0
    if cd >= 3 and chg > 0: s += 5
    elif chg < 0 and cd <= -3: s += 0
    else: s += 2
    va = num(t.get("vol_vs_avg20"))
    if va is None: s += 1
    elif va >= 1.5: s += 4
    else: s += 1
    return min(25, max(0, s))

def smart_money(e, pledge, in_acc):
    """Smart Money /10"""
    s = 0
    fii = num(e.get("fii_pct"))
    if fii is not None:
        if fii >= 20: s += 2
        elif fii >= 10: s += 1
        elif fii < 5: s -= 1
    dii = num(e.get("dii_pct"))
    if dii is not None:
        if dii >= 10: s += 2
        elif dii >= 5: s += 1
    prom = num(e.get("promoters_pct"))
    if prom is not None:
        if prom >= 50: s += 2
        elif prom >= 35: s += 1
        elif prom < 20: s -= 2
    if pledge is None or pledge <= 0: s += 1
    elif pledge > 50: s -= 4
    elif pledge > 25: s -= 2
    if in_acc: s += 2
    return min(10, max(0, s))

def main():
    sf = jload("data/screener-fundamentals.json")
    bs = jload("data/brain-screener.json")
    nv = jload("data/news-volume.json")
    rd = jload("data/radar.json")
    stocks = sf.get("stocks", {})
    if isinstance(stocks, list):
        stocks = {p[0]: p[1] for p in stocks if isinstance(p, list) and len(p) == 2}
    tech = {s.get("symbol"): s for s in bs.get("stocks", []) if isinstance(s, dict)}
    acc = set(x.get("sym") for x in rd.get("accumulation", []) if isinstance(x, dict))

    out, flags_all = {}, []
    for sym, e in stocks.items():
        if not isinstance(e, dict): continue
        t = tech.get(sym, {})
        pl = num(e.get("pledge_pct"))
        f = f_score(e)
        tc = t_score(t)
        se, hasnews = s_score(sym, nv)
        ai = ai_score(t)
        score = min(100, max(0, round(f + tc + se + ai)))
        sm = smart_money(e, pl, sym in acc)
        flags = []
        if pl is not None and pl > 25: flags.append("pledge " + str(round(pl)) + "%")
        prom = num(e.get("promoters_pct"))
        if prom is not None and prom < 20: flags.append("low promoter " + str(round(prom)) + "%")
        if flags:
            flags_all.append({"sym": sym, "flags": flags, "sm": sm})
        out[sym] = {
            "n": (t.get("company") or sym)[:28],
            "p": num(e.get("Current Price")),
            "s": score, "f": f, "t": tc, "se": se, "ai": ai, "sm": sm,
            "nw": 1 if hasnews else 0,
            "fl": ", ".join(flags) if flags else ""
        }
    ranked = sorted(out.items(), key=lambda kv: -kv[1]["s"])
    res = {
        "updated": NOW.strftime("%d %b %Y, %H:%M IST"),
        "note": "ArthaSaar Score = Fundamental 25 + Technical 25 + News Sentiment 25 + Trend AI 25 (MACD/volume machine signals; TimesFM index-level hai). Smart Money 0-10 = FII/DII/promoter/pledge/accumulation. Sentiment sirf 41 Nifty stocks ke liye live hai, baaki neutral 12.5. Indicative only - not advice.",
        "count": len(out),
        "stocks": out,
        "top": [k for k, _ in ranked[:30]],
        "flags": sorted(flags_all, key=lambda x: -x["sm"])[:40]
    }
    os.makedirs("data", exist_ok=True)
    with open("data/mb-score.json", "w") as f:
        json.dump(res, f, ensure_ascii=False, separators=(",", ":"))
    print("OK wrote data/mb-score.json -", len(out), "stocks")
    for k, v in ranked[:8]:
        print(f"  {k:12s} score={v['s']:3d} f={v['f']:2d} t={v['t']:2d} se={v['se']:4} ai={v['ai']:2d} sm={v['sm']:2d}")

if __name__ == "__main__":
    main()
