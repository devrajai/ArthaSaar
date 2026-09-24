#!/usr/bin/env python3
"""stress.py - CORRECTION ALARM (Dev's Bloomberg): Market Stress Meter 0-100.
2008/2020 jaisi correction ka early-warning system. Components:
- NIFTY 200-DMA se doori (Yahoo ^NSEI)
- VIX dar level (Yahoo ^VIX)
- Stage-4 stocks ka % (stages.json - girti hui trend wale stocks)
- FII selling streak (fii-history.json)
Score >= 60 -> TG alert ALL members (position chhota karne ka signal).
Honest note: indicator hai, prediction nahi."""
import json, os, urllib.request
from datetime import datetime, timezone, timedelta

IST = datetime.now(timezone(timedelta(hours=5, minutes=30)))
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
TG = "https://api.telegram.org/bot{}/sendMessage"

def yclose(sym, rng):
    u = "https://query1.finance.yahoo.com/v8/finance/chart/%s?range=%s&interval=1d" % (sym, rng)
    d = json.loads(urllib.request.urlopen(urllib.request.Request(u, headers=UA), timeout=30).read())
    r = d["chart"]["result"]
    cl = r[0]["indicators"]["quote"][0]["close"]
    return [c for c in cl if c]

def load(p, default=None):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def send(tok, chat, text):
    data = json.dumps({"chat_id": chat, "text": text, "disable_web_page_preview": True}).encode()
    req = urllib.request.Request(TG.format(tok), data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=20)
    except Exception as e:
        print("tg fail", e)

def main():
    comp = {}
    # 1) NIFTY vs 200-DMA (0-30)
    try:
        cl = yclose("%5ENSEI", "2y")
        dma = sum(cl[-200:]) / 200.0
        dist = (cl[-1] / dma - 1) * 100
        comp["dma"] = {"d": round(dist, 1), "s": round(min(30, max(0, -dist * 3)))}
    except Exception:
        dist = None
        comp["dma"] = {"d": None, "s": 0}
    # 2) VIX (0-25)
    try:
        vix = yclose("%5EVIX", "1mo")[-1]
        comp["vix"] = {"v": round(vix, 1), "s": round(min(25, max(0, (vix - 12) * 2)))}
    except Exception:
        vix = None
        comp["vix"] = {"v": None, "s": 0}
    # 3) Stage-4 % (0-25)
    st = load("data/stages.json", {})
    allst = st.get("all", {})
    tot = len(allst)
    s4 = sum(1 for v in allst.values() if v and v[0] == 4)
    pct = (s4 / tot * 100) if tot else 0
    comp["s4"] = {"n": s4, "t": tot, "p": round(pct, 1), "s": round(min(25, pct * 0.5))}
    # 4) FII selling streak (0-20)
    fii = load("data/fii-history.json", [])
    streak = 0
    for row in reversed(fii):
        if row.get("fii", 0) < 0:
            streak += 1
        else:
            break
    comp["fii"] = {"n": streak, "s": round(min(20, streak * 4))}
    score = round(sum(c["s"] for c in comp.values()))
    band = "Normal" if score < 30 else ("Alert" if score < 55 else ("High" if score < 75 else "DANGER"))
    out = {"u": IST.strftime("%d %b %Y"), "score": score, "band": band,
           "nifty": {"c": round(cl[-1], 1) if dist is not None else None,
                      "dma": round(dma, 1) if dist is not None else None},
           "comp": comp,
           "hist": {"2008": {"fall": -60, "recover": "~5 saal"}, "2020": {"fall": -38, "recover": "~6 mahine"},
                    "note": "Crash me stress meter pehle se high hota hai - indicator hai, prediction nahi."}}
    with open("data/stress.json", "w") as f:
        json.dump(out, f, separators=(",", ":"))
    print("OK stress: %d/100 %s | dma=%s vix=%s s4=%.1f%% fii_streak=%d" % (score, band, dist, vix, pct, streak))
    # TG alert jab stress HIGH
    if score >= 60:
        tok = os.environ.get("TG_TOKEN")
        if not tok:
            print("no TG token - skip alert")
            return
        m = ("\U0001F6A8 MARKET STRESS METER: %d/100 (%s)\n" % (score, band.upper()))
        if dist is not None:
            m += "NIFTY 200-DMA se %.1f%% %s\n" % (abs(dist), "neeche" if dist < 0 else "ooper")
        if vix:
            m += "VIX (dar): %.1f\n" % vix
        m += "Stage-4 stocks: %.1f%% (%d)\nFII bech rahe: %d din lagaatar\n\n" % (pct, s4, streak)
        m += "\u26A0\uFE0F Position size chhota rakho, risk control karo.\n\U0001F4CC Indicator hai, prediction nahi. (Market Brain by Dev)"
        for mem in load("data/members.json", []):
            send(tok, mem.get("chat_id"), m)
        print("TG alerts sent (stress >= 60)")

if __name__ == "__main__":
    main()
