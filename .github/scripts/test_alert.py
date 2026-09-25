#!/usr/bin/env python3
"""test_alert.py - MANUAL test: stress-meter format ka test message Dev + Jems Bonda ko.
Sirf testing ke liye (baaki 4 logon ko nahi). Real alert stress >= 60 pe stress.py bhejta hai sabko."""
import json, os, urllib.request

TOKEN = os.environ.get("TG_TOKEN")
TARGETS = [("Dev", "1392604324"), ("Jems Bonda", "1073463083")]  # testing only

def main():
    if not TOKEN:
        print("no TG_TOKEN"); return
    try:
        d = json.load(open("data/stress.json"))
        c = d.get("comp", {})
        msg = "\U0001F9EA TEST \u2014 MARKET STRESS METER (Dev's Bloomberg)\n\n"
        msg += "Score: %s/100 (%s)\n\n" % (d.get("score", "?"), d.get("band", "?").upper())
        if "dma" in c:
            msg += "\u2022 NIFTY 200-DMA: %s%% %s \u2014 %s/30 pts\n" % (abs(c["dma"]["d"]), "neeche" if c["dma"]["d"] < 0 else "ooper", c["dma"]["s"])
        if "vix" in c:
            msg += "\u2022 VIX (dar): %s \u2014 %s/25 pts\n" % (c["vix"]["v"], c["vix"]["s"])
        if "s4" in c:
            msg += "\u2022 Stage-4 stocks: %s%% (%s) \u2014 %s/25 pts\n" % (c["s4"]["p"], c["s4"]["n"], c["s4"]["s"])
        if "fii" in c:
            msg += "\u2022 FII bech rahe: %s din \u2014 %s/20 pts\n\n" % (c["fii"]["n"], c["fii"]["s"])
        msg += "Asli alert stress >= 60 pe roz shaam 6:20 baje aayega \u2014 position chhota karne ka signal.\n\U0001F4CC Indicator hai, prediction nahi. (ArthaSaar \U0001F60E)"
    except Exception as e:
        msg = "\U0001F9EA TEST alert \u2014 stress.json load nahi hua (%s). System chal raha hai! (ArthaSaar)" % e
    for name, chat in TARGETS:
        data = json.dumps({"chat_id": chat, "text": msg}).encode()
        req = urllib.request.Request("https://api.telegram.org/bot%s/sendMessage" % TOKEN, data=data, headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(req, timeout=20)
            print("SENT to", name)
        except Exception as e:
            print("FAIL", name, e)

if __name__ == "__main__":
    main()
