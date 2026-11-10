#!/usr/bin/env python3
"""One "data as of" date for the whole site.

THE PROBLEM
On 6 November the page mixed two different trading days: the Nifty figure, the sector map,
History and Global were from 4 November, while the screener, the story and the circuit card
were from 5 November. A visitor saw a green sector map next to "79% of stocks fell". Both
numbers were correct; they described different days.

Listing a date on each card is not enough - nobody compares twelve timestamps. This computes
the single session the site is describing, publishes it, and names any file that disagrees so
the page can say so out loud.

HOW THE SESSION DATE IS FOUND
Files carry it in different places, so this tries the usual keys and then the last row.
A file whose date cannot be determined is listed as unknown rather than assumed to match.
"""
import json, os, sys
from datetime import datetime, timezone

OUT = "docs/data_asof.json"

# Files whose session date matters for what a reader sees. Order is by importance.
WATCH = [
    ("data.json", "the main feed"),
    ("screener.json", "screener"),
    ("indices.json", "indices"),
    ("sectors.json", "sector map"),
    ("history.json", "history"),
    ("story.json", "story of the day"),
    ("circuits.json", "circuit limits"),
    ("global.json", "global"),
    ("rs.json", "relative strength"),
    ("breadth.json", "breadth"),
    ("series.json", "price series"),
    ("market_stats.json", "market stats"),
    ("report_cards.json", "report cards"),
]


def read(name):
    try:
        return json.load(open("docs/" + name))
    except Exception:
        return None


def norm_date(v):
    """Return YYYY-MM-DD from either YYYY-MM-DD or DD-MM-YYYY."""
    if not isinstance(v, str) or len(v) < 10:
        return None
    v = v[:10]
    if v[4] == "-" and v[:4].isdigit():
        return v                      # YYYY-MM-DD
    # DD-MM-YYYY - the dashes are at index 2 and 5, not 2 and 6
    if v[2] == "-" and v[5] == "-" and v[:2].isdigit() and v[3:5].isdigit():
        return "%s-%s-%s" % (v[6:10], v[3:5], v[:2])
    return None


def session_date(name, d):
    """Best-effort session date for one published file."""
    if not isinstance(d, dict):
        return None

    # direct fields, in order of reliability
    for k in ("as_of", "session", "session_date", "date", "last", "for_date"):
        v = d.get(k)
        nd = norm_date(v)
        if nd:
            return nd

    # a date inside a nested block, e.g. {"today": {"date": ...}}
    for k in ("today", "latest", "current"):
        v = d.get(k)
        if isinstance(v, dict):
            for kk in ("date", "as_of", "session"):
                vv = v.get(kk)
                nd = norm_date(vv)
                if nd:
                    return nd

    # the last row of a series
    for k in ("rows", "series"):
        rows = d.get(k)
        if isinstance(rows, list) and rows:
            r = rows[-1]
            if isinstance(r, dict):
                for kk in ("d", "date", "as_of"):
                    vv = r.get(kk)
                    nd = norm_date(vv)
                    if nd:
                        return nd
            elif isinstance(r, list) and r and isinstance(r[0], str):
                nd = norm_date(r[0])
                if nd:
                    return nd

    # a "generated"/"updated" timestamp is NOT a session date - deliberately ignored,
    # because a file rebuilt at midnight would then claim to describe the next day.
    return None


def archive_session():
    """The trading session the pipeline actually analysed, from the candle archive."""
    import glob
    for path in sorted(glob.glob("data/candles/*adj*.parquet")) + sorted(glob.glob("data/candles/*.parquet")):
        try:
            import duckdb
            con = duckdb.connect(); con.execute("SET threads=1")
            row = con.execute("SELECT MAX(CAST(date AS VARCHAR)) FROM read_parquet(?)", [path]).fetchone()
            con.close()
            if row and row[0]:
                return norm_date(row[0]), path
        except Exception:
            try:
                import pandas as pd
                df = pd.read_parquet(path, columns=["date"])
                return norm_date(str(df["date"].max())), path
            except Exception:
                continue
    return None, None


