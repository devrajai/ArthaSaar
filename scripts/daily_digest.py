#!/usr/bin/env python3
"""daily_digest.py - 21:10 IST: kya badla aaj - 52w highs/lows, movers, volume garam, mood, breadth, FII, social buzz."""
import sys, datetime
sys.path.insert(0, "scripts")
from tghelp import jload, send, crash_score, status

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
sc = jload("data/brain-screener.json")
stocks = sc.get("stocks") or []
mood = jload("data/mood.json")
sb = jload("data/smart-brain.json")
fd = jload("data/fii-dii.json")
score, _ = crash_score({"tf": jload("data/timesfm_forecasts.json"), "fu": jload("data/futures.json"),
                        "fd": fd, "br": jload("data/breadth.json"), "sb": sb})

hi = [s for s in stocks if s.get("high_52w") and s.get("price") and s["price"] >= s["high_52w"] * 0.999]
lo = [s for s in stocks if s.get("low_52w") and s.get("price") and s["price"] <= s["low_52w"] * 1.001]
up = sorted([s for s in stocks if (s.get("tier") or 9) <= 1], key=lambda s: -(s.get("change_pct") or 0))[:4]
dn = sorted([s for s in stocks if (s.get("tier") or 9) <= 1], key=lambda s: (s.get("change_pct") or 0))[:4]
vol = sorted(stocks, key=lambda s: -(s.get("vol_vs_avg20") or 0))[:4]

L = ["\U0001F4DD <b>Kya badla aaj - Daily Digest</b>", now.strftime("%A, %d %b"), ""]
if hi:
    extra = " (+%d)" % (len(hi) - 8) if len(hi) > 8 else ""
    L.append("\U0001F3AF 52w HIGH: " + ", ".join(s["symbol"] for s in hi[:8]) + extra)
if lo:
    L.append("\U0001F53F 52w LOW: " + ", ".join(s["symbol"] for s in lo[:6]))
if up:
    L.append("\U0001F534 Top: " + " - ".join("%s %+.0f%%" % (s["symbol"], s.get("change_pct") or 0) for s in up))
if dn:
    L.append("\U0001F53D Bottom: " + " - ".join("%s %+.0f%%" % (s["symbol"], s.get("change_pct") or 0) for s in dn))
if vol:
    L.append("\U0001F4C9 Volume garam: " + " - ".join("%s (%.1fx)" % (s["symbol"], s.get("vol_vs_avg20") or 0) for s in vol))
L.append("\U0001F4AC Mood: %s/100 (%s)" % (mood.get("overall", "-"), mood.get("tag", "-")))
cats = (fd.get("categories") or {})
fii = (cats.get("FII/FPI") or {}).get("net_cr"); dii = (cats.get("DII") or {}).get("net_cr")
if fii is not None:
    L.append("\U0001F4B8 FII %+.0f Cr | DII %+.0f Cr" % (fii, dii or 0))
st, _ = status(score)
L.append("\U0001F6A8 Crash score: %d/100 (%s)" % (score, st))
soc = jload("data/social.json")
tr = (soc.get("trending") or [])[:4]
if tr:
    L.append("\U0001F4E3 Social buzz: " + " - ".join("%s (%d, %d%% pos)" % (t["sym"], t["n"], t["pos_pct"]) for t in tr))
send("\n".join(L))
