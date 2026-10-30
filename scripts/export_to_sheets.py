#!/usr/bin/env python3
"""Push every published dataset into one Google Sheet, one tab per dataset.

WHY A SHEET AS WELL AS JSON
The site reads small JSON files, which is right for a web page. A sheet is right for a
different job: sorting, filtering, pivot tables, sharing with family who will not open a
GitHub repo, and keeping a copy that survives the repo being deleted.

WHAT IT NEEDS
A service account with the Sheet shared to it as Editor:
  GOOGLE_SA_JSON          - the whole service-account JSON, as a secret
  ARTHASAAR_SHEET_ID      - the spreadsheet id from the URL
Without both, this exits quietly and the rest of the pipeline is unaffected.

IDEMPOTENT
Each run clears the tab and rewrites it, so you never get yesterday's rows left below
today's. It does not create the spreadsheet - that is a one-time manual step, because
creating shared documents from CI is a permission surface nobody needs.

USAGE
  python scripts/export_to_sheets.py
  python scripts/export_to_sheets.py --dry-run     # build the tabs, write nothing
"""
import argparse, json, os, sys
from pathlib import Path

DOCS = Path("docs")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def load(name):
    p = DOCS / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def rows_of(obj, keys):
    """dict list -> [header] + rows, keeping only the keys that exist."""
    if not obj:
        return None
    present = [k for k in keys if k in obj[0]]
    if not present:
        return None
    return [present] + [[r.get(k) for k in present] for r in obj]


