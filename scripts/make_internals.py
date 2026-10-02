#!/usr/bin/env python3
"""
ARTHASAAR - Market Internals collector.
daily-*.json chunks (5y EOD per symbol) se compute karta hai:
  - Advance/Decline line (cumulative)
  - TRIN (Arms Index)
  - McClellan Oscillator (EMA19 - EMA39 of net advances)
  - New 52w Highs / Lows count
  - Zweig Breadth Thrust (10d EMA of adv ratio, 40% -> 61.5%)
Output: data/internals.json (last ~260 trading days) - CDN pe serve hota hai.
Runs on GitHub Actions (daily) or locally. Zero paid APIs.
"""
import json
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DAYS = 260          # output history length
TRADING_YEAR = 252  # 52w window


def ema(vals, n):
    k = 2.0 / (n + 1)
    out = []
    e = None
    for v in vals:
        e = v if e is None else (v * k + e * (1 - k))
        out.append(e)
    return out


def main():
    t0 = time.time()
    chunks = sorted(DATA.glob("daily-*.json"))
    if not chunks:
        raise SystemExit("no daily-*.json chunks found")

    dates = None
    rows = []  # (sym, tmap, c, h, v)
    for cf in chunks:
        d = json.loads(cf.read_text(encoding="utf-8"))
        for s, e in d.get("syms", {}).items():
            t = e.get("t", [])
            if len(t) < 60:
                continue
            if dates is None or len(t) > len(dates):
                dates = list(t)
            rows.append((s, {ts: i for i, ts in enumerate(t)}, e.get("c", []), e.get("h", []), e.get("v", [])))

    if not dates or not rows:
        raise SystemExit("no data")

    n_cal = len(dates)
    print(f"symbols: {len(rows)}  calendar bars: {n_cal}  (loaded {time.time()-t0:.1f}s)")

    start = max(0, n_cal - DAYS - 40)
    out_dates, adv, dec, upv, dnv, nh, nl = [], [], [], [], [], [], []

    for di in range(start, n_cal):
        ts = dates[di]
        a = dcn = uv = dv = h52 = l52 = 0
        for sym, tmap, c, h, v in rows:
            i = tmap.get(ts)
            if i is None or i < 1:
                continue
            pc = c[i - 1]
            if pc:
                ch = c[i] - pc
                if ch > 0:
                    a += 1; uv += (v[i] or 0)
                elif ch < 0:
                    dcn += 1; dv += (v[i] or 0)
            lo = max(0, i - TRADING_YEAR + 1)
            hi_win = h[lo:i + 1]
            c_win = c[lo:i + 1]
            if hi_win and h[i] is not None and h[i] >= max(hi_win):
                h52 += 1
            if c_win and c[i] is not None and c[i] <= min(c_win):
                l52 += 1
        out_dates.append(datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d"))
        adv.append(a); dec.append(dcn); upv.append(uv); dnv.append(dv)
        nh.append(h52); nl.append(l52)
        if (di - start) % 60 == 0:
            print(f"  day {di-start}/{n_cal-start}  {out_dates[-1]}  adv {a} dec {dcn}  ({time.time()-t0:.0f}s)")

    out_dates = out_dates[-DAYS:]
    adv = adv[-DAYS:]; dec = dec[-DAYS:]
    upv = upv[-DAYS:]; dnv = dnv[-DAYS:]
    nh = nh[-DAYS:]; nl = nl[-DAYS:]

    net = [adv[i] - dec[i] for i in range(len(adv))]
    ad, run = [], 0
    for v in net:
        run += v
        ad.append(run)
    trin = []
    for i in range(len(adv)):
        ar = (adv[i] / dec[i]) if dec[i] else 2.0
        vr = (upv[i] / dnv[i]) if dnv[i] else 2.0
        trin.append(round(min(ar / vr, 4.0), 3) if vr else 2.0)
    e19 = ema(net, 19); e39 = ema(net, 39)
    mcos = [round(e19[i] - e39[i], 1) for i in range(len(net))]
    ratio = [(adv[i] / (adv[i] + dec[i])) if (adv[i] + dec[i]) else 0.5 for i in range(len(adv))]
    r10 = ema(ratio, 10)
    thrust_last = None
    for i in range(1, len(r10)):
        if r10[i - 1] < 0.615 <= r10[i] and r10[i - 1] >= 0.40:
            thrust_last = i
    thrust_recent = bool(thrust_last is not None and (len(r10) - 1 - thrust_last) <= 30)

    out = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "ArthaSaar daily EOD chunks (~2200 NSE symbols)",
        "days": len(out_dates),
        "dates": out_dates,
        "adv": adv, "dec": dec, "ad": ad, "trin": trin,
        "mcos": mcos, "nh": nh, "nl": nl,
        "thrust10": [round(x, 4) for x in r10],
        "last": {
            "adv": adv[-1] if adv else 0, "dec": dec[-1] if dec else 0,
            "ad": ad[-1] if ad else 0, "trin": trin[-1] if trin else None,
            "mcos": mcos[-1] if mcos else None,
            "nh": nh[-1] if nh else 0, "nl": nl[-1] if nl else 0,
            "thrust_recent": thrust_recent,
        },
    }
    (DATA / "internals.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"internals.json written: {len(out_dates)} days, last: {out['last']}")


if __name__ == "__main__":
    main()
