#!/usr/bin/env python3
"""What the put-call ratio has actually preceded - measured, not asserted.

THE FOLKLORE, AND WHY IT NEEDS CHECKING
Every options trader is told the put-call ratio is contrarian: a very HIGH ratio means
everyone is bearish, so the market is near a bottom and due to bounce; a very LOW ratio means
everyone is bullish, so it is near a top. It is repeated everywhere and rarely tested.

This tests it on our own 1,930 sessions of Nifty open interest and Nifty closes. For each PCR
band it reports what the Nifty actually did over the next 5 and 21 sessions, with the sample
size and the unconditional baseline beside it. If the folklore holds, the high-PCR band should
show better forward returns than the baseline. If it does not, this says so.

WHAT IS PUBLISHED
  trend          PCR now, and its change over 5 and 20 sessions - the direction, which a
                 single number cannot show
  bands          forward Nifty returns by PCR band, against the baseline
  current        which band today sits in, and what that band has historically preceded

WHAT IS NOT PUBLISHED
A direction call. Even a band that beats the baseline does so by a few percentage points of
average return with a wide spread - it is a tilt in the odds, not a prediction. The sample
size and the baseline are shown so the reader can judge it rather than take it.
"""
import json, os, sys
from datetime import datetime, timezone

OUT = "docs/pcr_signal.json"
NIFTY_URL = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?interval=1d&range=10y"
BANDS = [(0.0, 0.8, "very low (<0.80)"), (0.8, 1.0, "low (0.80-1.00)"),
         (1.0, 1.2, "high (1.00-1.20)"), (1.2, 9.9, "very high (>1.20)")]
