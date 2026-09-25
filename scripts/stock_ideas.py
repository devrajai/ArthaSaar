#!/usr/bin/env python3
"""stock_ideas.py - monthly AI stock ideas (tech+fund+volume/OI ke reasons ke saath).
Telegram par 1 tareekh ko. Rule-based analysis hai, recommendation nahi."""
import sys, json, datetime
sys.path.insert(0, "scripts")
from tghelp import jload, send

sc = jload("data/brain-screener.json")
sc_map = {s.get("symbol"): s for s in (sc.get("stocks") or [])}
fu = jload("data/futures.json")
fu_map = {s.get("symbol"): s for s in (fu.get("stocks") or [])}
ss = jload("data/stock-scores.json")

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
L = ["\U0001F4A1 <b>ArthaSaar - Monthly AI Stock Ideas</b>", now.strftime("%B %Y"), ""]
picked = 0
for row in (ss.get("top") or []):
    sym = row.get("sym"); s = sc_map.get(sym)
    if not s: continue
    if not s.get("above_ema200"): continue
    o = fu_map.get(sym) or {}
    oi_note = ""
    if o.get("oi_chg_pct") is not None:
        if (o.get("change_pct") or 0) > 0 and o["oi_chg_pct"] > 3: oi_note = "OI buildup long"
        elif (o.get("change_pct") or 0) < 0 and o["oi_chg_pct"] < -3: oi_note = "OI shorts nikal rahe"
    horizon = "swing (2-6 hafte)" if (s.get("rsi14") or 50) > 60 else "positional (3-6 mahine)"
    entry = "%.0f-%.0f" % ((s.get("ema20") or s.get("price")) * 0.98, (s.get("ema20") or s.get("price")) * 1.02)
    stop = "%.0f (EMA200/-8%%)" % (s.get("ema200") or (s.get("price") or 0) * 0.92)
    tgt = "%.0f (52w high)" % (s.get("high_52w") or (s.get("price") or 0) * 1.15)
    L.append("\U0001F539 <b>%s</b> - AI score %s/10" % (sym, row.get("total")))
    L.append("Reasons: " + " - ".join((row.get("r") or [])[:4]))
    if oi_note: L.append("Derivative: " + oi_note)
    L.append("Approach: %s | Entry: %s | Stop: %s | Target: %s" % (horizon, entry, stop, tgt))
    L.append("")
    picked += 1
    if picked >= 5: break
if picked == 0:
    L.append("Aaj koi clean setup nahi - market weak hai, next month dekhte hain.")
L.append("\u26A0 Ye sirf technical+fundamental analysis hai, tip nahi. Apna risk khud dekho.")
send("\n".join(L))
