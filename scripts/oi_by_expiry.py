#!/usr/bin/env python3
"""
ARTHASAAR - option walls PER EXPIRY, straight from NSE's F&O bhavcopy.

WHY THIS EXISTS
docs/oi_strikes.json and oi_walls.json currently publish expiry "—" and spot null,
and they sum open interest across every expiry. That makes "call wall 25,000"
meaningless: it is a weekly and a monthly wall added together, with no spot to
measure distance from. This builds the same thing correctly - per expiry, with
spot - from the one free source that actually carries XpryDt and UndrlygPric.

Output: docs/oi_by_expiry.json
  { updated, date, indices: { NIFTY: { spot, expiries: [ {expiry, days_out, dte_label,
      pcr, max_pain, call_wall, put_wall, total_ce_oi, total_pe_oi, strikes:[...] } ] } } }

Only the two nearest expiries are kept (the ones people actually trade).
"""
import csv, io, json, sys, urllib.request, zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

DOCS = Path("docs")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
INDICES = ("NIFTY", "BANKNIFTY")
NEAR = 14          # strikes either side of spot
KEEP_EXPIRIES = 2  # nearest two


def grab_bhavcopy():
    now = datetime.now(timezone.utc)
    for back in range(0, 6):
        d = (now - timedelta(days=back)).strftime("%Y%m%d")
        url = f"https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_{d}_F_0000.csv.zip"
        try:
            r = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            raw = urllib.request.urlopen(r, timeout=60).read()
            z = zipfile.ZipFile(io.BytesIO(raw))
            name = [n for n in z.namelist() if n.endswith(".csv")][0]
            return z.read(name).decode("utf-8", "replace"), d
        except Exception as e:  # noqa: BLE001
            print("  skip", d, type(e).__name__)
    return None, None


def fnum(x):
    try:
        v = float(x)
        return v if v == v else 0.0
    except Exception:  # noqa: BLE001
        return 0.0


def max_pain(strikes):
    """Strike where total payout to option holders is smallest (writers' pain minimum)."""
    if not strikes:
        return None
    best, best_val = None, None
    for k in strikes:
        s = k["strike"]
        pain = 0.0
        for o in strikes:
            pain += max(0.0, s - o["strike"]) * o["pe_oi"]
            pain += max(0.0, o["strike"] - s) * o["ce_oi"]
        if best_val is None or pain < best_val:
            best, best_val = s, pain
    return best


def main():
    text, day = grab_bhavcopy()
    if not text:
        print("no bhavcopy available")
        return 1

    rows = list(csv.DictReader(io.StringIO(text)))
    print(f"  {len(rows)} rows from {day}")

    # index options only
    opt = []
    for r in rows:
        if (r.get("FinInstrmTp") or "") != "IDO":
            continue
        sym = (r.get("TckrSymb") or "").strip().upper()
        if sym not in INDICES:
            continue
        ot = (r.get("OptnTp") or "").strip().upper()
        if ot not in ("CE", "PE"):
            continue
        opt.append({
            "sym": sym, "exp": (r.get("XpryDt") or "")[:10], "ot": ot,
            "k": fnum(r.get("StrkPric")), "oi": fnum(r.get("OpnIntrst")),
            "chg": fnum(r.get("ChngInOpnIntrst")), "vol": fnum(r.get("TtlTradgVol")),
            "spot": fnum(r.get("UndrlygPric")),
        })
    if not opt:
        print("no index option rows")
        return 1

    today = datetime.strptime(day, "%Y%m%d").date()
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "date": today.isoformat(), "source": "NSE F&O bhavcopy (UDiFF)",
           "indices": {}}

    for sym in INDICES:
        sub = [r for r in opt if r["sym"] == sym]
        if not sub:
            continue
        exps = sorted({r["exp"] for r in sub if r["exp"]})[:KEEP_EXPIRIES]
        spot = next((r["spot"] for r in sub if r["spot"]), None)
        blocks = []
        for exp in exps:
            e = [r for r in sub if r["exp"] == exp]
            by = {}
            for r in e:
                b = by.setdefault(r["k"], {"strike": r["k"], "ce_oi": 0.0, "pe_oi": 0.0,
                                           "ce_chg": 0.0, "pe_chg": 0.0})
                if r["ot"] == "CE":
                    b["ce_oi"] += r["oi"]; b["ce_chg"] += r["chg"]
                else:
                    b["pe_oi"] += r["oi"]; b["pe_chg"] += r["chg"]
            allk = sorted(by.values(), key=lambda x: x["strike"])
            if spot:
                near = sorted(allk, key=lambda x: abs(x["strike"] - spot))[: NEAR * 2]
                near = sorted(near, key=lambda x: x["strike"])
            else:
                near = sorted(allk, key=lambda x: -(x["ce_oi"] + x["pe_oi"]))[: NEAR * 2]
                near = sorted(near, key=lambda x: x["strike"])
            tce = sum(x["ce_oi"] for x in allk)
            tpe = sum(x["pe_oi"] for x in allk)
            cw = max(allk, key=lambda x: x["ce_oi"]) if allk else None
            pw = max(allk, key=lambda x: x["pe_oi"]) if allk else None
            try:
                dte = (datetime.strptime(exp, "%Y-%m-%d").date() - today).days
            except Exception:  # noqa: BLE001
                dte = None
            blocks.append({
                "expiry": exp,
                "days_out": dte,
                "label": ("weekly" if dte is not None and dte <= 7 else "monthly"),
                "spot": round(spot, 2) if spot else None,
                "pcr": round(tpe / tce, 2) if tce else None,
                "max_pain": max_pain(allk),
                "call_wall": cw["strike"] if cw else None,
                "put_wall": pw["strike"] if pw else None,
                "total_ce_oi": int(tce),
                "total_pe_oi": int(tpe),
                "strikes": [{"strike": x["strike"], "ce_oi": int(x["ce_oi"]),
                             "pe_oi": int(x["pe_oi"]), "ce_chg": int(x["ce_chg"]),
                             "pe_chg": int(x["pe_chg"])} for x in near],
            })
        out["indices"][sym] = {"spot": round(spot, 2) if spot else None, "expiries": blocks}
        print(f"  {sym}: spot {out['indices'][sym]['spot']} | " +
              " | ".join(f"{b['expiry']} ({b['label']}) PCR {b['pcr']} wall {b['call_wall']}/{b['put_wall']}"
                         for b in blocks))

    out["note"] = ("Call and put open interest at each strike, per expiry, with the spot the "
                   "chain was quoted against. Only the two nearest expiries are kept. A big "
                   "call wall above spot is where sellers expect resistance; a big put wall "
                   "below is where they expect support. This is positioning, not a forecast, "
                   "and not a recommendation.")
    DOCS.mkdir(exist_ok=True)
    (DOCS / "oi_by_expiry.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print("wrote docs/oi_by_expiry.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