HORIZONS = (5, 21)
MIN_CASES = 20


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def nifty_closes():
    import datetime as dt
    import urllib.request
    try:
        j = json.loads(urllib.request.urlopen(
            urllib.request.Request(NIFTY_URL, headers={"User-Agent": "Mozilla/5.0"}),
            timeout=60).read())
        r = j["chart"]["result"][0]
        q = r["indicators"]["quote"][0]
        rows = sorted([(dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d"), c)
                       for t, c in zip(r["timestamp"], q["close"]) if c is not None])
        return [d for d, _ in rows], [c for _, c in rows]
    except Exception as e:
        print("  nifty fetch failed: %s" % type(e).__name__)
        return [], []


def main():
    out = {"updated": now(), "current": None, "trend": None, "bands": [],
           "baseline": {}, "note": "", "cautions": {}}

    try:
        hist = json.load(open("docs/oi_history.json"))
    except Exception:
        out["note"] = "No oi_history.json; run the F&O collector first."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
        print("pcr: no OI history")
        return 0

    # Nifty PCR by date
    pcr = {}
    for r in (hist.get("series") or []):
        if r.get("i") == "N" and r.get("p") is not None:
            pcr[str(r.get("d"))[:10]] = float(r["p"])
    if not pcr:
        out["note"] = "oi_history.json has no Nifty PCR rows."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
        print("pcr: no Nifty rows")
        return 0

    dates, closes = nifty_closes()
    idx = {d: i for i, d in enumerate(dates)}

    # ---- trend: where is PCR now, and which way is it going ----------------------------
    pcr_dates = sorted(pcr)
    latest_d = pcr_dates[-1]
    latest = pcr[latest_d]
    def back(n):
        return pcr[pcr_dates[-1 - n]] if len(pcr_dates) > n else None
    p5, p20 = back(5), back(20)
    out["current"] = {"date": latest_d, "pcr": round(latest, 3)}
    out["trend"] = {
        "pcr": round(latest, 3),
        "chg_5": round(latest - p5, 3) if p5 is not None else None,
        "chg_20": round(latest - p20, 3) if p20 is not None else None,
        "direction_5": ("rising" if p5 is not None and latest > p5 + 0.02
                        else "falling" if p5 is not None and latest < p5 - 0.02 else "flat"),
        "direction_20": ("rising" if p20 is not None and latest > p20 + 0.02
                         else "falling" if p20 is not None and latest < p20 - 0.02 else "flat"),
    }

    # ---- forward returns by band -------------------------------------------------------
    def forward(d, h):
        i = idx.get(d)
        if i is None or i + h >= len(closes):
            return None
        return (closes[i + h] / closes[i] - 1) * 100

    base = {}
    for h in HORIZONS:
        vals = [forward(d, h) for d in pcr_dates if forward(d, h) is not None]
        base[h] = {"n": len(vals),
                   "mean": round(sum(vals) / len(vals), 2) if vals else None,
                   "up_pct": round(sum(1 for v in vals if v > 0) / len(vals) * 100, 1) if vals else None}
    out["baseline"] = base

    for lo, hi, label in BANDS:
        row = {"band": label, "n": 0, "horizons": []}
        sel = [d for d in pcr_dates if lo <= pcr[d] < hi]
        row["n"] = len(sel)
        for h in HORIZONS:
            vals = [forward(d, h) for d in sel if forward(d, h) is not None]
            if len(vals) < MIN_CASES:
                row["horizons"].append({"h": h, "n": len(vals), "insufficient": True})
                continue
            mean = sum(vals) / len(vals)
            up = sum(1 for v in vals if v > 0) / len(vals) * 100
            b = base[h]
            row["horizons"].append({
                "h": h, "n": len(vals), "mean_pct": round(mean, 2),
                "up_pct": round(up, 1),
                "vs_baseline_pp": (round(mean - b["mean"], 2)
                                   if b["mean"] is not None else None),
                "edge": ("better than baseline" if b["mean"] is not None and mean > b["mean"] + 0.1
                         else "worse than baseline" if b["mean"] is not None and mean < b["mean"] - 0.1
                         else "no different from baseline"),
            })
        out["bands"].append(row)

    cur_band = next((b for b in out["bands"]
                     if b["band"].split()[0] in ("very",) and
                     ((b["band"].find("<0.80") > 0 and latest < 0.8) or
                      (b["band"].find(">1.20") > 0 and latest > 1.2))), None)
    if cur_band is None:
        for b in out["bands"]:
            if b["band"].startswith("low") and 0.8 <= latest < 1.0:
                cur_band = b
            elif b["band"].startswith("high") and 1.0 <= latest < 1.2:
                cur_band = b
    out["current"]["band"] = cur_band["band"] if cur_band else None

    out["note"] = ("Nifty PCR and its trend, with what each PCR band has actually preceded over "
                   "%d sessions. The baseline beside every band is what a random session did, "
                   "so a band that matches the baseline has no edge." % len(pcr_dates))
    out["cautions"] = {
        "tilt_not_call": ("A band that beats the baseline beats it by a small average margin "
                          "with a wide spread. That is a tilt in the odds, not a direction call."),
        "contrarian_folklore": ("The usual reading is contrarian - high PCR means too many puts "
                                "and a likely bounce, low PCR the opposite. The bands below are "
                                "the test of that, not a restatement of it."),
        "one_number": ("PCR is one input. It says nothing about news, results, policy or a "
                       "global risk-off move."),
        "summed_expiries": ("The ratio is built from open interest summed across expiries, "
                            "which is the standard NSE presentation."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    t = out["trend"]
    print("   PCR %.3f on %s | 5d %s (%s) | 20d %s (%s)"
          % (latest, latest_d, t["chg_5"], t["direction_5"], t["chg_20"], t["direction_20"]))
    for h in HORIZONS:
        b = base[h]
        print("   baseline %dd: n=%d mean %.2f%% up %.1f%%" % (h, b["n"], b["mean"], b["up_pct"]))
    for b in out["bands"]:
        for hh in b["horizons"]:
            if hh.get("insufficient"):
                print("   %-18s %2dd  n=%d (too few)" % (b["band"], hh["h"], hh["n"]))
            else:
                print("   %-18s %2dd  n=%-4d mean %+6.2f%%  up %5.1f%%  vs base %+.2fpp  %s"
                      % (b["band"], hh["h"], hh["n"], hh["mean_pct"], hh["up_pct"],
                         hh["vs_baseline_pp"], hh["edge"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
