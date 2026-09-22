#!/usr/bin/env python3
"""weekly_card.py - Sunday 10 AM: week ka hisaab - Nifty week, movers, accuracy, backtest."""
import sys, json, time, datetime
sys.path.insert(0, "scripts")
from tghelp import jload, yahoo, send, crash_score, status

now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=5, minutes=30)))
L = ["\U0001F4D8 <b>Market Brain - Sunday Report Card</b>", now.strftime("%d %b %Y"), ""]

p, pc = yahoo("%5ENSEI", "7d")
if p and pc:
    L.append("\U0001F4C8 Nifty (7 din): %+.1f%% - abhi %s" % ((p / pc - 1) * 100, "{:,.0f}".format(p)))

fu = jload("data/futures.json")
top_oi = sorted(fu.get("stocks") or [], key=lambda s: -(s.get("oi") or 0))[:15]
wk = []
for s in top_oi:
    a, b = yahoo(s["symbol"] + ".NS", "7d")
    if a and b:
        wk.append((s["symbol"], (a / b - 1) * 100))
    time.sleep(0.12)
wk.sort(key=lambda x: -x[1])
if wk:
    L.append("\U0001F534 Week ke winners: " + " - ".join("%s %+.1f%%" % w for w in wk[:3]))
    L.append("\U0001F53D Losers: " + " - ".join("%s %+.1f%%" % w for w in sorted(wk, key=lambda x: x[1])[:3]))

tf = jload("data/timesfm_forecasts.json")
a = tf.get("accuracy") or {}
if a.get("tracked"):
    rate = ("%.0f%%" % (a["rate"] * 100)) if a.get("rate") is not None else "-"
    L.append("\U0001F393 TimesFM: %d/%d direction hits (%s)" % (a.get("hits", 0), a["tracked"], rate))
else:
    L.append("\U0001F393 TimesFM: predictions jama ho rahi hain - report card 21-din baad")

bt = jload("data/backtest.json")
if bt:
    L.append("\U0001F9EA Backtest (1 saal, Nifty): Buy\u0026Hold %s | EMA20/50 %s | RSI30/70 %s" % (
        ("%+.1f%%" % bt["buy_hold_pct"]) if bt.get("buy_hold_pct") is not None else "-",
        ("%+.1f%%" % bt["ema_pct"]) if bt.get("ema_pct") is not None else "-",
        ("%+.1f%%" % bt["rsi_pct"]) if bt.get("rsi_pct") is not None else "-"))

mood = jload("data/mood.json")
score, _ = crash_score({"tf": tf, "fu": fu, "fd": jload("data/fii-dii.json"),
                        "br": jload("data/breadth.json"), "sb": jload("data/smart-brain.json")})
st, _ = status(score)
L.append("\U0001F4AC Mood abhi: %s/100 - Crash score: %d/100 (%s)" % (mood.get("overall", "-"), score, st))
L.append("")
L.append("agli week ke liye - dhyan se, tips nahi")
send("\n".join(L))
