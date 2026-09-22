#!/usr/bin/env python3
"""macro.py - Macro Pulse: oil/DXY/10Y/rupee/gold + FII streak -> data/macro.json
Free sources only (yfinance + repo fii-dii.json). Never fails hard."""
import json, math, os, datetime

OUT = "data/macro.json"
MAXH = 90  # days of history kept

def load_hist():
    try:
        with open(OUT) as f:
            h = json.load(f).get("history", [])
        if isinstance(h, list):
            return h
    except Exception:
        pass
    return []

def yf_series(sym, days=40):
    import yfinance as yf
    df = yf.Ticker(sym).history(period="6mo")
    closes = df["Close"].dropna()
    return closes

def pct(a, b):
    try:
        return round((a - b) / b * 100.0, 2)
    except Exception:
        return None

def main():
    today = datetime.date.today().isoformat()
    hist = {h["date"]: h for h in load_hist()}

    out = {"updated": datetime.datetime.now().isoformat(), "today": {}, "history": []}

    # --- fetch macro assets ---
    assets = {
        "crude": "CL=F", "dxy": "DX-Y.NYB", "gold": "GC=F",
        "us10y": "^TNX", "usdinr": "USDINR=X", "spx": "^GSPC",
    }
    px = {}
    chg5 = {}
    for k, sym in assets.items():
        try:
            c = yf_series(sym)
            px[k] = round(float(c.iloc[-1]), 2)
            if len(c) >= 6:
                chg5[k] = pct(float(c.iloc[-1]), float(c.iloc[-6]))
        except Exception:
            pass
    out["today"] = {"date": today, **px}

    # --- FII net today from repo data ---
    fii_net = None
    try:
        with open("data/fii-dii.json") as f:
            fd = json.load(f)
        fii_net = round(float(fd["categories"]["FII/FPI"]["net_cr"]), 1)
        out["today"]["fii_net_cr"] = fii_net
    except Exception:
        pass

    # --- history row for today ---
    row = {"date": today}
    for k in px:
        row[k] = px[k]
    if fii_net is not None:
        row["fii_net_cr"] = fii_net
    hist[today] = row
    ordered = [hist[d] for d in sorted(hist)][-MAXH:]

    # --- FII selling streak ---
    streak = 0
    for r in reversed(ordered):
        v = r.get("fii_net_cr")
        if v is None:
            continue
        if v < 0:
            streak += 1
        else:
            break
    out["streak_fii_sell_days"] = streak

    # --- macro score (-10..+10, negative = risk OFF) ---
    score = 0
    signals = []
    c5 = chg5.get("crude")
    if c5 is not None and c5 > 3: score -= 2; signals.append("crude 5d +" + str(c5) + "% (oil shock)")
    elif c5 is not None and c5 > 1: score -= 1; signals.append("crude 5d +" + str(c5) + "%")
    d5 = chg5.get("dxy")
    if d5 is not None and d5 > 0.5: score -= 1; signals.append("dollar index strong +" + str(d5) + "%")
    t5 = chg5.get("us10y")
    if t5 is not None and t5 > 3: score -= 1; signals.append("US 10Y yields up (Fed hawkish)")
    r5 = chg5.get("usdinr")
    if r5 is not None and r5 > 0.5: score -= 1; signals.append("rupee weak " + str(r5) + "%")
    if streak >= 5: score -= 2; signals.append("FII bech rahe " + str(streak) + " din se")
    elif streak >= 3: score -= 1; signals.append("FII streak " + str(streak) + " din")
    g5 = chg5.get("gold")
    if g5 is not None and g5 > 2: score -= 1; signals.append("gold bhaag raha (safe-haven)")
    s5 = chg5.get("spx")
    if s5 is not None and s5 > 2: score += 1; signals.append("S&P strong +" + str(s5) + "%")

    if score <= -4:
        verdict = "RISK OFF - oil/dollar/FII sab against. Bade position avoid, cash rakho."
    elif score <= -2:
        verdict = "CAUTION - macro headwind hai. Positions chhote, stop-loss pakka."
    elif score <= 0:
        verdict = "NEUTRAL - mixed signals. Normal, par alert raho."
    else:
        verdict = "RISK ON - global support hai. Trend follow karo."
    out["score"] = score
    out["verdict"] = verdict
    out["signals"] = signals
    out["history"] = ordered

    os.makedirs("data", exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1)
    print("macro.json written | score", score, "| streak", streak)
    print("verdict:", verdict)

if __name__ == "__main__":
    main()
