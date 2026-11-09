#!/usr/bin/env python3
"""Self-audit: what each signal has actually done, and what is still unproven.

WHY THIS PAGE EXISTS
The site publishes an early-warning score, a forecast band, range breakers, a PCR reading and
a deal radar. Each one states a probability or a claim. None of them, until this page, said
whether it had ever been right.

A competitor can copy the code in a week. They cannot copy a record of timestamped calls scored
against what happened. This is the only asset here that compounds, and the only one that
protects the reader from a signal that has quietly stopped working.

TWO KINDS OF EVIDENCE, KEPT APART
  forward     a call logged BEFORE the outcome, then settled. This is a track record.
  historical  a rule tested over past data in one pass. This is a backtest.

They are not the same thing and are never added together. A backtest says a rule would have
worked on data the author could see. A track record says it worked on data nobody had seen. The
first is cheap; the second is the point.

WHAT IT REFUSES TO DO
Call anything "proven" below a stated number of settled cases. A 3-of-3 hit rate is not an
edge, and a page that reports 100% on three calls teaches the reader to trust noise.
"""
import json, os, sys
from datetime import datetime, timezone

OUT = "docs/audit.json"
READABLE_AT = 100       # settled cases before a forward record is called measurable
EARLY_AT = 20           # below this it is noise, not a signal


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def status(settled):
    if settled == 0:
        return "collecting", "no outcome has settled yet - there is no evidence either way"
    if settled < EARLY_AT:
        return "too early", ("%d settled calls. Below %d this is noise: a short run of hits "
                             "cannot be told apart from luck." % (settled, EARLY_AT))
    if settled < READABLE_AT:
        return "early signal", ("%d settled. Enough to watch, not enough to rely on - %d more "
                                "before it is called measurable." % (settled, READABLE_AT - settled))
    return "measurable", "%d settled calls - enough to read." % settled


