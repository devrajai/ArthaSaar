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

## Architecture — updated 18/09/26 night (PHASE 2 added)
### Workflows
- .github/workflows/morning-brain.yml — 9:20 AM IST Mon-Fri: pre-open movers + FII/DII + index changes
- .github/workflows/brain-collect.yml — 18:35 & 21:05 IST Mon-Sat: full pipeline

### Scripts
- scripts/brain_collect.py — FULL universe: 2,305 stocks (Nifty 500 tier 1 + 1,804 others tier 2)
  from nsearchives.nseindia.com CSVs. History in data/history/, technicals (EMA20/200, RSI14, MACD,
  52w/200d, volume, consecutive days) -> data/brain-screener.json/.csv + data/breadth.json
- scripts/indices_collect.py — ALL 139 NSE indices (allIndices API w/ yearHigh/Low PE PB) + BSE Sensex
  via Yahoo ^BSESN -> data/indices-all.json
- scripts/phase2_collect.py — PHASE 2:
  1. Pre-open movers: NSE market-data-pre-open?key=ALL (2,180 stocks, IEP, %chg, purpose)
     -> data/preopen.json (buckets >=1..5% both sides, top20 gainers/losers, corp action alerts)
  2. FII/DII flows: NSE fiidiiTradeReact -> data/fii-dii.json (buy/sell/net Cr per category)
  3. Index add/remove: diffs tier-1 universe daily vs data/nifty500-prev.json -> data/index-changes.json
- scripts/budget_study.py — Nifty ±10-day windows around budgets 2015-2026 -> data/budget-study.json
- scripts/fundamentals_collect.py — yfinance staggered (300/run, 10-day refresh): PE, PB, ROE, ROA,
  D/E, heldPercentInsiders (≈promoter), heldPercentInstitutions (≈FII+DII), marketCap, beta,
  dividendYield, margins, growth, cash, debt, sector -> data/fundamentals.json

### Google Sheet "Market Brain Hub — Screener + Budget Study" (1sTq7IQ17i_CxGHiw1WHGi62O__9OGZvjfwIBACqrXdc, public)
Tabs: Sheet1(README), Nifty500_Screener, Budget_Day_Study, Budget_Theme_Stocks, Daily_Digest_Archive,
Dividend_Calendar (Dev's handwritten monthly dividend stock notes — Jan: TCS/Wipro/HCL/Axis; Jul: MRF/
Hindalco/HZL/TCS/Coal India; Sep: Cipla/Coal India — verify + extend freely)

### Dev's study notes (PDFs received 18/09/26)
- Advance.pdf: 36 pages handwritten market course notes (broker structure, limit/market orders, IPO
  truth, market psychology: buyer/seller, market cycles, bull/bear phases, technical basics, market
  participants: corporates 4.3%, DII 0.1%, FII 6.1%, individuals 26.8%, brokers 57.8%) — foundation
  for future Education Library phase
- sensex_history.pdf: 9 pages handwritten Sensex history study
- Divided_stocks_list.pdf: monthly dividend stocks -> already in Dividend_Calendar tab

### Cron
- Daily digest 6:30 PM IST covers BOTH repos + appends to sheet Daily_Digest_Archive. Includes
  FII/DII flows, pre-open highlights, fundamental insight, IPO status, movers.

## Data Source Facts (learned the hard way)
- nsearchives.nseindia.com CSVs work from datacenter IPs (nifty500list.csv, EQUITY_L.csv: 2,578 stocks,
  EQ 2,302 / BE 249 / BZ 27 — skip BE/BZ)
- www.nseindia.com/api/allIndices WORKS from datacenters (139 indices)
- www.nseindia.com/api/market-data-pre-open?key=ALL WORKS (2,180 stocks w/ metadata.symbol, iep,
  pChange, purpose)
- www.nseindia.com/api/fiidiiTradeReact WORKS (FII/FPI + DII buy/sell/net Cr)
- www.nseindia.com/api/equity-stockIndices needs cookies (403/404 from datacenters) — do NOT use
- Yahoo chart API: rate-limits sustained calls (429) — short sleeps, self-heal across runs
- Stooq: /q/d/l/?s={sym.lower()}&i=d — history fallback
- yfinance: .info fundamentals; ROCE not available — ROE+ROA proxy

## Roadmap
- Phase 1 DONE: full-market screener + all indices + budget study + fundamentals
- Phase 2 DONE (18/09/26): pre-open movers, FII/DII flows, index add/remove detection, dividend calendar
- Phase 3: super-investor portfolios (Kedia/Damani/Jhunjhunwala), AMFI MF data, panchang calendar
- Phase 4: watchlist + education library (use Advance.pdf notes) + dashboard site on GitHub Pages

## Conventions
- All data in data/ as JSON. Commit via github-actions bot.
- If a script fails partially, it still writes what it got — never lose a day of data.
- Sandbox: keep build scripts in /workspace/notes/ (durable); /scratch/work wiped on restart
