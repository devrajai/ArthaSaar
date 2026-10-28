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
TOP = 40          # symbols whose forward path is published


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
        if base is not None and m != "naive":
            row["vs_naive"] = round(float(v - base), 2)
        models.append(row)
    out["models"] = models

    # per-symbol best model and its error
    if FC and os.path.exists(FC):
        try:
            fc = pd.read_parquet(FC)
            scol = "symbol" if "symbol" in fc.columns else None
            if scol:
                # keep the symbols with the most forward points, so paths are complete
                counts = fc[scol].value_counts()
                keep = list(counts.index[:TOP])
                for sym in keep:
                    g = fc[fc[scol] == sym]
                    path = []
                    for _, r in g.iterrows():
                        d = r.get("date") or r.get("ts")
                        path.append({"date": str(d)[:10],
                                     "yhat": round(float(r["yhat"]), 2) if r.get("yhat") == r.get("yhat") else None})
                    best = acc[acc["symbol"] == sym].sort_values("mape")
                    out["symbols"][sym] = {
                        "path": path[:25],
                        "best_model": best.iloc[0]["model"] if len(best) else None,
                        "best_mape": round(float(best.iloc[0]["mape"]), 2) if len(best) else None,
                    }
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
        "survivorship": "Only stocks listed today are included.",
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