def main():
    out = {"updated": now(), "forward": [], "historical": [],
           "readable_at": READABLE_AT, "note": "", "cautions": {}}

    # ---------------------------------------------------------------- forward records
    sc = load("docs/scorecard.json")
    if sc:
        settled = sc.get("scored") or 0
        st, why = status(settled)
        slices = sc.get("slices") or []
        flagged = next((s for s in slices if "flagged" in str(s.get("label", ""))), None)
        base = sc.get("base_rate_pct")
        out["forward"].append({
            "signal": "Early warning of a big move",
            "what": "Flags sessions likely to be large, in either direction.",
            "logged": sc.get("logged"), "settled": settled,
            "hit_pct": (flagged or {}).get("hit_pct"),
            "baseline_pct": base,
            "lift": (flagged or {}).get("lift"),
            "status": st, "why": why,
        })

    ts = load("docs/timesfm_score.json")
    if ts:
        settled = ts.get("scored") or 0
        st, why = status(settled)
        ov = ts.get("overall") or {}
        out["forward"].append({
            "signal": "TimesFM 10-90 band",
            "what": "Whether the forecast band contains the share of outcomes it should.",
            "logged": ts.get("runs_logged"), "settled": settled,
            "hit_pct": ov.get("inside_pct"), "baseline_pct": 80.0,
            "lift": None, "status": st, "why": why,
        })

    br = load("docs/breakers.json")
    if br:
        settled = br.get("settled") or 0
        st, why = status(settled)
        out["forward"].append({
            "signal": "Range breakers",
            "what": "Stocks closing outside the band the model gave them.",
            "logged": br.get("runs"), "settled": settled,
            "hit_pct": br.get("coverage_pct"), "baseline_pct": br.get("target_pct"),
            "lift": None, "status": st, "why": why,
        })

    # ---------------------------------------------------------------- historical studies
    em = load("docs/earlymove.json")
    if em:
        lift = em.get("lift") or []
        top = next((x for x in lift if x.get("top_pct") == 5), None)
        if top:
            out["historical"].append({
                "study": "Early warning, tested on 10 years",
                "cases": em.get("sessions"),
                "finding": ("The top 5% of scores preceded a big move %.1f%% of the time, "
                            "against a %.1f%% base rate - a %.1fx lift."
                            % (top.get("big_day_rate_pct", 0), em.get("base_rate_pct", 0),
                               top.get("lift", 0))),
                "caveat": "A backtest on data the rule was built from. It is the reason to watch the signal, not evidence that it works live.",
            })

    ps = load("docs/pcr_signal.json")
    if ps:
        bands = ps.get("bands") or []
        base = (ps.get("baseline") or {}).get("21") or {}
        best = None
        for b in bands:
            for hh in (b.get("horizons") or []):
                if hh.get("h") == 21 and hh.get("edge") == "better than baseline":
                    best = (b.get("band"), hh)
        if best:
            out["historical"].append({
                "study": "PCR bands, tested on 7 years",
                "cases": base.get("n"),
                "finding": ("Only the %s band beat the baseline: %.2f%% average over 21 sessions "
                            "against %.2f%%, up in %.1f%% of cases against %.1f%%."
                            % (best[0], best[1].get("mean_pct", 0), base.get("mean", 0),
                               best[1].get("up_pct", 0), base.get("up_pct", 0))),
                "caveat": "Every other PCR band did worse than the baseline, so the folk reading of PCR is mostly wrong on this data.",
            })
        elif base:
            out["historical"].append({
                "study": "PCR bands, tested on 7 years",
                "cases": base.get("n"),
                "finding": "No PCR band beat the baseline over 21 sessions.",
                "caveat": "The contrarian reading of PCR did not hold on this data.",
            })

    ll = load("docs/leadlag.json")
    if ll:
        cors = ll.get("correlations") or []
        sp = next((c for c in cors if "S&P" in str(c.get("label", ""))), None)
        if sp:
            out["historical"].append({
                "study": "US to India lead-lag",
                "cases": sp.get("n"),
                "finding": ("The prior S&P session correlates %.3f with Nifty's next one, "
                            "explaining %.1f%% of it." % (sp.get("corr", 0), sp.get("r2_pct", 0))),
                "caveat": "Weak on an average day. The relationship only sharpens in the tails.",
            })

    n_fwd = len(out["forward"])
    settled_total = sum((f.get("settled") or 0) for f in out["forward"])
    out["summary"] = {
        "signals_forward": n_fwd,
        "settled_total": settled_total,
        "readable": sum(1 for f in out["forward"] if f.get("status") == "measurable"),
        "historical_studies": len(out["historical"]),
    }
    out["note"] = (
        "%d signals are being scored forward, with %d settled calls between them. %d are "
        "readable yet. %d more are backtested studies, which are kept separate because a "
        "backtest is not a track record."
        % (n_fwd, settled_total,
           out["summary"]["readable"], len(out["historical"])))

    out["cautions"] = {
        "not_proven": ("Nothing on this page is called proven below %d settled calls. A short "
                       "run of hits cannot be told apart from luck." % READABLE_AT),
        "backtest_is_not_record": ("A backtest tests a rule on data its author could see. A "
                                   "track record tests it on data nobody had seen. Only the "
                                   "second is evidence, and the two are never added together."),
        "misses_count": ("A hit rate is published with the misses it implies. A page showing "
                         "only the winners is an advertisement."),
        "no_advice": "This is a record of measurement, not a recommendation.",
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   %s" % out["note"])
    print()
    print("   FORWARD (scored against what happened):")
    for f in out["forward"]:
        hit = "—" if f.get("hit_pct") is None else "%.1f%%" % f["hit_pct"]
        base = "—" if f.get("baseline_pct") is None else "%.1f%%" % f["baseline_pct"]
        print("     %-32s %-12s settled %-5s hit %-7s base %s"
              % (f["signal"], f["status"], f.get("settled"), hit, base))
    print()
    print("   HISTORICAL (backtests, not records):")
    for s in out["historical"]:
        print("     %-32s %s cases" % (s["study"], s.get("cases")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
