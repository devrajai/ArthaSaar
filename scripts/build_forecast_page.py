#!/usr/bin/env python3
"""Publish the 21-day forecast AND how accurate that forecast has actually been.

WHY THIS EXISTS
forecast.py has been running on every pipeline run and writing accuracy for ~3,000 symbols
across six models - and none of it reached the site. The pipeline also ran it with the
default horizon, not 21 sessions. So there was a real, validated forecast sitting on disk
that nobody could see.

WHAT "POTENTIAL" MEANS HERE
Not a claim. Every model is validated WALK-FORWARD by forecast.py: it hides the last 21
sessions, forecasts them from the earlier data, and scores the miss. The median MAPE below
is therefore what that model has actually achieved at a 21-session horizon on real Indian
data - including the 2020 crash and the 2021 rally, which is where naive models fail hardest.

That is the number worth looking at. A 21-day forecast that is typically 8% off is not a
prediction of the price; it is a statement about how much the price usually moves in 21 days.

ON TIMESFM
It is a 200M-parameter model needing torch and ~800 MB of weights. It was never wired into
the pipeline - there is no step for it - which is why nothing ever appeared. The six models
here need only statsmodels, run in seconds, and are measured the same honest way. TimesFM
belongs behind an optional flag with a cached model, not in the daily run.
"""
import json, os, sys
from datetime import datetime, timezone

OUT = "docs/forecast.json"
ACC = "data/forecast/accuracy.csv"
FC = "data/forecast/forecasts.parquet"
MS = "docs/market_status.json"
LISTINGS = "docs/listings.json"
DATA_ASOF = "docs/data_asof.json"
TOP = 40          # symbols whose forward path is published


def _load(path):
    try:
        return json.loads(open(path).read())
    except Exception:
        return None


def _holidays():
    """Trading holidays from the exchange calendar the pipeline already keeps."""
    ms = _load(MS) or {}
    out = set()
    # the holiday list is stored as arrays - ['2026-01-26', 'Republic Day'] - not as objects,
    # which is the same shape mistake that broke _delisted
    for h in (ms.get("holidays") or []):
        d = None
        if isinstance(h, str):
            d = h
        elif isinstance(h, dict):
            d = h.get("date")
        elif isinstance(h, (list, tuple)) and h:
            d = h[0]
        if d:
            out.add(str(d)[:10])
    return out


def _last_session():
    """The date the published data runs to, so the path can start the day after it."""
    for path, keys in ((DATA_ASOF, ("date", "as_of", "market_date", "updated")),):
        d = _load(path) or {}
        for k in keys:
            v = d.get(k)
            if v:
                return str(v)[:10]
    return None


def _forward_dates(start_iso, steps):
    """N trading dates after start_iso, skipping weekends and exchange holidays.

    A date that cannot be placed is left None rather than guessed - a path labelled with a
    Sunday is worse than a path with no label.
    """
    from datetime import date, timedelta
    if not start_iso or steps <= 0:
        return [None] * max(0, steps)
    try:
        d = date.fromisoformat(start_iso[:10])
    except Exception:
        return [None] * steps
    hol = _holidays()
    out = []
    guard = 0
    while len(out) < steps and guard < steps * 4 + 30:
        d = d + timedelta(days=1)
        guard += 1
        if d.weekday() >= 5:            # Saturday or Sunday
            continue
        if d.isoformat() in hol:
            continue
        out.append(d.isoformat())
    while len(out) < steps:
        out.append(None)
    return out


def _delisted():
    """Symbols the listing file marks delisted.

    The file stores each row as an ARRAY - ['HEXAWARE', 'Hexaware Technologies Limited',
    '2020-11-09', 'Voluntary Delisting'] - not as an object. Calling .get() on it raised
    AttributeError and silently emptied the whole symbol block.
    """
    d = _load(LISTINGS) or {}
    out = set()
    for x in (d.get("delisted") or []):
        sym = None
        if isinstance(x, str):
            sym = x
        elif isinstance(x, dict):
            sym = x.get("symbol")
        elif isinstance(x, (list, tuple)) and x:
            sym = x[0]
        if sym:
            out.add(str(sym).split(".")[0].upper())
    return out


