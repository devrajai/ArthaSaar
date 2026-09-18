#!/usr/bin/env python3
"""
MARKET BRAIN — daily data collector for Nifty 500 universe.

What it does (self-healing, idempotent — safe to run every day):
  1. Fetches the Nifty 500 constituent list (symbol + company + industry) from
     NSE archives CSV. -> data/universe.json
  2. For every symbol, maintains a local price history (data/history/SYMBOL.json):
     - missing/stale -> fetch 1 year daily candles from Yahoo (fallback: Stooq)
     - exists -> append only the missing recent days
  3. Computes screener metrics per symbol:
     price, 1d change%, 52w high/low, 200d high/low, % from 52w high,
     EMA20, EMA200, price vs EMA200, RSI14, MACD line/signal/hist,
     volume vs 20d average, consecutive up/down days.
     -> data/brain-screener.json + data/brain-screener.csv
  4. Computes market breadth summary -> data/breadth.json

Rate-limit friendly: 0.4s between Yahoo calls, exponential backoff on 429,
stops a source after repeated failures and retries next run (self-healing).
No API keys. No paid services.
"""
import csv
import io
import json
import math
import time
import datetime as dt
import sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HIST = DATA / "history"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

HIST_KEEP_DAYS = 400          # ~1.5 years rolling window
MAX_YAHOO_FAILURES = 60       # stop hammering after this many consecutive failures


# ---------------------------------------------------------------- utilities
def get(url, timeout=25):
    req = Request(url, headers={"User-Agent": UA,
                                "Accept": "application/json,text/csv,*/*"})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def try_get(url, retries=2, sleep=3):
    for i in range(retries + 1):
        try:
            return get(url)
        except HTTPError as e:
            if e.code == 429 and i < retries:
                time.sleep(sleep * (i + 1))
                continue
            return None
        except (URLError, TimeoutError, OSError):
            if i == retries:
                return None
            time.sleep(sleep)
    return None


# ---------------------------------------------------------------- universe
def fetch_universe():
    """Nifty 500 list from NSE archives (free, no key)."""
    txt = try_get("https://nsearchives.nseindia.com/content/indices/"
                  "ind_nifty500list.csv")
    if not txt:
        return None
    rows = list(csv.DictReader(io.StringIO(txt)))
    uni = []
    for r in rows:
        sym = (r.get("Symbol") or "").strip()
        if not sym:
            continue
        uni.append({
            "symbol": sym,
            "company": (r.get("Company Name") or "").strip(),
            "industry": (r.get("Industry") or "").strip(),
        })
    return uni or None


# ---------------------------------------------------------------- history
def yahoo_daily(symbol, days=400):
    """Daily candles from Yahoo chart API -> list of {date, close, volume}."""
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           f"{quote(symbol)}.NS?range=1y&interval=1d")
    txt = try_get(url)
    if not txt:
        return None
    try:
        res = json.loads(txt)["chart"]["result"][0]
        ts = res.get("timestamp") or []
        q = res["indicators"]["quote"][0]
        out = []
        for i, t in enumerate(ts):
            c = q["close"][i]
            if c is None:
                continue
            d = dt.datetime.fromtimestamp(t, dt.timezone.utc).strftime("%Y-%m-%d")
            out.append({"date": d, "close": round(c, 2),
                        "volume": q["volume"][i] or 0})
        return out or None
    except Exception:  # noqa: BLE001
        return None


def stooq_daily(symbol):
    """Fallback history from Stooq CSV."""
    txt = try_get(f"https://stooq.com/q/d/l/?s={symbol.lower()}&i=d")
    if not txt or not txt.lower().startswith("date"):
        return None
    out = []
    try:
        for r in csv.DictReader(io.StringIO(txt)):
            c = r.get("Close")
            if not c:
                continue
            y, m, dd = r["Date"].split("-")
            out.append({"date": f"{y}-{m}-{dd}", "close": float(c),
                        "volume": int(r.get("Volume") or 0)})
    except Exception:  # noqa: BLE001
        return None
    return out[-HIST_KEEP_DAYS:] if out else None


def load_hist(symbol):
    p = HIST / f"{symbol}.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return None
    return None


def save_hist(symbol, rows):
    HIST.mkdir(parents=True, exist_ok=True)
    rows = rows[-HIST_KEEP_DAYS:]
    (HIST / f"{symbol}.json").write_text(
        json.dumps(rows), encoding="utf-8")


def merge_hist(old, new):
    by_date = {r["date"]: r for r in (old or [])}
    for r in new or []:
        by_date[r["date"]] = r
    return sorted(by_date.values(), key=lambda x: x["date"])


# ---------------------------------------------------------------- indicators
def ema(values, period):
    if not values:
        return None
    k = 2 / (period + 1)
    e = values[0]
    for v in values[1:]:
        e = v * k + e * (1 - k)
    return e


def rsi(closes, period=14):
    if len(closes) < period + 1:
        return None
    gains, losses = [], []
    for i in range(1, len(closes)):
        ch = closes[i] - closes[i - 1]
        gains.append(max(ch, 0))
        losses.append(max(-ch, 0))
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        ag = (ag * (period - 1) + gains[i]) / period
        al = (al * (period - 1) + losses[i]) / period
    if al == 0:
        return 100.0
    rs = ag / al
    return round(100 - 100 / (1 + rs), 2)


