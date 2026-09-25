#!/usr/bin/env python3
"""
ARTHASAAR — full-market price history + technicals.

Universe: 2,305 stocks (Nifty 500 tier 1 + NSE EQ-series others tier 2)
from nsearchives.nseindia.com CSVs (works from datacenter IPs).

History: BATCHED yfinance downloads (100 symbols per call, period=1y).
Plain urllib Yahoo calls get blocked from datacenter IPs — yfinance handles
the cookie/crumb dance (proven working for fundamentals on Actions runners).
FIX 19/09/26: every symbol needs its own .NS suffix (a bare string join
broke ~99% of tickers); rate-limit aware retry with backoff; 3s between
batches; zero-division guards in analyse().
Stooq CSV remains the per-symbol fallback. Local per-symbol history lives in
data/history/SYMBOL.json (merged, capped at ~400 rows).

Technicals per stock: price, change%, 52w high/low, 200d high/low, % from
52w high, EMA20, EMA200, above-EMA200 flag, RSI14, MACD (line/signal/hist),
volume vs 20d avg, consecutive up/down days.

Outputs: data/brain-screener.json (+ .csv mirror), data/breadth.json.
Self-healing: a failed batch just means those stocks keep yesterday's history.
"""
import csv
import datetime as dt
import io
import json
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
HIST = DATA / "history"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HIST_KEEP_DAYS = 400
BATCH = 100          # symbols per yfinance download call
NIFTY500_CSV = "https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv"
EQUITY_CSV = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"


def try_get(url, timeout=25):
    try:
        req = Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------- universe
def fetch_universe():
    uni = []
    seen = set()
    txt = try_get(NIFTY500_CSV)
    if txt:
        for r in csv.DictReader(io.StringIO(txt)):
            sym = (r.get("Symbol") or "").strip()
            if sym and sym not in seen:
                seen.add(sym)
                uni.append({"symbol": sym,
                            "company": (r.get("Company Name") or "").strip(),
                            "industry": (r.get("Industry") or "").strip(),
                            "tier": 1})
    n500 = len(uni)
    txt = try_get(EQUITY_CSV)
    if txt:
        for r in csv.DictReader(io.StringIO(txt)):
            sym, series = (r.get("SYMBOL") or "").strip(), (r.get(" SERIES") or r.get("SERIES") or "").strip()
            if sym and series == "EQ" and sym not in seen:
                seen.add(sym)
                uni.append({"symbol": sym,
                            "company": (r.get("NAME OF COMPANY") or "").strip(),
                            "industry": "",
                            "tier": 2})
    print(f"universe: {n500} nifty500 + {len(uni) - n500} others = {len(uni)}")
    return uni or None


# ---------------------------------------------------------------- history
def _ticker(sym):
    return sym if sym.endswith(".NS") else sym + ".NS"


def yahoo_batch(symbols, retries=3):
    """Batched daily candles via yfinance -> {symbol: [{date, close, volume}]}.
    Every NSE symbol needs its own .NS suffix (a bare join broke this
    before). Yahoo rate-limits datacenter IPs, so yfinance reports failed
    downloads instead of raising — detect and retry those with backoff."""
    out = {}
    todo = list(symbols)
    attempt = 0
    parts = []
    while todo and attempt <= retries:
        tickers = [_ticker(s) for s in todo]
        try:
            part = yf.download(tickers, period="1y", interval="1d",
                               group_by="ticker", threads=True, progress=False,
                               auto_adjust=True)
        except Exception as e:  # noqa: BLE001
            print(f"  batch failed: {e}")
            break
        if part is not None and not part.empty:
            parts.append(part)
        cols = set()
        for p in parts:
            if isinstance(p.columns, __import__("pandas").MultiIndex):
                cols |= {c for c in p.columns.get_level_values(0)}
            else:
                cols |= set(todo)
        still = [s for s in todo if _ticker(s) not in cols]
        got_now = len(todo) - len(still)
        if not still or attempt == retries:
            todo = still
            break
        # yfinance likely rate-limited the missing ones — back off, retry
        wait = 90 * (attempt + 1)
        print(f"  {len(still)} missing after attempt {attempt + 1} "
              f"(got {got_now}), sleeping {wait}s")
        time.sleep(wait)
        todo = still
        attempt += 1
    if not parts:
        return out
    pandas = __import__("pandas")
    df = parts[0] if len(parts) == 1 else pandas.concat(parts, axis=1)
    multi = isinstance(df.columns, pandas.MultiIndex)
    for s in symbols:
        try:
            sub = df[_ticker(s)] if multi else df
            sub = sub.dropna(subset=["Close"])
            rows = []
            for date, r in sub.iterrows():
                c = r["Close"]
                if c is None or c != c:
                    continue
                v = r.get("Volume", 0)
                rows.append({"date": date.strftime("%Y-%m-%d"),
                             "close": round(float(c), 2),
                             "volume": int(v or 0)})
            if rows:
                out[s] = rows
        except Exception:  # noqa: BLE001
            continue
    return out


def stooq_daily(symbol):
    """Fallback history from Stooq CSV (no .NS suffix)."""
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
    "+N = N straight up days, -N = N straight down days."
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
        "tier": meta.get("tier", 1),
        "price": price,
        "change_pct": round((price - prev) / prev * 100, 2) if prev else 0,
        "high_52w": max(w52),
        "low_52w": min(w52),
        "high_200d": max(d200),
        "low_200d": min(d200),
        "from_52w_high_pct": round((price / max(w52) - 1) * 100, 2) if max(w52) else 0,
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
    else:
        if (DATA / "universe.json").exists():
            uni = json.loads((DATA / "universe.json").read_text())
            print(f"universe: stale OK ({len(uni)} symbols)")
        else:
            print("FATAL: no universe available")
            sys.exit(1)

    # ---- batched history refresh (tier 1 first so the index is prioritised)
    syms = [m["symbol"] for m in uni]
    for start in range(0, len(syms), BATCH):
        chunk = syms[start:start + BATCH]
        fresh = yahoo_batch(chunk)
        got = len(fresh)
        missing = [s for s in chunk if s not in fresh]
        # merge + save
        for s, rows in fresh.items():
            old = load_hist(s)
            save_hist(s, merge_hist(old, rows))
        # stooq fallback for stragglers (max 10 per batch to stay fast)
        for s in missing[:10]:
            rows = stooq_daily(s)
            if rows:
                old = load_hist(s)
                save_hist(s, merge_hist(old, rows))
                got += 1
        print(f"history {start + len(chunk)}/{len(syms)} "
              f"(batch {got}/{len(chunk)} updated)")
        time.sleep(3.0)

    # ---- analyse everything we have history for
    results = []
    for m in uni:
        rows = load_hist(m["symbol"])
        if rows:
            a = analyse(m["symbol"], m, rows)
            if a:
                results.append(a)

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
