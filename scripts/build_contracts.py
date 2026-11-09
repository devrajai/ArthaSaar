#!/usr/bin/env python3
"""Contract Explorer data, premium movers, and the cheap-option base rate.

THE QUESTION THIS ANSWERS
Someone sees a Rs 0.85 option close at Rs 6 and asks why they never find those. This
measures, across every contract we hold: of options trading under Rs 2 in their final week,
how many ever doubled, how many reached 5x, how many expired worthless. That is the honest
counterweight to a screenshot of one winner.

It is only possible now, because the stored F&O files carry an expiry column. Before that a
"contract" was a merge of the weekly and the monthly at the same strike, so any follow-forward
compared different things and invented moves.

THREE OUTPUTS
  docs/premium_base_rates.json   the answer above, with sample sizes
  docs/premium_movers.json       options that gained 3x or more within 3 sessions
  docs/contracts/<SYMBOL>.json   per-underlying contract history for the explorer

WHAT IT REFUSES TO DO
Publish a "chance of a 10x" without the count it came from. Every figure carries its n, and
the worthlessness share is reported beside the upside ones - a page that shows only the
multipliers is an advertisement, not a measurement.
"""
import argparse, glob, json, os, sys
from datetime import datetime, timezone

OUT_RATES = "docs/premium_base_rates.json"
OUT_MOVERS = "docs/premium_movers.json"
OUT_DIR = "docs/contracts"
CHEAP = 2.0              # "cheap option" threshold in rupees
FINAL_WINDOW = 7         # sessions before expiry that count as the final week
MOVERS_WINDOW = 3        # sessions for the premium-mover scan
MOVERS_MULTIPLE = 3.0    # a "mover" tripled
MIN_CASES = 50


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fo_files():
    """Every F&O parquet we can see, wherever it landed."""
    pats = ["data/parquet/fo/fo_*.parquet", "data/fo/fo_*.parquet",
            "data/fo/fo_20*.parquet", "data/parquet/fo/yearly/fo_*.parquet"]
    out = []
    for p in pats:
        out.extend(glob.glob(p))
    return sorted(set(out))


def load(con, files):
    """One view over all the parquet, with the columns we need."""
    lst = "[" + ",".join("'%s'" % f.replace("'", "") for f in files) + "]"
    con.execute("CREATE OR REPLACE VIEW fo AS SELECT * FROM read_parquet(%s)" % lst)
    cols = [r[0] for r in con.execute("DESCRIBE SELECT * FROM fo").fetchall()]
    return cols


