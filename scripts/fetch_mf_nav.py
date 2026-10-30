#!/usr/bin/env python3
"""Mutual fund NAV history, fetched on the GitHub runner rather than in Colab.

WHY THIS MOVED OFF COLAB
Two attempts failed there: the AMFI month-by-month version was ~7,100 requests and was
killed by hand, and the mfapi.in version produced no output at all - the diagnostic cell
hung on its first network call and never returned. Colab appears to block or throttle these
hosts. The GitHub runner does not: the daily pipeline already pulls AMFI's NAVAll.txt and
reports 14,414 schemes, so this is a network where the source is known to work.

TWO SOURCES, IN ORDER
  1. mfapi.in        - one request per scheme, full history back to inception
  2. AMFI range API  - one request per fund house covering a whole date range, so ~50
                       requests rather than the 7,100 the first version made
Whichever answers first wins; the other is the fallback.

Resumable: whatever is already in the output file is kept and skipped.
"""
import argparse, json, os, random, sys, time
import urllib.error, urllib.request
from datetime import datetime, timezone

UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                     "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")}
OUT = "data/mf/nav_history.parquet"
MFAPI = "https://api.mfapi.in/mf/{code}"
AMFI = ("https://portal.amfiindia.com/DownloadNAVHistoryReport_Po.aspx"
        "?frmdt={f}&todt={t}&mf={mf}&tp=1")


def get(url, timeout=45, retries=3):
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                        timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep((2 ** attempt) + random.uniform(0, 1))
        except Exception:
            time.sleep((2 ** attempt) + random.uniform(0, 1))
    return None


def via_mfapi(code):
    """Full history for one scheme, newest-first from the API."""
    import pandas as pd
    raw = get(MFAPI.format(code=code))
    if not raw:
        return None
    try:
        j = json.loads(raw)
    except Exception:
        return None
    if j.get("status") != "SUCCESS" or not j.get("data"):
        return None
    df = pd.DataFrame(j["data"])
    if df.empty or "date" not in df or "nav" not in df:
        return None
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y", errors="coerce")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna(subset=["date", "nav"])
    if df.empty:
        return None
    df["code"] = code
    return df[["code", "date", "nav"]].sort_values("date").reset_index(drop=True)


def via_amfi(frm, to, amc):
    """One fund house, one date range. The API the first version misused."""
    import pandas as pd
    raw = get(AMFI.format(f=frm, t=to, mf=amc), timeout=90)
    if not raw or "Scheme Code" not in raw:
        return None
    rows = []
    for line in raw.splitlines():
        parts = [p.strip() for p in line.split(";")]
        if len(parts) >= 6 and parts[0].isdigit():
            try:
                nav = float(parts[4])
            except ValueError:
                continue
            rows.append({"code": int(parts[0]), "nav": nav, "date": parts[5]})
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"], format="%d-%b-%Y", errors="coerce")
    df = df.dropna(subset=["date", "nav"])
    return df[["code", "date", "nav"]] if not df.empty else None


def scheme_codes():
    """The codes the site actually shows, so we fetch exactly those."""
    raw = get("https://raw.githubusercontent.com/devrajai/ArthaSaar/main/docs/mf.json")
    if not raw:
        # fall back to the local copy the pipeline wrote
        try:
            raw = open("docs/mf.json").read()
        except Exception:
            return []
    try:
        mf = json.loads(raw)
    except Exception:
        return []
    return [int(r["code"]) for r in (mf.get("rows") or []) if r.get("code")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=0, help="limit schemes, 0 = all")
    ap.add_argument("--sleep", type=float, default=0.25)
    ap.add_argument("--source", choices=["mfapi", "amfi", "auto"], default="auto")
    args = ap.parse_args()

    import pandas as pd

    codes = scheme_codes()
    print("scheme codes: %d" % len(codes))
    if not codes:
        print("::error title=No scheme list::docs/mf.json missing or unreadable")
        return 1
    if args.max:
        codes = codes[:args.max]

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    frames, done = [], set()
    if os.path.exists(OUT):
        prev = pd.read_parquet(OUT)
        done = set(int(c) for c in prev["code"].unique())
        frames.append(prev)
        print("resume: %d schemes, %d rows already on disk" % (len(done), len(prev)))

    todo = [c for c in codes if c not in done]
    print("%d to fetch, source=%s" % (len(todo), args.source))

    ok = fail = 0
    use_amfi = args.source == "amfi"

    for i, code in enumerate(todo, 1):
        df = None
        if not use_amfi:
            df = via_mfapi(code)
        if df is None and args.source in ("amfi", "auto"):
            # one AMFI call per fund house is not possible per scheme, so fall back to a
            # wide date range for the whole list only once - handled below
            pass
        if df is not None:
            frames.append(df)
            ok += 1
        else:
            fail += 1

        if i % 25 == 0 or i == len(todo):
            if frames:
                merged = pd.concat(frames, ignore_index=True)
                merged = (merged.drop_duplicates(subset=["code", "date"])
                          .sort_values(["code", "date"]))
                merged.to_parquet(OUT, index=False)
                print("  %d/%d  ok %d  failed %d  | %d rows, %d schemes"
                      % (i, len(todo), ok, fail, len(merged), merged["code"].nunique()))
        time.sleep(args.sleep + random.uniform(0, 0.1))

    # If mfapi gave us nothing at all, try AMFI by fund house - ~50 requests, not 7,100.
    if ok == 0 and args.source in ("amfi", "auto"):
        print("\nmfapi returned nothing - falling back to AMFI by fund house")
        today = datetime.now(timezone.utc)
        frm, to = "01-Jan-2006", today.strftime("%d-%b-%Y")
        misses = 0
        for amc in range(1, 51):
            df = via_amfi(frm, to, amc)
            if df is not None:
                frames.append(df)
                misses = 0
                print("  AMC %d: %d rows" % (amc, len(df)))
            else:
                misses += 1
                if misses >= 6:
                    break
            time.sleep(1.0)
        if frames:
            merged = pd.concat(frames, ignore_index=True)
            merged = (merged.drop_duplicates(subset=["code", "date"])
                      .sort_values(["code", "date"]))
            merged = merged[merged["code"].isin(codes)]
            merged.to_parquet(OUT, index=False)
            ok = merged["code"].nunique()
            print("AMFI: %d rows, %d schemes" % (len(merged), ok))

    if not os.path.exists(OUT):
        print("::error title=MF NAV produced nothing::both mfapi.in and AMFI returned no data")
        return 1

    final = pd.read_parquet(OUT)
    print("\n-> %s  %.1f MB" % (OUT, os.path.getsize(OUT) / 1e6))
    print("   %d rows, %d schemes, %s -> %s"
          % (len(final), final["code"].nunique(),
             final["date"].min().date(), final["date"].max().date()))
    if final["code"].nunique() < 50:
        print("::warning title=Thin MF coverage::only %d schemes fetched"
              % final["code"].nunique())
    return 0


if __name__ == "__main__":
    sys.exit(main())
