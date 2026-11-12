#!/usr/bin/env python3
"""Find the exact request NSE's option chain accepts, from a runner.

THE FIRST PROBE CHANGED THE QUESTION. From the development sandbox the endpoint returns
HTTP 200 with a two-byte body - indistinguishable from a hard block. From a GitHub runner it
returned 73 bytes of plain text:

    missing symbol={ NIFTY | FINNIFTY | BANKNIFTY | NIFTYMID50 | MIDCPNIFTY }

That is the API answering. It is reachable; the request shape is wrong. A message that names
the accepted values is the opposite of a block, so "not usable" was the wrong verdict to
print and this probe retries with a matrix of parameter shapes instead of one guess.
"""
import json, sys, time, urllib.parse, urllib.request

UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.nseindia.com/option-chain",
}

BASE = "https://www.nseindia.com/api/option-chain-v3"
VARIANTS = [
    ("q type=Indices&symbol=NIFTY",   BASE + "?type=Indices&symbol=NIFTY"),
    ("q symbol=NIFTY&type=Indices",   BASE + "?symbol=NIFTY&type=Indices"),
    ("q type=indices&symbol=NIFTY",   BASE + "?type=indices&symbol=NIFTY"),
    ("q symbol=NIFTY only",           BASE + "?symbol=NIFTY"),
    ("q type=Indices only",           BASE + "?type=Indices"),
    ("q type=Indices&symbol=NIFTY&expiryDate=30-12-2026",
     BASE + "?type=Indices&symbol=NIFTY&expiryDate=" + urllib.parse.quote("30-12-2026")),
    ("path /NIFTY",                   BASE + "/NIFTY"),
    ("q index=NIFTY",                 BASE + "?type=Indices&index=NIFTY"),
]


def call(name, url, method="GET"):
    out = {"name": name, "url": url, "method": method}
    try:
        req = urllib.request.Request(url, headers=UA, method=method)
        with urllib.request.urlopen(req, timeout=30) as r:
            body = r.read()
            out["status"] = r.status
            out["bytes"] = len(body)
            txt = body.decode("utf-8", "replace")
            try:
                d = json.loads(txt)
                out["json"] = True
                rec = d.get("records") if isinstance(d, dict) else None
                if isinstance(rec, dict):
                    rows = rec.get("data") or []
                    out["strike_rows"] = len(rows)
                    out["expiry_dates"] = (rec.get("expiryDates") or [])[:3]
                    out["underlying"] = rec.get("underlyingValue")
                    if rows:
                        r0 = rows[0]
                        ce = r0.get("CE") or {}
                        pe = r0.get("PE") or {}
                        out["sample_oi"] = {"CE": ce.get("openInterest"),
                                            "PE": pe.get("openInterest"),
                                            "strike": r0.get("strikePrice")}
                elif isinstance(d, dict):
                    out["keys"] = list(d)[:8]
            except Exception:
                out["json"] = False
                out["text"] = txt[:140]
    except Exception as e:
        out["error"] = "%s: %s" % (type(e).__name__, str(e)[:120])
    return out


def main():
    print("=" * 72)
    print("NSE OPTION CHAIN - PARAMETER MATRIX")
    print("=" * 72)
    # a homepage visit sometimes sets the cookie the API wants
    try:
        urllib.request.urlopen(urllib.request.Request(
            "https://www.nseindia.com/", headers=UA), timeout=30).read()
        print("homepage: reachable")
    except Exception as e:
        print("homepage: %s: %s" % (type(e).__name__, str(e)[:90]))
    time.sleep(1.5)

    results = []
    for name, url in VARIANTS:
        r = call(name, url)
        results.append(r)
        rows = r.get("strike_rows") or 0
        flag = "WORKS" if rows else "     "
        print("\n%s %-42s status=%s bytes=%s" %
              (flag, name, r.get("status", "-"), r.get("bytes", "-")))
        if rows:
            print("      strike rows: %d | expiries: %s" % (rows, r.get("expiry_dates")))
            print("      sample OI: %s | underlying: %s" % (r.get("sample_oi"), r.get("underlying")))
        elif r.get("text"):
            print("      text: %r" % r["text"][:110])
        elif r.get("keys") is not None:
            print("      keys: %s" % r.get("keys"))
        elif r.get("error"):
            print("      error: %s" % r["error"])
        time.sleep(1.1)

    good = [r for r in results if (r.get("strike_rows") or 0) > 0]
    print("\n" + "=" * 72)
    if good:
        print("VERDICT: option chain IS usable from a runner.")
        print("Working shape: %s" % good[0]["name"])
        print("Intraday PCR is buildable - sum PE open interest over CE per snapshot.")
    else:
        print("VERDICT: no parameter shape returned strike rows.")
        print("The API answers, but not with data. Read the text above before concluding.")
    print("=" * 72)
    with open("option_chain_probe.json", "w") as fh:
        json.dump(results, fh, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
