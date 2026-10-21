# Market Data Hub — NSE EOD archive

A self-updating, no-website data hub. A scheduled GitHub Action downloads the NSE
end-of-day bhavcopy after market close, normalises it, and commits it back into the
repo. The repo **is** the archive — there is no landing page, no GitHub Pages, no site.

Pairs with the **Market Data Hub (Archive)** Google Sheet, which is the *view* layer
(tabs: README, Config, Universe, Daily_Snapshot, Fundamentals, Technicals, F_and_O,
Index_MF). The bulk data lives here as files, not in the Sheet — a Google Sheet caps
at 10,000,000 cells, and all-company history blows past that quickly.

## What it collects

Free, no API key, no login, no cookies required — a browser User-Agent is enough.

| Era | Segment | URL |
|-----|---------|-----|
| Modern (≥ 2024-07-08, UDiFF) | Capital Market (equities) | `https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip` |
| Modern (≥ 2024-07-08, UDiFF) | Futures & Options | `https://nsearchives.nseindia.com/content/fo/BhavCopy_NSE_FO_0_0_0_YYYYMMDD_F_0000.csv.zip` |
| Legacy (≤ 2024-07-05) | Capital Market | `https://archives.nseindia.com/content/historical/EQUITIES/YYYY/MMM/cmDDmmmYYYYbhav.csv.zip` |
| Legacy (≤ 2024-07-05) | F&O | `https://archives.nseindia.com/content/historical/DERIVATIVES/YYYY/MMM/foDDmmmYYYYbhav.csv.zip` |

The script picks the right era automatically. Only trading days exist; weekends and
exchange holidays return 404 and are skipped. Very old legacy dates can occasionally
403 — the backfill tolerates and logs those.

## Layout

```
scripts/nse_source.py      URL builders, download, normalise to one canonical schema
scripts/fetch_bhavcopy.py  CLI: --latest | --date | --start/--end | --days
scripts/sync_google.py     OPTIONAL: mirror to Drive + push watchlist to the Sheet
scripts/youtube_source.py  YouTube Atom-feed parser (no API key needed)
scripts/fetch_youtube.py   polls config/channels.json, logs new uploads
scripts/analyze_youtube.py the "brain": symbols, themes, sentiment, channel stats
config/channels.json       the channels to watch
scripts/fetch_arthasaar_data.py pulls ArthaSaar's market-data JSONs into data/
scripts/telegram_brain.py  Telegram morning + day-analysis messages
scripts/telegram_alert.py  Telegram open/close alerts (multi-chat)
scripts/morning_unified.py 8:30 AM IST merged morning brief
scripts/telegram_who.py    lists chat ids that messaged the bot
scripts/timesfm_forecast.py TimesFM 3.0 multi-horizon forecasts
scripts/tghelp.py, rotpts.py  helpers for the above
scripts/candles_from_drive.py restores the candle archive from Google Drive
scripts/build_features.py  candle archive -> model-ready feature table
scripts/candles_from_bhavcopy.py grows a candle archive from NSE bhavcopy
scripts/build_analytics.py derives futures.json / breadth.json from hub data
scripts/check_freshness.py the watchdog - fails when a feed goes stale
INDEX.md                   what holds what (repo / Drive / Sheets)
reference/                 ArthaSaar full source dump (323 files, reference only)
.github/workflows/
  pipeline.yml             THE pipeline - collects everything, analyses, commits, alerts
  youtube-live.yml         hourly YouTube poll -> triggers the pipeline on a new video
  tests.yml                indicator + backtest tests on every push
  backfill.yml             manual one-off history backfill
  health.yml               independent freshness watchdog (checks the pipeline itself)
  telegram.yml             close summary (16:00 IST)
  telegram-morning.yml     8:30 AM IST morning brief
  telegram-day.yml         manual day analysis
  telegram-who.yml         manual chat-id lookup
data/
  raw/<seg>/               original .csv.zip (git-ignored, kept local)
  parquet/<seg>/           normalised columnar files  <- backtest from these
  csv/<seg>/               normalised CSV             <- human / Sheets friendly
  manifest.csv             index of everything archived (date, segment, rows, symbols)
  youtube/videos.csv       every new upload seen, one row per video (deduped)
  youtube/<channel>.csv    per-channel snapshot
  analysis/                the brain's output (see below)
```

