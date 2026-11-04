#!/usr/bin/env python3
"""One story a day, built only from numbers we can trace.

WHAT THIS IS
A rule-based narrative generator. It looks at the day's data, finds the one thread worth
telling, and writes it in sentences with the actual figures attached. No model, no invented
facts, no claim that is not computed from docs/stocks.json and friends.

HOW IT PICKS THE THREAD
Four candidate stories are scored and the strongest wins:
  1. DIVERGENCE  a sector whose members moved far apart - the market is repricing something
  2. TREND       the strongest established trend (highest ADX) and what is against it
  3. CROSSING    stocks that just crossed their 200-day average, in either direction
  4. BREADTH     a one-sided day, when almost everything moved the same way

WHY RULES AND NOT A LANGUAGE MODEL
A model would write better prose and invent numbers doing it. Every figure below is read
from a file the pipeline produced, so a reader can check any sentence. The writing is plainer
than a YouTube explainer; the arithmetic is not.

WHAT IT CANNOT DO
It describes the market. It cannot say why Blinkit runs four store formats, because we hold
no segment, store-count or category-margin data. That is the other half of the job.
"""
import json, os, sys
from datetime import datetime, timezone

STOCKS = "docs/stocks.json"
OUT = "docs/story.json"
MIN_SECTOR_MEMBERS = 5
MCAP_FLOOR = 1000 * 1e7      # Rs 1,000 crore, so micro-caps cannot define a story


def load():
    try:
        return json.load(open(STOCKS)).get("stocks") or {}
    except Exception:
        return {}


def universe(raw):
    """Normalise into the fields the story needs, dropping anything incomplete."""
    out = []
    for k, v in raw.items():
        if v.get("close") is None or v.get("chg_pct") is None:
            continue
        t = v.get("tech") or {}
        out.append({
            "sym": v.get("symbol") or k,
            "name": v.get("name") or k,
            "sector": v.get("sector") or "Unclassified",
            "close": float(v["close"]),
            "chg": float(v["chg_pct"]),
            "rsi": t.get("rsi_14"),
            "adx": t.get("adx"),
            "sma200": t.get("sma_200"),
            "vol_ratio": t.get("vol_ratio") or t.get("volume_ratio"),
            "mcap": (v.get("fund") or {}).get("mcap"),
        })
    return out


def vs200(r):
    if not r.get("sma200") or not r.get("close"):
        return None
    return (r["close"] / r["sma200"] - 1) * 100


