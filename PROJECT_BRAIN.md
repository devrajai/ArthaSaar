# MARKET BRAIN — PROJECT BRAIN

Single source of truth. Any AI session starts here. Owner: Dev (mobile-only, Android Chrome).
Repo: devrajai/market-brain | Sister project: devrajai/ipo-terminal (read its PROJECT_BRAIN.md too)

## Mission
Dev's personal market intelligence brain — the "backend of a personal Aladdin".
Phase 1: Nifty 500 screener with fundamentals + technicals, budget-day historical study, daily digest. 100% free sources, fully automatic.

## Hard Rules (from Dev)
- NO paid APIs ever. Free sources only.
- Sarvam AI assistant is the ONLY developer (no GPT, no other AI).
- Dev is on weekly message limits — build in phases, be efficient, never redo work.
- All times IST (Asia/Kolkata). Dates dd/mm/yy in user-facing content.
- This repo is DATA + BRAIN backend. A site can be added later (GitHub Pages ready).

## Architecture
- scripts/brain_collect.py — runs daily 18:05 IST via .github/workflows/brain-collect.yml
  - Universe: Nifty 500 list from https://nsearchives.nseindia.com/content/indices/ind_nifty500list.csv (verified working, no key)
  - History per symbol: data/history/SYMBOL.json (Yahoo chart API .NS 1y, Stooq fallback, incremental append, self-healing on failure)
  - Computes: price, 1d%, 52w high/low, 200d high/low, % from 52w high, EMA20, EMA200, above/below EMA200, RSI14 (Wilder), MACD 12/26/9, volume vs 20d avg, consecutive up/down days
  - Outputs: data/brain-screener.json + .csv + data/breadth.json (market breadth: % above EMA200, RSI counts, volume spikes, near-52w-high counts)
- scripts/budget_study.py — Nifty ±10 trading-day windows around every budget 2015-2026 -> data/budget-study.json
- Google Sheet "Market Brain Hub — Screener + Budget Study" (ID: 1sTq7IQ17i_CxGHiw1WHGi62O__9OGZvjfwIBACqrXdc, public)
  - Tabs: Sheet1(README), Nifty500_Screener, Budget_Day_Study, Budget_Theme_Stocks, Daily_Digest_Archive
- Daily digest cron 6:30 PM IST covers BOTH repos (ipo-terminal + market-brain)

## Data Source Facts
- nsearchives.nseindia.com CSV works from datacenter IPs; www.nseindia.com/api/equity-stockIndices needs cookies (403/404 from datacenters) — do NOT rely on it
- Yahoo chart API: rate-limits rapid calls (429) — always sleep 0.4s+, self-heal across runs
- Stooq: https://stooq.com/q/d/l/?s={sym.lower()}&i=d — daily history fallback
- NSE allIndices API works (used in ipo-terminal repo)

## Roadmap
- Phase 1 (current): screener + budget study + digest — DONE 18/09/2026, first data lands after first workflow run
- Phase 1b: fundamentals layer (PE/PB/ROE/ROCE/D-E, promoter/DII/FII holding) — research-driven, add progressively via daily brain runs
- Phase 2: pre-open movers 9:00-9:15, index add/remove, FII/DII flows
- Phase 3: super-investor portfolios, AMFI MF data, panchang calendar
- Phase 4: watchlist + site on GitHub Pages (market-brain.github.io style dashboard)

## Conventions
- All data in data/ as JSON (+CSV mirrors). Commit via github-actions bot.
- If a script fails partially, it still writes what it got — never lose a day of data.