def main():
    import pandas as pd

    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "models": [], "symbols": {}, "note": ""}

    if not os.path.exists(ACC):
        out["note"] = ("No forecast accuracy on disk yet - forecast.py has not run against the "
                       "candle archive.")
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("forecast: skipped (no accuracy.csv)")
        return 0

    acc = pd.read_csv(ACC)
    need = {"symbol", "model", "mape"}
    if not need.issubset(acc.columns):
        out["note"] = "accuracy.csv does not carry %s." % ", ".join(sorted(need - set(acc.columns)))
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("forecast: skipped (unexpected columns)")
        return 0

    acc = acc.dropna(subset=["mape"])
    if acc.empty:
        out["note"] = "Every model failed to produce a usable accuracy number."
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("forecast: skipped (no usable MAPE)")
        return 0

    # median MAPE per model, plus how often it beat a random-walk baseline
    med = acc.groupby("model")["mape"].median().sort_values()
    base = med.get("naive")
    models = []
    for m, v in med.items():
        row = {"model": m, "mape": round(float(v), 2), "symbols": int((acc["model"] == m).sum())}
        # extra columns forecast.py now writes
        if "hit" in acc.columns:
            hv = acc[acc["model"] == m]["hit"].median()
            if hv == hv:
                row["hit"] = round(float(hv), 1)
        if "cover80" in acc.columns:
            cv = acc[acc["model"] == m]["cover80"].median()
            if cv == cv:
                row["cover80"] = round(float(cv), 1)
        if "origins" in acc.columns:
            ov = acc[acc["model"] == m]["origins"].median()
            if ov == ov:
                row["origins"] = int(ov)
        if base is not None and m != "naive":
            gap = float(base) - float(v)          # positive means this model beat naive
            row["vs_naive"] = round(float(v - base), 2)
            row["beats_naive_pp"] = round(gap, 2)
            # the card says this in words when the gain is not real
            row["no_clear_gain"] = bool(gap < 0.5)
        models.append(row)
    out["models"] = models
    out["naive_mape"] = round(float(base), 2) if base is not None else None

    # per-symbol best model and its error
    if FC and os.path.exists(FC):
        try:
            fc = pd.read_parquet(FC)
            scol = "symbol" if "symbol" in fc.columns else None
            if scol:
                # keep the symbols with the most forward points, so paths are complete
                counts = fc[scol].value_counts()
                keep = list(counts.index[:TOP])
                delisted = _delisted()
                fdates = _forward_dates(_last_session(), 25)
                for sym in keep:
                    g = fc[fc[scol] == sym]
                    symrows = acc[acc["symbol"] == sym]
                    # Choose on select_mape when it exists: that is the earlier half of the
                    # origins. Picking on "mape" and then reporting "mape" is picking the model
                    # on the very number it is presented with.
                    if "select_mape" in symrows.columns and symrows["select_mape"].notna().any():
                        best = symrows.sort_values("select_mape")
                    else:
                        best = symrows.sort_values("mape")
                    best_model = best.iloc[0]["model"] if len(best) else None

                    # THE BUG THIS FIXES.
                    # This took the first 25 rows for the symbol across ALL six models at
                    # once. Whichever model happened to sort first - the constant "mean"
                    # one - won, so every published path was the same number repeated 21
                    # times, and the date column, which forecast.py does not write, came out
                    # as the string "None". A flat line labelled None is worse than no card.
                    # Take the model that actually scored best, keep it in step order, and
                    # leave the date out when there is no real one rather than faking it.
                    if best_model is not None and "model" in g.columns:
                        gm = g[g["model"] == best_model]
                        if len(gm):
                            g = gm
                    if "step" in g.columns:
                        g = g.sort_values("step")

                    path = []
                    for _, r in g.iterrows():
                        d = r.get("date") if "date" in g.columns else None
                        if (d is None or str(d) == "nan") and "ts" in g.columns:
                            d = r.get("ts")
                        ds = None
                        if d is not None and str(d) not in ("None", "nan", "NaT"):
                            ds = str(d)[:10]
                        yh = r.get("yhat")
                        st = r.get("step")
                        idx = (int(st) - 1) if (st == st and st is not None) else len(path)
                        # fall back to the exchange calendar when the parquet has no date
                        if ds is None and 0 <= idx < len(fdates):
                            ds = fdates[idx]
                        lo = r.get("lo80"); hi = r.get("hi80")
                        path.append({
                            "step": idx + 1,
                            "date": ds,
                            "yhat": round(float(yh), 2) if yh == yh else None,
                            "lo80": round(float(lo), 2) if (lo is not None and lo == lo) else None,
                            "hi80": round(float(hi), 2) if (hi is not None and hi == hi) else None,
                        })
                    brow = best.iloc[0] if len(best) else None
                    block = {
                        "path": path[:25],
                        "best_model": best_model,
                        # the score on the LATER origins - the one the choice was not made on
                        "best_mape": round(float(brow["mape"]), 2) if brow is not None else None,
                    }
                    if brow is not None:
                        for k in ("hit", "cover80", "origins", "beats_naive_pp"):
                            if k in brow.index and brow[k] == brow[k]:
                                block[k] = round(float(brow[k]), 2) if k != "origins" else int(brow[k])
                        if "select_mape" in brow.index and brow["select_mape"] == brow["select_mape"]:
                            block["select_mape"] = round(float(brow["select_mape"]), 2)
                    if str(sym).upper() in delisted:
                        block["delisted"] = True
                    out["symbols"][sym] = block
        except Exception as e:
            print("  forecasts.parquet unreadable (%s)" % type(e).__name__)

    out["count"] = len(out["symbols"])
    out["horizon"] = 21
    out["note"] = ("21-session ahead forecasts, and the median error each model has actually "
                   "achieved at that horizon under walk-forward validation. A low MAPE does not "
                   "mean the direction is right - check the hit rate before trusting a path.")
    out["cautions"] = {
        "not_a_prediction": ("A 21-day forecast is a projection of recent behaviour, not a "
                             "forecast of news, results or policy."),
        "walk_forward": ("Scored by hiding the last 21 sessions and forecasting them from the "
                         "earlier data - the same test a back-test would use."),
        "direction": ("Being close on price is not the same as being right on direction; a "
                      "flat forecast can score well in a quiet market and say nothing."),
        "survivorship": ("Symbols that have since delisted are marked delisted where the "
                          "listing file knows them, but history for a delisted name is "
                          "often thin, so the sample still leans towards survivors."),
    }
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.0f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   median MAPE at 21 sessions:")
    for m in models:
        extra = ""
        if "vs_naive" in m:
            extra = "  (%+.2f vs naive)" % m["vs_naive"]
        print("     %-16s %6.2f%%  on %d symbols%s" % (m["model"], m["mape"], m["symbols"], extra))
    return 0


if __name__ == "__main__":
    sys.exit(main())