def main():
    ap = argparse.ArgumentParser(description="Contract explorer and premium base rates.")
    ap.add_argument("--max-contract-symbols", type=int, default=250)
    ap.add_argument("--per-symbol-contracts", type=int, default=120)
    args = ap.parse_args()

    files = fo_files()
    if not files:
        print("no F&O parquet found")
        for path, payload in ((OUT_RATES, {"updated": now(), "available": False,
                                           "note": "No F&O parquet present."}),
                              (OUT_MOVERS, {"updated": now(), "rows": [],
                                            "note": "No F&O parquet present."})):
            os.makedirs("docs", exist_ok=True)
            json.dump(payload, open(path, "w"), ensure_ascii=False, separators=(",", ":"))
        return 0

    import duckdb
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='1500MB'")
    cols = load(con, files)
    print("  %d parquet file(s), columns: %s" % (len(files), ", ".join(cols[:10])))

    if "expiry" not in cols:
        print("  NO expiry column - refusing to compute base rates.")
        print("  Without expiry a 'contract' merges weekly and monthly, so any follow-forward")
        print("  compares different things. Rebuild the history with expiry first.")
        os.makedirs("docs", exist_ok=True)
        json.dump({"updated": now(), "available": False,
                   "note": ("The stored F&O files have no expiry column, so a contract cannot "
                            "be followed over time. Rebuild the history with expiry.")},
                  open(OUT_RATES, "w"), ensure_ascii=False, separators=(",", ":"))
        return 0

    sessions = con.execute("SELECT COUNT(DISTINCT date) FROM fo").fetchone()[0]
    first, last = con.execute("SELECT MIN(date), MAX(date) FROM fo").fetchone()
    print("  %d sessions, %s to %s" % (sessions, first, last))

    # ---------------------------------------------------------------- base rates
    # For every contract: its last trading date is its expiry session. Take the price at the
    # start of its final window, keep the contracts that were under CHEAP then, and follow
    # them to the end.
    print("\ncomputing cheap-option base rates ...")
    q = """
    WITH opts AS (
      SELECT symbol, strike, opt_type, expiry, CAST(date AS VARCHAR) d,
             CAST(close AS DOUBLE) px
      FROM fo
      WHERE opt_type IN ('CE','PE') AND close IS NOT NULL AND CAST(close AS DOUBLE) > 0
    ),
    ends AS (SELECT symbol,strike,opt_type,expiry, MAX(d) last_d FROM opts GROUP BY 1,2,3,4),
    ranked AS (
      SELECT o.*, ROW_NUMBER() OVER (PARTITION BY o.symbol,o.strike,o.opt_type,o.expiry
                                     ORDER BY o.d DESC) rn
      FROM opts o
    ),
    finalw AS (SELECT * FROM ranked WHERE rn <= ?),
    entry AS (
      SELECT r.symbol,r.strike,r.opt_type,r.expiry, r.px AS entry_px, r.d AS entry_d
      FROM finalw r WHERE r.rn = ? AND r.px <= ?
    ),
    path AS (
      SELECT e.symbol,e.strike,e.opt_type,e.expiry,e.entry_px,
             MAX(r.px) peak, MIN(r.px) trough,
             (SELECT px FROM ranked x WHERE x.symbol=e.symbol AND x.strike=e.strike
                AND x.opt_type=e.opt_type AND x.expiry=e.expiry AND x.rn=1) end_px
      FROM entry e
      JOIN ranked r ON r.symbol=e.symbol AND r.strike=e.strike
                   AND r.opt_type=e.opt_type AND r.expiry=e.expiry AND r.rn <= ?
      GROUP BY 1,2,3,4,5
    )
    SELECT COUNT(*) n,
           SUM(CASE WHEN peak >= entry_px*2  THEN 1 ELSE 0 END) d2,
           SUM(CASE WHEN peak >= entry_px*5  THEN 1 ELSE 0 END) d5,
           SUM(CASE WHEN peak >= entry_px*10 THEN 1 ELSE 0 END) d10,
           SUM(CASE WHEN end_px <= entry_px*0.25 THEN 1 ELSE 0 END) worthless,
           SUM(CASE WHEN peak >= entry_px*2  AND end_px <= entry_px*0.25 THEN 1 ELSE 0 END) doubled_then_died
    FROM path
    """
    try:
        row = con.execute(q, [FINAL_WINDOW, FINAL_WINDOW, CHEAP, FINAL_WINDOW]).fetchone()
    except Exception as e:
        print("  base-rate query failed: %s: %s" % (type(e).__name__, str(e)[:160]))
        row = None

    rates = {"updated": now(), "available": True, "sessions": sessions,
             "first": first, "last": last, "cheap_threshold": CHEAP,
             "final_window_sessions": FINAL_WINDOW, "note": "", "cautions": {}}
    if row and row[0]:
        n, d2, d5, d10, worth, dtd = row
        pct = lambda v: round(v / n * 100, 1) if n else None
        rates.update({
            "contracts_followed": int(n),
            "reached_2x_pct": pct(d2 or 0),
            "reached_5x_pct": pct(d5 or 0),
            "reached_10x_pct": pct(d10 or 0),
            "ended_below_quarter_pct": pct(worth or 0),
            "doubled_then_fell_pct": pct(dtd or 0),
        })
        rates["note"] = (
            "Of %s contracts that were trading under Rs %.0f in the last %d sessions before "
            "expiry: %s%% ever doubled, %s%% reached 5x, %s%% reached 10x, and %s%% ended at a "
            "quarter of that price or less."
            % (f"{n:,}", CHEAP, FINAL_WINDOW, rates["reached_2x_pct"], rates["reached_5x_pct"],
               rates["reached_10x_pct"], rates["ended_below_quarter_pct"]))
        if n < MIN_CASES:
            rates["note"] += (" Only %d contracts - too few to read as a rate." % n)
    else:
        rates["note"] = "No cheap contracts found in a final week."
    rates["cautions"] = {
        "peak_not_exit": ("'Reached 2x' means the premium touched 2x at some close. Selling at "
                          "the peak is not something a person reliably does."),
        "worthless_is_common": ("The share ending at a quarter or less is the number to read "
                                "beside the multipliers, not after them."),
        "charges_excluded": ("Brokerage, STT, exchange charges and GST are not included. On a "
                             "Rs 2 premium they are a large share of the stake."),
        "survivorship": ("Only contracts that existed and traded are counted. A strike nobody "
                         "traded is invisible here."),
    }

    # ---------------------------------------------------------------- movers
    print("scanning premium movers ...")
    movers = []
    try:
        mq = """
        WITH opts AS (
          SELECT symbol,strike,opt_type,expiry,CAST(date AS VARCHAR) d,CAST(close AS DOUBLE) px,
                 CAST(volume AS DOUBLE) vol, CAST(oi AS DOUBLE) oi
          FROM fo WHERE opt_type IN ('CE','PE') AND CAST(close AS DOUBLE) > 0
        ),
        seq AS (
          SELECT *, LAG(px,?) OVER (PARTITION BY symbol,strike,opt_type,expiry ORDER BY d) prev_px,
                    LAG(d,?)  OVER (PARTITION BY symbol,strike,opt_type,expiry ORDER BY d) prev_d
          FROM opts
        )
        SELECT symbol,strike,opt_type,expiry,prev_d,d,prev_px,px,px/prev_px mult,vol,oi
        FROM seq
        WHERE prev_px > 0 AND px/prev_px >= ? AND prev_px <= ?
        ORDER BY mult DESC LIMIT 200
        """
        for r in con.execute(mq, [MOVERS_WINDOW, MOVERS_WINDOW, MOVERS_MULTIPLE, 20.0]).fetchall():
            movers.append({"symbol": r[0], "strike": r[1], "type": r[2], "expiry": str(r[3]),
                           "from_date": str(r[4]), "to_date": str(r[5]),
                           "from_px": round(r[6], 2), "to_px": round(r[7], 2),
                           "multiple": round(r[8], 1),
                           "volume": int(r[9] or 0), "oi": int(r[10] or 0)})
    except Exception as e:
        print("  mover scan failed: %s: %s" % (type(e).__name__, str(e)[:140]))

    movers_doc = {"updated": now(), "count": len(movers), "rows": movers,
                  "window_sessions": MOVERS_WINDOW, "multiple": MOVERS_MULTIPLE,
                  "note": ("Options whose premium multiplied %.0fx or more within %d sessions, "
                           "from an entry under Rs 20. A move like this is rare and usually on "
                           "a cheap far strike - the base rates say how rarely it ends well."
                           % (MOVERS_MULTIPLE, MOVERS_WINDOW))}

    # ---------------------------------------------------------------- contracts
    print("writing per-symbol contract files ...")
    os.makedirs(OUT_DIR, exist_ok=True)
    syms = [r[0] for r in con.execute("""
        SELECT symbol FROM (
          SELECT symbol, COUNT(*) n FROM fo WHERE opt_type IN ('CE','PE') GROUP BY symbol
        ) ORDER BY n DESC LIMIT ?
    """, [args.max_contract_symbols]).fetchall()]
    written = 0
    for s in syms:
        try:
            rows = con.execute("""
              SELECT CAST(date AS VARCHAR), CAST(expiry AS VARCHAR), CAST(strike AS DOUBLE),
                     opt_type, CAST(close AS DOUBLE), CAST(volume AS DOUBLE), CAST(oi AS DOUBLE)
              FROM fo WHERE symbol = ? AND opt_type IN ('CE','PE')
              ORDER BY date DESC, expiry, strike LIMIT ?
            """, [s, args.per_symbol_contracts * 40]).fetchall()
            if not rows:
                continue
            json.dump({"symbol": s, "updated": now(),
                       "columns": ["date", "expiry", "strike", "type", "close", "volume", "oi"],
                       "rows": [[r[0], r[1], r[2], r[3],
                                 round(r[4], 2) if r[4] is not None else None,
                                 int(r[5] or 0), int(r[6] or 0)] for r in rows]},
                      open(os.path.join(OUT_DIR, "%s.json" % s), "w"),
                      separators=(",", ":"))
            written += 1
        except Exception:
            continue

    os.makedirs("docs", exist_ok=True)
    json.dump(rates, open(OUT_RATES, "w"), ensure_ascii=False, separators=(",", ":"))
    json.dump(movers_doc, open(OUT_MOVERS, "w"), ensure_ascii=False, separators=(",", ":"))

    print("\n-> %s" % OUT_RATES)
    print("   %s" % rates["note"])
    print("-> %s  (%d movers)" % (OUT_MOVERS, len(movers)))
    print("-> %s/  (%d symbol files)" % (OUT_DIR, written))
    for m in movers[:6]:
        print("     %-11s %8.0f %s %s  Rs %.2f -> Rs %.2f  = %.1fx"
              % (m["symbol"], m["strike"], m["type"], m["expiry"],
                 m["from_px"], m["to_px"], m["multiple"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
