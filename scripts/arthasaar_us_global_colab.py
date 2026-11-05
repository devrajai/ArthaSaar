#!/usr/bin/env python3
# =============================================================================
# ArthaSaar - US and global market data collector  (Google Colab)
# =============================================================================
# WHY COLAB
#   Your Colab runtime reaches Yahoo directly and has Drive mounted, which makes it the right
#   place to build a US history once. The GitHub runner keeps it fresh afterwards.
#
# WHAT IT COLLECTS
#   1. US indices            S&P 500, Nasdaq, Dow, Russell 2000, VIX
#   2. US sector ETFs        the 11 SPDR sectors, so sector rotation is measurable
#   3. AI and megacap names  the stocks that move the index
#   4. Global indices        the ones an Indian investor actually watches
#
# WHAT IT SAVES
#   /content/drive/MyDrive/ArthaSaar_us/us_<SYMBOL>.parquet  (one file per symbol)
#   /content/drive/MyDrive/ArthaSaar_us/_summary.json        (row counts, date range, size)
#
# HOW TO RUN
#   Paste each cell into a separate Colab cell and run them in order. Cells are plain code,
#   not strings - a quoted cell silently does nothing.
#
# HONEST LIMITS
#   * Yahoo is an unofficial endpoint. It rate-limits and occasionally changes shape.
#   * Data is delayed and not licensed for redistribution.
#   * This is history, not a feed. Nothing here is real-time.
# =============================================================================


# ============================== CELL 1 =======================================
# Connectivity and disk check. If this fails, nothing below will work.
import urllib.request, json, sys, os

print("python:", sys.version.split()[0])

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"}


def probe(symbol):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol) + "?interval=1d&range=5d")
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
            j = json.loads(r.read())
        res = j["chart"]["result"][0]
        return len(res.get("timestamp") or [])
    except Exception as e:
        return "FAILED: %s" % type(e).__name__


import urllib.parse
for s in ("^GSPC", "AAPL", "XLK"):
    print("  %-8s -> %s bars" % (s, probe(s)))

print("\ndisk:")
print("  free:", round(os.statvfs("/content").f_bavail * os.statvfs("/content").f_frsize / 1e9, 1), "GB")


# ============================== CELL 2 =======================================
# Mount Drive. On this account it lands at /content/gdrive, so the path is resolved
# with realpath rather than assumed.
from google.colab import drive
drive.mount("/content/gdrive")

import os
root = os.path.realpath("/content/gdrive/MyDrive")
print("Drive root:", root)
OUT = os.path.join(root, "ArthaSaar_us")
os.makedirs(OUT, exist_ok=True)
print("output folder:", OUT)
print("writable:", os.access(OUT, os.W_OK))


# ============================== CELL 3 =======================================
# The universe. Kept explicit rather than scraped, so a symbol that 404s is obvious.
INDICES = {
    "^GSPC": "S&P 500", "^IXIC": "Nasdaq Composite", "^DJI": "Dow Jones",
    "^RUT": "Russell 2000", "^VIX": "VIX",
    "^NSEI": "Nifty 50", "^NSEBANK": "Bank Nifty", "^BSESN": "Sensex",
    "^N225": "Nikkei 225", "^HSI": "Hang Seng", "^FTSE": "FTSE 100",
    "^GDAXI": "DAX", "^FCHI": "CAC 40", "^STOXX50E": "Euro Stoxx 50",
}

# the 11 SPDR sectors - sector rotation is the clearest read on what a market move means
SECTORS = {
    "XLK": "Technology", "XLF": "Financials", "XLE": "Energy", "XLV": "Health Care",
    "XLY": "Consumer Discretionary", "XLP": "Consumer Staples", "XLI": "Industrials",
    "XLB": "Materials", "XLU": "Utilities", "XLRE": "Real Estate",
    "XLC": "Communication Services",
}

# the names that actually drive the index, plus the AI complex
MEGACAP = {
    "NVDA": "Nvidia", "MSFT": "Microsoft", "AAPL": "Apple", "GOOGL": "Alphabet",
    "AMZN": "Amazon", "META": "Meta", "AVGO": "Broadcom", "TSLA": "Tesla",
    "AMD": "AMD", "PLTR": "Palantir", "MU": "Micron", "TSM": "TSMC",
    "ORCL": "Oracle", "CRM": "Salesforce", "NFLX": "Netflix", "BRK-B": "Berkshire",
    "JPM": "JPMorgan", "XOM": "Exxon", "UNH": "UnitedHealth", "LLY": "Eli Lilly",
}

UNIVERSE = {}
UNIVERSE.update(INDICES)
UNIVERSE.update(SECTORS)
UNIVERSE.update(MEGACAP)
print("symbols to collect:", len(UNIVERSE))
print("  indices :", len(INDICES))
print("  sectors :", len(SECTORS))
print("  megacap :", len(MEGACAP))


