#!/usr/bin/env python3
"""Strike-wise open interest for Nifty and Bank Nifty.

WHY
The site had max pain and a put-call ratio - single numbers that summarise the whole option
chain. What a trader actually looks at is the SHAPE: where the call walls and put walls sit.
A large call OI at 23,000 and a large put OI at 22,500 says something max pain cannot.

Output: docs/oi_strikes.json - per index, per expiry, call and put OI at every strike, plus
the walls and the PCR. Small: a few hundred strikes.

COLUMN NAMES
NSE renames F&O columns from time to time, so every lookup goes through pick(), which matches
on substrings. That keeps this working when 'OpnIntrst' becomes 'OpenInterest'.
"""
import glob, json, os, sys
from datetime import datetime, timezone

OUT = "docs/oi_strikes.json"
INDICES = ("NIFTY", "BANKNIFTY")
TOP_N = 14          # strikes either side of spot to publish (a readable band, not the whole chain)


def pick(df, *cands):
    """First column whose name matches any candidate, case/space-insensitively."""
    norm = {c.lower().replace(" ", "").replace("_", ""): c for c in df.columns}
    for cand in cands:
        k = cand.lower().replace(" ", "").replace("_", "")
        if k in norm:
            return norm[k]
    return None


def load_latest():
    for pat in ("data/parquet/fo/fo_*.parquet", "data/csv/fo/fo_*.csv"):
        files = sorted(glob.glob(pat))
        if not files:
            continue
        path = files[-1]
        try:
            if path.endswith(".parquet"):
                import pandas as pd
                return pd.read_parquet(path), path
            import pandas as pd
            return pd.read_csv(path, dtype=str), path
        except Exception as e:
            print("  could not read %s (%s)" % (path, type(e).__name__))
    return None, None


