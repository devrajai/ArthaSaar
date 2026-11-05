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
import urllib.parse, urllib.request
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


_COMBINED = {"df": None, "tried": False}


def _combined():
    """The single-file route: one parquet with a symbol column, uploaded by hand.

    This exists so the site can use the data without a GitHub token. If it is present it
    takes precedence for any symbol missing from the per-file layout.
    """
    if _COMBINED["tried"]:
        return _COMBINED["df"]
    _COMBINED["tried"] = True
    import pandas as pd
    for name in ("global_combined.parquet", "us_combined.parquet"):
        p = os.path.join(YAHOO, name)
        if not os.path.exists(p):
            continue
        try:
            df = pd.read_parquet(p)
            cols = {c.lower(): c for c in df.columns}
            if "symbol" in cols and "close" in cols:
                _COMBINED["df"] = df
                print("  combined file found: %s (%d rows, %d symbols)"
                      % (name, len(df), df[cols["symbol"]].nunique()))
                return df
        except Exception:
            continue
    return None



def live_check(sym):
    """The last close Yahoo reports right now, or None.

    A heuristic on the series shape cannot tell a noisy synthetic walk from a real market -
    the fake Nifty had 2,041 distinct daily returns and sailed through every such test. What
    does work is comparing against the source: a file whose last close is far from the live
    quote is stale or fabricated, whatever it looks like internally.
    """
    try:
        u = ("https://query1.finance.yahoo.com/v8/finance/chart/"
             + urllib.parse.quote(sym) + "?interval=1d&range=5d")
        j = json.loads(urllib.request.urlopen(
            urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}),
            timeout=20).read())
        res = j["chart"]["result"][0]
        q = res["indicators"]["quote"][0]
        closes = [c for c in q["close"] if c is not None]
        return float(closes[-1]) if closes else None
    except Exception as e:
        print("  live check failed for %s: %s: %s" % (sym, type(e).__name__, str(e)[:60]))
        return None


def load(sym):
    import pandas as pd
    cdf = _combined()
    if cdf is not None:
        try:
            cols = {c.lower(): c for c in cdf.columns}
            sub = cdf[cdf[cols["symbol"]] == sym]
            if not sub.empty:
                ser = {str(d)[:10]: float(c)
                       for d, c in zip(sub[cols["date"]], sub[cols["close"]])
                       if c == c}
                return ser
        except Exception:
            pass
    # THREE naming conventions exist in this repo and they do not agree:
    #   fetch_yahoo._safe()  re.sub(r"[^A-Za-z0-9]+","_",sym).strip("_")  -> "GSPC", "BRK_B"
    #   the older pipeline   ^ -> _IDX_, = -> _EQ_, . -> _                -> "_IDX_GSPC"
    #   the Colab            ^ -> IDX_                                   -> "IDX_GSPC"
    # Looking for only one of them means the file exists and is reported missing, which is
    # exactly what happened. Try every form.
    import re as _re
    yahoo_style = _re.sub(r"[^A-Za-z0-9]+", "_", sym).strip("_")
    legacy = sym.replace("^", "_IDX_").replace("=", "_EQ_").replace(".", "_")
    colab = sym.replace("^", "IDX_").replace("=", "EQ_").replace(".", "_")
    candidates = []
    for base in (yahoo_style, legacy, colab, sym):
        candidates += [base + ".parquet", "us_" + base + ".parquet"]
    for name in candidates:
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
        # Cross-check against the live quote. A file that disagrees by more than 10% is
        # stale or fabricated; drop it rather than publish a wrong level.
        live = live_check(sym)
        if live and abs(s[d[-1]] / live - 1) > 0.10:
            print("  REJECTED %s: file says %.2f on %s, Yahoo says %.2f"
                  % (sym, s[d[-1]], d[-1], live))
            continue
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
    # The correlation path reads the series directly, so it bypassed the rejection above and
    # happily computed 0.03 from the fabricated Nifty. Same cross-check applies here.
    for _sym, _ser in (("^GSPC", us), ("^NSEI", ind)):
        if not _ser:
            continue
        _d = sorted(_ser)
        _live = live_check(_sym)
        if _live and abs(_ser[_d[-1]] / _live - 1) > 0.10:
            print("  REJECTED %s from the correlation: file %.2f vs Yahoo %.2f"
                  % (_sym, _ser[_d[-1]], _live))
            if _sym == "^GSPC":
                us = {}
            else:
                ind = {}
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
