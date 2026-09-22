#!/usr/bin/env python3
"""xray.py - Market X-Ray: evening auto-analysis like YouTube 'Market X-ray' videos.
Reads existing data files (indices, FII/DII, OI, GTI, radar) and writes data/xray.json
with a Hinglish narrative + verdict. Runs ~5:45 PM IST Mon-Fri."""
import json, os
from datetime import datetime, timezone, timedelta

IST = timezone(timedelta(hours=5, minutes=30))

def load(p, default=None):
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def main():
    idx = load("data/indices-all.json", {"indices": []})
    fii = load("data/fii-dii.json", {"categories": {}})
    oi = load("data/oi-gti.json", {"symbols": {}})
    gti = load("data/gti.json", {}).get("symbols", {})
    radar = load("data/radar.json", {"accumulation": []})

    indices = idx.get("indices", [])
    def find(name):
        for i in indices:
            if i.get("index") == name or i.get("symbol") == name:
                return i
        return None

    nifty = find("NIFTY 50") or {}
    bank = find("NIFTY BANK") or {}
    spot = nifty.get("price") or 0
    chg = nifty.get("change_pct") or 0

    MAIN = {"NIFTY 50", "NIFTY BANK", "NIFTY NEXT 50", "NIFTY MIDCAP 100",
            "NIFTY SMALLCAP 100", "NIFTY MIDCAP SELECT", "INDIA VIX"}
    pos = neg = 0
    pos_list, neg_list = [], []
    for i in indices:
        nm = i.get("index", "")
        if not nm.startswith("NIFTY") or nm in MAIN:
            continue
        c = i.get("change_pct") or 0
        if c > 0:
            pos += 1; pos_list.append((nm.replace("NIFTY ", ""), c))
        else:
            neg += 1; neg_list.append((nm.replace("NIFTY ", ""), c))

    cats = fii.get("categories", {})
    fii_net = (cats.get("FII/FPI") or {}).get("net_cr")
    dii_net = (cats.get("DII") or {}).get("net_cr")

    nfty_oi = (oi.get("symbols", {}) or {}).get("NIFTY 50") or {}
    put_wall = nfty_oi.get("put_wall")
    call_wall = nfty_oi.get("call_wall")
    pcr = nfty_oi.get("pcr")
    max_pain = nfty_oi.get("max_pain")

    nifty_g = None
    for key in ("NIFTY", "NIFTY 50", "^NSEI", "NIFTY50"):
        if key in gti:
            nifty_g = gti[key]; break

    acc = sorted(radar.get("accumulation", []), key=lambda x: -(x.get("chg") or 0))[:5]

    pts = []
    score = 0

    # 1. Close verdict
    if chg > 0.3:
        s = "NIFTY aaj buyers ke kaboo me band hua (+{}%).".format(chg)
        c = "g"; score += 1
    elif chg < -0.3:
        s = "NIFTY aaj sellers ke pressure me band hua ({}%). Opening ki strength close tak gayab - classic distribution pattern.".format(chg)
        c = "r"; score -= 1
    else:
        s = "NIFTY flat band hua ({}) - dono side fight, koi winner nahi.".format(chg)
        c = "n"
    if bank.get("change_pct") is not None:
        s += " Bank Nifty {}%.".format(bank.get("change_pct"))
    pts.append({"h": "Closing Picture", "t": s, "c": c})

    # 2. Sector breadth
    if pos + neg > 0:
        if pos > neg:
            s = "{} sector green, {} red - andar mujhe demand hai".format(pos, neg)
            c = "g"; score += 1
        else:
            s = "{} sector red, sirf {} green - breadth kamzor, upar jane me bhaari".format(neg, pos)
            c = "r"; score -= 1
        if pos_list:
            s += ". Strongest: " + ", ".join("{} +{}%".format(n, round(v, 1)) for n, v in sorted(pos_list, key=lambda x: -x[1])[:3])
        pts.append({"h": "Sector Breadth", "t": s, "c": c})

    # 3. FII vs DII
    if fii_net is not None and dii_net is not None:
        f = round(fii_net); d = round(dii_net)
        if f < 0 and d > 0 and d > abs(f):
            s = "FII ne {} Cr becha, DII ne poora digest kiya (+{} Cr). DII = MF/LIC ka paisa - girawat ko rok raha.".format(f, d)
            c = "n"
        elif f < 0 and d > 0:
            s = "FII bech rahe ({} Cr), DII thoda hi kheench raha (+{} Cr) - FII ka pressure zyada.".format(f, d)
            c = "r"; score -= 1
        elif f > 0 and d > 0:
            s = "Dono kharid rahe - FII +{} Cr, DII +{} Cr. Bilkul bullish flow.".format(f, d)
            c = "g"; score += 1
        else:
            s = "FII +{} Cr, DII {} Cr.".format(f, d)
            c = "n"
        pts.append({"h": "FII vs DII (Cash)", "t": s, "c": c})

    # 4. OI walls
    if put_wall and call_wall and spot:
        if spot >= call_wall:
            s = "Price call wall ({} ke upar sab Calls) tod chuka - ab {} pe naya resistance.".format(call_wall, call_wall + 100)
            c = "g"; score += 1
        elif spot <= put_wall:
            s = "Price put wall ({}) ke neeche aa gaya - support toota, ab aage wala support dekho.".format(put_wall)
            c = "r"; score -= 1
        else:
            s = "Price walls ke beech phansa: Support {} (Put OI), Resistance {} (Call OI). Expiry tak is range me khelna.".format(put_wall, call_wall)
            c = "n"
        if pcr is not None:
            if pcr < 0.8:
                s += " PCR {} - puts zyada likhe gaye, sentiment thoda dar.".format(pcr)
            elif pcr > 1.2:
                s += " PCR {} - call writers confident, upar ka room hai.".format(pcr)
            else:
                s += " PCR {} - balanced.".format(pcr)
        if max_pain:
            s += " Max pain: {}.".format(max_pain)
        pts.append({"h": "Option Data (Walls)", "t": s, "c": c})

    # 5. GTI zone
    if nifty_g:
        near = nifty_g.get("nearest") or ["?", 0]
        zones = (nifty_g.get("day_zones") or {}).get("SD") or [None, None]
        blood = zones[0] if isinstance(zones, list) else None
        comp = (nifty_g.get("compression") or {}).get("compressed")
        s = "Nearest GTI zone: {} (distance {}).".format(near[0] if isinstance(near, list) else near, round(near[1] if isinstance(near, list) and len(near) > 1 else 0, 1))
        if comp:
            s += " Zone compression ON - bada move aane wala, direction market khud batayega."
        if blood:
            s += " Blood bath level: {} - ye toda to niche khul jayega (blood bath)".format(round(blood))
        pts.append({"h": "GTI Zone", "t": s, "c": "n", "blood": blood})

    # 6. Midcap movers (video ka hidden story)
    if acc:
        top = ", ".join("{} +{}%".format(a.get("sym"), round(a.get("chg") or 0, 1)) for a in acc[:4] if (a.get("chg") or 0) > 0)
        if top:
            pts.append({"h": "Chhote me Kiska Dum (Delivery+Gain)",
                         "t": "Index girta hua ho to bhi ye bhaage: {} - inme delivery % bhi high, matlab smart paisa.".format(top), "c": "g"})

    # Verdict
    if score >= 2:
        verdict = "BUYERS IN CONTROL - dips ko buying mana jaye. Lekin SL zaroori."
        vc = "#77f37b"
    elif score <= -2:
        verdict = "SELLERS IN CONTROL - har bounce pe selling. Long lene se pehle 2 baar socho."
        vc = "#ff8b8b"
    else:
        verdict = "TUG OF WAR - range hai, breakout ka wait karo. Walls ke bahar hi asli story."
        vc = "#f0b429"

    out = {
        "updated": datetime.now(IST).isoformat(),
        "date": datetime.now(IST).strftime("%d-%m-%Y"),
        "headline": "NIFTY {} | {}% | Spot {}".format(spot, chg, spot),
        "points": pts,
        "verdict": verdict,
        "vc": vc,
        "note": "Auto-analysis: FII/DII cash + Option OI + GTI zones + delivery data se banta hai (shaam ~6 PM). Ye levels aur bias hai, guarantee nahi - SL hamesha."
    }
    with open("data/xray.json", "w") as f:
        json.dump(out, f, ensure_ascii=False)
    print("xray.json written:", verdict)

if __name__ == "__main__":
    main()