Canonical columns: `date, segment, symbol, series, isin, open, high, low, close, last,
prevclose, volume, turnover, trades, oi, oi_change`.

## Quickstart

```bash
pip install -r requirements.txt

python scripts/fetch_bhavcopy.py --latest                 # most recent trading day
python scripts/fetch_bhavcopy.py --date 2026-10-16        # one day
python scripts/fetch_bhavcopy.py --days 30                # last 30 calendar days
python scripts/fetch_bhavcopy.py --start 2024-01-01 --end 2026-10-16 --segments cm
```

## YouTube triggers

The daily job also polls each channel in `config/channels.json` via its public Atom
feed - no API key, no login, no quota:

```
https://www.youtube.com/feeds/videos.xml?channel_id=<UC...>
```

Watched channels:

| Channel | Handle | Channel ID |
|---------|--------|------------|
| Abhishek Kar | @abhishekkar | `UCcanCrgSWVYW7ZFNKQZso0g` |
| WAY2LAABH | @way2laabh | `UC0OPnM1WTYZO1BFLE017DFQ` |
| Markets by Zerodha Hindi | @marketsbyzerodhahindi | `UCorKX0CAjQh0SnflWPnnI9w` |
| Markets by Zerodha | @marketsbyzerodha | `UCXbKJML9pVclFHLFzpvBgWw` |
| Upstox | @upstoxofficial | `UCOBm5PAfMS7wy_WYPvGjSiQ` |
| Moneytalks by Groww | @moneytalksbygroww | `UCuA2G-T1WmPRCHwDb713pVQ` |
| Groww | @groww | `UCw5TLrz3qADabwezTEcOmgQ` |
| Groww Edge | @groww_edge | `UCirSG61aPwX5V3lpFj6wbRA` |
| Ghanshyam Tech | @ghanshyamtech | `UCw4496t84F_8HvhQPwtmWpQ` |
| POWER OF STOCKS | @powerofstocksbysubasish | `UCE5wDMNEZElnuRDk6TDPOYg` |

```bash
python scripts/fetch_youtube.py          # poll all channels, append new uploads
```

Each run appends any video IDs it hasn't seen before to `data/youtube/videos.csv`
(video_id, channel, title, published, url, thumbnail, views, description, first_seen).
Re-running is safe - it dedupes on `video_id`.

**Limits:** the feed carries only the ~15 most recent uploads per channel. Run it
daily and you accumulate a full history over time; counting a channel's *entire*
back-catalogue needs the YouTube Data API (free key). To add a channel, find its
`externalId` on `https://www.youtube.com/@<handle>` - not the first `channelId` on
the page, which can belong to a related channel.

## The brain (analysis)

`analyze_youtube.py` reads `data/youtube/videos.csv` and turns raw uploads into signal.
It is keyword-based and fully transparent - no black box:

```bash
python scripts/analyze_youtube.py
```

Outputs in `data/analysis/`:

- `video_scores.csv` - per video: symbols mentioned, themes, bull/bear score
- `symbol_buzz.csv` - which stocks/indices the channels are actually talking about
- `channel_stats.csv` - per-channel cadence and reach (avg/median views, top video)
- `theme_counts.csv` - which topics dominate (earnings, IPO, F&O, outlook, ...)
- `brain_summary.json` - headline numbers for a dashboard or site
- `brain_report.md` - a readable digest

How it reads: symbols come from an alias map (company/ticker names to NSE symbol) so
it does not fire on stray uppercase words; themes are keyword buckets; sentiment is a
rough bull-vs-bear keyword count. Swap in an LLM over the same input if you want
deeper reading later - the data contract does not change.

## One pipeline

Everything runs as a single pipeline, in one file, on one schedule:

```
.github/workflows/pipeline.yml      17:30 UTC (23:00 IST / 11 PM) daily, or by hand
scripts/run_pipeline.sh             the same sequence, runnable locally
```

