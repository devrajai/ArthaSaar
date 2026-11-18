#!/usr/bin/env python3
"""Gold and silver in rupees per gram, with the change in rupees and in percent.

WHAT THIS IS, EXACTLY
The price is the international spot quote (COMEX front month, USD per troy ounce) converted
at the live USD/INR rate:

    rupees per gram = usd_per_ounce / 31.1034768 * usd_inr

This is NOT the rate your jeweller quotes. The local retail rate adds import duty, GST and a
dealer premium, so it sits roughly 10-15% above this figure. The message says so on every
send, because a gold price that is quietly 12% low is worse than no gold price.

WHY NOT MCX
The MCX feed returns 403 from every route we have tried, and the domestic ETF prices are per
unit rather than per gram. The ETF is carried alongside as a domestic cross-check, not as the
price.

UNITS
One troy ounce is 31.1034768 grams. Indian retail gold is normally quoted per 10 grams; the
message shows 1, 10 and 12 grams because all three get asked for.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

OUT = "docs/metals.json"
OZ_TO_G = 31.1034768
IST = timezone(timedelta(hours=5, minutes=30))

SOURCES = {
    "gold": "GC=F",
    "silver": "SI=F",
    "usdinr": "INR=X",
}
ETFS = {"goldbees": "GOLDBEES.NS", "silverbees": "SILVERBEES.NS"}


def quote(sym):
    try:
        u = ("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=5d&interval=1d"
             % urllib.parse.quote(sym))
        d = json.loads(urllib.request.urlopen(
            urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=25).read())
        r = d["chart"]["result"][0]
        m = r["meta"]
        cl = [c for c in ((r.get("indicators") or {}).get("quote") or [{}])[0].get("close") or [] if c]
        px = m.get("regularMarketPrice")
        pc = cl[-2] if len(cl) >= 2 else m.get("chartPreviousClose")
        return px, pc
    except Exception:
        return None, None


def per_gram(usd_oz, fx):
    if not usd_oz or not fx:
        return None
    return usd_oz / OZ_TO_G * fx


def main() -> int:
    g, g_prev = quote(SOURCES["gold"])
    s, s_prev = quote(SOURCES["silver"])
    fx, fx_prev = quote(SOURCES["usdinr"])

    if not (g and s and fx):
        print("gold/silver/fx unavailable - writing an explicit gap rather than a guess")
        os.makedirs("docs", exist_ok=True)
        json.dump({
            "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "available": False,
            "reason": "The Yahoo quote for gold, silver or USD/INR did not return a price.",
            "note": "No rate is published rather than a stale or invented one.",
        }, open(OUT, "w"), separators=(",", ":"))
        return 0

    g_pg = per_gram(g, fx)
    s_pg = per_gram(s, fx)
    # previous close, converted at the previous FX rate where we have it
    fxp = fx_prev or fx
    g_pg_prev = per_gram(g_prev, fxp) if g_prev else None
    s_pg_prev = per_gram(s_prev, fxp) if s_prev else None

    def block(cur, prev):
        if cur is None:
            return None
        out = {"per_gram": round(cur, 2)}
        for gm in (1, 10, 12):
            out["per_%dg" % gm] = round(cur * gm, 0)
        if prev:
            out["prev_per_gram"] = round(prev, 2)
            out["chg_per_gram"] = round(cur - prev, 2)
            out["chg_pct"] = round((cur / prev - 1.0) * 100.0, 2)
            out["chg_per_10g"] = round((cur - prev) * 10, 0)
            out["chg_per_12g"] = round((cur - prev) * 12, 0)
        return out

    etfs = {}
    for k, sym in ETFS.items():
        px, pc = quote(sym)
        if px:
            etfs[k] = {"price": round(px, 2),
                       "chg_pct": round((px / pc - 1) * 100.0, 2) if pc else None}

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "as_of_ist": datetime.now(IST).strftime("%d %b %Y %H:%M IST"),
        "available": True,
        "gold": block(g_pg, g_pg_prev),
        "silver": block(s_pg, s_pg_prev),
        "usdinr": round(fx, 3),
        "usdinr_chg_pct": round((fx / fx_prev - 1.0) * 100.0, 2) if fx_prev else None,
        "spot_usd": {"gold_per_oz": round(g, 2), "silver_per_oz": round(s, 3)},
        "etf_cross_check": etfs,
        "note": ("International spot converted at the live USD/INR rate. This is NOT the "
                 "jeweller's rate: local retail adds import duty, GST and a dealer premium, so "
                 "it usually sits 10-15% above this figure."),
        "method": ("rupees per gram = USD per troy ounce / 31.1034768 * USD/INR. One troy "
                   "ounce is 31.1034768 grams."),
    }
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    for nm in ("gold", "silver"):
        b = out[nm]
        if b:
            print("   %-6s Rs %s/g · 10g Rs %s · 12g Rs %s  (%s, %s%%)"
                  % (nm, "{:,.0f}".format(b["per_gram"]),
                     "{:,.0f}".format(b["per_10g"]), "{:,.0f}".format(b["per_12g"]),
                     ("%+.0f" % b.get("chg_per_gram", 0)), ("%+.2f" % b.get("chg_pct", 0))))
    print("   USD/INR %.3f" % fx)
    return 0


if __name__ == "__main__":
    sys.exit(main())
