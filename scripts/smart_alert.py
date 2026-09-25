#!/usr/bin/env python3
"""smart_alert.py - trigger-based alerts (no spam): Nifty big move, VIX spike,
crash score, FII selling, 52w high breaks. Dedup via data/alert-state.json."""
import sys, json, datetime
sys.path.insert(0, "scripts")
from tghelp import jload, yahoo, send, crash_score, status

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
key_date = now.strftime("%Y-%m-%d")
state = jload("data/alert-state.json")
alerts = []

p, pc = yahoo("%5ENSEI")
if p and pc:
    chg = (p / pc - 1) * 100
    if abs(chg) >= 1.5 and state.get("nifty_move") != key_date:
        alerts.append(("\U0001F4C8" if chg > 0 else "\U0001F534", "NIFTY %s (%+.2f%%) - bada move chal raha hai" % ("{:,.0f}".format(p), chg)))
        state["nifty_move"] = key_date

v, _ = yahoo("%5INDIAVIX")
if v and v >= 18 and state.get("vix") != key_date:
    alerts.append("\U0001F6A8 India VIX %.1f - dar badh raha hai" % v)
    state["vix"] = key_date

score, pts = crash_score({"tf": jload("data/timesfm_forecasts.json"), "fu": jload("data/futures.json"),
                          "fd": jload("data/fii-dii.json"), "br": jload("data/breadth.json"),
                          "sb": jload("data/smart-brain.json")})
st, _ = status(score)
if score >= 50 and state.get("crash") != key_date:
    alerts.append("\U0001F6A8 Crash score %d/100 - %s (%s)" % (score, st, " - ".join(pts[:3])))
    state["crash"] = key_date

fd = jload("data/fii-dii.json")
fii = (((fd.get("categories") or {}).get("FII/FPI") or {}).get("net_cr"))
if fii is not None and fii <= -3000 and state.get("fii") != key_date:
    alerts.append("\U0001F4B8 FII ne %+.0f Cr becha - bada outflow" % fii)
    state["fii"] = key_date

sc = jload("data/brain-screener.json")
highs = []
for s in (sc.get("stocks") or []):
    if s.get("high_52w") and s.get("price") and s.get("price") >= s.get("high_52w") * 0.999:
        highs.append(s.get("symbol"))
if len(highs) >= 3 and state.get("high52") != key_date:
    extra = " (+%d aur)" % (len(highs) - 6) if len(highs) > 6 else ""
    alerts.append("\U0001F3AF 52-week high: " + ", ".join(highs[:6]) + extra)
    state["high52"] = key_date

if alerts:
    msg = "\U0001F514 <b>ArthaSaar ALERT</b>\n" + now.strftime("%d %b, %H:%M IST") + "\n\n" + "\n".join("- " + (a if isinstance(a, str) else a[1]) for a in alerts)
    send(msg)
else:
    print("no triggers")
json.dump(state, open("data/alert-state.json", "w"), indent=1)