Order: bhavcopy -> Yahoo -> YouTube -> brain -> candles -> analytics -> features ->
optional sources (Drive / Sheets / Notion / ArthaSaar) -> freshness check -> commit.
Each step is independent: one failing does not abort the rest, and the run exits
non-zero if anything failed so the `alert` job can open an issue.

**Optional sources light up on their own.** Add a secret and the matching step starts
running - nothing to edit:

| Secret | Turns on |
|---|---|
| `GOOGLE_SA_JSON` + `ARTHASAAR_DRIVE_FOLDER` | Drive candle archive |
| `GOOGLE_SA_JSON` + `SHEET_SOURCE_ID` + `SHEET_SOURCE_RANGE` | Google Sheets source |
| `NOTION_TOKEN` + `NOTION_DATABASE_ID` | Notion source |
| `ARTHASAAR_TOKEN` | ArthaSaar analytics JSONs |
| repo variable `RUN_TIMESFM=true` | the TimesFM forecast job |

Run it locally exactly as CI does:

```bash
bash scripts/run_pipeline.sh
SKIP_YAHOO=1 bash scripts/run_pipeline.sh   # skip the slow step
```

**Why Telegram and the watchdog are separate files.** The Telegram briefs are
time-of-day specific (8:30 AM, 4:00 PM) - folding them into an 11 PM pipeline would
send them at the wrong time. And `health.yml` must be *independent*: a watchdog that
runs inside the pipeline cannot notice the pipeline itself dying.

## Live YouTube trigger

A new upload should drive collection, not wait for 23:00. `youtube-live.yml` polls the
10 channels **every hour** and, when something new appears, dispatches the full pipeline:

```
new video detected  ->  gh workflow run pipeline.yml  ->  full data collection
```

How it knows: `fetch_youtube.py` writes `data/youtube/last_run.json` with a `new` count,
and the workflow triggers only when it is above zero. When nothing is new, the pipeline
keeps its normal nightly run and nothing extra happens.

**Why hourly and not instant:** YouTube offers no webhook we can use without hosting a
public endpoint, so the public Atom feed is the only free, key-less route. Polling is
the honest answer; hourly is the practical floor for GitHub cron reliability. On a
public repo the minutes are free, so 24 polls a day cost nothing.

The poll also **retries on throttling** - YouTube answers an existing channel with
404/5xx when it is rate-limiting rather than saying so, which matters a lot at hourly
frequency.

## Automating it

Push this folder to a **public** GitHub repo. `pipeline.yml` then runs once a day at
23:00 IST (17:30 UTC) and commits the new files. Public repos get unlimited Actions
minutes — that's why public is the right call for a daily job. To backfill history,
run the `backfill` workflow from the Actions tab with a date range.

## Google Drive + Sheet (optional)

`sync_google.py` can mirror the parquet files into a Drive folder and append the
latest day's rows for your watchlist into the Sheet. It uses a **service account**:

1. Create a service account, download its JSON key.
2. Share the Drive folder and the Sheet with the service-account email.
3. Add repo secrets `GOOGLE_SA_JSON`, `DRIVE_FOLDER_ID`, `SHEET_ID`.

`update.yml` runs that step only when `GOOGLE_SA_JSON` is set. Credentials are read
from the environment and are never hard-coded.

**No-service-account alternative:** because the repo is public, the Sheet can pull the
latest CSV straight from the repo's raw URL with a formula, e.g.
`=IMPORTDATA("https://raw.githubusercontent.com/<you>/<repo>/main/data/csv/cm/cm_2026-10-16.csv")`.

## ArthaSaar layer

Merged in from the IpoBodh/ArthaSaar bundle. This is the market-data + alerting +
forecasting side: it publishes Telegram briefs and runs TimesFM forecasts.

| Piece | What it does | Trigger |
|---|---|---|
| `fetch_arthasaar_data.py` | pulls 16 market-data JSONs into `data/` | start of each Telegram job |
| `telegram_brain.py` | morning pre-open brief / afternoon day-analysis | `telegram-morning.yml`, `telegram-day.yml` |
| `telegram_alert.py` | open/close alert, live movers + OI | `telegram.yml` |
| `morning_unified.py` | single 8:30 AM merged brief | `telegram-morning.yml` |
| `timesfm_forecast.py` | TimesFM 3.0 forecasts, 88 series, 7d-3m | `timesfm-forecast.yml` |

