#!/usr/bin/env python3
"""Global and sector read-through: what kind of move was it?

WHY THIS EXISTS
"Global markets fell" is not information. Which sectors fell tells you what the market was
pricing: a technology-led fall is a rates or AI-spending story, an energy-led fall is a demand
story, a utilities-and-staples-led fall is usually forced selling rather than a view on the
economy. The 11 SPDR sector ETFs turn one index number into that distinction.

WHAT IT READS
data/yahoo/*.parquet written by the Colab collector (arthasaar_us_global_colab.py):
  US indices  ^GSPC ^IXIC ^DJI ^RUT ^VIX
  sectors     XLK XLF XLE XLV XLY XLP XLI XLB XLU XLRE XLC
  megacap     NVDA MSFT AAPL GOOGL AMZN META AVGO TSLA AMD PLTR ...
  global      ^NSEI ^NSEBANK ^BSESN ^N225 ^HSI ^FTSE ^GDAXI ^FCHI ^STOXX50E

WHAT IT WRITES
docs/global_market.json
"""
import json, os, sys
from datetime import datetime, timezone

YAHOO = "data/yahoo"
OUT = "docs/global_market.json"

INDICES = [("^GSPC", "S&P 500"), ("^IXIC", "Nasdaq"), ("^DJI", "Dow"),
           ("^RUT", "Russell 2000"), ("^VIX", "VIX"),
           ("^NSEI", "Nifty 50"), ("^NSEBANK", "Bank Nifty"), ("^BSESN", "Sensex"),
           ("^N225", "Nikkei"), ("^HSI", "Hang Seng"), ("^FTSE", "FTSE 100"),
           ("^GDAXI", "DAX"), ("^FCHI", "CAC 40"), ("^STOXX50E", "Euro Stoxx 50")]

SECTORS = [("XLK", "Technology", "growth"), ("XLC", "Communication", "growth"),
           ("XLY", "Consumer Disc.", "growth"), ("XLF", "Financials", "cyclical"),
           ("XLI", "Industrials", "cyclical"), ("XLB", "Materials", "cyclical"),
           ("XLE", "Energy", "cyclical"), ("XLV", "Health Care", "defensive"),
           ("XLP", "Consumer Staples", "defensive"), ("XLU", "Utilities", "defensive"),
           ("XLRE", "Real Estate", "rate-sensitive")]

MEGA = ["NVDA", "MSFT", "AAPL", "GOOGL", "AMZN", "META", "AVGO", "TSLA", "AMD", "PLTR"]


def load(sym):
    import pandas as pd
    safe = sym.replace("^", "_IDX_").replace("=", "_EQ_").replace(".", "_")
    for name in (safe + ".parquet", "us_" + safe + ".parquet", sym + ".parquet"):
        p = os.path.join(YAHOO, name)
        if not os.path.exists(p):
            continue
        try:
            df = pd.read_parquet(p)
            cols = {c.lower(): c for c in df.columns}
            d = next((cols[k] for k in ("date", "datetime", "index") if k in cols), None)
            c = next((cols[k] for k in ("close", "adj close", "adj_close") if k in cols), None)
            if d is None or c is None:
                return {}
            out = {}
            for dd, cc in zip(df[d], df[c]):
                try:
                    if cc is None or cc != cc:
                        continue
                except Exception:
                    continue
                out[str(dd)[:10]] = float(cc)
            return out
        except Exception:
            continue
    return {}