def main():
    import pandas as pd

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "indices": {}, "note": ""}

    df, path = load_latest()
    if df is None or df.empty:
        out["note"] = "No F&O bhavcopy on disk, so no strike-wise open interest is published."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("oi strikes: skipped (no F&O file)")
        return 0
    print("  source:", path, len(df), "rows")

    c_sym = pick(df, "TckrSymb", "Symbol")
    c_typ = pick(df, "FinInstrmTp", "Instrument")
    c_str = pick(df, "StrkPric", "StrikePrice", "Strike")
    c_opt = pick(df, "OptnTp", "OptionType")
    c_oi = pick(df, "OpnIntrst", "OpenInterest")
    c_chg = pick(df, "ChngInOpnIntrst", "ChangeinOpenInterest")
    c_exp = pick(df, "XpryDt", "ExpiryDate", "Expiry")
    c_px = pick(df, "UndrlygPric", "UnderlyingPrice", "ClsPric", "ClosePrice")

    missing = [n for n, c in (("symbol", c_sym), ("strike", c_str), ("option type", c_opt),
                              ("open interest", c_oi)) if not c]
    if missing:
        out["note"] = ("The F&O file does not carry %s - NSE may have changed the format."
                       % ", ".join(missing))
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("oi strikes: skipped (%s)" % out["note"])
        return 0

    # Keep only the columns actually used. The bhavcopy carries ~30 columns, and holding all
    # of them through the groupby ran the sandbox out of memory on a 41k-row file.
    keep = [c for c in (c_sym, c_typ, c_str, c_opt, c_oi, c_chg, c_exp, c_px) if c]
    df = df[keep].copy()
    df[c_sym] = df[c_sym].astype(str).str.strip().str.upper()
    df[c_opt] = df[c_opt].astype(str).str.strip().str.upper()
    df[c_str] = pd.to_numeric(df[c_str], errors="coerce")
    df[c_oi] = pd.to_numeric(df[c_oi], errors="coerce")
    if c_chg:
        df[c_chg] = pd.to_numeric(df[c_chg], errors="coerce")

    # Options only, and only the two indices.
    #
    # NOT filtered on FinInstrmTp: NSE codes index options as "IDO" and stock options as
    # "STO" - neither contains "OPT", so a contains("OPT") test silently matched nothing.
    # Filtering on OptnTp in (CE, PE) plus the symbol is unambiguous anyway: no listed stock
    # is called NIFTY or BANKNIFTY.
    df = df[df[c_opt].isin(["CE", "PE"]) & df[c_str].notna() & df[c_oi].notna()]
    df = df[df[c_sym].isin(INDICES)]

    if df.empty:
        out["note"] = ("The F&O file has no Nifty or Bank Nifty option rows - it may be a "
                       "day the file did not include index options.")
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("oi strikes: skipped (no index options in the file)")
        return 0

    for sym in INDICES:
        sub = df[df[c_sym] == sym]
        if sub.empty:
            continue

        # nearest expiry only - that is the one people watch
        expiries = sorted(sub[c_exp].astype(str).unique()) if c_exp else ["—"]
        exp = expiries[0] if expiries else "—"
        if c_exp:
            sub = sub[sub[c_exp].astype(str) == exp]

        ce = sub[sub[c_opt] == "CE"].groupby(c_str)[c_oi].sum()
        pe = sub[sub[c_opt] == "PE"].groupby(c_str)[c_oi].sum()
        chg_ce = sub[sub[c_opt] == "CE"].groupby(c_str)[c_chg].sum() if c_chg else None
        chg_pe = sub[sub[c_opt] == "PE"].groupby(c_str)[c_chg].sum() if c_chg else None

        strikes = sorted(set(ce.index) | set(pe.index))
        spot = None
        if c_px:
            try:
                spot = float(pd.to_numeric(sub[c_px], errors="coerce").dropna().iloc[0])
            except Exception:
                spot = None

        # centre the window on spot when we know it, otherwise on the biggest total OI
        if spot:
            strikes = sorted(strikes, key=lambda k: abs(k - spot))[: TOP_N * 2]
            strikes = sorted(strikes)
        else:
            tot = ce.add(pe, fill_value=0)
            strikes = sorted(tot.sort_values(ascending=False).index[: TOP_N * 2])

        rows = []
        for k in strikes:
            rows.append({
                "strike": float(k),
                "ce_oi": int(ce.get(k, 0)),
                "pe_oi": int(pe.get(k, 0)),
                "ce_chg": int(chg_ce.get(k, 0)) if chg_ce is not None else None,
                "pe_chg": int(chg_pe.get(k, 0)) if chg_pe is not None else None,
            })

        total_ce = int(ce.sum())
        total_pe = int(pe.sum())
        pcr = round(total_pe / total_ce, 2) if total_ce else None

        # the walls: the strikes carrying the most OI on each side
        call_wall = max(rows, key=lambda r: r["ce_oi"]) if rows else None
        put_wall = max(rows, key=lambda r: r["pe_oi"]) if rows else None

        out["indices"][sym] = {
            "expiry": exp,
            "spot": round(spot, 2) if spot else None,
            "pcr": pcr,
            "total_ce_oi": total_ce,
            "total_pe_oi": total_pe,
            "call_wall": call_wall["strike"] if call_wall else None,
            "put_wall": put_wall["strike"] if put_wall else None,
            "strikes": rows,
        }
        print("  %-10s expiry %s | spot %s | PCR %s | call wall %s | put wall %s | %d strikes"
              % (sym, exp, out["indices"][sym]["spot"], pcr,
                 out["indices"][sym]["call_wall"], out["indices"][sym]["put_wall"], len(rows)))

    out["count"] = len(out["indices"])
    out["note"] = ("Call and put open interest at every strike near the money, for the nearest "
                   "expiry. A big call wall above spot is where sellers expect resistance; a "
                   "big put wall below is where they expect support. It is positioning, not "
                   "prediction.")
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.0f KB" % (OUT, os.path.getsize(OUT) / 1024))
    return 0


if __name__ == "__main__":
    sys.exit(main())