**Secrets required** (Settings > Secrets and variables > Actions):
`TG_TOKEN`, `TG_CHAT_ID` (comma-separated for several chats), `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_CHAT_ID`. Without them the jobs run but cannot send.

Run any of them locally without sending:

```bash
python scripts/fetch_arthasaar_data.py
python scripts/telegram_brain.py morning --dry
TG_DRY=1 python scripts/morning_unified.py
```

### IMPORTANT - the data source is currently unreachable

`fetch_arthasaar_data.py` pulls from `devrajai/ArthaSaar`. As of this merge that repo
returns **404** to the public raw URL, so all 16 files come back MISSING and the
Telegram messages would go out nearly empty ("no data sections survived"). A 404 on a
private repo looks identical to a deleted one.

Two fixes, either works:

1. **If the repo is private**, add a PAT as the `ARTHASAAR_TOKEN` secret - the script
   now falls back to the GitHub contents API, which works for private repos.
2. **If it moved**, set `ARTHASAAR_REPO=owner/name` (and optionally `ARTHASAAR_BRANCH`).

Set `SITE_URL` if you want a link in the Telegram footer; otherwise it is omitted.

## Candle archive (Google Drive)

The GitHub candle source is gone too - `devrajai/ArthaSaar` and its `candles` release
tag both 404. The surviving copy is the **ArthaSaar Backup** folder in Google Drive
(27 Sep 2026): ~2,119 symbols, 5-year daily candles (`daily-00..21.json.gz`), full
history since listing (`full-00..21.json.gz`) and intraday (`intraday.json.gz`).

```bash
# restore from Drive (needs a service account, same as sync_google.py)
python scripts/candles_from_drive.py --folder-id <DRIVE_FOLDER_ID> --kind daily
python scripts/candles_from_drive.py --kind full

# or from already-downloaded .json.gz files, no creds needed
python scripts/candles_from_drive.py --local-dir ./downloaded --kind daily

# build a model-ready table
python scripts/build_features.py --in data/candles/daily.parquet
```

Outputs: `data/candles/<kind>.parquet` (symbol, ts, date, open, high, low, close,
volume) and `data/training/features.parquet` (9 features + forward-return labels).
Both are git-ignored - they are large and reproducible from Drive.

**This fixes charts, backtesting and model training. It does NOT fix the Telegram
jobs** - those read the 16 *derived analytics* JSONs (smart-brain, breadth, fii-dii,
...), which are a different dataset and are not in the Drive backup.

## Candle archive from NSE (self-sustaining)

The Drive backup is a frozen snapshot. To keep the price feed alive without any
third-party pipeline, grow the archive from the bhavcopy the hub already downloads:

```bash
# ingest what the daily job has archived
python scripts/candles_from_bhavcopy.py --from-local

# backfill history straight from NSE (weekends/holidays skipped automatically)
python scripts/candles_from_bhavcopy.py --backfill 2024-01-01 2026-10-16
```

Output `data/candles/cm_daily.parquet` is append-safe - re-running never duplicates
a symbol/date. This is the official exchange record, free and key-less.

## Watchdog

`health.yml` runs daily and checks that each feed is fresh (bhavcopy, YouTube, candles).
If any has gone stale it opens a GitHub issue - so a silent breakage tells you instead
of going quiet. Run it yourself any time:

```bash
python scripts/check_freshness.py --max-age 4
```

## Telegram analytics status

`build_analytics.py` regenerates the JSONs the hub can derive from its own data:

| JSON | Source | Status |
|---|---|---|
| `futures.json` | F&O bhavcopy | regenerated - stock-futures OI, index futures, Nifty PCR + max pain |
| `breadth.json` | candle archive | regenerated - % above 200-day EMA |
| `timesfm_forecasts.json` | TimesFM job | produced nightly |
| 11 others | old ArthaSaar pipeline | **not available** - smart-brain, mood, gti, oi-gti, radar, events, global, fii-dii, mf-top, preopen, brain-screener |