def pct(x):
    return ("+" if x > 0 else "") + ("%.2f" % x) + "%"


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "story": None, "alternatives": [], "note": ""}

    raw = load()
    uni = universe(raw)
    if not uni:
        out["note"] = "No stocks.json on disk."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("story: skipped (no data)")
        return 0

    movers = [r for r in uni if abs(r["chg"]) < 60]     # drop obvious bad ticks
    median_chg = sorted(r["chg"] for r in movers)[len(movers) // 2]
    fell = sum(1 for r in movers if r["chg"] < 0)

    # Stories about individual companies are restricted to those above the size floor with a
    # known market cap. Micro-caps produce ADX 99 and RSI 0 from a handful of one-way sessions
    # - real numbers, meaningless stories. Among the 1,310 stocks above the floor there were
    # zero implausible readings, so the floor fixes the data quality and the relevance at once.
    core = [r for r in movers
            if r.get("mcap") is not None and r["mcap"] >= MCAP_FLOOR
            and (r.get("rsi") is None or 1 < r["rsi"] < 99)
            and (r.get("adx") is None or r["adx"] <= 75)]

    candidates = []

    # ---- 1. divergence inside a sector ------------------------------------------------
    # Only companies of a meaningful size, and an interquartile spread rather than max-min.
    # max-min let two unrelated micro-caps define a whole sector's story: Spencer's (1,619 cr)
    # against Standard Industries (1,254 cr) read as a "47 point split" when neither is big
    # enough to matter. IQR ignores the tails; the size floor keeps the examples real.
    by_sec = {}
    for r in core:
        by_sec.setdefault(r["sector"], []).append(r)
    best_div = None
    for sec, members in by_sec.items():
        if len(members) < MIN_SECTOR_MEMBERS:
            continue
        ch = sorted(members, key=lambda r: r["chg"])
        n = len(ch)
        q1 = ch[n // 4]["chg"]
        q3 = ch[(3 * n) // 4]["chg"]
        spread = q3 - q1
        # examples from the right tail of the size distribution, not the extremes of price
        lower = [m for m in ch if m["chg"] <= q1] or [ch[0]]
        upper = [m for m in ch if m["chg"] >= q3] or [ch[-1]]
        big = lambda xs: max(xs, key=lambda m: (m.get("mcap") or 0))
        if best_div is None or spread > best_div["spread"]:
            best_div = {"sector": sec, "spread": spread, "n": n,
                        "weak": big(lower), "strong": big(upper),
                        "mean": sum(m["chg"] for m in members) / len(members)}
    if best_div and best_div["spread"] > 4:
        b = best_div
        w200, s200 = vs200(b["weak"]), vs200(b["strong"])
        text = ("<b>%s split %.2f points today, by the middle half of the sector.</b> "
                "%s fell %s while %s rose %s, against a sector average of %s. "
                % (b["sector"], b["spread"], b["weak"]["name"], pct(b["weak"]["chg"]),
                   b["strong"]["name"], pct(b["strong"]["chg"]), pct(b["mean"])))
        if w200 is not None and s200 is not None:
            text += ("The gap is not just today's: %s sits %s its 200-day average and %s sits %s. "
                     "One day moved them together; the year has moved them apart."
                     % (b["weak"]["name"], pct(w200), b["strong"]["name"], pct(s200)))
        candidates.append({"kind": "divergence", "score": b["spread"] * 1.2, "headline":
                           "%s split %.1f points" % (b["sector"], b["spread"]),
                           "text": text, "sector": b["sector"]})

    # ---- 2. the strongest established trend ------------------------------------------
    with_adx = [r for r in core if r.get("adx") is not None]
    if with_adx:
        top = max(with_adx, key=lambda r: r["adx"])
        falling = [r for r in with_adx if (vs200(r) or 0) < 0]
        if falling:
            worst = min(falling, key=lambda r: vs200(r) or 0)
            text = ("<b>%s has the strongest trend on the board</b> - ADX %s, RSI %s, %s its "
                    "200-day average. The steepest established downtrend belongs to %s at %s, "
                    "ADX %s. ADX measures trend strength, not direction: a high reading says "
                    "the move has been orderly, not that it will continue."
                    % (top["name"], round(top["adx"], 1), top.get("rsi"),
                       pct(vs200(top) or 0), worst["name"], pct(vs200(worst) or 0),
                       round(worst["adx"], 1)))
            candidates.append({"kind": "trend", "score": top["adx"] * 0.4,
                               "headline": "%s, ADX %.0f" % (worst["name"], worst["adx"]),
                               "text": text})

    # ---- 3. crossings of the 200-day average -----------------------------------------
    crossings = []
    for r in core:
        v = vs200(r)
        if v is None:
            continue
        if -1.5 < v < 1.5:          # sitting right on the line
            crossings.append(r)
    # only a story if a meaningful SHARE of the universe is at the line, not just a raw count
    cross_share = len(crossings) / max(1, len(core)) * 100
    if len(crossings) >= 5 and cross_share >= 8:
        names = ", ".join("%s (%s)" % (r["name"].split()[0], pct(r["chg"]))
                          for r in sorted(crossings, key=lambda r: -abs(r["chg"]))[:5])
        text = ("<b>%d stocks are sitting within 1.5%% of their 200-day average</b>, the line "
                "most funds use to separate an uptrend from a downtrend. Among the busiest: %s. "
                "A stock hovering on that line has no trend to follow yet."
                % (len(crossings), names))
        candidates.append({"kind": "crossing", "score": cross_share * 1.5,
                           "headline": "%d stocks at the 200-day line" % len(crossings),
                           "text": text})

    # ---- 4. a one-sided breadth day ---------------------------------------------------
    share = fell / len(movers) * 100
    if share > 75 or share < 25:
        direction = "fell" if share > 50 else "rose"
        # which sectors led it, and how broad it was inside them
        sec_stat = []
        for sec, members in by_sec.items():
            if len(members) < MIN_SECTOR_MEMBERS:
                continue
            down = sum(1 for m in members if m["chg"] < 0)
            sec_stat.append((sec, down / len(members) * 100,
                             sum(m["chg"] for m in members) / len(members), len(members)))
        sec_stat.sort(key=lambda x: x[1], reverse=(share > 50))
        detail = ""
        if sec_stat:
            worst = sec_stat[0]
            best = sec_stat[-1]
            detail = (" The most one-sided sector was %s: %d of %d names fell, averaging %s. "
                      "The least one-sided was %s at %s on average."
                      % (worst[0], round(worst[1] * worst[3] / 100), worst[3], pct(worst[2]),
                         best[0], pct(best[2])))
        text = ("<b>%d of %d stocks %s today</b> (%.0f%%), with the median stock at %s.%s "
                "A day this one-sided is about the whole market rather than any single "
                "company - stock-specific news rarely moves nine in ten names the same way."
                % (fell if share > 50 else len(movers) - fell, len(movers), direction,
                   share if share > 50 else 100 - share, pct(median_chg), detail))
        candidates.append({"kind": "breadth",
                           "score": abs(share - 50),
                           "headline": "%.0f%% moved the same way" % (share if share > 50 else 100 - share),
                           "text": text})

    if not candidates:
        out["note"] = "No story cleared the thresholds today - that is a quiet market, not an error."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("story: no thread today")
        return 0

    candidates.sort(key=lambda c: -c["score"])
    out["story"] = candidates[0]
    out["alternatives"] = [{"kind": c["kind"], "headline": c["headline"]} for c in candidates[1:4]]
    out["count"] = 1
    out["context"] = {"universe": len(movers), "median_chg": round(median_chg, 2),
                      "fell": fell, "rose": len(movers) - fell}
    out["note"] = ("Generated from rules over docs/stocks.json. Every figure is computed, none "
                   "is written by a model. It describes the market; it cannot explain a "
                   "company's business model, which needs segment and margin data we do not hold.")

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.1f KB" % (OUT, os.path.getsize(OUT) / 1024))
    print("   thread: %s" % out["story"]["kind"])
    print("   headline: %s" % out["story"]["headline"])
    print("   median %s, %d fell of %d" % (pct(median_chg), fell, len(movers)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
