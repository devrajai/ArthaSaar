#!/usr/bin/env python3
"""ArthaSaar - circuit limits from NSE bhavcopy (free).
Upper circuit = close locked at day high (no sellers). Lower = locked at low.
Band = implied from the day's move (rounded to the usual 5/10/20% buckets)."""
import csv, io, json, sys, urllib.request, zipfile
from datetime import datetime, timedelta, timezone

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

def grab(d):
    u = f"https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_{d}_F_0000.csv.zip"
    r = urllib.request.Request(u, headers={"User-Agent": UA, "Accept": "*/*"})
    raw = urllib.request.urlopen(r, timeout=60).read()
    z = zipfile.ZipFile(io.BytesIO(raw))
    name = [n for n in z.namelist() if n.endswith(".csv")][0]
    return z.read(name).decode("utf-8", "replace")

def main():
    text = None; day = None
    for back in range(0, 6):
        d = (datetime.now(timezone.utc) - timedelta(days=back)).strftime("%Y%m%d")
        try:
            text = grab(d); day = d; break
        except Exception as e:
            print("skip", d, e)
    if not text:
        sys.exit("no bhavcopy")
    up, dn = [], []
    for row in csv.DictReader(io.StringIO(text)):
        if row.get("SctySrs") != "EQ":
            continue
        try:
            c = float(row["ClsPric"]); h = float(row["HghPric"]); l = float(row["LwPric"])
            pc = float(row["PrvsClsgPric"]); v = float(row["TtlTradgVol"] or 0)
        except Exception:
            continue
        if pc <= 0 or c <= 0 or v <= 0 or c < 1:
            continue
        chg = (c - pc) / pc * 100
        band = 5 if abs(chg) < 7.5 else 10 if abs(chg) < 15 else 20
        item = {"s": row["TckrSymb"], "c": round(c, 2), "p": round(chg, 2), "b": band, "v": round(v / 1e5, 2)}
        if abs(c - h) < 0.005 and chg > 0.5:
            up.append(item)
        elif abs(c - l) < 0.005 and chg < -0.5:
            dn.append(item)
    up.sort(key=lambda x: -x["p"]); dn.sort(key=lambda x: x["p"])
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "date": f"{day[6:8]}-{day[4:6]}-{day[0:4]}",
           "n_uc": len(up), "n_lc": len(dn),
           "uc": up[:60], "lc": dn[:60],
           "note": "Upper circuit = close locked at the day's high (buyers stuck, no sellers). Lower = locked at the low. Band = implied from the day's move (5/10/20%). Source: NSE bhavcopy. A hit means the stock could not move further that day - a crowding signal, not advice."}
    json.dump(out, open("docs/circuits.json", "w"), separators=(",", ":"))
    print("date", out["date"], "| upper", len(up), "| lower", len(dn))

if __name__ == "__main__":
    main()
