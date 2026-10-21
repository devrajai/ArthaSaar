#!/usr/bin/env bash
# run_pipeline.sh - the whole hub in one sequence: collect -> analyse -> verify.
#
# This is the same order the GitHub workflow runs, so what you test locally is what
# runs in CI. Every step is independent: one failing does not abort the rest, and the
# script exits non-zero if anything failed, so the workflow can raise an alert.
#
# Optional steps run only when their credentials are present, so the pipeline works
# out of the box and grows as you add sources.
#
# Usage:
#   bash scripts/run_pipeline.sh              # everything configured
#   SKIP_YAHOO=1 bash scripts/run_pipeline.sh # skip a slow step
set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

FAILED=0
STEPS_OK=0
STEPS_RUN=0

step()  { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }
run()   {
  STEPS_RUN=$((STEPS_RUN + 1))
  if "$@"; then STEPS_OK=$((STEPS_OK + 1)); return 0
  else echo "  [warn] step failed: $*"; FAILED=$((FAILED + 1)); return 1; fi
}
skip()  { echo "  [skip] $* (not configured)"; }

echo "==================================================================="
echo " ArthaSaar pipeline  $(date -u +%Y-%m-%dT%H:%M:%SZ)  (UTC)"
echo "==================================================================="

# ---------------------------------------------------------------- 1. market data
step "1. NSE bhavcopy (equities + F&O)"
run python scripts/fetch_bhavcopy.py --latest || true

step "2. Yahoo Finance (indices, global)"
if [ "${SKIP_YAHOO:-0}" = "1" ]; then skip "yahoo"; else
  run python scripts/fetch_yahoo.py --group indices --period 5y || true
fi

# ---------------------------------------------------------------- 2. youtube
step "3. YouTube channels -> uploads"
run python scripts/fetch_youtube.py || true

step "4. YouTube analysis (the brain)"
run python scripts/analyze_youtube.py || true

# ---------------------------------------------------------------- 3. derived data
step "5. Candle archive from bhavcopy"
run python scripts/candles_from_bhavcopy.py --from-local || true

step "5b. Corporate actions + price adjustment (BEFORE any analysis)"
run python scripts/corporate_actions.py --fetch || true
run python scripts/corporate_actions.py --adjust || true

step "6. Analytics (futures, breadth)"
run python scripts/build_analytics.py || true

step "7. Feature table (if the archive has enough history)"
if [ -f data/candles/cm_daily.parquet ] || [ -f data/candles/daily.parquet ]; then
  run python scripts/build_features.py || true
else
  skip "features (no candle archive yet)"
fi

# ---------------------------------------------------------------- 4. optional sources
step "7b. Indicators (verified library)"
run python scripts/build_indicators.py || true

step "7c. Forecasts (free models, walk-forward accuracy)"
run python scripts/forecast.py --models naive,drift,mean,seasonal_naive,ets,arima || true

step "7d. Crypto (Binance, Yahoo fallback)"
run python scripts/fetch_crypto.py || true

step "7f. Data quality check"
run python scripts/validate_data.py || true

step "7g. Patterns + relative strength + screens"
run python scripts/patterns.py --all || true
run python scripts/relative_strength.py || true
run python scripts/screen.py --rule trend_up || true
run python scripts/screen.py --rule oversold || true

step "7h. Reference backtest"
run python scripts/backtest.py --strategy sma_cross --fast 20 --slow 50 --stop 0.08 --target 0.20 || true

step "7i. NSE reference data (FII/DII, symbol master, indices)"
run python scripts/fetch_nse_extra.py || true

step "7j. Mutual fund NAVs (AMFI)"
run python scripts/fetch_amfi.py || true

step "7k. News headlines (RSS)"
run python scripts/fetch_news.py || true

step "7l. Website data (docs/data.json)"
run python scripts/build_site_data.py || true

step "8. Google Drive archive (if configured)"
if [ -n "${GOOGLE_SA_JSON:-}${GOOGLE_APPLICATION_CREDENTIALS:-}" ] && [ -n "${ARTHASAAR_DRIVE_FOLDER:-}" ]; then
  run python scripts/candles_from_drive.py --kind daily || true
else
  skip "drive archive (no credentials/folder)"
fi

step "9. Google Sheets (if configured)"
if [ -n "${GOOGLE_SA_JSON:-}${GOOGLE_APPLICATION_CREDENTIALS:-}" ] && [ -n "${SHEET_SOURCE_ID:-}" ] && [ -n "${SHEET_SOURCE_RANGE:-}" ]; then
  run python scripts/fetch_from_sheets.py --spreadsheet-id "$SHEET_SOURCE_ID" --range "$SHEET_SOURCE_RANGE" || true
else
  skip "sheets (no credentials/range)"
fi

step "10. Notion (if configured)"
if [ -n "${NOTION_TOKEN:-}" ] && [ -n "${NOTION_DATABASE_ID:-}" ]; then
  run python scripts/fetch_notion.py --database-id "$NOTION_DATABASE_ID" --name "${NOTION_NAME:-notion}" || true
else
  skip "notion (no token/database)"
fi

step "11. ArthaSaar analytics JSONs (only if ARTHASAAR_TOKEN is set)"
# The default source (devrajai/ArthaSaar) is now THIS repo, which holds only a
# couple of the 16 files - so this step self-fetches unless pointed elsewhere.
# It runs only when a token is supplied, i.e. when you know the source is live.
if [ -n "${ARTHASAAR_TOKEN:-}" ]; then
  run python scripts/fetch_arthasaar_data.py || true
else
  skip "arthasaar data (no ARTHASAAR_TOKEN)"
fi

# ---------------------------------------------------------------- 5. verify
step "12. Freshness check (watchdog)"
run python scripts/check_freshness.py --max-age 4 || true

echo ""
echo "==================================================================="
echo " pipeline done: $STEPS_OK/$STEPS_RUN steps ok, $FAILED failed"
echo "==================================================================="
exit "$FAILED"