def build_tabs():
    """Every tab as a list of rows. Header row first."""
    tabs = {}

    # OI history - the most valuable set, back to 2019
    oh = load("oi_history.json") or {}
    ser = oh.get("series") or []
    if ser:
        tabs["OI_history"] = ([["date", "index", "pcr", "spot", "oi_proxy_spot"]]
                              + [[r.get("d"), r.get("i"), r.get("p"), r.get("s"), r.get("x")]
                                 for r in ser])

    # stocks
    st = (load("stocks.json") or {}).get("stocks") or {}
    if st:
        rows = [["symbol", "name", "sector", "close", "chg_pct", "rsi_14",
                 "trend", "pe", "mcap", "div_yield"]]
        for v in st.values():
            t = v.get("tech") or {}
            f = v.get("fund") or {}
            rows.append([v.get("symbol"), v.get("name"), v.get("sector"), v.get("close"),
                         v.get("chg_pct"), t.get("rsi_14"), t.get("trend"),
                         f.get("pe"), f.get("mcap"), f.get("div_yield")])
        tabs["Stocks"] = rows

    # seasonality: symbol + years + 12 monthly averages
    sea = (load("seasonality.json") or {}).get("rows") or []
    if sea:
        rows = [["symbol", "years"] + MONTHS]
        for r in sea:
            m = r.get("months") or []
            rows.append([r.get("symbol"), r.get("years")]
                        + [(m[i] if i < len(m) else None) for i in range(12)])
        tabs["Seasonality"] = rows

    # report cards
    tabs["Report_cards"] = rows_of(
        (load("report_cards.json") or {}).get("cards"),
        ["symbol", "vol_pct", "max_drawdown_pct", "worst_day_pct", "years_up",
         "years_total", "best_month", "worst_month", "beta"])

    # correlation, long form - a matrix is useless in a sheet
    co = load("correlation.json") or {}
    syms, mat = co.get("symbols") or [], co.get("matrix") or []
    if syms and mat:
        rows = [["symbol_a", "symbol_b", "correlation"]]
        for i in range(len(syms)):
            for j in range(i + 1, len(syms)):
                try:
                    v = mat[i][j]
                except Exception:
                    continue
                if v is not None:
                    rows.append([syms[i], syms[j], round(float(v), 4)])
        tabs["Correlation"] = rows

    tabs["Mutual_funds"] = rows_of(
        (load("mf.json") or {}).get("rows"),
        ["code", "name", "fund_house", "category", "type", "nav", "nav_date",
         "years", "r1y", "r3y", "r5y"])

    tabs["ETF_premium"] = rows_of(
        (load("etf_premium.json") or {}).get("rows"),
        ["symbol", "name", "close", "scheme_code"])

    lv = (load("levels.json") or {}).get("rows") or []
    if lv:
        keys = list(lv[0].keys())
        tabs["Levels"] = [keys] + [[r.get(k) for k in keys] for r in lv]

    # volume structure (GTI) is a dict keyed by symbol
    g = (load("gti.json") or {}).get("stocks") or {}
    if g:
        keys = ["close", "poc_daily", "poc_weekly", "vah", "val", "supply", "demand",
                "ad_slope", "ad_state", "ret20", "vol20"]
        rows = [["symbol"] + keys]
        for sym, v in g.items():
            rows.append([sym] + [v.get(k) for k in keys])
        tabs["Volume_structure"] = rows

    # FII/DII
    fii = (load("fii_dii.json") or {}).get("history") or []
    if fii:
        tabs["FII_DII"] = ([["date", "fii_net_cr", "dii_net_cr"]]
                           + [[h.get("date"), h.get("fii"), h.get("dii")] for h in fii])

    # IPOs
    ipo = load("ipo.json") or {}
    rows = [["bucket", "name", "symbol", "open", "close", "status", "price"]]
    for bucket in ("open", "upcoming", "closed", "listed"):
        for r in (ipo.get(bucket) or []):
            rows.append([bucket, r.get("name"), r.get("symbol"), r.get("open"),
                         r.get("close"), r.get("status"), r.get("price")])
    if len(rows) > 1:
        tabs["IPOs"] = rows

    # the two option studies, flattened
    os_ = load("oi_stats.json") or {}
    rows = [["index", "bucket", "horizon_days", "avg_forward_pct", "cases"]]
    for idx, s in (os_.get("pcr_extremes") or {}).items():
        for b in ("baseline", "low", "high"):
            for h in ("1", "5", "20"):
                v = (s.get(b) or {}).get(h)
                if v and v[0] is not None:
                    rows.append([idx, b, int(h), v[0], v[1]])
    if len(rows) > 1:
        tabs["PCR_extremes"] = rows

    wl = load("oi_walls.json") or {}
    rows = [["index", "wall_move", "horizon_days", "avg_forward_pct", "cases"]]
    for idx, s in (wl.get("wall_shifts") or {}).items():
        for b in ("baseline", "call_wall_down", "call_wall_up", "put_wall_up", "put_wall_down"):
            for h in ("1", "5", "20"):
                v = (s.get(b) or {}).get(h)
                if v and v[0] is not None:
                    rows.append([idx, b, int(h), v[0], v[1]])
    if len(rows) > 1:
        tabs["OI_walls"] = rows

    return {k: v for k, v in tabs.items() if v and len(v) > 1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    tabs = build_tabs()
    print("tabs built: %d" % len(tabs))
    for k, v in sorted(tabs.items()):
        print("  %-18s %6d rows x %d cols" % (k, len(v), len(v[0])))

    if args.dry_run:
        return 0

    sid = os.environ.get("ARTHASAAR_SHEET_ID", "").strip()
    sa = os.environ.get("GOOGLE_SA_JSON", "").strip()
    if not sid or not sa:
        print("sheets: skipped - ARTHASAAR_SHEET_ID and GOOGLE_SA_JSON must both be set")
        return 0

    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        print("sheets: skipped - gspread not installed")
        return 0

    creds = Credentials.from_service_account_info(
        json.loads(sa),
        scopes=["https://www.googleapis.com/auth/spreadsheets"])
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sid)

    existing = {w.title for w in sh.worksheets()}
    for name, rows in sorted(tabs.items()):
        ws = sh.worksheet(name) if name in existing else sh.add_worksheet(
            title=name, rows=max(len(rows) + 10, 100), cols=len(rows[0]) + 2)
        # clear first, so yesterday's longer table does not leave rows below today's
        ws.clear()
        ws.update(rows, value_input_option="RAW")
        print("  %-18s %6d rows" % (name, len(rows)))

    print("sheets: done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
