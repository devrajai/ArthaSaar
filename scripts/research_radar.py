#!/usr/bin/env python3
"""Build ArthaSaar's free-data Research Radar.

This layer intentionally uses only repository snapshots plus public NSE index
constituent CSVs. It survives upstream failures by preserving previous
membership/history files and never writing an empty replacement.
"""
import csv
import io
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
UA = "Mozilla/5.0 ArthaSaar/ResearchRadar (+https://github.com/devrajai/ArthaSaar)"
KEEP_HISTORY = 260

NSE_MEMBERSHIP = {
    "NIFTY 50": "https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv",
    "NIFTY 100": "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv",
    "NIFTY 200": "https://nsearchives.nseindia.com/content/indices/ind_nifty200list.csv",
}

def load(name, default):
    try:
        return json.loads((DATA / name).read_text(encoding="utf-8"))
    except Exception:
        return default

def save(name, obj):
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / name).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

def norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s or "").strip().lower())

def pick(headers, *names):
    by_norm = {norm(h): h for h in headers}
    for n in names:
        if norm(n) in by_norm:
            return by_norm[norm(n)]
    for h in headers:
        nh = norm(h)
        if any(norm(n) in nh for n in names if n):
            return h
    return None

def fetch_csv(url):
    req = Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/csv,text/plain,*/*",
        "Referer": "https://www.nseindia.com/",
    })
    raw = urlopen(req, timeout=35).read().decode("utf-8", "replace")
    if len(raw) < 30 or "<html" in raw[:500].lower():
        raise ValueError("non-csv response")
    return raw

def membership_snapshot():
    current, failed = {}, []
    for index_name, url in NSE_MEMBERSHIP.items():
        try:
            rows = list(csv.DictReader(io.StringIO(fetch_csv(url))))
            if not rows:
                raise ValueError("empty csv")
            headers = rows[0].keys()
            sym_col = pick(headers, "Symbol", "Symbol Code", "Company Symbol")
            name_col = pick(headers, "Company Name", "Company")
            weight_col = pick(headers, "Weight", "Weight (%)", "Weightage", "Index Weight")
            if not sym_col:
                raise ValueError("symbol column not found")
            members = {}
            for r in rows:
                sym = str(r.get(sym_col) or "").strip().upper()
                if not sym or sym in {"SYMBOL", "TOTAL"}:
                    continue
                rec = {"symbol": sym, "company": str(r.get(name_col) or "").strip() if name_col else ""}
                if weight_col:
                    try:
                        rec["weight_pct"] = round(float(str(r.get(weight_col, "")).replace("%", "").replace(",", "").strip()), 4)
                    except Exception:
                        pass
                members[sym] = rec
            if not members:
                raise ValueError("no members parsed")
            current[index_name] = {"source": "NSE", "source_url": url, "count": len(members), "members": members}
        except Exception as exc:
            failed.append({"index": index_name, "error": str(exc)[:160]})
    return current, failed

def membership_changes(current, previous):
    out = {}
    for idx, snap in current.items():
        old = (previous.get(idx) or {}).get("members") or {}
        cur = snap.get("members") or {}
        added = sorted(set(cur) - set(old))
        removed = sorted(set(old) - set(cur))
        weight = []
        for sym in sorted(set(cur) & set(old)):
            a, b = cur[sym].get("weight_pct"), old[sym].get("weight_pct")
            if a is not None and b is not None and abs(a - b) >= 0.10:
                weight.append({"symbol": sym, "from_pct": b, "to_pct": a, "delta_pct": round(a - b, 4)})
        weight.sort(key=lambda x: abs(x["delta_pct"]), reverse=True)
        out[idx] = {"added": added[:20], "removed": removed[:20], "weight_changes": weight[:20]}
    return out

def filing_events(filings):
    keywords = [
        ("Dividend", r"dividend"), ("Buyback", r"buyback|buy back"), ("Bonus", r"bonus"),
        ("Split", r"split"), ("Rights", r"rights issue|rights"),
        ("Merger / Demerger", r"merger|demerger|scheme of arrangement"),
        ("Preferential / QIP", r"preferential|qip"),
        ("Board Meeting", r"board meeting"),
        ("AGM / EGM", r"\bagm\b|\begm\b|annual general|extraordinary general"),
    ]
    out, seen = [], set()
    for f in filings or []:
        text = " ".join(str(f.get(k) or "") for k in ("category", "nse_desc", "subject"))
        kind = next((label for label, pat in keywords if re.search(pat, text, re.I)), None)
        if not kind:
            continue
        key = (f.get("symbol"), f.get("date"), f.get("subject"))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "symbol": f.get("symbol"), "company": f.get("company"), "date": f.get("date"),
            "kind": kind, "category": f.get("category"), "subject": f.get("subject"), "pdf": f.get("pdf"),
        })
    out.sort(key=lambda x: (x.get("date") or "", x.get("symbol") or ""), reverse=True)
    return out[:80]

def high_low(stocks):
    highs, lows = [], []
    for s in stocks or []:
        price, hi, lo = s.get("price"), s.get("high_52w"), s.get("low_52w")
        if price is None:
            continue
        dhi = round((price / hi - 1) * 100, 2) if hi else None
        dlo = round((price / lo - 1) * 100, 2) if lo else None
        r = {"symbol": s.get("symbol"), "company": s.get("company"), "price": price,
             "high_52w": hi, "low_52w": lo, "from_high_pct": dhi, "from_low_pct": dlo,
             "change_pct": s.get("change_pct")}
        if dhi is not None and dhi >= -0.50:
            highs.append(r)
        if dlo is not None and dlo <= 0.50:
            lows.append(r)
    highs.sort(key=lambda x: x.get("from_high_pct", -999), reverse=True)
    lows.sort(key=lambda x: x.get("from_low_pct", 999))
    return {"new_high_zone_count": len(highs), "new_low_zone_count": len(lows),
            "near_highs": highs[:20], "near_lows": lows[:20]}

def breadth(stocks):
    vals = [s for s in stocks or [] if s.get("change_pct") is not None]
    adv = sum(1 for s in vals if float(s.get("change_pct") or 0) > 0)
    dec = sum(1 for s in vals if float(s.get("change_pct") or 0) < 0)
    flat = len(vals) - adv - dec
    b = load("breadth.json", {})
    return {"stocks": len(vals), "advancers": adv, "decliners": dec, "unchanged": flat,
            "advance_ratio_pct": round(100 * adv / len(vals), 1) if vals else 0,
            "ema200_pct": b.get("above_ema200_pct"), "rsi_gt_60": b.get("rsi_above_60"),
            "rsi_lt_40": b.get("rsi_below_40"), "volume_spike_2x": b.get("volume_spike_2x")}

def sector_rotation(stocks):
    groups = defaultdict(list)
    for s in stocks or []:
        if s.get("change_pct") is not None:
            groups[(s.get("industry") or "Other").strip() or "Other"].append(s)
    rows = []
    for sector, vals in groups.items():
        ch = sorted(float(x.get("change_pct") or 0) for x in vals)
        med = ch[len(ch)//2] if ch else 0
        rows.append({"sector": sector, "stocks": len(vals),
                     "avg_1d_pct": round(sum(ch) / len(ch), 2) if ch else 0,
                     "median_1d_pct": round(med, 2),
                     "breadth_pct": round(100 * sum(1 for x in ch if x > 0) / len(ch), 1) if ch else 0,
                     "above_ema200_pct": round(100 * sum(1 for x in vals if x.get("above_ema200")) / len(vals), 1) if vals else 0})
    rows.sort(key=lambda x: (x["avg_1d_pct"], x["stocks"]), reverse=True)
    return rows[:30]

def index_watch(indices):
    rows = []
    for x in indices or []:
        price, yh, yl = x.get("price"), x.get("year_high"), x.get("year_low")
        if price is None:
            continue
        rows.append({"index": x.get("index") or x.get("symbol"), "price": price, "change_pct": x.get("change_pct"),
                     "year_high": yh, "year_low": yl,
                     "from_year_high_pct": round((price / yh - 1) * 100, 2) if yh else None,
                     "from_year_low_pct": round((price / yl - 1) * 100, 2) if yl else None})
    rows.sort(key=lambda x: x.get("change_pct", -999), reverse=True)
    return rows[:20]

def macro_snapshot(econ, macro):
    inds, out = econ.get("ind") or [], []
    for x in inds:
        src = str(x.get("src") or "")
        if re.search(r"RBI|MoSPI|Finance|NPCI|CEA|Rail|GST|PMI|FADA|MOCI|EPFO|Power|Port", src, re.I):
            out.append({"name": x.get("name"), "value": x.get("val"), "sub": x.get("sub"),
                        "date": x.get("date"), "source": src, "yoy": x.get("yoy")})
    return {"economy_updated": econ.get("updated"), "macro_updated": macro.get("updated"), "indicators": out[:16]}

def regime(stocks, fii, delivery, indices):
    b = breadth(stocks)
    nifty = next((x for x in indices if x.get("index") == "NIFTY 50"), None)
    try:
        fii_net = (fii.get("categories") or {}).get("FII/FPI", {}).get("net_cr")
    except Exception:
        fii_net = None
    score = 0
    if b["advance_ratio_pct"] >= 55: score += 1
    if b["advance_ratio_pct"] <= 45: score -= 1
    if (b.get("ema200_pct") or 0) >= 55: score += 1
    if (b.get("ema200_pct") or 0) <= 45: score -= 1
    if nifty and float(nifty.get("change_pct") or 0) > 0: score += 1
    if nifty and float(nifty.get("change_pct") or 0) < 0: score -= 1
    if fii_net is not None:
        score += 1 if fii_net > 0 else -1 if fii_net < 0 else 0
    label = "BALANCED"
    if score >= 3: label = "RISK-ON"
    elif score <= -3: label = "RISK-OFF"
    elif score > 0: label = "SLIGHTLY POSITIVE"
    elif score < 0: label = "SLIGHTLY NEGATIVE"
    return {"label": label, "score": score, "advance_ratio_pct": b["advance_ratio_pct"],
            "ema200_pct": b.get("ema200_pct"), "nifty_change_pct": nifty.get("change_pct") if nifty else None,
            "fii_net_cr": fii_net, "method": "Derived from breadth + trend + NIFTY 50 + FII/FPI. Descriptive, not a forecast."}

def history_update(hist, current):
    today = datetime.now(timezone.utc).date().isoformat()
    rows = [x for x in (hist.get("daily") or []) if x.get("date") != today]
    rows.append({"date": today, "advancers": current["advancers"], "decliners": current["decliners"],
                 "advance_ratio_pct": current["advance_ratio_pct"], "ema200_pct": current.get("ema200_pct"),
                 "new_high_zone_count": current.get("new_high_zone_count"), "new_low_zone_count": current.get("new_low_zone_count")})
    rows.sort(key=lambda x: x.get("date", ""))
    return {"updated": datetime.now(timezone.utc).isoformat(), "daily": rows[-KEEP_HISTORY:]}


def num(v):
    try:
        if v is None or v == "": return None
        return float(str(v).replace(",", "").replace("%", "").strip())
    except Exception:
        return None

def load_brain_csv():
    pth = DATA / "brain-screener.csv"
    out = []
    try:
        with pth.open("r", encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                x = dict(r)
                for k in ("tier","price","change_pct","high_52w","low_52w","high_200d","low_200d",
                          "from_52w_high_pct","ema20","ema200","rsi14","macd","macd_signal","macd_hist",
                          "vol_vs_avg20","consec_days","history_days"):
                    if k in x:
                        x[k] = num(x[k])
                if x.get("above_ema200") in ("True","true","1"):
                    x["above_ema200"] = True
                elif x.get("above_ema200") in ("False","false","0"):
                    x["above_ema200"] = False
                out.append(x)
    except Exception:
        return []
    return out

def pct_change(a, b):
    return round((a / b - 1.0) * 100.0, 2) if a is not None and b not in (None, 0) else None

def mean(vals):
    vals = [float(x) for x in vals if x is not None]
    return sum(vals) / len(vals) if vals else None

def stdev(vals):
    vals = [float(x) for x in vals if x is not None]
    if len(vals) < 2:
        return None
    m = sum(vals) / len(vals)
    return (sum((x-m)*(x-m) for x in vals) / len(vals)) ** 0.5

def history_metrics():
    out = {}
    hp = DATA / "history"
    if not hp.exists():
        return out
    for fp in hp.glob("*.json"):
        if fp.name == "history-index.json":
            continue
        try:
            arr = json.loads(fp.read_text(encoding="utf-8"))
            if not isinstance(arr, list):
                continue
            rows = [r for r in arr if isinstance(r, dict) and num(r.get("close")) not in (None, 0)]
            rows.sort(key=lambda r: str(r.get("date") or ""))
            if len(rows) < 2:
                continue
            closes = [float(r["close"]) for r in rows]
            vols = [num(r.get("volume")) or 0 for r in rows]
            rets = [pct_change(closes[i], closes[i-1]) for i in range(1, len(closes))]
            rets = [r for r in rets if r is not None]
            def sma(n):
                return mean(closes[-n:]) if len(closes) >= n else None
            def ret_n(n):
                return pct_change(closes[-1], closes[-1-n]) if len(closes) > n else None
            rv20 = stdev(rets[-20:]) if len(rets) >= 5 else None
            rv60 = stdev(rets[-60:]) if len(rets) >= 10 else None
            avgv20 = mean(vols[-20:]) if len(vols) >= 5 else None
            volratio = (vols[-1] / avgv20) if avgv20 not in (None, 0) else None
            ma50, ma200 = sma(50), sma(200)
            prev50 = mean(closes[-51:-1]) if len(closes) >= 51 else None
            prev200 = mean(closes[-201:-1]) if len(closes) >= 201 else None
            out[fp.stem.upper()] = {
                "date": rows[-1].get("date"),
                "price": closes[-1],
                "prev_price": closes[-2],
                "return_1d": pct_change(closes[-1], closes[-2]),
                "return_5d": ret_n(5),
                "return_20d": ret_n(20),
                "return_60d": ret_n(60),
                "volatility20": rv20,
                "volatility60": rv60,
                "vol_expansion": (rv20 / rv60) if rv20 is not None and rv60 not in (None, 0) else None,
                "avg_volume20": avgv20,
                "volume_ratio": volratio,
                "sma20": sma(20),
                "sma50": ma50,
                "sma200": ma200,
                "prev_sma50": prev50,
                "prev_sma200": prev200,
                "roc20": ret_n(20),
                "high_252": max(closes[-252:]) if closes else None,
                "low_252": min(closes[-252:]) if closes else None,
                "high_200": max(closes[-200:]) if closes else None,
                "low_200": min(closes[-200:]) if closes else None,
                "history_days": len(rows),
            }
        except Exception:
            continue
    return out

def filing_keyword_radar(filings):
    pats = {
        "promoter_insider": r"promoter|insider|director|key managerial|acquisition of shares|disposal of shares",
        "pledge": r"pledge|re-pledge|encumbrance",
        "dividend": r"dividend",
        "buyback_open_offer": r"buyback|buy back|open offer|delisting",
        "results": r"financial results|quarterly results|audited results|unaudited results|earnings",
    }
    out = {k: [] for k in pats}
    seen = {k:set() for k in pats}
    for f in filings or []:
        txt = " ".join(str(f.get(k) or "") for k in ("category","nse_desc","subject","company","symbol"))
        for key, pat in pats.items():
            if not re.search(pat, txt, re.I):
                continue
            sig = (f.get("symbol"), f.get("date"), f.get("subject"), f.get("pdf"))
            if sig in seen[key]:
                continue
            seen[key].add(sig)
            out[key].append({
                "symbol": f.get("symbol"), "company": f.get("company"), "date": f.get("date"),
                "category": f.get("category"), "subject": f.get("subject"), "pdf": f.get("pdf")
            })
    for key in out:
        out[key].sort(key=lambda x: (x.get("date") or "", x.get("symbol") or ""), reverse=True)
        out[key] = out[key][:60]
    return out

def momentum_features(stocks, hmap, universe_benchmark):
    rows = []
    for s in stocks:
        sym = str(s.get("symbol") or "").upper()
        h = hmap.get(sym) or {}
        bench20 = universe_benchmark
        r20 = h.get("return_20d")
        rs20 = round(r20 - bench20, 2) if r20 is not None and bench20 is not None else None
        vol_exp = h.get("vol_expansion")
        cross = "GOLDEN" if h.get("sma50") and h.get("sma200") and h["sma50"] > h["sma200"] else "DEATH" if h.get("sma50") and h.get("sma200") and h["sma50"] < h["sma200"] else "NA"
        rows.append({
            "symbol": s.get("symbol"), "company": s.get("company"), "industry": s.get("industry"),
            "price": s.get("price"), "change_pct": s.get("change_pct"), "rsi14": s.get("rsi14"),
            "ema20": s.get("ema20"), "ema200": s.get("ema200"), "above_ema200": s.get("above_ema200"),
            "macd_hist": s.get("macd_hist"), "vol_vs_avg20": s.get("vol_vs_avg20"),
            "return_5d": h.get("return_5d"), "return_20d": r20, "return_60d": h.get("return_60d"),
            "relative_strength_20d": rs20, "volatility20": h.get("volatility20"),
            "volatility60": h.get("volatility60"), "vol_expansion": vol_exp,
            "sma50": h.get("sma50"), "sma200": h.get("sma200"), "cross": cross,
            "high_252": h.get("high_252"), "low_252": h.get("low_252"),
            "distance_252_high_pct": pct_change(h.get("price"), h.get("high_252")),
            "distance_252_low_pct": pct_change(h.get("price"), h.get("low_252")),
            "history_days": h.get("history_days", s.get("history_days"))
        })
    return rows

def top_rows(rows, key, reverse=True, limit=12, minval=None):
    vals = [r for r in rows if r.get(key) is not None]
    if minval is not None:
        vals = [r for r in vals if float(r.get(key) or 0) >= minval]
    vals.sort(key=lambda r: float(r.get(key) or 0), reverse=reverse)
    return vals[:limit]

def delivery_feature(stocks, delivery):
    d = delivery.get("d") or {}
    rows = []
    for s in stocks:
        sym = s.get("symbol")
        dv = num(d.get(sym))
        if dv is None:
            continue
        ch = num(s.get("change_pct"))
        conv = ((dv - 50.0) / 50.0 * 100.0) if dv is not None else None
        rows.append({"symbol":sym,"company":s.get("company"),"delivery_pct":dv,"change_pct":ch,"conviction_index":round((dv/100.0)*(abs(ch) if ch is not None else 0),2)})
    high = [r for r in rows if (r.get("change_pct") or 0) > 0]
    low = [r for r in rows if (r.get("change_pct") or 0) < 0]
    high.sort(key=lambda r:(r.get("delivery_pct") or 0, r.get("change_pct") or 0),reverse=True)
    low.sort(key=lambda r:(r.get("delivery_pct") or 0, abs(r.get("change_pct") or 0)),reverse=True)
    return {"coverage":len(rows),"avg_delivery_pct":round(mean([r["delivery_pct"] for r in rows]) or 0,1),
            "high_delivery_up":high[:12],"high_delivery_down":low[:12]}

def accumulation_feature(stocks, delivery, hmap):
    d = delivery.get("d") or {}
    acc, dist = [], []
    for s in stocks:
        sym = s.get("symbol")
        ch = num(s.get("change_pct"))
        vr = num(s.get("vol_vs_avg20"))
        dv = num(d.get(sym))
        if ch is None or vr is None:
            continue
        rec = {"symbol":sym,"company":s.get("company"),"change_pct":ch,"volume_ratio":vr,"delivery_pct":dv}
        if ch > 0 and vr >= 1.5 and (dv is None or dv >= 55):
            acc.append(rec)
        if ch < 0 and vr >= 1.5 and (dv is None or dv >= 55):
            dist.append(rec)
    acc.sort(key=lambda r:(r["volume_ratio"],r["change_pct"]),reverse=True)
    dist.sort(key=lambda r:(r["volume_ratio"],abs(r["change_pct"])),reverse=True)
    return {"accumulation":acc[:15],"distribution":dist[:15],"method":"price direction + volume/20D average + delivery where available"}

def relative_strength_feature(rows):
    vals=[r for r in rows if r.get("relative_strength_20d") is not None]
    vals.sort(key=lambda r:r["relative_strength_20d"],reverse=True)
    return {"benchmark":"NIFTY 20D","leaders":vals[:15],"laggards":vals[-15:][::-1],"benchmark_20d":mean([]) if False else None}

def sector_matrix(stocks, rows):
    by=defaultdict(list)
    for r in rows:
        key=(r.get("industry") or "Other").strip() or "Other"
        by[key].append(r)
    out=[]
    for sector, vals in by.items():
        one=[x.get("change_pct") for x in vals if x.get("change_pct") is not None]
        tw=[x.get("return_20d") for x in vals if x.get("return_20d") is not None]
        rs=[x.get("relative_strength_20d") for x in vals if x.get("relative_strength_20d") is not None]
        out.append({"sector":sector,"stocks":len(vals),"avg_1d_pct":round(mean(one) or 0,2),
                    "avg_20d_pct":round(mean(tw) or 0,2),"avg_rs20d":round(mean(rs) or 0,2),
                    "breadth_pct":round(100*sum(1 for x in one if x>0)/len(one),1) if one else 0,
                    "above_ema200_pct":round(100*sum(1 for x in vals if x.get("above_ema200"))/len(vals),1) if vals else 0})
    out.sort(key=lambda x:(x["avg_20d_pct"],x["breadth_pct"]),reverse=True)
    return out[:30]

def fo_features(futures, stocks):
    smap={str(s.get("symbol") or "").upper():s for s in stocks}
    fr=[x for x in futures.get("stocks") or [] if x.get("symbol")]
    rows=[]
    for x in fr:
        sym=str(x.get("symbol")).upper()
        s=smap.get(sym,{})
        oi=num(x.get("oi")) or 0; chg=num(x.get("oi_chg")) or 0
        prev=oi-chg
        oipct=(chg/prev*100) if prev>0 else None
        price_ch=num(s.get("change_pct"))
        basis=num(x.get("basis_pct"))
        build="NEUTRAL"
        if price_ch is not None and chg>0 and price_ch>0: build="LONG BUILD"
        elif price_ch is not None and chg>0 and price_ch<0: build="SHORT BUILD"
        elif price_ch is not None and chg<0 and price_ch>0: build="SHORT COVER"
        elif price_ch is not None and chg<0 and price_ch<0: build="LONG UNWIND"
        rows.append({"symbol":sym,"price_change_pct":price_ch,"oi":oi,"oi_change":chg,"oi_change_pct":round(oipct,2) if oipct is not None else None,"basis_pct":basis,"build":build})
    return rows

def index_bucket_breadth(members, stocks):
    smap={str(s.get("symbol") or "").upper():s for s in stocks}
    sets={}
    for idx,snap in members.items():
        sets[idx]=set((snap.get("members") or {}).keys())
    n50=sets.get("NIFTY 50",set())
    n100=sets.get("NIFTY 100",set())
    n200=sets.get("NIFTY 200",set())
    buckets=[
        ("NIFTY 50",n50),
        ("NIFTY 100 ex-50",n100-n50),
        ("NIFTY 200 ex-100",n200-n100),
        ("Outside NIFTY 200",set(smap)-n200)
    ]
    out=[]
    for name,syms in buckets:
        vals=[smap[x].get("change_pct") for x in syms if x in smap and smap[x].get("change_pct") is not None]
        out.append({"bucket":name,"stocks":len(vals),"advancers":sum(1 for x in vals if x>0),"decliners":sum(1 for x in vals if x<0),
                    "breadth_pct":round(100*sum(1 for x in vals if x>0)/len(vals),1) if vals else 0})
    return out

def concentration_feature(members):
    out=[]
    for idx,snap in members.items():
        vals=[dict(v) for v in (snap.get("members") or {}).values() if v.get("weight_pct") is not None]
        vals.sort(key=lambda x:x.get("weight_pct",0),reverse=True)
        out.append({"index":idx,"count":len(vals),"top5_weight_pct":round(sum(x.get("weight_pct",0) for x in vals[:5]),2),
                    "top10_weight_pct":round(sum(x.get("weight_pct",0) for x in vals[:10]),2),
                    "top10":vals[:10]})
    return out

def nifty_leadership(members, rows):
    rmap={str(x.get("symbol") or "").upper():x for x in rows}
    snap=members.get("NIFTY 50") or {}
    vals=[]
    for sym,meta in (snap.get("members") or {}).items():
        x=rmap.get(str(sym).upper())
        if not x:
            continue
        vals.append({"symbol":sym,"company":x.get("company"),"weight_pct":meta.get("weight_pct"),
                     "return_20d":x.get("return_20d"),"relative_strength_20d":x.get("relative_strength_20d"),
                     "change_pct":x.get("change_pct"),"above_ema200":x.get("above_ema200")})
    vals.sort(key=lambda x:(x.get("weight_pct") or 0),reverse=True)
    return vals[:20]

def flow_trend(fii, macro):
    hist=macro.get("history") or []
    out=[{"date":x.get("date"),"fii_net_cr":x.get("fii_net_cr")} for x in hist if x.get("fii_net_cr") is not None]
    return {"current":(fii.get("categories") or {}).get("FII/FPI",{}),"dii_current":(fii.get("categories") or {}).get("DII",{}),"history":out[-20:],
            "fii_sell_days":sum(1 for x in out[-10:] if (x.get("fii_net_cr") or 0)<0)}

def resilience_detail(stocks, delivery, futures, hmap):
    total=len(stocks); hist200=sum(1 for s in stocks if (s.get("history_days") or 0)>=200)
    ema200=sum(1 for s in stocks if s.get("ema200") not in (None,""))
    delivery_n=len(delivery.get("d") or {})
    futures_n=len(futures.get("stocks") or [])
    history_n=len(hmap)
    return {"stocks":total,"history_files":history_n,"history_ge_200d":hist200,"history_ge_200d_pct":round(100*hist200/total,1) if total else 0,
            "ema200_coverage_pct":round(100*ema200/total,1) if total else 0,
            "delivery_coverage":delivery_n,"futures_stock_coverage":futures_n,
            "coverage_score_pct":round(100*mean([hist200/total if total else 0, ema200/total if total else 0, delivery_n/total if total else 0, min(1,futures_n/total) if total else 0]) or 0,1)}

def main():
    stocks = load_brain_csv()
    if not stocks:
        brain = load("brain-screener.json", {})
        stocks = brain.get("stocks") or []
    filings_obj = load("filings.json", {})
    filings = filings_obj.get("filings") or []
    big = load("bigplayer.json", {})
    indices = load("indices-all.json", {}).get("indices") or []
    fii = load("fii-dii.json", {})
    delivery = load("delivery.json", {})
    results, econ, macro, health = load("results.json", {}), load("economy-pulse.json", {}), load("macro.json", {}), load("data-health.json", {})

    members, failed = membership_snapshot()
    previous = load("index-membership.json", {})
    old_members = previous.get("indices") or {}
    if members:
        save("index-membership.json", {"updated": datetime.now(timezone.utc).isoformat(), "source": "NSE", "indices": members})
    else:
        members = old_members
    changes = membership_changes(members, old_members) if members and old_members else {}

    hmap = history_metrics()
    bench = hmap.get("NIFTY", {}).get("return_20d")
    if bench is None:
        bench = 0.0
    rows = momentum_features(stocks, hmap, bench)
    hl = high_low(stocks)
    br = breadth(stocks)
    hist = history_update(load("research-history.json", {}), {**br, **hl})
    save("research-history.json", hist)

    filed = filing_keyword_radar(filings)
    fo = fo_features(load("futures.json", {}), stocks)
    action_ev = filing_events(filings)
    rr = results.get("results") or []
    results_evidence = [x for x in rr if x.get("date")]

    # New radar calculations, all descriptive/derived from repository snapshots.
    breakout = [x for x in rows if x.get("distance_252_high_pct") is not None and x["distance_252_high_pct"] >= -0.75]
    breakout.sort(key=lambda x:x.get("distance_252_high_pct", -999), reverse=True)

    volshock = [x for x in rows if x.get("vol_vs_avg20") is not None]
    volshock.sort(key=lambda x:x.get("vol_vs_avg20",0), reverse=True)

    rs = [x for x in rows if x.get("relative_strength_20d") is not None]
    rs.sort(key=lambda x:x.get("relative_strength_20d",0), reverse=True)

    vol_exp = [x for x in rows if x.get("vol_expansion") is not None and x.get("volatility20") is not None]
    vol_exp.sort(key=lambda x:x.get("vol_expansion",0), reverse=True)

    dma = [x for x in rows if x.get("sma50") is not None and x.get("sma200") is not None]
    dma_crosses = {"golden":[x for x in dma if x.get("cross")=="GOLDEN"],"death":[x for x in dma if x.get("cross")=="DEATH"]}

    earnings_surprise = {
        "surprise_data_available": False,
        "reason": "Current free repository snapshots contain results dates/filings but not standardized EPS/consensus surprise fields.",
        "upcoming_results": results_evidence[:25],
        "results_filing_events": filed.get("results") or []
    }

    gap_feature = {
        "available": False,
        "reason": "Current history files store close + volume, not session open prices. Research Radar will activate true gap-up/gap-down calculations automatically if OHLC opens are added."
    }
    atr_feature = {
        "available": False,
        "proxy_available": True,
        "reason": "Current history files are close + volume. The Radar therefore exposes close-to-close volatility expansion as a range proxy instead of inventing ATR from missing OHLC."
    }

    build_counts=defaultdict(int)
    for x in fo: build_counts[x.get("build","NEUTRAL")] += 1
    long_build=[x for x in fo if x.get("build")=="LONG BUILD"]
    short_build=[x for x in fo if x.get("build")=="SHORT BUILD"]
    short_cover=[x for x in fo if x.get("build")=="SHORT COVER"]
    long_unwind=[x for x in fo if x.get("build")=="LONG UNWIND"]
    long_build.sort(key=lambda x:x.get("oi_change_pct") or 0, reverse=True)
    short_build.sort(key=lambda x:x.get("oi_change_pct") or 0, reverse=True)
    short_cover.sort(key=lambda x:x.get("oi_change_pct") or 0, reverse=True)
    long_unwind.sort(key=lambda x:x.get("oi_change_pct") or 0, reverse=True)

    futures_obj = load("futures.json", {})
    pcr = futures_obj.get("pcr") or {}
    basis = sorted([x for x in fo if x.get("basis_pct") is not None], key=lambda x:abs(x.get("basis_pct") or 0), reverse=True)

    bulk = []
    for x in (big.get("bulk") or [])[:30]:
        sym=str(x.get("s") or "").upper()
        s=next((z for z in stocks if str(z.get("symbol") or "").upper()==sym),{})
        bulk.append({"symbol":sym,"company":x.get("n"),"deal_value_cr":x.get("t"),"days":x.get("d"),"change_pct":s.get("change_pct")})
    bulk.sort(key=lambda x:x.get("deal_value_cr") or 0, reverse=True)

    out = {
      "updated": datetime.now(timezone.utc).isoformat(),
      "schema_version": "44-modules",
      "source_policy": "Free/public sources only; NSE primary where available, Yahoo historical backup.",
      "features": {
        "corporate_actions": {"count":len(action_ev),"events":action_ev,"source":"NSE corporate filings snapshot"},
        "week52": hl,
        "breadth_history": {"today":br,"history":hist.get("daily") or []},
        "index_changes": {"indices_count":len(indices),"daily_watch":index_watch(indices),"membership_changes":changes,
                          "membership_sources":{k:v.get("source_url") for k,v in members.items()},"fetch_warnings":failed},
        "rbi_macro": macro_snapshot(econ, macro),
        "bulk_block": {"bulk":(big.get("bulk") or [])[:15],"block":(big.get("block") or [])[:10],"updated":big.get("updated"),"source":"NSE-derived big-player snapshot"},
        "results": {"updated":results.get("updated"),"quarter":results.get("quarter"),"items":rr,"source":"Existing exchange-filings/results calendar"},
        "sector_rotation": {"sectors":sector_rotation(stocks),"basis":"Average/median 1D move, breadth and EMA200 participation from screener rows."},
        "market_regime": regime(stocks,fii,delivery,indices),
        "data_resilience": {"health_updated":health.get("updated"),"summary":health.get("summary") or {},"feeds":health.get("feeds") or [],
                            "fallback_policy":"NSE EOD → Yahoo historical backup → last valid committed snapshot"},

        "breakout_radar": {"count":len(breakout),"rows":breakout[:20],"method":"Within 0.75% of 252-session high from ArthaSaar history."},
        "volume_shock": {"rows":volshock[:20],"method":"Current volume divided by trailing 20-session average where available."},
        "delivery_conviction": delivery_feature(stocks,delivery),
        "accumulation_distribution": accumulation_feature(stocks,delivery,hmap),
        "gap_radar": gap_feature,
        "relative_strength": {"benchmark":"NIFTY","benchmark_return_20d_pct":bench,"leaders":rs[:20],"laggards":rs[-20:][::-1]},
        "sector_matrix": {"sectors":sector_matrix(stocks,rows)},
        "volatility_expansion": {"rows":vol_exp[:20],"method":"20-session close-to-close volatility / 60-session volatility."},
        "range_expansion": atr_feature,
        "momentum_dashboard": {"rsi_high":[x for x in rows if x.get("rsi14") is not None and x["rsi14"]>=60][:20],
                               "rsi_low":[x for x in rows if x.get("rsi14") is not None and x["rsi14"]<=40][:20],
                               "macd_positive":[x for x in rows if (x.get("macd_hist") or 0)>0][:20],
                               "roc_leaders":sorted([x for x in rows if x.get("return_20d") is not None],key=lambda x:x["return_20d"],reverse=True)[:20]},
        "trend_health": {"above_ema200_pct":br.get("ema200_pct"),"above_ema200":[x for x in rows if x.get("above_ema200")][:15],"below_ema200":[x for x in rows if x.get("above_ema200") is False][:15]},
        "dma_cross_radar": {"golden_cross_count":len(dma_crosses["golden"]),"death_cross_count":len(dma_crosses["death"]),
                            "golden_candidates":sorted(dma_crosses["golden"],key=lambda x:x.get("return_20d") or 0,reverse=True)[:15],
                            "death_candidates":sorted(dma_crosses["death"],key=lambda x:x.get("return_20d") or 0)[:15]},
        "distance_map": {"near_high_200d":sorted([x for x in rows if x.get("distance_252_high_pct") is not None],key=lambda x:x["distance_252_high_pct"],reverse=True)[:20],
                         "near_low_200d":sorted([x for x in rows if x.get("distance_252_low_pct") is not None],key=lambda x:x["distance_252_low_pct"])[:20]},
        "earnings_surprise": earnings_surprise,
        "promoter_insider": {"count":len(filed.get("promoter_insider") or []),"events":filed.get("promoter_insider") or [],"source":"exchange filing keyword radar"},
        "pledge_watch": {"count":len(filed.get("pledge") or []),"events":filed.get("pledge") or [],"source":"exchange filing keyword radar"},
        "corporate_calendar": {"next_results":sorted([x for x in rr if x.get("date")],key=lambda x:x["date"])[:25],"filing_actions":action_ev[:30]},
        "dividend_radar": {"count":len(filed.get("dividend") or []),"events":filed.get("dividend") or []},
        "buyback_open_offer": {"count":len(filed.get("buyback_open_offer") or []),"events":filed.get("buyback_open_offer") or []},
        "fo_oi_change": {"rows":sorted(fo,key=lambda x:abs(x.get("oi_change_pct") or 0),reverse=True)[:20],"coverage":len(fo)},
        "oi_price_matrix": {"long_build":long_build[:20],"short_build":short_build[:20],"short_cover":short_cover[:20],"long_unwind":long_unwind[:20],"counts":dict(build_counts)},
        "option_pulse": {"nifty_pcr_oi":pcr.get("nifty_pcr_oi"),"nifty_pcr_vol":pcr.get("nifty_pcr_vol"),"call_oi":pcr.get("nifty_call_oi"),"put_oi":pcr.get("nifty_put_oi"),
                         "max_pain":pcr.get("nifty_max_pain"),"expiry":pcr.get("nifty_expiry"),"spot":pcr.get("nifty_spot"),"all_index_pcr_oi":pcr.get("all_index_pcr_oi")},
        "futures_basis": {"rows":basis[:20],"method":"Near-month futures close versus underlying snapshot."},
        "fo_buildup": {"counts":dict(build_counts),"long_build":long_build[:15],"short_build":short_build[:15],"short_cover":short_cover[:15],"long_unwind":long_unwind[:15]},
        "bulk_followthrough": {"rows":bulk[:20],"method":"Bulk-deal snapshot joined with current EOD percentage move."},
        "institutional_flow_trend": flow_trend(fii,macro),
        "breadth_momentum": {"today":br,"three_day_up":sum(1 for s in stocks if (s.get("consec_days") or 0)>=3 and (s.get("change_pct") or 0)>0),
                             "three_day_down":sum(1 for s in stocks if (s.get("consec_days") or 0)>=3 and (s.get("change_pct") or 0)<0),
                             "volume_spike_2x":br.get("volume_spike_2x")},
        "high_low_breadth": {"new_high_zone":hl.get("new_high_zone_count"),"new_low_zone":hl.get("new_low_zone_count"),
                             "near_highs":hl.get("near_highs")[:20],"near_lows":hl.get("near_lows")[:20]},
        "market_concentration": {"indices":concentration_feature(members)},
        "nifty_leadership": {"leaders":nifty_leadership(members,rows)},
        "index_bucket_breadth": {"buckets":index_bucket_breadth(members,stocks)},
        "liquidity_stress": {"low_volume_lt_0_5x":sum(1 for s in stocks if (s.get("vol_vs_avg20") or 0)<0.5),
                             "high_volume_gt_2x":sum(1 for s in stocks if (s.get("vol_vs_avg20") or 0)>=2),
                             "illiquid_history_lt_60d":sum(1 for s in stocks if (s.get("history_days") or 0)<60),
                             "coverage":len(stocks)},
        "data_reliability": resilience_detail(stocks,delivery,futures_obj,hmap),
        "data_resilience_detail": {**resilience_detail(stocks,delivery,futures_obj,hmap), "health_summary": health.get("summary") or {}, "health_updated": health.get("updated")},
      },
      "notes": [
        "All sections are EOD / snapshot research unless a source explicitly says otherwise.",
        "No paid API is required. Sources remain exchange/public snapshots plus ArthaSaar calculations.",
        "Gap and true ATR are deliberately marked unavailable because current stored history is close+volume; no values are fabricated.",
        "Earnings surprise is shown as unavailable until a standardized public EPS/consensus field is present.",
        "Market regime and derived rankings are descriptive analytics, not forecasts or investment recommendations."
      ]
    }
    save("research-radar.json",out)
    print("Research Radar built:",len(stocks),"stocks /",len(indices),"indices / 44 modules")

if __name__ == "__main__":
    main()
