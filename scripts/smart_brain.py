#!/usr/bin/env python3
"""smart_brain.py — auto-analyst.
Combines existing free data (screener technicals + TimesFM AI + OI + breadth +
FII/DII + filings) into one smart-brain.json:
  1. confluence  — top bull/bear stocks by agreement score
  2. guess       — kal ka regime call (breadth + FII/DII + AI Nifty)
  3. results     — result radar (upcoming board meetings, recent results)
  4. highs/lows/rs — 52-week high/low + relative-strength radar
Run daily after brain-collect and timesfm. No new APIs, no deps.
"""
import json, re, datetime as dt, os

def load(p):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return {}

bs = load("data/brain-screener.json")
stocks = {}
for s in bs.get("stocks", []):
    stocks[s["symbol"]] = s
tf = load("data/timesfm_forecasts.json")
breadth = load("data/breadth.json")
fii = load("data/fii-dii.json")
fut = load("data/futures.json")
fil = load("data/filings.json")

chgs = sorted(s["change_pct"] for s in stocks.values() if s.get("change_pct") is not None)
market_med = chgs[len(chgs) // 2] if chgs else 0.0

futmap = {}
for r in fut.get("stocks", []):
    sym = r.get("symbol")
    o = r.get("oi_chg") or 0
    if sym and sym not in futmap and o:
        futmap[sym] = o

def conf(f):
    sym = (f.get("symbol") or "").split(".")[0].lstrip("^")
    s = stocks.get(sym)
    if not s or s.get("price") is None:
        return None
    sc, why = 0, []
    t = f.get("median_chg_pct") or 0
    if t > 0.5:
        sc += max(8, min(25, t * 2.5)); why.append("AI↑")
    elif t < -0.5:
        sc -= max(8, min(25, -t * 2.5)); why.append("AI↓")
    if s.get("above_ema200"): sc += 20; why.append(">EMA200")
    else: sc -= 20
    if (s.get("ema20") or 0) > (s.get("ema200") or 0): sc += 15; why.append("trend up")
    else: sc -= 15
    r = s.get("rsi14") or 50
    if 50 <= r <= 70: sc += 15; why.append("RSI ok")
    elif r > 75: sc -= 8; why.append("RSI garam")
    elif r < 32: sc -= 5; why.append("RSI giraa")
    fh = s.get("from_52w_high_pct")
    if fh is not None and fh > -12: sc += 10; why.append("52wH paas")
    elif fh is not None and fh < -40: sc -= 10
    if (s.get("macd_hist") or 0) > 0: sc += 10
    else: sc -= 10
    o = futmap.get(s["symbol"])
    cp = s.get("change_pct")
    if o and cp is not None:
        if o > 0 and cp > 0.5: sc += 5; why.append("OI long")
        elif o > 0 and cp < -0.5: sc -= 5; why.append("OI short")
    return {"symbol": s["symbol"], "name": f.get("name") or s["symbol"],
            "price": s["price"], "chg": cp, "score": round(sc), "why": ", ".join(why)}

cands = [c for c in (conf(f) for f in tf.get("forecasts", []) if f.get("cat") == "stock") if c]
bull = sorted(cands, key=lambda c: -c["score"])[:8]
bear = sorted(cands, key=lambda c: c["score"])[:8]

# ---- kal ka guess ----
score, pts = 50.0, []
ab = breadth.get("above_ema200_pct")
if ab is not None:
    score += (ab - 50) * 0.6
    pts.append("Breadth: %.0f%% stocks EMA200 ke upar" % ab)
cat = (fii.get("categories") or {})
fnet = cat.get("FII/FPI", {}).get("net_cr")
dnet = cat.get("DII", {}).get("net_cr")
if fnet is not None:
    score += max(-10, min(10, fnet / 500.0))
    pts.append("FII net %s%.0f Cr" % ("+" if fnet >= 0 else "", fnet))
if dnet is not None:
    score += max(-6, min(6, dnet / 800.0))
    pts.append("DII net %s%.0f Cr" % ("+" if dnet >= 0 else "", dnet))
nf = next((f for f in tf.get("forecasts", [])
          if f.get("cat") == "index" and
          ((f.get("symbol") or "") in ("^NSEI", "^BSESN") or "nifty 50" in (f.get("name") or "").lower())), None)
if nf:
    n = nf.get("median_chg_pct") or 0
    nm = "Nifty" if (nf.get("symbol") or "") == "^NSEI" else "Sensex"
    score += max(-8, min(8, n))
    pts.append("TimesFM: %s 21-din %+.1f%%" % (nm, n))
if breadth.get("rsi_above_60"):
    pts.append("%d stocks RSI>60 (momentum)" % breadth["rsi_above_60"])
if breadth.get("rsi_below_40"):
    pts.append("%d stocks RSI<40 (kamzor)" % breadth["rsi_below_40"])
score = int(max(0, min(100, round(score))))
verdict = ("STRONG BULLISH" if score >= 65 else "BULLISH TILT" if score >= 55 else
           "NEUTRAL / MIXED" if score >= 45 else "BEARISH TILT" if score >= 35 else "STRONG BEARISH")
guess = {"score": score, "verdict": verdict, "points": pts}

# ---- result radar ----
today = dt.date.today()
upc = []
for x in fil.get("filings", []):
    sub = x.get("subject") or ""
    if x.get("category") == "Board Meeting":
        m = re.search(r"(\d{2})[/-](\d{2})[/-](\d{4})", sub)
        if not m:
            continue
        try:
            rd = dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            continue
        if 0 <= (rd - today).days <= 15 and "outcome" not in sub.lower()[:20]:
            upc.append({"symbol": x["symbol"], "company": x.get("company") or x["symbol"],
                        "date": rd.isoformat(), "note": "board meeting — result aa sakta hai",
                        "chg": (stocks.get(x["symbol"]) or {}).get("change_pct")})
    elif x.get("category") in ("Results", "Investor Presentation"):
        try:
            d = dt.date.fromisoformat(x["date"])
        except ValueError:
            continue
        if 0 <= (today - d).days <= 5:
            upc.append({"symbol": x["symbol"], "company": x.get("company") or x["symbol"],
                        "date": x["date"],
                        "note": ("result diya" if x["category"] == "Results" else "investor presentation"),
                        "chg": (stocks.get(x["symbol"]) or {}).get("change_pct")})
upc.sort(key=lambda r: r["date"])

def slim(s, extra=None):
    d = {"symbol": s["symbol"], "company": (s.get("company") or "")[:26],
         "price": s.get("price"), "chg": s.get("change_pct")}
    if extra:
        d.update(extra)
    return d

hi = sorted((s for s in stocks.values()
             if s.get("price") and (s.get("from_52w_high_pct") or -99) > -1.5),
            key=lambda s: -s["change_pct"])[:12]
lo = sorted((s for s in stocks.values()
             if s.get("price") and s.get("low_52w") and
             s["price"] / s["low_52w"] - 1 < 0.015),
            key=lambda s: s["change_pct"])[:12]
rs = sorted((s for s in stocks.values() if (s.get("tier") or 9) <= 1 and s.get("change_pct") is not None),
            key=lambda s: -(s["change_pct"] - market_med))[:12]
rs = [slim(s, {"rs": round(s["change_pct"] - market_med, 1)}) for s in rs]

out = {"updated": dt.datetime.now(dt.timezone.utc).isoformat(),
       "market_med": round(market_med, 2), "guess": guess, "bull": bull, "bear": bear,
       "results": upc[:12], "highs": [slim(s) for s in hi], "lows": [slim(s) for s in lo],
       "rs": rs,
       "disclaimer": "Rule-based auto-analysis on free EOD data. Not investment advice — apna dimaag lagao."}
with open("data/smart-brain.json", "w") as f:
    json.dump(out, f, ensure_ascii=False)
print("smart-brain.json written: bull=%d bear=%d results=%d highs=%d lows=%d rs=%d score=%d" %
      (len(bull), len(bear), len(upc), len(hi), len(lo), len(rs), score))
