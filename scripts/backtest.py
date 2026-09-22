#!/usr/bin/env python3
"""backtest.py - strategy vs buy-hold on Nifty 1y daily closes. Writes data/backtest.json (no message)."""
import sys, json, urllib.request

def closes():
    u = "https://query1.finance.yahoo.com/v8/finance/chart/%5ENSEI?range=1y&interval=1d"
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
    d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode())
    r = d["chart"]["result"][0]
    return [(r["timestamp"][i], c) for i, c in enumerate(r["indicators"]["quote"][0]["close"]) if c]

def ema(vals, n):
    k = 2.0 / (n + 1); e = [vals[0]]
    for v in vals[1:]:
        e.append(v * k + e[-1] * (1 - k))
    return e

def rsi(vals, n=14):
    out = [None] * len(vals)
    for i in range(n, len(vals)):
        g = l = 0.0
        for j in range(i - n + 1, i + 1):
            ch = vals[j] - vals[j - 1]
            g += max(ch, 0); l += max(-ch, 0)
        out[i] = 100.0 if l == 0 else 100 - 100 / (1 + (g / n) / (l / n))
    return out

def run():
    px = closes()
    if len(px) < 60:
        print("not enough data"); return
    vals = [p[1] for p in px]
    bh = (vals[-1] / vals[0] - 1) * 100
    e20, e50 = ema(vals, 20), ema(vals, 50)
    eq = 1.0; trades = 0; prev_in = False
    for i in range(1, len(vals)):
        inn = e20[i] > e50[i]
        if inn != prev_in: trades += 1
        if inn: eq *= vals[i] / vals[i - 1]
        prev_in = inn
    ema_r = (eq - 1) * 100
    r = rsi(vals)
    eq = 1.0; hold = False; rtrades = 0
    for i in range(1, len(vals)):
        if r[i] is not None:
            if not hold and r[i] < 30: hold = True; rtrades += 1
            elif hold and r[i] > 70: hold = False
        if hold: eq *= vals[i] / vals[i - 1]
    rsi_r = (eq - 1) * 100
    out = {"days": len(vals), "buy_hold_pct": round(bh, 1), "ema_pct": round(ema_r, 1),
           "rsi_pct": round(rsi_r, 1), "ema_trades": trades, "rsi_trades": rtrades,
           "note": "Nifty 1y daily. EMA: 20>50 mein invested. RSI: <30 buy, >70 sell. Simple test hai, perfect nahi."}
    json.dump(out, open("data/backtest.json", "w"), indent=1)
    print("backtest:", out)

run()
