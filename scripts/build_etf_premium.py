#!/usr/bin/env python3
"""ETF premium / discount to NAV (Task 16).

An ETF trades on the exchange at a price that can drift from the value of what it holds.
AMCs publish their ETFs' NAVs to AMFI, and mfapi.in republishes that list. So:

    premium_pct = (market_close - nav) / nav * 100

The hard part is the NAME MATCH, and a wrong premium is worse than a missing one. So a row
is published only when the AMC name AND a distinctive underlying token both appear in the
scheme name. Everything ambiguous is dropped, and the script prints matched vs dropped.
"""
import csv, glob, json, os, re, sys, urllib.request
from datetime import datetime, timezone

OUT = "docs/etf_premium.json"
MF_LIST = "https://api.mfapi.in/mf"
UA = {"User-Agent": "Mozilla/5.0 (compatible; ArthaSaar/1.0)"}

# Only packaging words are dropped. "nifty", "sensex", "gold", "50" and the rest are
# KEPT: they are the words that tell one ETF from another, and dropping them made
# "Nifty 50 BeES" look like "Nifty BeES".
STOP = {"etf", "fund", "exchange", "traded", "scheme", "regular", "direct", "plan",
        "growth", "option", "options", "idcw", "dividend", "the", "of", "and", "an",
        "series", "class", "units"}


def norm(s):
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


# NSE writes ETFs in shorthand that AMFI spells out. Expanding first is what lets
# "NIFTYBEES" and "Nippon India ETF Nifty 50 BeES" agree.
ABBREV = {
    "n50": "nifty 50", "n100": "nifty 100", "n500": "nifty 500", "nn50": "nifty next 50",
    "bnf": "bank nifty", "nbn": "bank nifty", "midcap150": "nifty midcap 150",
    "smlcap250": "nifty smallcap 250", "nxt50": "nifty next 50",
    "midsml": "midcap smallcap", "gtilt": "gsec gilt", "gs": "gsec",
}


def expand(s):
    t = " " + norm(s) + " "
    for k, v in ABBREV.items():
        t = t.replace(" " + k + " ", " " + v + " ")
    return t


def tokens(s):
    return [t for t in expand(s).split() if t and t not in STOP and len(t) > 1]


def load_etf_list():
    """NSE's own ETF list: symbol, name. Written by fetch_nse_extra.py."""
    for path in ("data/nse/etf_list.csv", "data/nse/eq_etfseclist.csv"):
        if not os.path.exists(path):
            continue
        out = []
        with open(path, newline="", encoding="utf-8", errors="replace") as fh:
            for row in csv.DictReader(fh):
                sym = (row.get("SYMBOL") or row.get("Symbol") or "").strip()
                nm = (row.get("NAME OF COMPANY") or row.get("Underlying")
                      or row.get("Security Name") or row.get("NAME") or "").strip()
                if sym:
                    out.append((sym, nm))
        if out:
            print("  etf list: %d from %s" % (len(out), path))
            return out
    return []


def load_closes():
    """Latest close per symbol from the newest bhavcopy CSV on disk."""
    files = sorted(glob.glob("data/csv/cm/*.csv"))
    if not files:
        return {}
    latest = files[-1]
    closes = {}
    with open(latest, newline="", encoding="utf-8", errors="replace") as fh:
        for row in csv.DictReader(fh):
            # Case-insensitive: NSE's raw UDiFF file uses TckrSymb/ClsPric, but the
            # normalised CSV this repo keeps uses lowercase symbol/close. Looking for only
            # one spelling silently returned zero rows.
            low = {str(k).strip().lower(): v for k, v in row.items()}
            sym = (low.get("tckrsymb") or low.get("symbol") or "").strip()
            px = low.get("clspric") or low.get("close")
            if sym and px:
                try:
                    closes[sym] = float(str(px).replace(",", ""))
                except ValueError:
                    pass
    print("  closes: %d from %s" % (len(closes), os.path.basename(latest)))
    return closes


def fetch_mf_list():
    try:
        req = urllib.request.Request(MF_LIST, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read().decode("utf-8", "replace"))
        print("  mfapi schemes: %d" % len(data))
        return data
    except Exception as e:
        print("  mfapi list -> %s" % type(e).__name__)
        return []


