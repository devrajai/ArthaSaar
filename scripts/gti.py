#!/usr/bin/env python3
"""gti.py - GTI (Ghost Trade Indicator) zones: demand/supply + POC
for NIFTY/BANKNIFTY + top F&O stocks. Market Mindset math from the
original Pine script, ported to Python. Output: data/gti.json"""
import json, math, os, datetime

OUT = "data/gti.json"

INDICES = {"NIFTY 50": "^NSEI", "BANKNIFTY": "^NSEBANK"}
STOCKS = ["RELIANCE", "HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "INFY",
          "TCS", "TECHM", "WIPRO", "LT", "ITC", "BHARTIARTL", "KOTAKBANK",
          "TATAMOTORS", "TATASTEEL", "ADANIENT", "ADANIPORTS", "ASIANPAINT",
          "BAJFINANCE", "BPCL", "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT",
          "GRASIM", "HINDALCO", "HINDUNILVR", "JSWSTEEL", "MARUTI", "NTPC",
          "ONGC", "POWERGRID", "SUNPHARMA", "TITAN", "ULTRACEMCO"]

PHI = 1.618034

def atr(hist, n=20):
    """ATR(n) over [high, low, close] lists (simple TR average)."""
    if len(hist) < n + 1:
        return None
    trs = []
    for i in range(1, len(hist)):
        h, l, pc = hist[i][1], hist[i][2], hist[i - 1][3]
        trs.append(max(h - l, abs(h - pc), abs(l - pc)))
    return sum(trs[-n:]) / n

def zones(P, sigma, ws_div=4.0, ww_div=None):
    """GTI zone math: strong/weak demand below open, weak/strong supply above."""
    if sigma is None or P is None or P <= 0:
        return None
    ws = round(sigma / ws_div)
    ww = round(sigma / (ww_div or (4.0 * PHI)))
    dist_s = sigma
    dist_w = sigma / (2.0 * math.sqrt(2.0))
    return {
        "SD": [round(P - dist_s - ws / 2), round(P - dist_s + ws / 2)],
        "WD": [round(P - dist_w - ww / 2), round(P - dist_w + ww / 2)],
        "WS": [round(P + dist_w - ww / 2), round(P + dist_w + ww / 2)],
        "SS": [round(P + dist_s - ws / 2), round(P + dist_s + ws / 2)],
    }

def compute(sym):
    import yfinance as yf
    df = yf.Ticker(sym).history(period="1y")
    if df is None or len(df) < 60:
        return None
    rows = [(str(i.date()), float(r.Open), float(r.High), float(r.Low), float(r.Close))
            for i, r in df.iterrows()]
    last = rows[-1]
    price = round(last[4], 2)

    # ---- daily zones ----
    P = round(last[1])  # today's open
    a = atr(rows[:-1], 20)  # ATR of completed days before today
    prev = rows[-2]
    if a is None or prev[3] <= 0:
        return None
    atr_ann = a / prev[3] * math.sqrt(252) * 100
    effvol = 0.69 * atr_ann
    sigma = P * effvol / (100.0 * math.sqrt(252))
    dz = zones(P, sigma)
    dpoc = round((prev[2] + prev[3] + prev[4]) / 3.0)

    # ---- weekly zones (current week open, weekly ATR of last week) ----
    weeks = {}
    for r in rows:
        weeks.setdefault(iso_week(r[0]), []).append(r)
    wkeys = sorted(weeks)
    wbars = []  # aggregate daily rows into weekly OHLC bars
    for k in wkeys:
        grp = weeks[k]
        wbars.append((str(k), grp[0][1], max(g[2] for g in grp),
                      min(g[3] for g in grp), grp[-1][4]))
    cur_open = weeks[wkeys[-1]][0][1]
    P_w = round(cur_open)
    a_w = atr(wbars[:-1], 20) if len(wbars) > 21 else None
    if a_w and len(wbars) >= 2:
        wprev_close = wbars[-2][4]
        w_atr_ann = a_w / wprev_close * math.sqrt(52) * 100
        effvol_w = 0.68 * w_atr_ann
        sigma_w = P_w * effvol_w / (100.0 * math.sqrt(252.0 / 5.0))
        wz = zones(P_w, sigma_w)
        wpoc = round((wbars[-2][2] + wbars[-2][3] + wbars[-2][4]) / 3.0)
    else:
        wz, wpoc = None, None

    # ---- nearest zone from price ----
    near = None
    if dz:
        for name, rng in dz.items():
            mid = (rng[0] + rng[1]) / 2
            d = pct(price, mid)
            if near is None or abs(d) < abs(near[1]):
                near = [name + " " + str(int(mid)), d]
    return {"price": price, "day_open": P, "day_poc": dpoc, "day_zones": dz,
            "week_open": P_w, "week_poc": wpoc, "week_zones": wz,
            "nearest": near}

def iso_week(dstr):
    return datetime.date.fromisoformat(dstr).isocalendar()[:2]

def pct(a, b):
    return round((a - b) / b * 100.0, 1)

def main():
    out = {"updated": datetime.datetime.now().isoformat(), "symbols": {}, "errors": []}
    for name, sym in list(INDICES.items()) + [(s, s + ".NS") for s in STOCKS]:
        try:
            r = compute(sym)
            if r:
                out["symbols"][name] = r
        except Exception as e:
            out["errors"].append(name + ": " + str(e)[:60])
    os.makedirs("data", exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print("gti.json written:", len(out["symbols"]), "symbols |", len(out["errors"]), "errors")

if __name__ == "__main__":
    main()
