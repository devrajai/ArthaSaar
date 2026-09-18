#!/usr/bin/env python3
"""
PHASE 2 — pre-open movers, FII/DII flows, index add/remove detection.

All sources verified working from datacenter IPs (no cookies, no keys):
  1. Pre-open session data (9:00-9:15 IST): ~2,180 stocks with IEP, % change,
     year high/low, corporate-action purpose
     GET https://www.nseindia.com/api/market-data-pre-open?key=ALL
     -> data/preopen.json (mover buckets >=1..5% both sides, top 20 lists,
        corporate action alerts)
  2. FII/DII daily cash market flows (live during day, final after close)
     GET https://www.nseindia.com/api/fiidiiTradeReact
     -> data/fii-dii.json (buy/sell/net in Rs crore per category)
  3. Index add/remove detection: diffs today's Nifty 500 tier-1 universe
     (data/universe.json written by brain_collect.py) against yesterday's
     snapshot (data/nifty500-prev.json)
     -> data/index-changes.json (added / removed symbols)

Run in the morning workflow (9:20 AM IST snapshot of pre-open) and in the
evening brain run (final FII/DII + index change detection after close).
Self-healing: each part fails independently, never blocks the others.
"""
import json
import datetime as dt
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
TIMEOUT = 25


def get_json(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def now_iso():
    return dt.datetime.now(dt.timezone.utc).isoformat()


# ------------------------------------------------------------ pre-open
def collect_preopen():
    try:
        j = get_json("https://www.nseindia.com/api/market-data-pre-open?key=ALL")
    except Exception as e:  # noqa: BLE001
        print("WARN pre-open failed:", e)
        return
    rows = []
    for item in j.get("data", []):
        m = item.get("metadata") or {}
        if m.get("pChange") is None or m.get("lastPrice") is None:
            continue
        rows.append({
            "symbol": m.get("symbol"),
            "iep": m.get("iep"),
            "last_price": m.get("lastPrice"),
            "prev_close": m.get("previousClose"),
            "change_pct": m.get("pChange"),
            "year_high": m.get("yearHigh"),
            "year_low": m.get("yearLow"),
            "purpose": m.get("purpose"),   # corporate action reason if any
        })
    if not rows:
        return
    up = sorted([r for r in rows if r["change_pct"] > 0],
                key=lambda x: x["change_pct"], reverse=True)
    down = sorted([r for r in rows if r["change_pct"] < 0],
                  key=lambda x: x["change_pct"])

    def buckets(pool):
        return {f"up_ge_{p}pct": sum(1 for r in pool if r["change_pct"] >= p)
                for p in (1, 2, 3, 4, 5)}

    dbuckets = {f"down_ge_{p}pct": sum(1 for r in down if r["change_pct"] <= -p)
                for p in (1, 2, 3, 4, 5)}

    out = {
        "updated": now_iso(),
        "stocks": len(rows),
        "gainer_buckets": buckets(up),
        "loser_buckets": dbuckets,
        "top20_gainers": up[:20],
        "top20_losers": down[:20],
        "corporate_action_alerts": [r for r in rows
                                    if r["purpose"] and
                                    str(r["purpose"]).strip() not in ("", "-")][:20],
    }
    (DATA / "preopen.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))
    print(f"preopen: {len(rows)} stocks | "
          f">=5% up: {out['gainer_buckets']['up_ge_5pct']} | "
          f">=5% down: {out['loser_buckets']['down_ge_5pct']}")


# ------------------------------------------------------------ FII/DII
def collect_fii_dii():
    try:
        j = get_json("https://www.nseindia.com/api/fiidiiTradeReact")
    except Exception as e:  # noqa: BLE001
        print("WARN fii/dii failed:", e)
        return
    out = {"updated": now_iso(), "date": None, "categories": {}}
    for r in j:
        out["date"] = r.get("date")
        out["categories"][r.get("category")] = {
            "buy_cr": float(r.get("buyValue", 0)),
            "sell_cr": float(r.get("sellValue", 0)),
            "net_cr": float(r.get("netValue", 0)),
        }
    if out["categories"]:
        (DATA / "fii-dii.json").write_text(json.dumps(out, indent=1))
        fii = out["categories"].get("FII/FPI", {})
        dii = out["categories"].get("DII", {})
        print(f"fii-dii: FII net {fii.get('net_cr')} Cr | "
              f"DII net {dii.get('net_cr')} Cr | date {out['date']}")


# ------------------------------------------------------------ index changes
def detect_index_changes():
    uni_p = DATA / "universe.json"
    prev_p = DATA / "nifty500-prev.json"
    chg_p = DATA / "index-changes.json"
    if not uni_p.exists():
        print("WARN no universe.json yet — run brain_collect first")
        return
    uni = json.loads(uni_p.read_text(encoding="utf-8"))
    current = {m["symbol"] for m in uni if m.get("tier") == 1}
    if not current:
        current = {m["symbol"] for m in uni}  # fallback: whole universe
    if prev_p.exists():
        prev = set(json.loads(prev_p.read_text(encoding="utf-8")))
        added = sorted(current - prev)
        removed = sorted(prev - current)
        chg = {"detected_on": now_iso(),
               "universe_size": len(current),
               "added": added, "removed": removed}
        chg_p.write_text(json.dumps(chg, indent=1))
        if added or removed:
            print(f"index-changes: +{added} -{removed}")
        else:
            print("index-changes: none")
    else:
        print("index-changes: first snapshot (baseline saved)")
    prev_p.write_text(json.dumps(sorted(current)))


def main():
    DATA.mkdir(exist_ok=True)
    collect_preopen()
    collect_fii_dii()
    detect_index_changes()


if __name__ == "__main__":
    main()