def main():
    per, unknown, missing = {}, [], []
    for name, label in WATCH:
        d = read(name)
        if d is None:
            missing.append(name)
            continue
        sd = session_date(name, d)
        if sd:
            per[name] = {"date": sd, "label": label}
        else:
            unknown.append(name)

    guard = None
    try:
        guard = json.load(open("docs/_guard_report.json"))
    except Exception:
        pass

    sess, src = archive_session()
    dates = sorted({v["date"] for v in per.values()})
    # THE SESSION COMES FROM THE DATA, NOT FROM THE ARCHIVE.
    #
    # This used to treat the candle archive as authoritative, so when the archive lagged -
    # it ended 2026-10-23 while history.json held 2026-11-09 - every current file was labelled
    # "ahead" of the session, `behind` came out empty, and the page printed "Every dated file
    # describes the same session: 2026-10-23". That is the exact inverse of the truth: the
    # archive was the stale thing, and the files were right.
    #
    # The newest date any published file describes IS the session. The archive is reported
    # separately so a lagging archive is visible instead of silently redefining "today".
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "files": per, "unknown": unknown, "missing": missing,
           "dates": dates,
           "session": (dates[-1] if dates else sess),
           "session_source": "newest dated published file",
           "archive_session": sess, "archive_source": src,
           "spread_days": None, "consistent": None, "behind": [], "ahead": [],
           # "kept" is populated by the empty-file guard when it preserves a
           # previously good file. It was read here but never set, so this script
           # crashed at the very end of every run - after writing its output, which
           # is why the file looked fine and nobody noticed.
           "kept": [], "note": ""}

    if dates:
        try:
            d0 = datetime.fromisoformat(dates[0]).date()
            d1 = datetime.fromisoformat(dates[-1]).date()
            out["spread_days"] = (d1 - d0).days
        except Exception:
            pass
        latest = out["session"]
        # Anything older than the newest session is genuinely behind. Nothing can be "ahead"
        # now that the session is defined as the newest date, so that list is always empty -
        # kept in the output so an older reader of this file does not break.
        out["behind"] = [{"file": k, "date": v["date"], "label": v["label"]}
                         for k, v in per.items() if v["date"] < latest]
        out["ahead"] = []
        out["consistent"] = not out["behind"]
        out["archive_lags"] = bool(sess and sess < latest)
        out["archive_lag_days"] = None
        if out["archive_lags"]:
            try:
                out["archive_lag_days"] = (datetime.fromisoformat(latest).date()
                                           - datetime.fromisoformat(sess).date()).days
            except Exception:
                pass

    if out.get("archive_lags"):
        out["note"] = ("The site describes the %s session. The candle archive ends %s - %s days "
                       "behind - so anything built from it (levels, patterns, deep history) is "
                       "that much older than the rest of the page."
                       % (out["session"], out.get("archive_session"),
                          out.get("archive_lag_days")))
    elif out["consistent"]:
        out["note"] = ("Every dated file describes the same session: %s." % out["session"])
    elif dates:
        names = ", ".join("%s (%s)" % (b["label"], b["date"]) for b in out["behind"][:5])
        out["note"] = ("Not every file describes the same session. The site is built from the "
                       "%s session; these are behind it: %s. Files that carry no date are "
                       "rebuilt in the same pipeline pass, so they share the build session."
                       % (out["session"], names))
    else:
        out["note"] = "No session dates could be determined."

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s" % OUT)
    print("   session: %s  (from %s)" % (out["session"], out["session_source"]))
    print("   consistent: %s | spread: %s days | undated files: %d"
          % (out["consistent"], out["spread_days"], len(unknown)))
    if out["behind"]:
        print("   behind the newest session:")
        for b in out["behind"]:
            print("     %-20s %s  (%s)" % (b["file"], b["date"], b["label"]))
    if out["kept"]:
        print("   kept from previous commit (this run built them empty):")
        for k in out["kept"]:
            print("     %-24s published %s rows, built %s" % (k["file"], k["before"], k["now"]))
    if unknown:
        print("   no date in file (rebuilt this run):", ", ".join(unknown[:8]),
              "..." if len(unknown) > 8 else "")
    if missing:
        print("   missing:", ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
