#!/usr/bin/env python3
"""Volume at price: where trading actually happened, from real one-minute bars.

WHY THIS EXISTS
A live order book and individual buy/sell orders are paid exchange feeds. Free data does not
have them, and NSE's terms limit redistributing live depth. Anything that shows "live orders"
from free data is simulated, and should say so.

What free one-minute bars DO support is the same picture from the other side: for every price
level, how much volume traded there. That is a volume profile, the numbers are real, and it
answers the question people actually have - where did the market agree?

WHAT IS PUBLISHED, PER SYMBOL
  poc        point of control - the price with the most volume
  value_area the band containing 70% of the session's volume (VAH and VAL)
  levels     the busiest price levels, so a chart can draw the shape
  pressure   an ESTIMATE of buyer- versus seller-driven volume, from each bar's close against
             its open. Labelled an estimate everywhere, because that is all it is - a bar that
             closes above its open is not proof that buyers bought.

WHAT IS DELIBERATELY NOT PUBLISHED
Individual orders, order-book depth, or any claim about who bought. None of that exists in
free data, and inventing it would be the one thing worse than not having it.
"""
import argparse, glob, json, os, sys
from datetime import datetime, timezone

OUT = "docs/volume_profile.json"
BUCKETS = 40            # price levels per symbol
VALUE_AREA = 0.70       # share of volume that defines the value area
TOP_LEVELS = 12         # busiest levels published per symbol


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def files():
    pats = ["data/intraday/*/*.parquet", "data/intraday/*.parquet"]
    out = []
    for p in pats:
        out.extend(glob.glob(p))
    return sorted(set(out))


def main():
    ap = argparse.ArgumentParser(description="Volume at price from one-minute bars.")
    ap.add_argument("--max-symbols", type=int, default=120)
    args = ap.parse_args()

    fs = files()
    out = {"updated": now(), "sessions": 0, "symbols": {}, "note": "", "cautions": {}}
    if not fs:
        out["note"] = "No intraday parquet found."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), separators=(",", ":"))
        print("volume profile: no intraday data")
        return 0

    import duckdb
    con = duckdb.connect()
    con.execute("SET threads=1")
    con.execute("SET memory_limit='1200MB'")
    lst = "[" + ",".join("'%s'" % f.replace("'", "") for f in fs) + "]"
    con.execute("CREATE OR REPLACE VIEW iv AS SELECT * FROM read_parquet(%s)" % lst)

    # the latest session only - a profile mixing days describes no session anyone traded
    last = con.execute("SELECT MAX(CAST(date AS VARCHAR)) FROM iv").fetchone()[0]
    sessions = con.execute("SELECT COUNT(DISTINCT CAST(date AS VARCHAR)) FROM iv").fetchone()[0]
    out["sessions"] = sessions
    out["session"] = last
    print("  %d file(s), %d session(s), latest %s" % (len(fs), sessions, last))

    syms = [r[0] for r in con.execute("""
        SELECT symbol FROM (
          SELECT symbol, SUM(volume) v FROM iv WHERE CAST(date AS VARCHAR)=?
          GROUP BY symbol ORDER BY v DESC
        ) LIMIT ?
    """, [last, args.max_symbols]).fetchall()]
    print("  %d symbols in the latest session" % len(syms))

    for s in syms:
        try:
            rows = con.execute("""
              SELECT CAST(low AS DOUBLE), CAST(high AS DOUBLE), CAST(close AS DOUBLE),
                     CAST(open AS DOUBLE), CAST(volume AS DOUBLE)
              FROM iv WHERE symbol=? AND CAST(date AS VARCHAR)=? AND CAST(volume AS DOUBLE)>0
            """, [s, last]).fetchall()
        except Exception:
            continue
        if len(rows) < 30:
            continue

        lo_all = min(r[0] for r in rows if r[0] is not None)
        hi_all = max(r[1] for r in rows if r[1] is not None)
        if not (hi_all > lo_all):
            continue
        step = (hi_all - lo_all) / BUCKETS
        if step <= 0:
            continue

        prof = [0.0] * BUCKETS
        buy_vol = sell_vol = 0.0
        for lo, hi, cl, op, vol in rows:
            if lo is None or hi is None or cl is None or vol is None:
                continue
            # spread the bar's volume evenly across the price levels it touched, rather than
            # dumping it all on the close - a bar that ran 40 points did not trade at one price
            a = max(0, min(BUCKETS - 1, int((lo - lo_all) / step)))
            b = max(0, min(BUCKETS - 1, int((hi - lo_all) / step)))
            n = b - a + 1
            share = vol / n
            for k in range(a, b + 1):
                prof[k] += share
            # ESTIMATE of pressure: close above open suggests buying drove the bar
            if op is not None:
                if cl > op:
                    buy_vol += vol
                elif cl < op:
                    sell_vol += vol

        total = sum(prof)
        if total <= 0:
            continue

        poc_i = max(range(BUCKETS), key=lambda i: prof[i])
        # value area: grow outward from the POC until VALUE_AREA of volume is covered
        lo_i = hi_i = poc_i
        acc = prof[poc_i]
        while acc < total * VALUE_AREA and (lo_i > 0 or hi_i < BUCKETS - 1):
            left = prof[lo_i - 1] if lo_i > 0 else -1
            right = prof[hi_i + 1] if hi_i < BUCKETS - 1 else -1
            if right >= left:
                hi_i += 1; acc += prof[hi_i]
            else:
                lo_i -= 1; acc += prof[lo_i]

        top = sorted(range(BUCKETS), key=lambda i: -prof[i])[:TOP_LEVELS]
        price_of = lambda i: round(lo_all + (i + 0.5) * step, 2)
        pv = buy_vol + sell_vol
        out["symbols"][s] = {
            "low": round(lo_all, 2), "high": round(hi_all, 2),
            "poc": price_of(poc_i),
            "vah": price_of(hi_i), "val": price_of(lo_i),
            "levels": [[price_of(i), int(prof[i])] for i in sorted(top)],
            "buy_pct_est": round(buy_vol / pv * 100, 1) if pv else None,
            "sell_pct_est": round(sell_vol / pv * 100, 1) if pv else None,
            "bars": len(rows),
        }

    out["count"] = len(out["symbols"])
    out["note"] = ("Volume by price level for %d symbols in the %s session, built from one-minute "
                   "bars. POC is the busiest price, and the value area is the band holding %d%% "
                   "of the volume." % (out["count"], last, int(VALUE_AREA * 100)))
    out["cautions"] = {
        "no_order_book": ("Individual orders and market depth are paid exchange feeds. Free data "
                          "does not contain them, so nothing here shows who bought or how many "
                          "orders there were."),
        "pressure_is_an_estimate": ("buy_pct_est classifies each bar by close against open. A bar "
                                    "closing above its open is not proof that buyers drove it - "
                                    "it is a proxy, and it is labelled one."),
        "one_session": ("A profile describes one session. It is not a support level that lasts; "
                        "run it again tomorrow and the shape changes."),
        "volume_from_bars": ("Volume is spread evenly across the price range each bar touched, "
                             "which is more honest than assigning it all to the close but still "
                             "an approximation."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %s" % out["note"])
    for s in list(out["symbols"])[:5]:
        d = out["symbols"][s]
        print("     %-12s POC %8.2f  value area %8.2f - %8.2f  buy est %s%%"
              % (s, d["poc"], d["val"], d["vah"], d["buy_pct_est"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
