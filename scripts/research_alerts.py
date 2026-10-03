#!/usr/bin/env python3
"""Build the free ArthaSaar Research Radar alert feed."""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"

def load(name, default):
    try:
        return json.loads((DATA/name).read_text(encoding="utf-8"))
    except Exception:
        return default

def main():
    rr=load("research-radar.json",{})
    f=rr.get("features") or {}
    alerts=[]
    def add(kind,symbol,title,detail,source="ArthaSaar",severity="info"):
        alerts.append({"date":datetime.now(timezone.utc).date().isoformat(),"kind":kind,"symbol":symbol,
                       "title":title,"detail":detail,"source":source,"severity":severity})
    for x in (f.get("breakout_radar") or {}).get("rows") or []:
        add("52W_BREAKOUT",x.get("symbol"),"52W breakout zone",
            "Within 0.75% of 252-session high.","ArthaSaar history","up")
    for x in (f.get("volume_shock") or {}).get("rows") or []:
        try: vr=float(x.get("vol_vs_avg20") or 0)
        except Exception: vr=0
        if vr >= 2:
            add("VOLUME_SHOCK",x.get("symbol"),"Volume shock",
                f"Volume {vr:.1f}× 20D average.","ArthaSaar screener","up")
    for x in (f.get("delivery_conviction") or {}).get("high_delivery_up") or []:
        add("DELIVERY",x.get("symbol"),"High delivery",
            f"Delivery {float(x.get('delivery_pct') or 0):.1f}% with positive EOD move.","NSE delivery","up")
    for x in (f.get("fo_buildup") or {}).get("long_build") or []:
        add("F&O_LONG_BUILD",x.get("symbol"),"Long-build style",
            f"Price up + OI up; OI change {float(x.get('oi_change_pct') or 0):.1f}%.","NSE futures","up")
    for x in (f.get("fo_buildup") or {}).get("short_build") or []:
        add("F&O_SHORT_BUILD",x.get("symbol"),"Short-build style",
            f"Price down + OI up; OI change {float(x.get('oi_change_pct') or 0):.1f}%.","NSE futures","down")
    ix=f.get("index_changes") or {}
    for idx,z in (ix.get("membership_changes") or {}).items():
        for s in z.get("added") or []:
            add("INDEX_ADD",s,f"{idx} addition","New constituent in latest NSE membership comparison.","NSE","info")
        for s in z.get("removed") or []:
            add("INDEX_REMOVE",s,f"{idx} removal","Constituent absent from latest NSE membership comparison.","NSE","down")
    for x in (f.get("corporate_actions") or {}).get("events") or []:
        if x.get("symbol"):
            add("FILING",x.get("symbol"),x.get("kind") or "Corporate filing",
                x.get("subject") or "Exchange filing detected.","NSE/public filings","info")
    # Keep the alert feed compact for the static site.
    rank={"down":0,"up":1,"info":2}
    alerts=sorted(alerts,key=lambda x:(str(x.get("symbol") or ""),rank.get(x.get("severity"),2)))[:200]
    out={"updated":datetime.now(timezone.utc).isoformat(),"count":len(alerts),
         "policy":"Descriptive alerts from committed public snapshots; not recommendations.","alerts":alerts}
    (DATA/"research-alerts.json").write_text(json.dumps(out,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print("Research alerts:",len(alerts))

if __name__=="__main__":
    main()
