#!/usr/bin/env python3
"""Probe NSE's option chain from wherever this runs, and report exactly what came back.

WHY
An intraday put-call ratio needs option-chain snapshots through the session. From the
development sandbox the endpoint answers HTTP 200 with a two-byte body - an empty payload,
the same block the insider endpoints return. A GitHub runner has a different network path,
so the only way to know whether intraday PCR is buildable is to ask from there.

This prints the raw evidence rather than a verdict: status, byte count, and the shape of
whatever came back. A 200 with an empty body is not a success and must not be read as one.
"""
import json, sys, time, urllib.request

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
    "Connection": "keep-alive",
}

TARGETS = [
    ("option-chain-v3-indices",
     "https://www.nseindia.com/api/option-chain-v3"),
    ("option-chain-v3-banknifty",
     "https://www.nseindia.com/api/option-chain-v3"),
    ("option-chain-indices",
     "https://www.nseindia.com/api/option-chain-indices"),
    ("option-chain-equities",
     "https://www.nseindia.com/api/option-chain-equities"),
]


def probe(name, url):
    out = {"name": name, "url": url}
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            out["status"] = r.status
            out["bytes"] = len(body)
            out["content_type"] = r.headers.get("Content-Type", "")
            if len(body) < 200:
                out["body_preview"] = body.decode("utf-8", "replace")
            try:
                d = json.loads(body)
            except Exception:
                out["parsed"] = False
                return out
            out["parsed"] = True
            if isinstance(d, dict):
                out["keys"] = list(d)[:8]
                rec = d.get("records") or {}
                if isinstance(rec, dict):
                    out["expiry_dates"] = (rec.get("expiryDates") or [])[:3]
                    rows = rec.get("data") or []
                    out["strike_rows"] = len(rows)
                    if rows:
                        r0 = rows[0]
                        out["sample"] = {k: r0.get(k) for k in
                                         ("strikePrice", "expiryDate") if k in r0}
                        ce = r0.get("CE") or {}
                        pe = r0.get("PE") or {}
                        out["sample_oi"] = {"CE_oi": ce.get("openInterest"),
                                            "PE_oi": pe.get("openInterest")}
                    under = rec.get("underlyingValue")
                    out["underlying"] = under
            elif isinstance(d, list):
                out["list_len"] = len(d)
    except Exception as e:
        out["error"] = "%s: %s" % (type(e).__name__, str(e)[:160])
    return out


def main():
    print("=" * 70)
    print("NSE OPTION CHAIN PROBE")
    print("=" * 70)
    # NSE sets a session cookie on the homepage; a bare API call is often refused without it
    try:
        urllib.request.urlopen(urllib.request.Request(
            "https://www.nseindia.com/", headers=UA), timeout=30).read()
        print("homepage: reachable (cookie may be set)")
    except Exception as e:
        print("homepage: %s: %s" % (type(e).__name__, str(e)[:100]))
    time.sleep(1.5)

    results = []
    for name, url in TARGETS:
        r = probe(name, url)
        results.append(r)
        status = r.get("status", "-")
        print("\n%-26s status=%s bytes=%s parsed=%s"
              % (name, status, r.get("bytes", "-"), r.get("parsed", "-")))
        if r.get("strike_rows"):
            print("   strike rows: %s | expiries: %s"
                  % (r["strike_rows"], r.get("expiry_dates")))
            print("   sample OI: %s" % r.get("sample_oi"))
            print("   underlying: %s" % r.get("underlying"))
        elif r.get("body_preview") is not None:
            print("   body: %r" % r["body_preview"][:120])
        elif r.get("error"):
            print("   error: %s" % r["error"])
        elif r.get("keys") is not None:
            print("   keys: %s" % r.get("keys"))
        time.sleep(1.2)

    workable = [r for r in results if (r.get("strike_rows") or 0) > 0]
    print("\n" + "=" * 70)
    if workable:
        print("VERDICT: option chain IS reachable from here - %d of %d endpoints returned "
              "strike rows." % (len(workable), len(results)))
        print("An intraday PCR is buildable: sum PE open interest over CE open interest "
              "per snapshot.")
    else:
        print("VERDICT: option chain is NOT usable from here - no endpoint returned strike "
              "rows. Intraday PCR cannot be built from NSE.")
    print("=" * 70)
    with open("option_chain_probe.json", "w") as fh:
        json.dump(results, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
