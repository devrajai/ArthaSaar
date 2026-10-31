#!/usr/bin/env python3
"""Before you buy: a research checklist that answers what our data can, and says so when it cannot.

Built from Brian Feroldi's "How to Research a Stock" flow: understand the business, read the
statements, check the ratios, weigh the risks, value it. Plus the technical checks from the
standard textbook - moving averages, MACD, relative strength.

THE HONEST SPLIT, which is the whole point
Of the checks that matter, our data can answer about a dozen. It cannot answer net margin,
debt, free cash flow, revenue growth or promoter holding - those live in the annual report,
and no free price feed carries them. Rather than inventing a number or quietly dropping the
check, every unanswered question is listed with what to look for and where.

A checklist that silently omits the hardest questions is worse than no checklist, because it
looks complete.
"""
import json, os, sys
from datetime import datetime, timezone

STOCKS = "docs/stocks.json"
CARDS = "docs/report_cards.json"
WHATIF = "docs/whatif.json"
SECTORS = "docs/sectors.json"
BAN = "docs/fo_ban.json"
OUT = "docs/checklist.json"

# Feroldi's bars, kept as inputs rather than buried constants
ROE_MIN = 15.0
NET_MARGIN_MIN = 10.0

# Checks we genuinely cannot answer from price data, with what to look for instead.
CANNOT = [
    {"k": "Net profit margin", "want": "above 10%",
     "where": "Annual report - Profit & Loss statement. Net profit divided by revenue."},
    {"k": "Debt to equity", "want": "below 1 for most businesses",
     "where": "Annual report - Balance sheet. Borrowings divided by shareholders' funds."},
    {"k": "Free cash flow", "want": "positive and growing",
     "where": "Annual report - Cash flow statement. Operating cash flow minus capex."},
    {"k": "Revenue growth", "want": "consistent, not one good year",
     "where": "Annual report - five-year P&L. Look at the trend, not the latest number."},
    {"k": "Promoter holding and pledging", "want": "stable, nothing pledged",
     "where": "Shareholding pattern filed with the exchanges each quarter."},
    {"k": "Concentration risk", "want": "no single customer or product dominating",
     "where": "Annual report - segment note and management discussion."},
    {"k": "Competitive advantage", "want": "something a rival cannot copy quickly",
     "where": "Your own reading. If you cannot say it in one sentence, that is the answer."},
    {"k": "Management quality", "want": "honest, competent, owns shares",
     "where": "Conference call transcripts and past guidance versus delivery."},
]


def verdict_roe(v):
    if v is None:
        return "unknown"
    if v >= ROE_MIN:
        return "pass"
    if v >= 10:
        return "watch"
    return "fail"


def verdict_pe(pe, sector_pe):
    if pe is None or pe <= 0:
        return "unknown"
    if sector_pe and sector_pe > 0:
        ratio = pe / sector_pe
        if ratio <= 0.9:
            return "pass"
        if ratio <= 1.3:
            return "watch"
        return "fail"
    return "watch"


