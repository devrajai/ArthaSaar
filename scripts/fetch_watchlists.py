#!/usr/bin/env python3
"""Surveillance lists (Task 6) - F&O ban, ASM and GSM.

Each endpoint is undocumented and changes shape. Every one is tried INDEPENDENTLY: if one
fails the others still publish, and if all fail the file carries a note saying so.
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone

OUT = "docs/watchlists.json"
UA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

ENDPOINTS = {
    "ban": "https://www.nseindia.com/api/fo-secban",
    "asm": "https://www.nseindia.com/api/reportASM",
    "gsm": "https://www.nseindia.com/api/reportGSM",
}


def get(url):
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except Exception as e:
        print("  %s -> %s" % (url.rsplit("/", 1)[-1], type(e).__name__))
        return None


def symbols_from(data):
    """Pull symbol-like strings out of whatever shape the endpoint returned."""
    out = []
    def walk(node):
        if isinstance(node, dict):
            sym = node.get("symbol") or node.get("Symbol") or node.get("scrip")
            if sym:
                reason = (node.get("reason") or node.get("Remark") or node.get("remarks")
                          or node.get("survDesc") or node.get("desc") or "")
                out.append([str(sym).strip(), str(reason).strip()[:90]])
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    walk(data)
    seen, uniq = set(), []
    for s in out:
        if s[0] and s[0] not in seen:
            seen.add(s[0])
            uniq.append(s)
    return uniq


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "ban": [], "asm": [], "gsm": [], "note": "", "failed": []}
    for key, url in ENDPOINTS.items():
        data = get(url)
        if data is None:
            out["failed"].append(key)
            continue
        rows = symbols_from(data)
        out[key] = rows
        print("  %s: %d symbols" % (key, len(rows)))
    total = len(out["ban"]) + len(out["asm"]) + len(out["gsm"])
    out["count"] = total
    if not total:
        out["note"] = ("None of the surveillance endpoints returned anything (%s). Nothing is "
                       "shown rather than an empty table that looks like good news."
                       % ", ".join(out["failed"]) or "all responded empty")
    else:
        out["note"] = ("F&O ban means no fresh positions may be taken in that contract. ASM and "
                       "GSM mean the exchange has flagged unusual price or disclosure behaviour. "
                       "A listing is a flag, not a verdict.")
    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False)
    print("watchlists: %d rows -> %s" % (total, OUT))
    return 0


if __name__ == "__main__":
    _rc = main()
    import os as _os, sys as _sys
    _sys.stdout.flush(); _sys.stderr.flush()
    _os._exit(_rc)
