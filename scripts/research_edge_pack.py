#!/usr/bin/env python3
"""ArthaSaar free-data Research Edge Pack.

Builds four auditable products from data already collected by the repository:
1) Days Like Today — similarity on breadth + TRIN + McClellan + highs/lows, with
   VIX/FII context when historical coverage exists, and Nifty 5D/20D outcomes.
2) Public Scoreboard — historical outcome tracker for Research Radar signals and
   forward tracking slots for GTI/TimesFM snapshots.
3) Smart-money footprint — current accumulation/distribution components plus a
   20-session price/volume mini timeline from the local history files.
4) Data Trust — source/freshness/coverage notes for the Edge Pack.

No paid APIs. Historical internals are read from the repository's data branch.
"""
import json, math, os, re
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
INTERNALS_URL = "https://raw.githubusercontent.com/devrajai/ArthaSaar/data/data/internals.json"
UA = "ArthaSaar/ResearchEdgePack (+https://github.com/devrajai/ArthaSaar)"

def load(name, default=None):
    try:
        with open(DATA / name, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else {}

def save(name, obj):
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

def fetch_json(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=35) as r:
        return json.loads(r.read().decode("utf-8"))

def fnum(v):
    try:
        if v is None or v == "": return None
        return float(str(v).replace(",", "").replace("%", "").strip())
    except Exception:
        return None

def parse_gmp(v):
    m = re.search(r"[-+]?\d+(?:\.\d+)?", str(v or ""))
    return float(m.group()) if m else None

def date_key(s):
    s = str(s or "")[:10]
    for fmt in ("%Y-%m-%d", "%d-%b-%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except Exception:
            pass
    return s

def similarity(a, b):
    pairs = [(a.get("breadth"), b.get("breadth")),
             (a.get("trin"), b.get("trin")),
             (a.get("mcos"), b.get("mcos")),
             (a.get("hl_balance"), b.get("hl_balance")),
             (a.get("vix"), b.get("vix")),
             (a.get("fii"), b.get("fii")),
             (a.get("dma_dist"), b.get("dma_dist"))]
    weights = [2.0, 1.7, 1.7, 1.4, 1.0, 1.0, 1.0]
    score = 0.0
    weight = 0.0
    ranges = {"breadth":0.5, "trin":1.5, "mcos":200.0, "hl_balance":2.0, "vix":10.0, "fii":10000.0, "dma_dist":10.0}
    for (x,y),w in zip(pairs, weights):
        if x is None or y is None: continue
        r = ranges.get(next((k for k,(xx,yy) in [
            ("breadth",(a.get("breadth"),b.get("breadth"))),
            ("trin",(a.get("trin"),b.get("trin"))),
            ("mcos",(a.get("mcos"),b.get("mcos"))),
            ("hl_balance",(a.get("hl_balance"),b.get("hl_balance"))),
            ("vix",(a.get("vix"),b.get("vix"))),
            ("fii",(a.get("fii"),b.get("fii"))),
            ("dma_dist",(a.get("dma_dist"),b.get("dma_dist")))] if xx==x and yy==y), "breadth"), 1.0)
        d = min(1.0, abs(x-y)/r)
        score += w*d
        weight += w
    return round(100 * score/weight, 1) if weight else None

def build_days_like_today():
    internals = fetch_json(INTERNALS_URL)
    dates = internals.get("dates") or []
    adv = internals.get("adv") or []
    dec = internals.get("dec") or []
    trin = internals.get("trin") or []
    mcos = internals.get("mcos") or []
    nh = internals.get("nh") or []
    nl = internals.get("nl") or []
    fii_rows = load("fii-history.json", [])
    fii_map = {date_key(x.get("date")): fnum(x.get("fii")) for x in fii_rows if isinstance(x, dict)}

    tfh = load("timesfm_history.json", [])
    nifty = {}
    vix = {}
    for x in tfh:
        if not isinstance(x, dict): continue
        d = date_key(x.get("d"))
        if x.get("s") == "^NSEI" and fnum(x.get("l")) is not None:
            nifty[d] = fnum(x.get("l"))
        if x.get("s") == "^INDIAVIX" and fnum(x.get("l")) is not None:
            vix[d] = fnum(x.get("l"))

    stress = load("stress.json", {})
    current_nifty = fnum((stress.get("nifty") or {}).get("c"))
    current_dma = fnum((stress.get("nifty") or {}).get("dma"))
    current_fii = fnum(((load("fii-dii.json", {}).get("categories") or {}).get("FII/FPI") or {}).get("net_cr"))
    today = date_key((internals.get("dates") or [""])[-1])
    current_idx = len(dates)-1
    current = {
        "date": today,
        "breadth": (adv[current_idx] / (adv[current_idx] + dec[current_idx])) if (adv[current_idx] + dec[current_idx]) else None,
        "trin": fnum((internals.get("last") or {}).get("trin")),
        "mcos": fnum((internals.get("last") or {}).get("mcos")),
        "hl_balance": ((fnum((internals.get("last") or {}).get("nh")) or 0) - (fnum((internals.get("last") or {}).get("nl")) or 0)) /
                      max(1, (fnum((internals.get("last") or {}).get("nh")) or 0) + (fnum((internals.get("last") or {}).get("nl")) or 0)),
        "vix": vix.get(today),
        "fii": current_fii,
        "dma_dist": ((current_nifty/current_dma)-1)*100 if current_nifty and current_dma else None,
    }

    hist = []
    for i,d in enumerate(dates):
        total = (fnum(adv[i]) or 0) + (fnum(dec[i]) or 0)
        row = {
            "date": date_key(d),
            "breadth": (fnum(adv[i]) or 0)/total if total else None,
            "trin": fnum(trin[i]) if i < len(trin) else None,
            "mcos": fnum(mcos[i]) if i < len(mcos) else None,
            "hl_balance": (((fnum(nh[i]) or 0)-(fnum(nl[i]) or 0)) / max(1,(fnum(nh[i]) or 0)+(fnum(nl[i]) or 0))) if i < len(nh) else None,
            "vix": vix.get(date_key(d)),
            "fii": fii_map.get(date_key(d)),
            "dma_dist": None,
            "nifty": nifty.get(date_key(d)),
        }
        if row["date"] != today:
            hist.append(row)

    ranked = sorted(hist, key=lambda x: similarity(current,x) if similarity(current,x) is not None else 999)
    # Forward Nifty outcomes only when actual daily closes exist.
    ordered = sorted(nifty.items())
    pos = {d:i for i,(d,_) in enumerate(ordered)}
    matches = []
    for r in ranked[:20]:
        idx = pos.get(r["date"])
        n5 = ((ordered[idx+5][1]/ordered[idx][1])-1)*100 if idx is not None and idx+5 < len(ordered) and ordered[idx][1] else None
        n20 = ((ordered[idx+20][1]/ordered[idx][1])-1)*100 if idx is not None and idx+20 < len(ordered) and ordered[idx][1] else None
        rr = dict(r)
        rr["similarity"] = similarity(current,r)
        rr["next5_pct"] = round(n5,2) if n5 is not None else None
        rr["next20_pct"] = round(n20,2) if n20 is not None else None
        matches.append(rr)
    return {
        "updated": datetime.now(timezone.utc).isoformat(),
        "today": current,
        "matches": matches[:10],
        "method": "Nearest historical EOD days using breadth, TRIN, McClellan, high-low balance; VIX/FII are used when coverage exists. Historical 200DMA distance is not yet available in the stored internals archive, so it is shown only for today until a daily NIFTY history feed is committed.",
        "coverage": {"internals_days": len(dates), "vix_days": len(vix), "nifty_days": len(nifty), "fii_days": len(fii_map)}
    }

def build_smart_money():
    radar = load("radar.json", {})
    delivery = load("delivery.json", {}).get("d") or {}
    big = load("bigplayer.json", {})
    circuits = load("circuits.json", {})
    stocks = load("brain-screener.json", {}).get("stocks") or []

    rmap = {}
    for k in ("accumulation","hidden_selling"):
        for x in radar.get(k) or []:
            rmap[(str(x.get("sym") or "").upper(), k)] = x
    bulk = {}
    for k in ("bulk","block"):
        for x in big.get(k) or []:
            sym = str(x.get("s") or x.get("symbol") or "").upper()
            if sym: bulk[sym] = {"type":k.upper(),"detail":x.get("n") or x.get("name") or ""}

    changed_bands = {str(x.get("s") or "").upper() for x in (circuits.get("bands") or {}).get("ch") or []}
    hist_dir = DATA / "history"
    rows = []
    for s in stocks:
        sym = str(s.get("symbol") or "").upper()
        ch = fnum(s.get("change_pct"))
        dv = fnum(delivery.get(sym))
        vr = fnum(s.get("vol_vs_avg20"))
        acc = rmap.get((sym,"accumulation"))
        dist = rmap.get((sym,"hidden_selling"))
        evidence = []
        score = 0
        if dv is not None and dv >= 60: evidence.append("delivery≥60%"); score += 1
        if vr is not None and vr >= 1.5: evidence.append("volume≥1.5×"); score += 1
        if acc: evidence.append("radar accumulation"); score += 2
        if dist: evidence.append("radar distribution"); score -= 2
        if sym in bulk: evidence.append(bulk[sym]["type"].lower()+" deal")
        if sym in changed_bands: evidence.append("circuit-band change")
        tag = "NEUTRAL"
        if score >= 3 and (ch or 0) >= 0: tag = "ACCUMULATION"
        elif score <= -2 or ((dv or 0) >= 60 and (ch or 0) < 0): tag = "DISTRIBUTION"
        elif evidence: tag = "MIXED / EVENT"
        if not evidence: continue
        timeline = []
        fp = hist_dir / (sym + ".json")
        try:
            arr = json.loads(fp.read_text(encoding="utf-8"))
            arr = [x for x in arr if isinstance(x,dict) and fnum(x.get("close")) is not None]
            arr = arr[-20:]
            for x in arr:
                timeline.append({"date":x.get("date"),"close":fnum(x.get("close")),"volume":fnum(x.get("volume"))})
        except Exception:
            pass
        rows.append({"symbol":sym,"company":s.get("company"),"tag":tag,"score":score,"delivery_pct":dv,
                     "change_pct":ch,"volume_ratio":vr,"evidence":evidence,"timeline":timeline})
    rows.sort(key=lambda x:(0 if x["tag"]=="ACCUMULATION" else 1 if x["tag"]=="MIXED / EVENT" else 2, -x["score"]))
    return {"updated":datetime.now(timezone.utc).isoformat(),"rows":rows[:60],
            "method":"Delivery + volume + Research Radar accumulation/distribution + bulk/block + circuit-band context. Descriptive footprint, not a trade signal."}

def build_scoreboard():
    sig = load("research-signal-history.json", {})
    aggregate = sig.get("aggregate") or {}
    rows = []
    for k,v in sorted(aggregate.items()):
        rows.append({"type":"Research Radar","signal":k,"observations":v.get("observations",0),
                     "5d_mean_pct":v.get("next5_mean_pct"),"5d_positive_pct":v.get("next5_positive_pct"),
                     "20d_mean_pct":v.get("next20_mean_pct"),"20d_positive_pct":v.get("next20_positive_pct")})
    tf = load("timesfm_forecasts.json", {})
    rows.append({"type":"TimesFM","signal":"Current forecast tracking","observations":0,"5d_mean_pct":None,"5d_positive_pct":None,
                 "20d_mean_pct":None,"20d_positive_pct":None})
    return {"updated":datetime.now(timezone.utc).isoformat(),"rows":rows,
            "disclaimer":"Public scoreboard shows historical outcomes where enough forward observations exist. New GTI/TimesFM snapshots will accumulate from this release onward; no missing results are treated as wins."}

def main():
    os.makedirs(DATA, exist_ok=True)
    edge = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "days_like_today": build_days_like_today(),
        "smart_money": build_smart_money(),
        "scoreboard": build_scoreboard(),
        "trust": {
            "sources": {
                "internals":"ArthaSaar data branch · 260 EOD days",
                "nifty_outcomes":"ArthaSaar TimesFM history archive",
                "delivery":"data/delivery.json",
                "radar":"data/radar.json",
                "bulk_block":"data/bigplayer.json",
                "circuits":"data/circuits.json",
            },
            "generated_from":"repository snapshots only; no paid APIs"
        }
    }
    save("research-edge-pack.json", edge)
    print("Research Edge Pack:", len(edge["smart_money"]["rows"]), "smart-money rows /", len(edge["days_like_today"]["matches"]), "similar days")

if __name__ == "__main__":
    main()
