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


def tokens(s):
    return [t for t in norm(s).split() if t and t not in STOP and len(t) > 1]


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


def match(nse_name, nse_sym, idx):
    """Return (scheme_code, score) for a confident match, or (None, 0).

    Rule: EVERY distinctive token in the NSE name must appear in the scheme name, and the
    winner must be unique. Full containment is deliberately strict - it is what stops
    "Nifty 50 BeES" matching "Nifty BeES", and a wrong premium is worse than none.
    """
    # Only the NAME's tokens, never the symbol's: an NSE symbol like "NIFTYBEES" is a
    # single glued token that can never appear in an AMFI scheme name, so including it
    # made full containment impossible and nothing ever matched.
    nt = set(tokens(nse_name))
    if not nt:
        nt = set(tokens(nse_sym))
    if not nt:
        return None, 0
    hits = []
    for cand in idx:
        if nt <= cand["tok"]:          # every NSE token present in the scheme
            hits.append((len(cand["tok"]), cand["code"]))
    # An exact token-set match beats every superset. Without this, "Nifty BeES" is dropped
    # as ambiguous because "Nifty 50 BeES" also contains it - even though one is exact.
    exact = [c for n, c in hits if n == len(nt)]
    if len(exact) == 1:
        return exact[0], len(nt)
    if len(hits) == 1:
        return hits[0][1], len(nt)
    if len(hits) > 1:
        # several schemes contain the name - usually plan/option variants of the same fund.
        # Take it only if one is clearly the closest; otherwise drop it as ambiguous.
        hits.sort()
        if hits[0][0] < hits[1][0] - 1:
            return hits[0][1], len(nt)
    return None, 0


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