So the Telegram jobs still cannot run end to end. The analytics step is a partial
revival; the remaining 11 need the old pipeline rebuilt or another source.

## Data sources (what the hub pulls, and how)

| Source | Script | What you get | Caveat |
|---|---|---|---|
| **NSE bhavcopy** | `fetch_bhavcopy.py` | equities + F&O, every listed symbol | none - the exchange's own record, free, no key |
| **Yahoo Finance** | `fetch_yahoo.py` | indices, global, FX, commodities, crypto, longer history | unofficial (`yfinance`); rate-limited; not a licensed feed |
| **YouTube** | `fetch_youtube.py` | 10 channels' uploads, views, thumbnails | the feed carries only the ~15 latest per channel |
| **Google Sheets** | `fetch_from_sheets.py` | any tab you maintain, snapshotted per run | needs a service account |
| **Notion** | `fetch_notion.py` | any database | needs `NOTION_TOKEN` + the DB shared with the integration |
| **Google Finance** | - | **no API.** Only via `=GOOGLEFINANCE()` inside a Sheet, then pull that tab with `fetch_from_sheets.py` | historical data cannot be pulled via the API at all |
| **ArthaSaar Drive archive** | `candles_from_drive.py` | 2,119 symbols, 5y daily + intraday | frozen 27 Sep 2026 |
| **ArthaSaar data repo** | `fetch_arthasaar_data.py` | the 16 analytics JSONs | source is 404 - dead |

```bash
python scripts/fetch_yahoo.py --group indices --period 5y
python scripts/fetch_from_sheets.py --spreadsheet-id <ID> --range "Quotes!A1:F50"
NOTION_TOKEN=... python scripts/fetch_notion.py --database-id <ID> --name trades
```

Companion docs (Google Drive):
- **Chart Patterns - reference** - the pattern shapes, plus the numeric rules to detect
  them on the archive, and the discipline that decides whether they work.
- **Market Data Hub - Index** - what holds what across the repo, Drive and Sheets.

## Indicators (verified library)

`indicators.py` is a dependency-light TA library (pure pandas/numpy) - SMA, EMA, WMA,
RSI, MACD, Bollinger, ATR, Stochastic, ADX/DI, OBV, VWAP, Donchian, CCI, ROC,
Williams %R, Supertrend, and `add_all()` for the whole set.

```bash
python scripts/test_indicators.py        # proves it correct - see below
python scripts/build_indicators.py       # whole archive -> data/indicators/latest.parquet
python scripts/build_indicators.py --history   # + per-symbol history
```

It is **verified**, not just written: `test_indicators.py` recomputes every indicator
with an independent implementation (explicit loops, a different code path) and requires
a match, then runs a **no-look-ahead** check - indicators computed on the full series
must equal those computed on a truncated series for the overlapping rows. If a value at
bar *i* depended on any bar after *i*, that test fails. All 31 columns pass.

Conventions are stated in the file so nothing is ambiguous: EMA seeds from the first
value (`adjust=False`), RSI/ATR/ADX use Wilder smoothing, windows are trailing.

## Forecasts (free models, honest accuracy)

`forecast.py` is model-agnostic. It runs whatever is available and reports how each
model actually did on held-out data, so you can see whether a fancy model beats a dumb
baseline instead of assuming it.

| Model | What it is |
|---|---|
| naive / drift / mean / seasonal_naive | baselines - no dependencies |
| ets | statsmodels Holt-Winters |
| arima | statsmodels ARIMA(1,1,1) |
| timesfm | Google TimesFM (2.5-200M via the `timesfm` package - heavy) |
| chronos | Amazon Chronos (only if `chronos` is installed) |

```bash
python scripts/forecast.py --horizon 21
python scripts/forecast.py --models naive,ets --symbols RELIANCE
```

Validation is **walk-forward**: the last `horizon` points are held out, each model is
fit only on earlier data, and the error is measured against the truth. Never a random
split - that leaks the future and makes every model look good. Output lands in
`data/forecast/` (`accuracy.csv` + `forecasts.parquet`).

