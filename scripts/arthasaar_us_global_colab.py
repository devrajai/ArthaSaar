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

# ============================== CELL 7 =======================================
# Push the parquet files into the repo so the GitHub pipeline can use them.
#
# BEFORE ANYTHING ELSE: this cell checks that the token actually works and says WHY if it
# does not. The first version swallowed the HTTP status and printed only "HTTPError" for
# every file, which told nobody anything.
import base64, json, os, time, urllib.request, urllib.error

GH_REPO  = "devrajai/ArthaSaar"
GH_PATH  = "data/yahoo"

# ---- supply the token -----------------------------------------------------------------
# Preferred: Colab Secrets (key icon in the left sidebar -> add GH_TOKEN -> Notebook access).
# Fallback: typed input. getpass is NOT used - it raises KeyboardInterrupt in Colab because
# the kernel's stdin is not a real terminal.
GH_TOKEN = ""
try:
    from google.colab import userdata
    GH_TOKEN = (userdata.get("GH_TOKEN") or "").strip()
    if GH_TOKEN:
        print("token loaded from Colab Secrets")
except Exception:
    pass
if not GH_TOKEN:
    print("No GH_TOKEN in Colab Secrets - falling back to typed input.")
    GH_TOKEN = input("Paste token: ").strip()

if not GH_TOKEN:
    print("No token. Stopping.")
else:
    H = {"Authorization": "Bearer " + GH_TOKEN,
         "Accept": "application/vnd.github+json",
         "User-Agent": "ArthaSaar-Sync"}

    def call(url, method="GET", payload=None):
        """Returns (status, body-text). Never raises, so the status is always visible."""
        data = json.dumps(payload).encode() if payload is not None else None
        hh = dict(H)
        if data:
            hh["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, method=method, headers=hh)
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except Exception as e:
            return 0, "%s: %s" % (type(e).__name__, str(e)[:150])

    # ---- pre-flight -------------------------------------------------------------------
    print("\nchecking the token against %s ..." % GH_REPO)
    status, body = call("https://api.github.com/repos/" + GH_REPO)
    if status != 200:
        print("  repository check FAILED: HTTP %s" % status)
        print("  GitHub says:", body[:300])
        print("\n  what this means:")
        print("   401  the token is wrong or incomplete - regenerate and copy the whole string")
        print("   403  the token has no access to this repository")
        print("   404  the token is fine but was not granted access to devrajai/ArthaSaar;")
        print("        set Repository access to 'Only select repositories' and pick it")
        print("\n  Nothing was uploaded. Fix the token and run this cell again.")
        GH_TOKEN = ""
    else:
        info = json.loads(body)
        perms = info.get("permissions") or {}
        print("  repository OK: %s" % info.get("full_name"))
        print("  your permission on it: push=%s admin=%s" % (perms.get("push"), perms.get("admin")))
        if not perms.get("push"):
            print("  WARNING: push is false - the token needs Contents: Read and write,")
            print("           otherwise every upload will fail with 403.")

if GH_TOKEN:
    files = sorted(f for f in os.listdir(OUT) if f.endswith(".parquet"))
    print("\nfiles to push:", len(files))
    ok = failed = 0
    first_error = None
    for i, fn in enumerate(files, 1):
        remote_name = fn[3:] if fn.startswith("us_") else fn
        url = "https://api.github.com/repos/%s/contents/%s/%s" % (GH_REPO, GH_PATH, remote_name)
        with open(os.path.join(OUT, fn), "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        payload = {"message": "data: US/global %s" % remote_name, "content": b64}

        st, bd = call(url)
        if st == 200:
            try:
                payload["sha"] = json.loads(bd)["sha"]
            except Exception:
                pass
        elif st not in (404,):
            failed += 1
            first_error = first_error or (remote_name, st, bd[:200])
            print("  %-24s FAILED HTTP %s" % (remote_name, st))
            if failed >= 3:
                print("\n  stopping after 3 failures - no point grinding through the rest.")
                break
            continue

        st2, bd2 = call(url, "PUT", payload)
        if st2 in (200, 201):
            ok += 1
        else:
            failed += 1
            first_error = first_error or (remote_name, st2, bd2[:200])
            print("  %-24s FAILED HTTP %s" % (remote_name, st2))
            if failed >= 3:
                print("\n  stopping after 3 failures - no point grinding through the rest.")
                break
        time.sleep(0.35)

    print("\npushed %d, failed %d" % (ok, failed))
    if first_error:
        name, st, bd = first_error
        print("\nfirst error on %s: HTTP %s" % (name, st))
        print("GitHub says:", bd)
        print("\n  403 on upload usually means the token lacks Contents: Read and write.")
        print("  404 on upload usually means the token cannot see this repository.")
    elif ok:
        print("done - the pipeline's build_global_market.py will pick these up next run")

# ============================== CELL 8 =======================================
# NO-TOKEN ROUTE. Combine every parquet into ONE file you can upload by hand.
#
# Why this exists: if creating a token keeps failing, this removes the credential entirely.
# One file, dragged into GitHub's web uploader. Slower to refresh (manual), but nothing to
# authenticate and nothing to leak.
import os
import pandas as pd

parts = []
for fn in sorted(f for f in os.listdir(OUT) if f.endswith(".parquet")):
    df = pd.read_parquet(os.path.join(OUT, fn))
    if df.empty:
        continue
    sym = fn[:-8]                     # strip .parquet
    sym = sym[3:] if sym.startswith("us_") else sym
    # Undo the filename-safe encoding, in the same order it was applied:
    #   ^GSPC -> IDX_GSPC, EURINR=X -> EURINR_EQ_X, BRK.B -> BRK_B
    # "IDX_" must be consumed before the generic "_" -> "." step, or "^GSPC" becomes "^GSPC"
    # only by luck. BRK-B is untouched because the hyphen was never encoded.
    # Tolerate BOTH encodings seen in this repo: "IDX_GSPC" (the Colab's own safe()) and
    # "_IDX_GSPC" (the pipeline's older convention). Without the lstrip the second form
    # decodes to ".^GSPC" - a leading dot that silently matches nothing.
    sym = sym.lstrip("_").replace("IDX_", "^").replace("EQ_", "=").replace("_", ".")
    df = df.copy()
    df["symbol"] = sym
    parts.append(df)

if not parts:
    print("no parquet files found in", OUT)
else:
    all_df = pd.concat(parts, ignore_index=True)
    all_df = all_df.sort_values(["symbol", "date"])
    dest = os.path.join(OUT, "global_combined.parquet")
    all_df.to_parquet(dest, index=False)
    mb = os.path.getsize(dest) / 1e6
    print("combined rows :", f"{len(all_df):,}")
    print("symbols       :", all_df["symbol"].nunique())
    print("date range    :", all_df["date"].min(), "->", all_df["date"].max())
    print("file size     : %.2f MB" % mb)
    print("saved to      :", dest)
    print()
    print("NEXT (no token needed):")
    print("  1. In Drive, find the file: ArthaSaar_us/global_combined.parquet")
    print("  2. Download it")
    print("  3. Open github.com/devrajai/ArthaSaar/tree/main/data/yahoo")
    print("  4. 'Add file' -> 'Upload files' -> drag it in -> Commit")
    print()
    if mb > 20:
        print("NOTE: %.1f MB is close to GitHub's web-upload limit; the per-symbol" % mb)
        print("      route via cell 7 is better if you can get a token working.")

