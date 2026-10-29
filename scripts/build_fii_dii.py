#!/usr/bin/env python3
"""FII and DII cash-market flows - the most-watched end-of-day number in India.

WHY THIS DID NOT EXIST
fetch_nse_extra.py has always pulled NSE's fiidiiTradeReact endpoint and written
data/nse/fii_dii.csv. Nothing ever turned that into a file the site reads, so the FII/DII
section has been rendering empty while the data sat on disk. This is the missing link.

AND WHY THERE WAS NO HISTORY
That endpoint returns only the LATEST session. The fetch overwrote the CSV every run, so
yesterday's figure was replaced by today's and nothing accumulated. It now appends,
de-duplicated on (date, category), so the series builds up day by day.

WHAT THE NUMBERS MEAN, because the sign is easy to misread
  netValue is in ₹ crore.
  FII net POSITIVE = foreigners bought more than they sold.
  FII net NEGATIVE = they sold more than they bought.
NSE reports FII/FPI and DII as separate categories, and they often move opposite ways - a
day where FIIs sell heavily is frequently a day DIIs buy. Reading only one of them tells you
half the story.
"""
import json, os, sys
from datetime import datetime, timezone

OUT = "docs/fii_dii.json"
SOURCES = ("data/nse/fii_dii_history.csv", "data/nse/fii_dii.csv")


def main():
    import pandas as pd

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "latest": [], "history": [], "note": ""}

    path = next((p for p in SOURCES if os.path.exists(p)), None)
    if not path:
        out["note"] = ("No FII/DII file on disk. NSE's endpoint returns only the latest "
                       "session, so this fills in once the fetch succeeds.")
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("fii/dii: skipped (no csv)")
        return 0

    df = pd.read_csv(path)
    print("  read %s: %d rows, columns %s" % (path, len(df), list(df.columns)[:6]))

    if "category" not in df.columns:
        out["note"] = "The file has no 'category' column: %s" % list(df.columns)[:10]
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        return 0

    for c in ("buyValue", "sellValue", "netValue"):
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # normalise the category label so FII/FPI variants group together
    def bucket(cat):
        c = str(cat).upper()
        if "FII" in c or "FPI" in c:
            return "FII"
        if "DII" in c:
            return "DII"
        return str(cat)

    df["who"] = df["category"].map(bucket)

    # parse dates like 28-Oct-2026
    if "date" in df.columns:
        d = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
        if d.isna().all():
            d = pd.to_datetime(df["date"], errors="coerce", dayfirst=True)
        df["d"] = d.dt.strftime("%Y-%m-%d")
    else:
        df["d"] = None

    df = df.dropna(subset=["netValue"])
    if df.empty:
        out["note"] = "Every netValue in the file was unreadable."
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        return 0

    latest_date = df["d"].dropna().max() if df["d"].notna().any() else None
    latest = df[df["d"] == latest_date] if latest_date else df.tail(2)

    for r in latest.itertuples(index=False):
        out["latest"].append({
            "who": getattr(r, "who"),
            "category": getattr(r, "category"),
            "date": getattr(r, "d"),
            "buy": round(float(getattr(r, "buyValue")), 2) if getattr(r, "buyValue") == getattr(r, "buyValue") else None,
            "sell": round(float(getattr(r, "sellValue")), 2) if getattr(r, "sellValue") == getattr(r, "sellValue") else None,
            "net": round(float(getattr(r, "netValue")), 2),
        })

    # history: one row per date with FII and DII net, so it can be charted
    if df["d"].notna().any():
        piv = df.pivot_table(index="d", columns="who", values="netValue", aggfunc="last")
        piv = piv.sort_index().tail(120)
        for d, row in piv.iterrows():
            out["history"].append({
                "date": d,
                "fii": round(float(row["FII"]), 2) if "FII" in piv.columns and row.get("FII") == row.get("FII") else None,
                "dii": round(float(row["DII"]), 2) if "DII" in piv.columns and row.get("DII") == row.get("DII") else None,
            })

    out["count"] = len(out["history"]) or len(out["latest"])
    out["note"] = ("Net cash-market flows in crore rupees for the latest session, plus whatever "
                   "history has accumulated. Positive means net buying. FII and DII often move "
                   "in opposite directions on the same day.")
    out["cautions"] = {
        "sign": ("netValue is in ₹ crore. Positive is net buying, negative is net selling."),
        "history": ("NSE's endpoint returns only the latest session, so the history here is as "
                    "long as this pipeline has been running - not back to 2019."),
        "provisional": ("These are provisional figures and NSE revises them. Treat the last day "
                        "as indicative."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB  |  %d latest, %d history rows"
          % (OUT, os.path.getsize(OUT) / 1024, len(out["latest"]), len(out["history"])))
    for r in out["latest"]:
        print("   %-4s %s  net %+0.2f cr" % (r["who"], r["date"] or "", r["net"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