**The baseline is the bar to clear.** On real data, `naive` (carry the last price
forward) is genuinely hard to beat - if a model cannot beat it, it is not earning its
complexity. `timesfm`/`chronos` are optional: they need a large download and a lot of
RAM, so the job skips them cleanly when they are not installed rather than failing.

### TimesFM status: API fixed, inference still unproven

The bundled `timesfm_forecast.py` imported `from timesfm3 import ...`, which **does not
exist** in the package it needs - so it had never actually been run. It has been
rewritten against the real API (verified by inspecting the installed `timesfm` 3.0.2):

```python
TimesFM_2p5_200M_torch.from_pretrained("google/timesfm-2.5-200m-pytorch")
model.compile(ForecastConfig(max_context=512, max_horizon=63, per_core_batch_size=1))
points, quantiles = model.forecast(horizon=63, inputs=[series, ...])
```

What that proved: the checkpoint **downloads**, the API is correct, and a load failure
is now handled gracefully instead of crashing.

What it did **not** prove: inference. The 200M checkpoint plus torch needs roughly
3-4 GB of RAM, and the build environment had 2 GB, so it aborted with a memory error.
That is a container limit, not a code fault - but it means **nobody has seen this model
produce a forecast yet**.

It is therefore gated **off by default** (`RUN_TIMESFM` repo variable). Do not turn it
on and trust the output until you have watched it run on a machine with the memory.
Until then, the baselines in `forecast.py` are the honest reference.

## Crypto

```bash
python scripts/fetch_crypto.py            # config/crypto_symbols.json
python scripts/fetch_crypto.py --source yahoo
```

Binance public REST is the primary source (free, no key, deep history); Yahoo is the
fallback. Both are unofficial for redistribution - fine for research, not for resale.
Output: `data/crypto/<pair>.parquet`.

## Correctness: corporate actions & validation

**`corporate_actions.py`** fixes the biggest silent bug in the hub. The candle archive
comes from the raw bhavcopy, which is *unadjusted* - so a 1:10 split looks like a -90%
day, and every indicator, feature and forecast built on it is reading a fiction.

```bash
python scripts/corporate_actions.py --fetch     # NSE corporate actions
python scripts/corporate_actions.py --adjust    # back-adjust the candle archive
```

Back-adjustment multiplies pre-ex-date prices by the action's factor, leaving the most
recent price untouched. Verified on a synthetic 1:2 split: the fake -50% crash becomes
a continuous series (max 1-day return 0.000000).

**The adjustment is actually used, not just produced.** It writes `<name>_adj.parquet`,
and every consumer (features, indicators, forecast, backtest, patterns, relative
strength, validation) resolves its input through `_archive.pick_candles()`, which
prefers the adjusted file. The pipeline runs the adjustment at step 5b - *before* any
analysis - so nothing downstream ever sees an unadjusted split.

**`validate_data.py`** checks for impossible bars (`high < low`), nulls, negative
volume, duplicate symbol/date rows, long gaps, staleness, and unexplained extreme moves.
It uses the corporate-actions file to *avoid* flagging legitimate splits as errors, and
exits 1 on real errors so the pipeline can raise an alert.

## Backtest (walk-forward, with costs)

`backtest.py` is what turns indicators into evidence. Without it, everything else is
just numbers.

```bash
python scripts/backtest.py --strategy sma_cross --fast 20 --slow 50 --stop 0.08 --target 0.20
python scripts/backtest.py --strategy rsi_reversion --cost-bps 5
```

Strategies: `sma_cross`, `rsi_reversion`, `breakout`, `momentum`.

It enforces the rules that make backtests lie when skipped:

- **No look-ahead.** A signal from bar *i* executes at bar *i+1*'s **open**.
- **Costs** charged per side; **stops/targets** checked intrabar against the low/high.
- **Open positions at the end are closed**, not dropped.
- **Time-sliced reporting** (`--windows`) so you can see if an edge is stable or lucky.