def chg(series, back):
    if len(series) < back + 1:
        return None
    d = sorted(series)
    a, b = series.get(d[-1 - back]), series.get(d[-1])
    if not a or not b:
        return None
    return round((b / a - 1) * 100, 2)


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "indices": [], "sectors": [], "rotation": None, "megacap": [],
           "india_us_corr": None, "note": ""}

    # indices
    for sym, name in INDICES:
        s = load(sym)
        if not s:
            continue
        d = sorted(s)
        out["indices"].append({"symbol": sym, "name": name, "close": round(s[d[-1]], 2),
                               "date": d[-1], "chg_1d": chg(s, 1), "chg_1w": chg(s, 5),
                               "chg_1m": chg(s, 21)})
    if not out["indices"]:
        out["note"] = ("No global parquet found. Run arthasaar_us_global_colab.py in Colab and "
                       "sync the files into data/yahoo/.")
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("global market: no data")
        return 0

    # sectors, with the style each belongs to
    for sym, name, style in SECTORS:
        s = load(sym)
        if not s:
            continue
        d = sorted(s)
        out["sectors"].append({"symbol": sym, "name": name, "style": style,
                               "chg_1d": chg(s, 1), "chg_1w": chg(s, 5), "chg_1m": chg(s, 21)})

    # the read-through: is this a growth-led move, a defensive rotation, or broad?
    if len(out["sectors"]) >= 6:
        w = [x for x in out["sectors"] if x["chg_1w"] is not None]
        if w:
            w.sort(key=lambda x: x["chg_1w"])
            by_style = {}
            for x in w:
                by_style.setdefault(x["style"], []).append(x["chg_1w"])
            style_avg = {k: round(sum(v) / len(v), 2) for k, v in by_style.items()}
            spread = round(w[-1]["chg_1w"] - w[0]["chg_1w"], 2)
            # a wide spread means the market was discriminating; a narrow one means it was not
            kind = ("broad, undiscriminating" if spread < 2.5
                    else "selective - the market was pricing something specific")
            out["rotation"] = {
                "week_leader": w[-1]["name"], "week_leader_pct": w[-1]["chg_1w"],
                "week_laggard": w[0]["name"], "week_laggard_pct": w[0]["chg_1w"],
                "spread_pct": spread, "style_average": style_avg, "kind": kind,
            }

    # megacap, because a few names drive the index
    for sym in MEGA:
        s = load(sym)
        if s:
            d = sorted(s)
            out["megacap"].append({"symbol": sym, "close": round(s[d[-1]], 2),
                                   "chg_1d": chg(s, 1), "chg_1w": chg(s, 5)})

    # does India follow the US? measured, not assumed
    us, ind = load("^GSPC"), load("^NSEI")
    shared = sorted(set(us) & set(ind))
    if len(shared) > 60:
        ru, ri = [], []
        for i in range(1, len(shared)):
            a0, a1 = us.get(shared[i - 1]), us.get(shared[i])
            b0, b1 = ind.get(shared[i - 1]), ind.get(shared[i])
            if None in (a0, a1, b0, b1) or not a0 or not b0:
                continue
            ru.append(a1 / a0 - 1)
            ri.append(b1 / b0 - 1)
        for window, label in ((len(ru), "full"), (60, "last 60 sessions")):
            xs, ys = ru[-window:], ri[-window:]
            n = len(xs)
            if n < 20:
                continue
            mx, my = sum(xs) / n, sum(ys) / n
            num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
            dx = sum((a - mx) ** 2 for a in xs) ** 0.5
            dy = sum((b - my) ** 2 for b in ys) ** 0.5
            r = num / (dx * dy) if dx and dy else None
            if r is not None:
                out["india_us_corr"] = out.get("india_us_corr") or {}
                out["india_us_corr"][label] = {"correlation": round(r, 2), "n": n}

    out["note"] = ("Which sectors moved, not just the index. A technology-led fall and an "
                   "energy-led fall are different events, and the index number hides that.")
    out["cautions"] = {
        "unofficial": "Yahoo data, delayed and not a licensed feed.",
        "correlation": ("A correlation is a description of the past. India and the US decouple "
                        "for long stretches, usually when a domestic driver dominates."),
        "sectors": ("SPDR ETFs are US-listed proxies. They describe the US sector, not the "
                    "Indian one."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    for x in out["indices"][:8]:
        print("   %-12s %10.2f  1d %s  1w %s" % (x["name"], x["close"], x["chg_1d"], x["chg_1w"]))
    if out["rotation"]:
        r = out["rotation"]
        print("   week: %s %+.1f%% .. %s %+.1f%% (spread %.1f) - %s"
              % (r["week_leader"], r["week_leader_pct"], r["week_laggard"],
                 r["week_laggard_pct"], r["spread_pct"], r["kind"]))
    if out["india_us_corr"]:
        print("   India vs US:", json.dumps(out["india_us_corr"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
