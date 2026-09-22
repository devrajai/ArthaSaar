#!/usr/bin/env python3
"""digest.py - Market Brain Morning Digest -> Telegram + FII history save."""
import json
import os
import urllib.request
from datetime import datetime

TG = "https://api.telegram.org/bot{}/sendMessage"


def load(p):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return {}


def main():
    gti = load("data/gti.json").get("symbols", {})
    fii = load("data/fii-dii.json")
    glo = load("data/global.json").get("items", [])
    radar = load("data/radar.json")
    oi = load("data/oi-gti.json").get("symbols", {}).get("NIFTY 50", {})
    ind = load("data/indices-all.json").get("indices", [])
    n = gti.get("NIFTY 50", {})
    nifty_chg = next((x.get("change_pct") for x in ind if x.get("index") == "NIFTY 50"), None)
    fc = ((fii.get("categories") or {}).get("FII/FPI") or {}).get("net_cr")
    dc = ((fii.get("categories") or {}).get("DII") or {}).get("net_cr")
    g = next((x for x in glo if x.get("name") == "S&P 500"), {})
    g2 = next((x for x in glo if x.get("name") == "Nasdaq Composite"), {})
    acc = (radar.get("accumulation") or [])[:3]
    hist = load("data/fii-history.json")
    if not isinstance(hist, list):
        hist = []
    today = fii.get("date") or datetime.now().strftime("%d-%b-%Y")
    if not hist or hist[-1].get("date") != today:
        hist.append({"date": today, "fii": fc, "dii": dc})
        hist = hist[-90:]
        os.makedirs("data", exist_ok=True)
        with open("data/fii-history.json", "w") as f:
            json.dump(hist, f)
    L = ["Market Brain Morning - " + datetime.now().strftime("%a %d %b"), ""]
    near = n.get("nearest") or ["?"]
    z = str(near[0]).upper()
    chgs = "{:+.2f}%".format(nifty_chg) if nifty_chg is not None else "?"
    comp = (n.get("compression") or {}).get("compressed")
    L.append("NIFTY: " + chgs + " | GTI nearest zone: " + z + (" (COMPRESSED!)" if comp else ""))
    if fc is not None:
        L.append("Kal: FII {:+.0f} Cr | DII {:+.0f} Cr".format(fc, dc))
    if g:
        L.append("Global: S&P {:+.2f}%, Nasdaq {:+.2f}%".format(g.get("chg_pct", 0), g2.get("chg_pct", 0) if g2 else 0))
    if oi:
        L.append("OI: max pain {} | PCR {} | put wall {} / call wall {}".format(oi.get("max_pain"), oi.get("pcr"), oi.get("put_wall"), oi.get("call_wall")))
    if acc:
        L.append("Radar top accumulation: " + ", ".join("{} ({}% deliv)".format(a["sym"], a["deliv"]) for a in acc[:2]))
    L.append("")
    L.append("Rule of the day: pehle zone, phir trade - zone ke bina trade = lottery.")
    msg = "\n".join(L)
    tok = os.environ.get("TG_TOKEN")
    chats = [c.strip() for c in os.environ.get("TG_CHAT_ID", "").split(",") if c.strip()]
    if tok and chats:
        ok = 0
        for chat in chats:
            try:
                data = json.dumps({"chat_id": chat, "text": msg}).encode()
                req = urllib.request.Request(TG.format(tok), data=data, headers={"Content-Type": "application/json"})
                urllib.request.urlopen(req, timeout=30)
                ok += 1
            except Exception as e:
                print("send fail", chat, str(e)[:60])
        print("sent to", ok, "of", len(chats))
    else:
        print("no TG creds; message:\n" + msg)


if __name__ == "__main__":
    main()