def macd(closes):
    if len(closes) < 35:
        return None
    k12, k26 = 2 / 13, 2 / 27
    e12 = e26 = closes[0]
    line = []
    for v in closes[1:]:
        e12 = v * k12 + e12 * (1 - k12)
        e26 = v * k26 + e26 * (1 - k26)
        line.append(e12 - e26)
    k9 = 2 / 10
    sig = line[0]
    for v in line[1:]:
        sig = v * k9 + sig * (1 - k9)
    return round(line[-1], 3), round(sig, 3), round(line[-1] - sig, 3)


def consecutive_days(closes):
    """+N = N straight up days, -N = N straight down days."""
    n = 0
    for i in range(len(closes) - 1, 0, -1):
        if closes[i] > closes[i - 1]:
            if n < 0:
                break
            n += 1
        elif closes[i] < closes[i - 1]:
            if n > 0:
                break
            n -= 1
        else:
            break
    return n


def analyse(symbol, meta, rows):
    closes = [r["close"] for r in rows]
    vols = [r["volume"] for r in rows]
    if len(closes) < 30:
        return None
    price = closes[-1]
    prev = closes[-2]
    w52 = closes[-252:] if len(closes) >= 252 else closes
    d200 = closes[-200:] if len(closes) >= 200 else closes
    e20 = ema(closes[-60:], 20)
    e200 = ema(closes, 200)
    m = macd(closes)
    v20 = sum(vols[-20:]) / max(len(vols[-20:]), 1)
    return {
        "symbol": symbol,
        "company": meta.get("company", ""),
        "industry": meta.get("industry", ""),
        "price": price,
        "change_pct": round((price - prev) / prev * 100, 2),
        "high_52w": max(w52),
        "low_52w": min(w52),
        "high_200d": max(d200),
        "low_200d": min(d200),
        "from_52w_high_pct": round((price / max(w52) - 1) * 100, 2),
        "ema20": round(e20, 2) if e20 else None,
        "ema200": round(e200, 2) if e200 else None,
        "above_ema200": bool(e200 and price > e200),
        "rsi14": rsi(closes),
        "macd": m[0] if m else None,
        "macd_signal": m[1] if m else None,
        "macd_hist": m[2] if m else None,
        "vol_vs_avg20": round(vols[-1] / v20, 2) if v20 else None,
        "consec_days": consecutive_days(closes),
        "history_days": len(closes),
    }


# ---------------------------------------------------------------- main
def main():
    DATA.mkdir(exist_ok=True)
    uni = fetch_universe()
    if uni:
        (DATA / "universe.json").write_text(json.dumps(uni, ensure_ascii=False))
        print(f"universe: {len(uni)} symbols")
    else:
        if (DATA / "universe.json").exists():
            uni = json.loads((DATA / "universe.json").read_text())
            print(f"universe: stale OK ({len(uni)} symbols)")
        else:
            print("FATAL: no universe available")
            sys.exit(1)

    yf_fails = 0
    results = []
    for i, m in enumerate(uni):
        sym = m["symbol"]
        rows = load_hist(sym)
        today = dt.date.today().strftime("%Y-%m-%d")
        needs = rows is None or (rows and rows[-1]["date"] < today)
        if needs and yf_fails < MAX_YAHOO_FAILURES:
            fresh = yahoo_daily(sym)
            if fresh is None:
                fresh = stooq_daily(sym)
            if fresh is None:
                yf_fails += 1
                time.sleep(0.4)
            else:
                rows = merge_hist(rows, fresh)
                save_hist(sym, rows)
                yf_fails = 0
            time.sleep(0.4)
        if rows:
            a = analyse(sym, m, rows)
            if a:
                results.append(a)
        if i % 50 == 0:
            print(f"...{i}/{len(uni)} symbols processed")

    results.sort(key=lambda x: x["change_pct"], reverse=True)
    (DATA / "brain-screener.json").write_text(
        json.dumps({"updated": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "count": len(results), "stocks": results},
                   ensure_ascii=False, indent=1))

    # CSV mirror (easy for sheets / future site)
    if results:
        cols = list(results[0].keys())
        with open(DATA / "brain-screener.csv", "w", newline="",
                  encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols)
            w.writeheader()
            w.writerows(results)

    # market breadth
    n = len(results)
    breadth = {
        "updated": dt.datetime.now(dt.timezone.utc).isoformat(),
        "stocks": n,
        "above_ema200_pct": round(100 * sum(r["above_ema200"] for r in results
                                             if r["above_ema200"] is not None) / n, 1) if n else 0,
        "rsi_above_60": sum(1 for r in results if (r["rsi14"] or 0) > 60),
        "rsi_below_40": sum(1 for r in results if (r["rsi14"] or 100) < 40),
        "near_52w_high": sum(1 for r in results if (r["from_52w_high_pct"] or -99) > -5),
        "volume_spike_2x": sum(1 for r in results if (r["vol_vs_avg20"] or 0) >= 2),
        "up_3plus_days": sum(1 for r in results if (r["consec_days"] or 0) >= 3),
        "down_3plus_days": sum(1 for r in results if (r["consec_days"] or 0) <= -3),
    }
    (DATA / "breadth.json").write_text(json.dumps(breadth, indent=1))
    print(f"screener: {n} stocks | breadth: {breadth['above_ema200_pct']}% above EMA200")


if __name__ == "__main__":
    main()
