#!/usr/bin/env python3
"""
ARTHASAAR - one canonical snapshot for the home page.

THE PROBLEM THIS FIXES
The home page showed Nifty PCR 1.15 in one card and 1.072 in another, max pain
25,000 in one and 24,612 in another, and a forecast anchored to a price the index
left behind days ago. Every card was reading a different file with its own date,
so the numbers disagreed and nobody could tell which was current.

WHAT THIS DOES
Builds docs/home_facts.json: one session date, one value per fact, and the date
and source of each fact kept alongside it. Any fact that is older than the
session is marked stale, in the data, so the page can say so instead of quietly
mixing days.

Output
  { asof, stale[], facts: { nifty:{v,d,src}, vix:{...}, breadth:{...},
                            fii:{...}, dii:{...}, pcr:{...}, max_pain:{...} } }
"""
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


def load(name):
    p = DOCS / name
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def main():
    recap = load("recap.json") or {}
    oi = load("oi_by_expiry.json") or {}
    breadth = load("breadth.json") or {}
    fd = load("fii_dii.json") or {}

    facts, stale = {}, []

    # --- session date and the index itself, from the recap's own rows ---
    session = None
    nrows = (recap.get("nifty") or {}).get("rows") or []
    if nrows:
        last = nrows[-1]
        session = str(last[0])[:10]
        facts["nifty"] = {"v": last[4], "chg_pct": last[5], "d": session, "src": "recap.json (NSE/Yahoo closes)"}

    # --- VIX ---
    vix = recap.get("vix") or {}
    if vix.get("last") is not None:
        facts["vix"] = {"v": vix["last"], "chg_10d_pct": vix.get("change_10d_pct"),
                        "d": session, "src": "recap.json (Yahoo ^INDIAVIX)"}

    # --- breadth ---
    br = recap.get("breadth") or {}
    if not br and breadth:
        br = {"above_50": breadth.get("above_50"), "above_200": breadth.get("above_200"),
              "total": breadth.get("total")}
    if br:
        facts["breadth"] = {"v": br, "d": session, "src": "recap.json / breadth.json"}

    # --- FII / DII (these lag by a day; keep their own date) ---
    fdl = recap.get("fii_dii") or []
    if not fdl:
        fdl = [{"category": x.get("category"), "date": x.get("date"), "net_cr": x.get("net")}
               for x in (fd.get("latest") or [])]
    for row in fdl:
        cat = str(row.get("category") or "")
        raw = str(row.get("date") or "").strip()
        d = raw[:10]
        # normalise 09-Nov-2026 -> 2026-11-09 (parse BEFORE truncating)
        try:
            d = datetime.strptime(raw, "%d-%b-%Y").strftime("%Y-%m-%d")
        except Exception:  # noqa: BLE001
            pass
        if cat.startswith("FII"):
            facts["fii"] = {"v": row.get("net_cr"), "d": d, "src": "fii_dii.json (NSE provisional)"}
        elif cat.startswith("DII"):
            facts["dii"] = {"v": row.get("net_cr"), "d": d, "src": "fii_dii.json (NSE provisional)"}

    # --- options: nearest expiry only, never summed across expiries ---
    idx = (oi.get("indices") or {}).get("NIFTY") or {}
    exps = idx.get("expiries") or []
    if exps:
        e = exps[0]
        facts["pcr"] = {"v": e.get("pcr"), "d": oi.get("date"), "expiry": e.get("expiry"),
                        "src": "oi_by_expiry.json (NSE F&O bhavcopy, nearest expiry)"}
        facts["max_pain"] = {"v": e.get("max_pain"), "d": oi.get("date"), "expiry": e.get("expiry"),
                             "src": "oi_by_expiry.json (nearest expiry)"}
        facts["spot"] = {"v": idx.get("spot"), "d": oi.get("date"), "src": "oi_by_expiry.json"}

    if not session:
        print("no session date available - cannot build home facts")
        return 1

    for k, f in facts.items():
        if f.get("d") and f["d"] != session:
            stale.append({"fact": k, "has": f["d"], "session": session})

    # coverage: does the price data reach as far as the session list the gap checker uses?
    hist = load("history.json") or {}
    hrows = hist.get("rows") or []
    hist_last = None
    for r in reversed(hrows):
        if isinstance(r, dict):
            hist_last = str(r.get("d") or r.get("date") or "")[:10] or None
            if hist_last:
                break
    gaps = (load("data_gaps.json") or {}).get("gaps") or []
    coverage = {"recap_last": session, "history_last": hist_last,
                "missing_sessions": [g.get("date") for g in gaps if isinstance(g, dict)]}
    if hist_last and hist_last > session:
        coverage["behind"] = True

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "coverage": coverage,
        "asof": session,
        "stale": stale,
        "facts": facts,
        "note": ("One value per fact, each carrying its own date and source. Anything whose "
                 "date is older than the session is listed in stale, so the page can show it "
                 "rather than mixing days. PCR and max pain are the nearest expiry only - "
                 "never summed across expiries."),
    }
    DOCS.mkdir(exist_ok=True)
    (DOCS / "home_facts.json").write_text(json.dumps(out, separators=(",", ":")), encoding="utf-8")
    print(f"asof {session} | facts {len(facts)} | stale {len(stale)}")
    for s in stale:
        print(f"  STALE {s['fact']}: has {s['has']}, session {s['session']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
