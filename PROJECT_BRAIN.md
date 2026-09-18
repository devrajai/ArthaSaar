# MARKET BRAIN — PROJECT BRAIN

Single source of truth. Any AI session starts here. Owner: Dev (mobile-only, Android Chrome).
Repo: devrajai/market-brain | Sister project: devrajai/ipo-terminal (read its PROJECT_BRAIN.md too)

## Mission
Dev's personal market intelligence brain — the "backend of a personal Aladdin".
FULL Indian market coverage, 100% free sources, fully automatic.

## Hard Rules (from Dev)
- NO paid APIs ever. Free sources only.
- Sarvam AI assistant is the ONLY developer (no GPT, no other AI).
- Dev is on weekly message limits — build in phases, be efficient, never redo work.
- All times IST (Asia/Kolkata). Dates dd/mm/yy in user-facing content.
- This repo is DATA + BRAIN backend. A site can be added later (GitHub Pages ready).

## Architecture — updated 18/09/26 evening (FULL MARKET upgrade)
Workflow .github/workflows/brain-collect.yml — runs 18:35 IST and 21:05 IST Mon-Sat (2 runs/day, self-healing):
- scripts/brain_collect.py — FULL universe: 2,305 stocks = Nifty 500 (tier 1, priority, with industry) + 1,804 other NSE EQ-series stocks (tier 2)
  - Sources: nsearchives.nseindia.com ind_nifty500list.csv + EQUITY_L.csv (both verified from datacenter IPs)
  - History per symbol data/history/SYMBOL.json (Yahoo .NS 1y daily, Stooq fallback, incremental append)
  - Symbols already current today are skipped instantly — extra runs continue where previous stopped (self-healing bootstrap)
  - Computes: price, 1d%, 52w/200d high-low, % from 52w high, EMA20/200, above EMA200, RSI14 (Wilder), MACD 12/26/9, vol vs 20d avg, consecutive up/down days
  - Outputs: data/brain-screener.json + .csv (sorted by change%), data/breadth.json, data/universe.json (with tier field)
- scripts/indices_collect.py — ALL 139 NSE indices (allIndices API, with yearHigh/Low, PE, PB) + BSE Sensex via Yahoo ^BSESN -> data/indices-all.json
- scripts/budget_study.py — Nifty ±10 trading-day windows around every budget 2015-2026 -> data/budget-study.json
- scripts/fundamentals_collect.py — yfinance staggered fundamentals (300/run, refresh if >10 days old):
  PE, PB, ROE, ROA, D/E, heldPercentInsiders (≈promoter), heldPercentInstitutions (≈FII+DII), marketCap, beta, dividendYield, profitMargins, revenueGrowth, earningsGrowth, freeCashflow, totalCash, totalDebt, sector, industry -> data/fundamentals.json
- Google Sheet "Market Brain Hub — Screener + Budget Study" (ID: 1sTq7IQ17i_CxGHiw1WHGi62O__9OGZvjfwIBACqrXdc, public)
  - Tabs: Sheet1(README), Nifty500_Screener, Budget_Day_Study, Budget_Theme_Stocks, Daily_Digest_Archive
- Daily digest cron 6:30 PM IST covers BOTH repos + appends digest to the sheet's Daily_Digest_Archive tab

## Bootstrap expectations (be honest with Dev)
- Prices/technicals: tier 1 (Nifty 500) completes in 1-2 runs; full 2,305 takes ~2-4 days across runs (Yahoo rate limits)
- Fundamentals: ~600/day across 2 runs -> full coverage in ~4 days, then stays fresh (10-day staggered refresh)
- If data/breadth.json 'stocks' count is growing daily, the system is healthy

## Data Source Facts
- nsearchives.nseindia.com CSVs work from datacenter IPs; www.nseindia.com/api/equity-stockIndices needs cookies (403/404) — do NOT rely on it
- www.nseindia.com/api/allIndices WORKS from datacenters (139 indices)
- EQUITY_L.csv: 2,578 stocks total, EQ series 2,302 (investable), BE 249, BZ 27 (skip BE/BZ — Yahoo doesn't cover them well)
- Yahoo chart API: rate-limits sustained rapid calls (429) — keep sleeps short, self-heal across runs
- Stooq: https://stooq.com/q/d/l/?s={sym.lower()}&i=d — daily history fallback
- yfinance: handles Yahoo crumb auth; .info gives screener-style fundamentals; ROCE is NOT available — use ROE+ROA as proxy

## Roadmap
- Phase 1 DONE: full-market screener + all indices + budget study + fundamentals engine
- Phase 2: pre-open movers 9:00-9:15, index add/remove tracking, FII/DII daily flows
- Phase 3: super-investor portfolios (Kedia/Damani/Jhunjhunwala via quarterly shareholding), AMFI MF data, panchang calendar
- Phase 4: watchlist + dashboard site on GitHub Pages

## Conventions
- All data in data/ as JSON (+CSV mirrors). Commit via github-actions bot.
- If a script fails partially, it still writes what it got — never lose a day of data.
- Sandbox: keep build scripts in /workspace/notes/ (durable); /scratch/work is wiped on restart
