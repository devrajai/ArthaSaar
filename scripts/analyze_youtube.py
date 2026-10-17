#!/usr/bin/env python3
"""
analyze_youtube.py - the "brain": turn raw collected uploads into structured signal.

Reads data/youtube/videos.csv and produces, in data/analysis/:
  video_scores.csv    per video: symbols mentioned, themes, bull/bear sentiment
  symbol_buzz.csv     which stocks/indices the market channels are talking about
  channel_stats.csv   per-channel cadence and reach
  theme_counts.csv    which topics dominate
  brain_summary.json  headline numbers
  brain_report.md     a readable digest

Method (deliberately transparent - no black box):
  * symbols  - matched from an alias map (company/ticker names -> NSE symbol), so we
               don't fire on every stray uppercase word.
  * themes   - keyword buckets (earnings, IPO, F&O, intraday, outlook, ...).
  * sentiment- a simple bull-vs-bear keyword score. It is a rough lean, not advice.

Everything is keyword-based and reproducible; swap in an LLM later if you want depth.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------- alias map
SYMBOL_ALIASES = {
    # index / broad
    "nifty 50": "NIFTY50", "nifty50": "NIFTY50", "nifty": "NIFTY50",
    "bank nifty": "BANKNIFTY", "banknifty": "BANKNIFTY", "nifty bank": "BANKNIFTY",
    "fin nifty": "FINNIFTY", "finnifty": "FINNIFTY",
    "sensex": "SENSEX", "midcap": "MIDCPNIFTY",
    # large caps
    "reliance": "RELIANCE", "jio": "RELIANCE", "ril": "RELIANCE",
    "tcs": "TCS", "tata consultancy": "TCS",
    "infosys": "INFY", "infy": "INFY",
    "hdfc bank": "HDFCBANK", "hdfcbank": "HDFCBANK",
    "icici": "ICICIBANK", "icici bank": "ICICIBANK",
    "sbi": "SBIN", "state bank": "SBIN",
    "axis bank": "AXISBANK", "kotak": "KOTAKBANK", "kotak bank": "KOTAKBANK",
    "itc": "ITC", "l&t": "LT", "larsen": "LT",
    "airtel": "BHARTIARTL", "bharti": "BHARTIARTL",
    "wipro": "WIPRO", "hcl": "HCLTECH", "hcl tech": "HCLTECH",
    "tech mahindra": "TECHM",
    "maruti": "MARUTI", "tata motors": "TATAMOTORS", "tata steel": "TATASTEEL",
    "tata power": "TATAPOWER",
    "adani": "ADANIENT", "adani enterprises": "ADANIENT", "adani ports": "ADANIPORTS",
    "adani green": "ADANIGREEN", "adani power": "ADANIPOWER",
    "ongc": "ONGC", "ntpc": "NTPC", "power grid": "POWERGRID", "coal india": "COALINDIA",
    "sun pharma": "SUNPHARMA", "dr reddy": "DRREDDY", "cipla": "CIPLA", "divis": "DIVISLAB",
    "asian paints": "ASIANPAINT", "britannia": "BRITANNIA", "nestle": "NESTLEIND",
    "hindustan unilever": "HINDUNILVR", "hul": "HINDUNILVR",
    "bajaj finance": "BAJFINANCE", "bajaj finserv": "BAJAJFINSV", "bajaj auto": "BAJAJ-AUTO",
    "zomato": "ZOMATO", "paytm": "PAYTM", "nykaa": "NYKAA", "irctc": "IRCTC",
    "lic": "LICI", "dmart": "DMART", "vedanta": "VEDL", "jsw steel": "JSWSTEEL",
    "hindalco": "HINDALCO", "grasim": "GRASIM", "ultratech": "ULTRACEMCO", "titan": "TITAN",
    "eicher": "EICHERMOT", "hero motocorp": "HEROMOTOCO", "indusind": "INDUSINDBK",
    "yes bank": "YESBANK", "pnb": "PNB", "bank of baroda": "BANKBARODA", "canara": "CANBK",
    "idfc": "IDFCFIRSTB", "irfc": "IRFC", "suzlon": "SUZLON", "vodafone": "IDEA",
    "indigo": "INDIGO", "spicejet": "SPICEJET", "dlf": "DLF", "dabur": "DABUR",
    "marico": "MARICO", "colgate": "COLPAL", "pidilite": "PIDILITIND", "havells": "HAVELLS",
    "voltas": "VOLTAS", "bhel": "BHEL", "bel": "BEL", "bharat electronics": "BEL",
    "hal": "HAL", "mazagon": "MAZDOCK", "cochin shipyard": "COCHINSHIP",
    "rvnl": "RVNL", "pfc": "PFC", "rec": "RECLTD", "nmdc": "NMDC", "sail": "SAIL",
    "gail": "GAIL", "ioc": "IOC", "bpcl": "BPCL", "hpcl": "HPCL", "petronet": "PETRONET",
    "jio financial": "JIOFIN", "angel one": "ANGELONE", "cdsl": "CDSL", "bse": "BSE",
    "policybazaar": "POLICYBZR", "delhivery": "DELHIVERY", "swiggy": "SWIGGY",
    "ola": "OLAELEC", "mamaearth": "HONASA", "apollo hospitals": "APOLLOHOSP",
    "lupin": "LUPIN", "aurobindo": "AUROPHARMA", "biocon": "BIOCON", "alkem": "ALKEM",
    "zydus": "ZYDUSLIFE", "laurus": "LAURUSLABS", "ashok leyland": "ASHOKLEY",
    "exide": "EXIDEIND", "bharat forge": "BHARATFORG", "firstcry": "FIRSTCRY",
}

THEMES = {
    "Earnings/Results": ["result", "earnings", "q1", "q2", "q3", "q4", "quarterly",
                          "profit", "revenue", "margin", "guidance"],
    "IPO": ["ipo", "listing", "allotment", "grey market", "gmp", "subscription", "anchor"],
    "Options/F&O": ["option", "f&o", "futures", "call", "put", "strike", "expiry", "weekly"],
    "Intraday": ["intraday", "day trading", "scalp", "live trade", "live market"],
    "Swing/Long-term": ["swing", "positional", "long term", "multibagger", "portfolio"],
    "Budget/Policy": ["budget", "rbi", "repo rate", "sebi", "gst", "tariff", "monetary policy"],
    "Gold/Commodity": ["gold", "silver", "crude", "commodity"],
    "MF/SIP": ["mutual fund", "sip", "nav", "index fund", "etf"],
    "Market Outlook": ["nifty prediction", "market outlook", "tomorrow", "weekly analysis",
                        "pre-market", "opening bell", "trade setup", "view"],
    "Beginner/Education": ["beginner", "how to", "explained", "basics", "learn", "tutorial"],
}

BULL = ["rally", "breakout", "bull", "bullish", "buy", "multibagger", "target", "surge",
        "all-time high", "all time high", "ath", "gain", "strong", "boom", "momentum",
        "profit", "rocket", "up ", "upside", "recovery", "rebound"]
BEAR = ["crash", "fall", "trap", "warning", "bear", "bearish", "sell", "correction",
        "downside", "loss", "risk", "caution", "slump", "plunge", "weak", "avoid",
        "bubble", "breakdown", "downtrend"]


def _find_symbols(text: str) -> list[str]:
    t = " " + text.lower() + " "
    hits = set()
    for alias, sym in SYMBOL_ALIASES.items():
        if re.search(r"(?<![a-z0-9])" + re.escape(alias) + r"(?![a-z0-9])", t):
            hits.add(sym)
    return sorted(hits)


def _find_themes(text: str) -> list[str]:
    t = text.lower()
    return sorted({th for th, kws in THEMES.items() if any(k in t for k in kws)})


def _sentiment(text: str) -> tuple[int, int]:
    t = text.lower()
    return (sum(t.count(k) for k in BULL), sum(t.count(k) for k in BEAR))


def main() -> int:
    ap = argparse.ArgumentParser(description="Analyse collected YouTube uploads.")
    ap.add_argument("--infile", default="data/youtube/videos.csv")
    ap.add_argument("--outdir", default="data/analysis")
    args = ap.parse_args()

    src = Path(args.infile)
    if not src.exists():
        raise SystemExit(f"No input at {src} - run fetch_youtube.py first.")
    df = pd.read_csv(src, dtype=str).fillna("")
    if df.empty:
        raise SystemExit("videos.csv is empty.")

    out = Path(args.outdir)
    out.mkdir(parents=True, exist_ok=True)

    rows = []
    for _, r in df.iterrows():
        text = f"{r['title']} {r.get('description','')}"
        syms = _find_symbols(text)
        themes = _find_themes(text)
        bull, bear = _sentiment(text)
        rows.append({
            "video_id": r["video_id"], "channel_name": r["channel_name"],
            "published": r["published"][:10], "title": r["title"],
            "symbols": "|".join(syms), "themes": "|".join(themes),
            "bull": bull, "bear": bear, "sentiment": bull - bear,
        })
    vs = pd.DataFrame(rows)
    vs.to_csv(out / "video_scores.csv", index=False)

    # symbol buzz
    buzz = defaultdict(lambda: {"mentions": 0, "channels": set(), "bull": 0, "bear": 0, "latest": ""})
    for _, r in vs.iterrows():
        for s in filter(None, r["symbols"].split("|")):
            b = buzz[s]
            b["mentions"] += 1
            b["channels"].add(r["channel_name"])
            b["bull"] += r["bull"]; b["bear"] += r["bear"]
            b["latest"] = max(b["latest"], r["published"])
    buzz_rows = [{
        "symbol": s, "mentions": v["mentions"], "channels": len(v["channels"]),
        "bull": v["bull"], "bear": v["bear"], "sentiment": v["bull"] - v["bear"],
        "latest_published": v["latest"],
    } for s, v in buzz.items()]
    bz = pd.DataFrame(buzz_rows).sort_values(["mentions", "channels"], ascending=False)
    bz.to_csv(out / "symbol_buzz.csv", index=False)

    # channel stats
    ch_rows = []
    for name, g in df.groupby("channel_name"):
        views = pd.to_numeric(g["views"], errors="coerce").dropna()
        top = g.assign(v=pd.to_numeric(g["views"], errors="coerce")).sort_values("v", ascending=False).iloc[0]
        ch_rows.append({
            "channel_name": name, "videos_in_feed": len(g),
            "newest": g["published"].max()[:10], "oldest": g["published"].min()[:10],
            "avg_views": int(views.mean()) if len(views) else 0,
            "median_views": int(views.median()) if len(views) else 0,
            "top_video": top["title"][:70], "top_views": int(top["v"]) if pd.notna(top["v"]) else 0,
        })
    ch = pd.DataFrame(ch_rows).sort_values("avg_views", ascending=False)
    ch.to_csv(out / "channel_stats.csv", index=False)

    # theme counts
    tc = Counter()
    for _, r in vs.iterrows():
        for th in filter(None, r["themes"].split("|")):
            tc[th] += 1
    theme_df = pd.DataFrame(sorted(tc.items(), key=lambda x: -x[1]), columns=["theme", "videos"])
    theme_df.to_csv(out / "theme_counts.csv", index=False)

    # summary + report
    summary = {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "channels": int(df["channel_name"].nunique()),
        "videos": int(len(df)),
        "window_start": df["published"].min()[:10],
        "window_end": df["published"].max()[:10],
        "total_views": int(pd.to_numeric(df["views"], errors="coerce").fillna(0).sum()),
        "top_symbols": bz.head(10)[["symbol", "mentions", "channels"]].to_dict("records"),
        "top_themes": theme_df.head(6).to_dict("records"),
        "net_sentiment": int(vs["sentiment"].sum()),
    }
    (out / "brain_summary.json").write_text(json.dumps(summary, indent=2))

    lines = [
        "# YouTube Brain - market-channel digest", "",
        f"Generated {summary['generated_at']}  |  {summary['channels']} channels, "
        f"{summary['videos']} videos, window {summary['window_start']} to {summary['window_end']}.", "",
        f"**Total views across the window:** {summary['total_views']:,}  |  "
        f"**net bull-bear keyword score:** {summary['net_sentiment']}", "",
        "## Most-talked-about symbols", "",
        "| Symbol | Mentions | Channels |", "|---|---|---|",
    ]
    for r in summary["top_symbols"]:
        lines.append(f"| {r['symbol']} | {r['mentions']} | {r['channels']} |")
    lines += ["", "## Dominant themes", "", "| Theme | Videos |", "|---|---|"]
    for r in summary["top_themes"]:
        lines.append(f"| {r['theme']} | {r['videos']} |")
    lines += ["", "## Channels by reach", "",
              "| Channel | Videos | Avg views | Newest |", "|---|---|---|---|"]
    for _, r in ch.iterrows():
        lines.append(f"| {r['channel_name']} | {r['videos_in_feed']} | {r['avg_views']:,} | {r['newest']} |")
    lines += ["", "_Keyword-based analysis. Not investment advice._", ""]
    (out / "brain_report.md").write_text("\n".join(lines))

    print(f"Brain done -> {out}")
    print(f"  {summary['channels']} channels, {summary['videos']} videos")
    print("  top symbols:", ", ".join(f"{r['symbol']}({r['mentions']})" for r in summary["top_symbols"][:8]))
    print("  top themes :", ", ".join(f"{r['theme']}({r['videos']})" for r in summary["top_themes"][:5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