# ============================== CELL 4 =======================================
# Collect. Resumable: a symbol already on disk with a full history is skipped, so a
# dropped Colab session never means starting over.
import urllib.parse, time, random, json, os
import pandas as pd

PERIOD = "10y"          # Yahoo accepts 1d..max; 10y is a good default for backtests
FORCE = False           # set True to re-download everything


def fetch(symbol, rng=PERIOD, retries=4):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol) + "?interval=1d&range=" + rng)
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                j = json.loads(r.read())
            res = j["chart"]["result"][0]
            q = res["indicators"]["quote"][0]
            rows = []
            for i, t in enumerate(res.get("timestamp") or []):
                o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
                if None in (o, h, l, c):
                    continue
                rows.append({"date": pd.to_datetime(t, unit="s", utc=True).strftime("%Y-%m-%d"),
                             "open": o, "high": h, "low": l, "close": c,
                             "volume": (q["volume"][i] if q.get("volume") else None)})
            return pd.DataFrame(rows)
        except Exception as e:
            if attempt == retries:
                return None
            time.sleep((2 ** attempt) + random.uniform(0, 1))
    return None


def safe(sym):
    return sym.replace("^", "IDX_").replace("=", "EQ_").replace(".", "_")


summary, done, skipped, failed = {}, 0, 0, 0
for i, (sym, name) in enumerate(UNIVERSE.items(), 1):
    path = os.path.join(OUT, "us_%s.parquet" % safe(sym))
    if os.path.exists(path) and not FORCE:
        try:
            old = pd.read_parquet(path)
            if len(old) > 500:
                summary[sym] = {"name": name, "rows": len(old),
                                "from": old["date"].min(), "to": old["date"].max()}
                skipped += 1
                continue
        except Exception:
            pass
    df = fetch(sym)
    if df is None or df.empty:
        failed += 1
        print("  %-10s FAILED" % sym)
        continue
    df.to_parquet(path, index=False)
    summary[sym] = {"name": name, "rows": len(df),
                    "from": df["date"].min(), "to": df["date"].max()}
    done += 1
    if i % 10 == 0 or i == len(UNIVERSE):
        print("  %d/%d  new %d  skipped %d  failed %d" % (i, len(UNIVERSE), done, skipped, failed))
    time.sleep(0.35 + random.uniform(0, 0.2))

print("\ncollected %d, skipped %d, failed %d" % (done, skipped, failed))


# ============================== CELL 5 =======================================
# Summary, written to Drive so the GitHub side can read what exists without opening 40 files.
import json, os

total_rows = sum(v["rows"] for v in summary.values())
size = sum(os.path.getsize(os.path.join(OUT, f)) for f in os.listdir(OUT) if f.endswith(".parquet"))
out = {
    "updated": pd.Timestamp.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
    "period": PERIOD,
    "symbols": len(summary),
    "total_rows": total_rows,
    "size_mb": round(size / 1e6, 2),
    "detail": summary,
}
with open(os.path.join(OUT, "_summary.json"), "w") as f:
    json.dump(out, f, indent=1)

print("symbols :", out["symbols"])
print("rows    :", f"{total_rows:,}")
print("size    :", out["size_mb"], "MB")
print("\ncoverage:")
for sym, v in list(summary.items())[:8]:
    print("  %-10s %-22s %6d rows  %s -> %s" % (sym, v["name"][:22], v["rows"], v["from"], v["to"]))

print("\nlongest history:")
for sym, v in sorted(summary.items(), key=lambda kv: -kv[1]["rows"])[:5]:
    print("  %-10s %6d rows" % (sym, v["rows"]))


# ============================== CELL 6 =======================================
# Quick sanity check: does the data look like a real market? A flat or absurd series means
# the fetch worked but the symbol was wrong.
import pandas as pd, os

checks = {"^GSPC": (-50, 50), "AAPL": (-50, 50), "XLK": (-50, 50)}
print("daily move sanity (|move| should be under ~15% for an index):")
for sym in checks:
    p = os.path.join(OUT, "us_%s.parquet" % safe(sym))
    if not os.path.exists(p):
        print("  %-8s missing" % sym)
        continue
    df = pd.read_parquet(p)
    df = df.sort_values("date")
    mv = df["close"].pct_change().dropna() * 100
    print("  %-8s %5d rows | median |move| %.2f%% | max %.2f%% | last close %.2f"
          % (sym, len(df), mv.abs().median(), mv.abs().max(), df["close"].iloc[-1]))

print("\nnext step: sync this folder into the repo's data/yahoo/ so the GitHub pipeline")
print("can use it. The GitHub side only needs the parquet files, not this notebook.")
