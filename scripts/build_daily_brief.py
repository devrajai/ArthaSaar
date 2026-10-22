#!/usr/bin/env python3
"""The daily brief (Task 4) - what moved today, in plain English.

Built ONLY from numbers already in the hub. If a figure is missing the sentence is dropped
entirely. It deliberately does NOT explain WHY anything moved: it has no reliable source for
causes, and "Nifty fell because of US yields" is the kind of line that sounds like analysis
and is really a guess.
"""
import json, os, sys
from datetime import datetime, timezone

OUT = "docs/brief.json"


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def fnum(v):
    try:
        return float(v)
    except Exception:
        return None


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "headline": "", "bullets": [], "note": ""}
    d, idx, sec = load("docs/data.json"), load("docs/indices.json"), load("docs/sectors.json")
    bullets = []

    # headline: the headline index and its move
    n50 = None
    if idx:
        for x in (idx.get("indices") or []):
            if x.get("id") == "nifty50":
                n50 = x
                break
    if n50 and n50.get("level") and n50.get("points") is not None:
        pts = fnum(n50["points"]) or 0
        chg = fnum(n50.get("chg_pct")) or 0
        out["headline"] = ("Nifty closed %s points %s at %s (%s%.2f%%)."
                           % (f"{abs(pts):,.0f}", "higher" if pts >= 0 else "lower",
                              f"{fnum(n50['level']):,.0f}", "+" if chg >= 0 else "", chg))
    elif d and d.get("markets", {}).get("rows"):
        for row in d["markets"]["rows"]:
            if str(row[0]).upper() in ("^NSEI", "NIFTY"):
                out["headline"] = "Nifty at %s (%s%.2f%%)." % (f"{fnum(row[1]):,.0f}", "+" if (fnum(row[2]) or 0) >= 0 else "", fnum(row[2]) or 0)
                break

    # breadth, from the index itself
    if n50 and n50.get("advances") is not None:
        bullets.append("Advances %s to %s within the Nifty 50."
                       % (n50.get("advances"), n50.get("declines")))

    # Sectors: the extremes only, never all 28.
    #
    # The sector list mixes two taxonomies, so it contains near-duplicates -
    # "Information Technology" AND "Technology", "Real Estate" AND "Realty". Taking the raw
    # min and max made the brief contrast a sector with itself ("weakest Technology,
    # strongest Information Technology"), which reads as nonsense. So collapse a name into
    # another when every one of its significant words already appears in the other, keeping
    # the broader bucket, and pick the extremes from what is left.
    if sec and sec.get("sectors"):
        stop = {"and", "of", "the", "services", "service", "materials", "components", "fuels"}
        def toks(nm):
            return {w for w in str(nm).lower().replace("&", " ").split()
                    if len(w) > 2 and w not in stop}
        cand = [x for x in sec["sectors"] if x.get("avg_chg") is not None]
        keep = []
        for x in sorted(cand, key=lambda z: -(z.get("count") or 0)):
            tx = toks(x["name"])
            if not tx:
                continue
            if any(tx <= toks(k["name"]) for k in keep):
                continue
            keep.append(x)
        keep.sort(key=lambda z: z["avg_chg"])
        if len(keep) >= 2:
            w, b = keep[0], keep[-1]
            bullets.append("Weakest sector %s (%s%.2f%%), strongest %s (%s%.2f%%)."
                           % (w["name"], "+" if w["avg_chg"] >= 0 else "", w["avg_chg"],
                              b["name"], "+" if b["avg_chg"] >= 0 else "", b["avg_chg"]))

    # F&O positioning. NOTE: fno["pcr"] is a DICT {nifty_pcr_oi, nifty_max_pain}, not a
    # number, and stock_futures is a COUNT, not a list. Both were wrong first time round.
    if d:
        fno = d.get("fno") or {}
        pcr = fno.get("pcr")
        if isinstance(pcr, dict):
            v = fnum(pcr.get("nifty_pcr_oi"))
            if v is not None:
                bullets.append("Nifty put-call ratio %.2f." % v)
        elif fnum(pcr) is not None:
            bullets.append("Nifty put-call ratio %.2f." % fnum(pcr))
        sf = fno.get("stock_futures")
        if isinstance(sf, list) and sf:
            bullets.append("%d stock futures carry open interest worth noting." % len(sf))
        elif isinstance(sf, int) and sf:
            bullets.append("%d stock futures carry open interest worth noting." % sf)

    # spikes
    if d:
        sp = (d.get("spikes") or {}).get("oi")
        if isinstance(sp, list) and sp:
            bullets.append("%d open-interest spikes today." % len(sp))

    # corporate actions. Each bucket is a DICT with a "total", not a list.
    if d:
        co = d.get("corporate") or {}
        bits = []
        for k, label in (("dividend", "dividends"), ("split", "splits")):
            v = co.get(k)
            n = v.get("total") if isinstance(v, dict) else (len(v) if isinstance(v, list) else None)
            if n:
                bits.append("%d %s" % (n, label))
        if bits:
            bullets.append("Went ex today: " + " and ".join(bits) + ".")

    # FII/DII. The category is a ROW value, not a column name - so the FII figure is found
    # by scanning rows for category == FII, not by looking for a "fii" column.
    if d:
        fd = d.get("fii_dii") or {}
        rows = fd.get("rows") or []
        cols = [str(c).strip().lower() for c in (fd.get("columns") or [])]
        ci = cols.index("category") if "category" in cols else None
        ni = cols.index("netvalue") if "netvalue" in cols else None
        if ci is not None and ni is not None:
            for r in rows:
                try:
                    if str(r[ci]).strip().upper().startswith("FII"):
                        v = fnum(r[ni])
                        if v is not None:
                            bullets.append("FII %s %s crore in the cash market."
                                           % ("bought" if v >= 0 else "sold", f"{abs(v):,.0f}"))
                        break
                except Exception:
                    continue

    out["bullets"] = bullets[:6]
    if not out["headline"] and not bullets:
        out["note"] = "No market data was available to summarise."
    else:
        out["note"] = ("This describes what moved, not why. It is generated from this hub's own "
                       "numbers, so anything not in the data is left out rather than guessed. "
                       "Correlation is not causation.")
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    print("brief: %d bullets" % len(out["bullets"]))
    print("  " + (out["headline"] or "(no headline)"))
    for b in out["bullets"]:
        print("  - " + b)
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