`test_backtest.py` proves the timing rather than asserting it: entry/exit land on the
right bar, the stop fills at the stop price, cost drag equals two sides, and a
future-peeking signal does **not** produce an absurd return.

## Screens, patterns, relative strength

```bash
python scripts/screen.py --list                  # 12 transparent rules
python scripts/screen.py --rule oversold
python scripts/patterns.py --all                 # numeric chart-pattern detection
python scripts/relative_strength.py --benchmark NIFTY50
```

Screens are one-line predicates over `data/indicators/latest.parquet`. Patterns
implement the rules from the Chart Patterns doc (double top/bottom, head & shoulders,
bull flag, triangle, hammer, shooting star, engulfing). Relative strength ranks symbols
against a benchmark - a stock up 5% while the index is up 12% is *weak*, not strong.

## More free data

| Script | What it adds |
|---|---|
| `fetch_nse_extra.py` | FII/DII flows, 2,619-symbol master, index constituents (Nifty 50/500/Bank/IT/Next50), corporate announcements |
| `fetch_amfi.py` | every mutual fund's daily NAV (AMFI, plain text, no key) |
| `fetch_news.py` | market headlines from free RSS feeds |

`fetch_amfi.py` and `fetch_news.py` are blocked behind some proxies (including this
sandbox) and skip cleanly with exit 0 - they work from normal CI runners.

## The website (GitHub Pages)

A static dashboard lives in `docs/` and is served by GitHub Pages — no build step, no
server, no dependencies. It reads one file, `docs/data.json`.

Why one file: most outputs (indicators, screens, forecasts, quality) are git-ignored,
so the site cannot fetch them from the repo. `build_site_data.py` runs inside the
pipeline, where those files exist, and folds the useful parts into that single JSON.

```bash
python scripts/build_site_data.py     # -> docs/data.json
```

To publish it: **Settings → Pages → Source: Deploy from a branch → main → /docs**.
It then lives at `https://<user>.github.io/<repo>/` and refreshes every time the
pipeline commits new data.

The page is self-contained (inline CSS/JS, no CDN) so a blocked external domain can
never break it. Sections appear only when their data exists.

### UI

Liquid-glass design system, fully dark **and** light:

- **Theme** — follows `prefers-color-scheme` on first visit, then remembers your choice
  in `localStorage`. Toggled from the header; set before first paint so there is no flash.
- **Glass surfaces** — `backdrop-filter: blur(22px) saturate(180%)` with a 1px light
  border and a top sheen; three slowly drifting colour blobs sit behind everything.
- **Layout** — sticky glass header with a segmented tab control (Overview / Market /
  YouTube / Signals / Data), KPI tile grid, then cards that reflow 2-up on desktop and
  1-up on mobile.
- **Tables** — sticky headers, tabular-nums for figures, abbreviated large numbers
  (Cr / L / k), colour-coded changes, hover highlighting.
- **Filter** — one search box filters the rows and bars of the view you are on.
- **Details** — `prefers-reduced-motion` respected, focus-visible outlines, ARIA roles on
  the tabs, deep-linkable views via `#market` etc., skeleton loading and a clear error
  state if `data.json` is missing.

Verified by executing the real render logic against the real `data.json` through a DOM
shim: 5 views, 25 cards, 12 tables, 118 rows, all sections present, no runtime errors.

## Limits & notes

- Google Sheets: 10,000,000 cells per workbook — keep the Sheet a view, not the store.
- GitHub: soft repo-size warning ~1 GB, hard block ~5 GB, 100 MB max per file. Parquet
  keeps this small; raw zips are git-ignored for that reason.
- Scheduled workflows on public repos are disabled after 60 days with no repo activity —
  the bot's own commits count as activity, so a healthy hub stays alive.
- `GOOGLEFINANCE()` in Sheets is delayed up to 20 min and its **historical** data cannot
  be pulled via the API or Apps Script (returns `#N/A`). Use this archive for history.

## Legal

NSE/BSE market data is subject to the exchanges' Data Sharing & Usage Policy. Personal
use of the bhavcopy files is generally fine. **Public redistribution** — e.g. serving
this data on a website — may require a licence. Check before you publish.
