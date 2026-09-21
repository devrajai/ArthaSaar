#!/usr/bin/env python3
"""Index + sector constituents — NSE free CSV downloads (no key).
Output: data/constituents.json — feeds the sector heatmap (sector -> stocks).
"""
import csv
import io
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

LISTS = {
    "nifty50": "ind_nifty50list.csv",
    "niftynext50": "ind_niftynext50list.csv",
    "niftymidcap150": "ind_niftymidcap150list.csv",
    "niftysmallcap250": "ind_niftysmallcap250list.csv",
    "nifty500": "ind_nifty500list.csv",
}
SECTORS = {
    "IT": "ind_niftyitlist.csv",
    "Bank": "ind_niftybanklist.csv",
    "Auto": "ind_niftyautolist.csv",
    "Pharma": "ind_niftypharmalist.csv",
    "FMCG": "ind_niftyfmcglist.csv",
    "Metal": "ind_niftymetallist.csv",
    "Energy": "ind_niftyenergylist.csv",
    "Oil & Gas": "ind_niftyoilgaslist.csv",
    "Realty": "ind_niftyrealtylist.csv",
    "Infra": "ind_niftyinfralist.csv",
    "Media": "ind_niftymedialist.csv",
    "Fin Serv": "ind_niftyfinancelist.csv",
    "Cons Dur": "ind_niftyconsumerdurableslist.csv",
    "Healthcare": "ind_niftyhealthcarelist.csv",
}

def get(name):
    url = "https://nsearchives.nseindia.com/content/indices/" + name
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        text = r.read().decode("utf-8", "ignore")
    rows = list(csv.DictReader(io.StringIO(text)))
    out = []
    for x in rows:
        sym = (x.get("Symbol") or "").strip()
        if sym:
            out.append({"symbol": sym,
                        "company": (x.get("Company Name") or "").strip()})
    return out

def main():
    out = {"updated": datetime.now(timezone.utc).isoformat(), "lists": {}, "sectors": {}}
    for key, fname in LISTS.items():
        try:
            out["lists"][key] = get(fname)
            print("ok", key, len(out["lists"][key]))
        except Exception as e:  # noqa: BLE001
            print("FAIL", key, str(e)[:60])
        time.sleep(1.2)  # be gentle
    for key, fname in SECTORS.items():
        try:
            out["sectors"][key] = get(fname)
            print("ok", key, len(out["sectors"][key]))
        except Exception as e:  # noqa: BLE001
            print("FAIL", key, str(e)[:60])
        time.sleep(1.2)  # be gentle
    (DATA / "constituents.json").write_text(json.dumps(out, separators=(",", ":")))
    n = sum(len(v) for v in out["lists"].values()) + sum(len(v) for v in out["sectors"].values())
    print(f"wrote data/constituents.json — {n} entries across "
          f"{len(out['lists'])} lists + {len(out['sectors'])} sectors")

if __name__ == "__main__":
    main()