def main():
    out = {"updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "count": 0, "stocks": {}, "cannot_answer": CANNOT, "note": ""}

    if not os.path.exists(STOCKS):
        out["note"] = "No stocks.json on disk."
        os.makedirs("docs", exist_ok=True)
        json.dump(out, open(OUT, "w"), ensure_ascii=False)
        print("checklist: skipped (no stocks.json)")
        return 0

    stocks = (json.load(open(STOCKS)).get("stocks") or {})
    cards = {}
    if os.path.exists(CARDS):
        for c in (json.load(open(CARDS)).get("cards") or []):
            if c.get("symbol"):
                cards[c["symbol"]] = c
    dd = {}
    if os.path.exists(WHATIF):
        dd = (json.load(open(WHATIF)).get("drawdowns") or {})
    banned = set()
    if os.path.exists(BAN):
        b = json.load(open(BAN))
        for r in (b.get("rows") or b.get("banned") or []):
            if isinstance(r, str):
                banned.add(r)
            elif isinstance(r, dict) and r.get("symbol"):
                banned.add(r["symbol"])
    # sector medians, if we can get them
    sec_pe = {}
    if os.path.exists(SECTORS):
        s = json.load(open(SECTORS))
        for r in (s.get("rows") or []):
            if isinstance(r, dict) and r.get("sector"):
                v = r.get("median_pe") or r.get("pe")
                if v:
                    sec_pe[r["sector"]] = float(v)

    print("  %d stocks, %d report cards, %d drawdowns, %d banned, %d sector PEs"
          % (len(stocks), len(cards), len(dd), len(banned), len(sec_pe)))

    answered = total = 0
    for key, v in stocks.items():
        sym = v.get("symbol") or key.replace(".NS", "")
        tech = v.get("tech") or {}
        fund = v.get("fund") or {}
        card = cards.get(sym) or cards.get(key) or {}
        checks = []

        # Notes are stored ONCE in out["notes"], keyed by check name. Repeating the same
        # sentence on 2,209 stocks made this file 2.4 MB for no information gain.
        # `extra` is only for genuinely per-stock detail (dates, rupee figures).
        def add(name, value, verdict, extra=""):
            c = {"k": name, "v": value, "verdict": verdict}
            if extra:
                c["x"] = extra
            checks.append(c)

        # --- what we CAN answer ---
        roe = fund.get("roe")
        add("Return on equity", ("%.1f%%" % roe) if roe is not None else None,
            verdict_roe(roe),
            "" if roe is not None else "not in our feed for this stock")

        pe = fund.get("pe")
        add("Price to earnings", ("%.1f" % pe) if pe else None,
            verdict_pe(pe, sec_pe.get(v.get("sector"))),
            ("vs sector median %.1f" % sec_pe[v["sector"]]) if v.get("sector") in sec_pe else "")

        pb = fund.get("pb")
        if pb:
            add("Price to book", "%.2f" % pb, "watch")

        dy = fund.get("div_yield")
        if dy is not None:
            add("Dividend yield", "%.2f%%" % dy, "pass" if dy >= 1 else "watch")

        hi, lo, close = fund.get("high_52w"), fund.get("low_52w"), v.get("close")
        if hi and close:
            off = (close / hi - 1) * 100
            add("Distance from 52-week high", "%.1f%%" % off,
                "pass" if off > -15 else ("watch" if off > -30 else "fail"))

        d = dd.get(sym) or dd.get(key)
        if d:
            add("Worst past fall", "%.1f%%" % d["pct"],
                "fail" if d["pct"] < -50 else ("watch" if d["pct"] < -30 else "pass"),
                "%s to %s; Rs 1,00,000 became Rs %s" % (d["from"], d["to"],
                                                       format(d["lakh_becomes"], ",")))

        if card.get("vol_pct") is not None:
            add("Volatility", "%.1f%%" % card["vol_pct"],
                "pass" if card["vol_pct"] < 30 else ("watch" if card["vol_pct"] < 45 else "fail"))

        trend = tech.get("trend")
        if trend:
            add("Trend", str(trend), "pass" if trend == "up" else
                ("watch" if trend == "mixed" else "fail"))

        rsi = tech.get("rsi_14")
        if rsi is not None:
            add("RSI (14)", "%.0f" % rsi,
                "watch" if rsi > 70 or rsi < 30 else "pass")

        macd = tech.get("macd_hist")
        if macd is not None:
            add("MACD histogram", "%.2f" % macd, "pass" if macd > 0 else "fail")

        sma200 = tech.get("sma_200")
        if sma200 and close:
            add("Price vs 200-day average",
                "%.1f%%" % ((close / sma200 - 1) * 100),
                "pass" if close > sma200 else "fail")

        if sym in banned:
            add("F&O ban list", "banned", "fail")
        elif banned:
            add("F&O ban list", "not banned", "pass")

        known = [c for c in checks if c["v"] is not None]
        answered += len(known)
        total += 1
        out["stocks"][sym] = {
            "checks": checks,
            "answered": len(known),
            "possible": len(checks) + len(CANNOT),
            "failed": sum(1 for c in checks if c["verdict"] == "fail"),
            "watch": sum(1 for c in checks if c["verdict"] == "watch"),
        }

    out["notes"] = {
        "Return on equity": "Feroldi's bar is above 15%. Banks and utilities never clear it.",
        "Price to earnings": "Cheaper than its sector is not the same as cheap.",
        "Price to book": "Meaningless for asset-light businesses; useful for banks.",
        "Dividend yield": "Not a reason to buy, but a cut is a warning.",
        "Distance from 52-week high": "How far it has already fallen from its peak.",
        "Worst past fall": "The rupee figure is the point. Past drawdowns do not predict future ones.",
        "Volatility": "Annualised. High volatility means position size matters more than the pick.",
        "Trend": "Price versus its moving averages.",
        "RSI (14)": "Above 70 is stretched, below 30 is washed out.",
        "MACD histogram": "Above zero means the short average is above the long one.",
        "Price vs 200-day average": "The standard long-term trend test.",
        "F&O ban list": "Position limits reached; new positions are restricted.",
    }
    # ROE is only in the feed for about one stock in nine. Saying so beats letting a blank
    # look like a data error.
    roe_n = sum(1 for s_ in out["stocks"].values()
                for c in s_["checks"] if c["k"] == "Return on equity" and c["v"] is not None)
    n_stocks = len(out["stocks"])
    out["roe_coverage"] = {"stocks_with_roe": roe_n, "stocks": n_stocks,
                           "note": ("ROE comes from our fundamentals feed and is present for "
                                    "only a minority of stocks. Where it is blank, the "
                                    "annual report is the only source.")}
    # COMPACT ENCODING. Check names were repeated ~22,000 times; the file was 1.4 MB of
    # which most was the same eleven strings. Store each name once and reference it by index.
    # Each check becomes [key_index, value, verdict_code, extra?].
    VC = {"unknown": 0, "fail": 1, "watch": 2, "pass": 3}
    key_order = sorted({c["k"] for s_ in out["stocks"].values() for c in s_["checks"]})
    kidx = {k: i for i, k in enumerate(key_order)}
    compact = {}
    for sym, s_ in out["stocks"].items():
        compact[sym] = {
            "c": [[kidx[c["k"]], c["v"], VC.get(c["verdict"], 0)] + ([c["x"]] if c.get("x") else [])
                  for c in s_["checks"]],
            "a": s_["answered"], "p": s_["possible"], "f": s_["failed"], "w": s_["watch"],
        }
    out["keys"] = key_order
    out["verdicts"] = ["unknown", "fail", "watch", "pass"]
    out["stocks"] = compact

    out["count"] = len(out["stocks"])
    out["note"] = ("Checks our own data can answer, plus the questions it cannot - listed with "
                   "what to look for, because a checklist that omits the hard questions looks "
                   "complete when it is not.")
    out["cautions"] = {
        "not_advice": "These are facts about the past, not a recommendation.",
        "thresholds": ("The 15% ROE and 10% margin bars are Brian Feroldi's, not universal "
                       "rules - banks and utilities never clear them and are not worse for it."),
        "missing": ("Net margin, debt, cash flow, growth and promoter holding are NOT in any "
                    "free price feed. The annual report is the only source."),
    }

    os.makedirs("docs", exist_ok=True)
    json.dump(out, open(OUT, "w"), ensure_ascii=False, separators=(",", ":"))
    print("-> %s  %.0f KB  |  %d stocks, %.1f checks answered on average"
          % (OUT, os.path.getsize(OUT) / 1024, out["count"],
             answered / max(1, total)))
    for sym in ("RELIANCE", "TCS", "HDFCBANK"):
        if sym in out["stocks"]:
            s = out["stocks"][sym]
            print("   %-10s %d/%d answered, %d fail, %d watch"
                  % (sym, s["a"], s["p"], s["f"], s["w"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
