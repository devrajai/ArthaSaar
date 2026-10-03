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

def main():
    brain, stocks = load("brain-screener.json", {}), []
    stocks = brain.get("stocks") or []
    filings = load("filings.json", {})
    big = load("bigplayer.json", {})
    indices = load("indices-all.json", {}).get("indices") or []
    fii, delivery = load("fii-dii.json", {}), load("delivery.json", {})
    results, econ, macro, health = load("results.json", {}), load("economy-pulse.json", {}), load("macro.json", {}), load("data-health.json", {})

    members, failed = membership_snapshot()
    previous = load("index-membership.json", {})
    old_members = previous.get("indices") or {}
    if members:
        save("index-membership.json", {"updated": datetime.now(timezone.utc).isoformat(), "source": "NSE", "indices": members})
    else:
        members = old_members
    changes = membership_changes(members, old_members) if members else {}

    hl = high_low(stocks)
    br = breadth(stocks)
    hist = history_update(load("research-history.json", {}), {**br, **hl})
    save("research-history.json", hist)

    out = {
      "updated": datetime.now(timezone.utc).isoformat(),
      "source_policy": "Free/public sources only; NSE primary where available, Yahoo remains historical backup.",
      "features": {
        "corporate_actions": {"count": len(filing_events(filings.get("filings") or [])), "events": filing_events(filings.get("filings") or []), "source": "NSE corporate filings snapshot"},
        "week52": hl,
        "breadth_history": {"today": br, "history": hist.get("daily") or []},
        "index_changes": {"indices_count": len(indices), "daily_watch": index_watch(indices), "membership_changes": changes,
                          "membership_sources": {k: v.get("source_url") for k, v in members.items()}, "fetch_warnings": failed},
        "rbi_macro": macro_snapshot(econ, macro),
        "bulk_block": {"bulk": (big.get("bulk") or [])[:15], "block": (big.get("block") or [])[:10], "updated": big.get("updated"), "source": "NSE-derived big-player snapshot"},
        "results": {"updated": results.get("updated"), "quarter": results.get("quarter"), "items": results.get("results") or [], "source": "Existing exchange-filings results calendar"},
        "sector_rotation": {"sectors": sector_rotation(stocks), "basis": "Average/median 1D move, breadth and EMA200 participation from screener rows."},
        "market_regime": regime(stocks, fii, delivery, indices),
        "data_resilience": {"health_updated": health.get("updated"), "summary": health.get("summary") or {}, "feeds": health.get("feeds") or [],
                            "fallback_policy": "NSE EOD → Yahoo historical backup → last valid committed snapshot."}
      },
      "notes": [
        "All sections are EOD / snapshot research unless a source explicitly says otherwise.",
        "Corporate-action entries are filing-driven events; precise ex-date/record-date fields are shown only when present upstream.",
        "Index membership/weight tracking uses NSE public constituent CSVs for NIFTY 50/100/200 when available.",
        "Market regime is a descriptive derived indicator, not a prediction or investment recommendation."
      ]
    }
    save("research-radar.json", out)
    print("Research Radar built:", len(stocks), "stocks /", len(indices), "indices")

if __name__ == "__main__":
    main()
