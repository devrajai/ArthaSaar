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
  update.yml               daily cron (13:30 UTC = 19:00 IST), commits new data
  backfill.yml             manual one-off history backfill
  telegram.yml             close summary (16:00 IST)
  telegram-morning.yml     8:30 AM IST morning brief
  telegram-day.yml         manual day analysis
  telegram-who.yml         manual chat-id lookup
  timesfm-forecast.yml     nightly TimesFM forecasts (20:35 IST)
  health.yml               daily freshness watchdog, opens an issue if stale
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

## Automating it

Push this folder to a **public** GitHub repo. `update.yml` then runs every weekday
after close and commits the new files. Public repos get unlimited Actions minutes —
that's why public is the right call for a daily job. To backfill history, run the
`backfill` workflow from the Actions tab with a date range.

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