def build_index(schemes):
    """Only schemes that look like ETFs, with their tokens precomputed."""
    idx = []
    for s in schemes:
        nm = s.get("schemeName") or ""
        if "etf" not in norm(nm):
            continue
        idx.append({"code": s.get("schemeCode"), "name": nm, "tok": set(tokens(nm))})
    print("  etf schemes on mfapi: %d" % len(idx))
    return idx


# Words too common to prove an identity on their own. Sharing ONLY these is not a match.
GENERIC = {"nifty", "sensex", "gold", "bank", "silver", "india", "index", "liquid",
           "gilt", "bond", "etf", "exchange", "traded", "fund"}


def match(nse_name, nse_sym, idx):
    """Return (scheme_code, score) for a confident match, or (None, 0).

    This used to require FULL containment - every distinctive token in the NSE name had to
    appear in the scheme name - which matched 0 of 354. NSE and AMFI simply name the same
    fund differently often enough that containment almost never holds.

    Now it SCORES, but with three guards that keep a wrong premium out:
      1. cover  >= 0.75  - most of the NSE name must appear in the scheme
      2. at least one DISTINCTIVE token shared - never match on "gold"/"nifty"/"bank" alone,
         which is exactly how "Nifty 50 BeES" would otherwise land on "Nifty BeES"
      3. the winner must beat the runner-up - if two candidates look equally good it is
         genuinely ambiguous and gets dropped rather than guessed
    """
    nt = set(tokens(nse_name)) or set(tokens(nse_sym))
    if not nt:
        return None, 0

    scored = []
    for cand in idx:
        shared = nt & cand["tok"]
        if not shared:
            continue
        cover = len(shared) / len(nt)                 # how much of the NSE name is present
        precision = len(shared) / max(1, len(cand["tok"]))   # penalise enormous schemes
        distinctive = len(shared - GENERIC)
        exact = 1 if cand["tok"] == nt else 0
        scored.append((exact, cover, precision, distinctive, len(cand["tok"]), cand["code"]))
    if not scored:
        return None, 0

    scored.sort(key=lambda x: (-x[0], -x[1], -x[2], x[4]))
    best = scored[0]
    if best[1] < 0.75:                                # guard 1
        return None, 0
    if best[3] < 1:                                   # guard 2
        return None, 0
    if len(scored) > 1 and not best[0]:               # guard 3, unless one is an exact set
        second = scored[1]
        if abs(best[1] - second[1]) < 0.15 and abs(best[2] - second[2]) < 0.15:
            return None, 0
    return best[5], int(round(best[1] * 100))


def main():
    etfs = load_etf_list()
    closes = load_closes()
    schemes = fetch_mf_list()
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "rows": [], "count": 0, "note": ""}

    if not etfs or not closes or not schemes:
        missing = []
        if not etfs:
            missing.append("NSE's ETF list")
        if not closes:
            missing.append("bhavcopy closes")
        if not schemes:
            missing.append("mfapi.in's scheme list")
        out["note"] = ("Could not build this yet - %s unavailable from this network. "
                       "Nothing is shown rather than a guessed premium." % ", ".join(missing))
        os.makedirs("docs", exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False)
        print("etf premium: skipped (%s)" % out["note"])
        return 0

    idx = build_index(schemes)
    matched = dropped = no_price = 0
    for sym, name in etfs:
        px = closes.get(sym)
        if px is None:
            no_price += 1
            continue
        code, score = match(name, sym, idx)
        if not code:
            dropped += 1
            continue
        matched += 1
        out["rows"].append({"symbol": sym, "name": name, "close": round(px, 2),
                            "scheme_code": code, "match_tokens": score})

    out["count"] = len(out["rows"])
    out["matched"], out["dropped"], out["no_price"] = matched, dropped, no_price
    if not out["count"]:
        out["note"] = ("No ETF could be matched to a published NAV with confidence "
                       "(%d dropped as ambiguous). A wrong premium is worse than none." % dropped)
    else:
        out["note"] = ("%d ETFs matched to a published NAV. %d were dropped as ambiguous and "
                       "%d had no close price. Only confident matches are shown."
                       % (matched, dropped, no_price))
    os.makedirs("docs", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False)
    print("etf premium: %d matched, %d dropped, %d no price -> %s"
          % (matched, dropped, no_price, OUT))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
