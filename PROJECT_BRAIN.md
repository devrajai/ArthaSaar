# MARKET BRAIN — PROJECT BRAIN

Single source of truth. Any AI session starts here. Owner: Dev (mobile-only, Android Chrome).
Repo: devrajai/market-brain | Sister project: devrajai/ipo-terminal (read its PROJECT_BRAIN.md too)

## Mission
Dev's personal market intelligence brain — a "poor-man's BlackRock Aladdin / Sharekhan TX3
quality terminal". FULL Indian market coverage, 100% free sources, fully automatic. Dev will
wait for perfection on DATA (daily reliability, zero issues) before the website — data first,
website second.

## Hard Rules (from Dev)
- NO paid APIs ever. Free sources only.
- Sarvam AI assistant is the ONLY developer (no GPT, no other AI).
- Dev is on weekly message limits — build in phases, be efficient, never redo work.
- All times IST (Asia/Kolkata). Dates dd/mm/yy in user-facing content.
- PERMANENT UI: Liquid Glass design (see below) — every future page/site uses it.

## PERMANENT UI — Liquid Glass Design System (approved by Dev 18/09/26)
- Dark mode default + light mode toggle (pill switch, saved in localStorage 'mb-theme')
- ZERO position:sticky and ZERO backdrop-filter ANYWHERE (Dev's confirmed rule after TWO
  rounds of screen-recorded feedback, 18/09/26 night: the header bar must scroll away with
  the page like every other card — NOTHING stays pinned/floating on top while scrolling).
  Cards use translucent gradient backgrounds only; they look glass without any blur filter.
- Header at top: brand + live IST clock + date + market status badge (PRE-OPEN 9:00-9:15 /
  OPEN / CLOSED) + theme toggle — as a normal in-flow card, not sticky.
- Fonts: Plus Jakarta Sans (body) + Azeret Mono (numbers/labels)
- Palette: bg dark #080d17→#0b1220 (light #e7edf5→#dde6f2), accents emerald #10b981 (up),
  rose #f43f5e (down), amber #f5a623 (gold/IPO), teal #14b8a6 (brand), floating blurred orbs
  (teal/navy/amber, 8-16% opacity) behind everything
- Components: KPI cards w/ count-up animation, index grid cards, pre-open breadth bars,
  gainers/losers tables, IPO cards w/ GMP highlight + featured IPO banner, system status rows
- Reference implementation: /workspace/notes/today_updates_dashboard.html (durable) —
  'Today_Updates_LiquidGlass_v3.html' delivered 18/09/26 (v3 = header un-pinned, final)

## Architecture — updated 21/09/26 (Phase 2 + fixes + Telegram Brain)
### Workflows
- .github/workflows/morning-brain.yml — 9:20 AM IST Mon-Fri: phase2_collect
- .github/workflows/brain-collect.yml — 18:35 & 21:05 IST Mon-Sat: full pipeline
- .github/workflows/telegram-morning.yml — 9:25 AM IST Mon-Fri: morning brief to Dev's
  Telegram (runs AFTER morning-brain commits; needs secrets TELEGRAM_BOT_TOKEN +
  TELEGRAM_CHAT_ID; manual dispatch available for testing)
- .github/workflows/telegram-day.yml — 3:45 PM IST Mon-Fri: post-close day analysis to
  Telegram (fresh NSE allIndices + FII/DII live fetch + yfinance Sensex fallback)
- BOTH collectors have rebase-and-retry git push (5 attempts, 15s apart) — fixes the 18/09 race where
  morning + evening runs collided and one run's data was lost. Telegram workflows NEVER
  commit (read-only) so they can never race the collectors.
### Scripts
- scripts/brain_collect.py — 2,305 stocks (Nifty 500 tier 1 + 1,804 tier 2). History via
  BATCHED yfinance downloads (100 symbols/call — plain urllib Yahoo is blocked on runners,
  v1 of this script produced 0 technicals). Universe from nsearchives CSVs.
- scripts/indices_collect.py — all 139 NSE indices + Sensex → indices-all.json
- scripts/phase2_collect.py — pre-open movers (2,180 stk) → preopen.json; FII/DII → fii-dii.json;
  index add/remove diff → index-changes.json (baseline nifty500-prev.json)
- scripts/telegram_brain.py — Telegram Brain (21/09/26): builds + sends 2 daily messages.
  'morning' mode: global cues + FII/DII (prev day) + pre-open movers + Smart Brain call
  + TimesFM rotation + index-change alerts. 'afternoon' mode: fresh close snapshot
  (Nifty/Bank/Sensex/Midcap/Smallcap/IT/VIX) + sector scoreboard + live FII/DII.
  --dry flag prints instead of sending. Self-healing sections, 4096-char chunking.
- scripts/telegram_ipo.py — IPO digest (21/09/26): reads ipo-terminal raw URLs, sends to
  TG_CHAT_ID_IPO (comma-separated, fallback TG_CHAT_ID). Daily 8:45 AM via telegram-ipo.yml.
- scripts/telegram_who.py + telegram-who.yml (manual) — lists chat ids of everyone who
  /started the bot (getUpdates).
- scripts/budget_study.py — budget-day Nifty ±10-day windows 2015-2026
- scripts/fundamentals_collect.py — yfinance staggered 300/run → fundamentals.json

### Telegram setup (one-time, Dev only)
1. @BotFather → /newbot → token
2. /start the bot from Dev's Telegram, get chat id via api.telegram.org/bot<TOKEN>/getUpdates
3. Repo Settings → Secrets → Actions: TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
4. Test: Actions → Telegram Morning Brief → Run workflow (manual dispatch)

### LIVE Telegram routing (21/09/26 — the names that ACTUALLY run)
- Secrets that run the messages: TG_TOKEN (bot token) + TG_CHAT_ID (market msgs via
  telegram.yml) + TG_CHAT_ID_IPO (IPO digest 8:45 AM via telegram-ipo.yml; fallback = TG_CHAT_ID)
- Both TG_CHAT_ID and TG_CHAT_ID_IPO = "1392604324,1148261593,1785489570,1182983939" =
  Dev + Nandan pithadiya (@Dev_pithadiya) + Hemant (____Hemant) + Solanki (@Rahul3573).
  All 4 get EVERYTHING (market + IPO). Verified sent to 4 chats 21/09/26.
- To add a person: they must /start the bot first (Telegram blocks bots messaging strangers),
  run "Telegram Who" workflow (telegram-who.yml) to see their chat_id, then update BOTH secrets
  with comma-separated ids (encrypt via repo public key + PyNaCl sealed box, push via GitHub MCP
  GITHUB_CREATE_OR_UPDATE_A_REPOSITORY_SECRET).

### Google Sheet "Market Brain Hub" (1sTq7IQ17i_CxGHiw1WHGi62O__9OGZvjfwIBACqrXdc, public)
Tabs: Sheet1(README), Nifty500_Screener, Budget_Day_Study, Budget_Theme_Stocks,
Daily_Digest_Archive, Dividend_Calendar (Dev's handwritten monthly dividend stocks)

### Dev's study notes (all received 18/09/26)
- Advance.pdf: 36 pages course notes (broker structure, market psychology, participants
  breakdown, bull/bear phases) → data/education.json devs_collected_rules
- sensex_history.pdf: 9 pages Sensex history study
- Divided_stocks_list.pdf: monthly dividend calendar → Dividend_Calendar tab
- data/education.json: books (12), podcasts (5), YouTube (5), free courses (5),
  Dev's Inspiring Traders playlist (25 Abhishek Kar videos, indexed with titles),
  Dev's collected rules (6) — feeds website Learn section

### Cron
Daily digest 6:30 PM IST covers both repos + appends to sheet. Includes FII/DII flows,
pre-open highlights, fundamental insight, IPO status, index changes. Verify the screener
is filling (run of 18/09 21:05 IST deployed the batched-yfinance fix — check breadth.json
'stocks' count and report it to Dev).

## Data Source Facts
- nsearchives.nseindia.com CSVs work from datacenter IPs (EQUITY_L.csv 2,578 → keep EQ only)
- www.nseindia.com/api/allIndices WORKS (139 indices)
- /api/market-data-pre-open?key=ALL WORKS (2,180 stocks, metadata.symbol/iep/pChange/purpose)
- /api/fiidiiTradeReact WORKS (FII/FPI + DII buy/sell/net Cr)
- /api/equity-stockIndices needs cookies — do NOT use
- Yahoo chart API via plain urllib: BLOCKED on datacenter/runner IPs — always use the
  yfinance library (it handles cookies/crumb); batch 100 symbols per yf.download call
- yfinance works on Actions runners (fundamentals + history, both proven 18/09)
- api.telegram.org sendMessage WORKS from runners (plain urllib + JSON body, proven 21/09)
- YouTube oEmbed works for fetching video titles (used for the playlist index)

## Roadmap
- Phase 1 DONE: full-market screener + all indices + budget study + fundamentals
- Phase 2 DONE: pre-open movers, FII/DII flows, index add/remove, dividend calendar
- Phase 3: super-investor portfolios, AMFI MF data, panchang calendar
- Phase 3.5 DONE (21/09/26): Telegram Brain — daily morning brief (9:25) + day analysis (15:45)
- Phase 4 WEBSITE (Dev-approved, WAIT for data reliability confirmation first):
  GitHub Pages site in Liquid Glass UI, FULL of data — today's dashboard sections + screener
  tables, budget study, education library (books/podcasts/articles + Inspiring Traders
  playlist + Dev's rules), articles. Aladdin/TX3-level ambition: as much data as free
  sources allow.

## Conventions
- All data in data/ as JSON. Commit via github-actions bot.
- If a script fails partially, write what it got — never lose a day.
- Sandbox: build scripts in /workspace/notes/ (durable); /scratch wiped on restart.
