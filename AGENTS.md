# AGENTS.md — ArthaSaar house rules

Read this before changing anything. This repo is a **data hub plus a static website**. It
is not a framework project, and several deliberate choices exist because simpler-looking
alternatives already failed in production. Please do not undo them.

## What this repo is

- A GitHub Actions pipeline (`/.github/workflows/pipeline.yml`) collects free market data,
  writes JSON, and commits it.
- The website is **one file**: `docs/index.html`. It is served by GitHub Pages from
  `docs/`. There is no build step, no bundler, no framework, no CDN, and no server.
- `docs/*.json` are **generated**. Never hand-edit them. Change the script that writes them.

## Hard rules

1. **Plain CSS only.** Do NOT use `color-mix()`, `backdrop-filter`, CSS nesting, or
   `:has()`. They have already failed on the user's phone. Use hex/rgba and plain
   properties.
2. **No external requests from the page** except to files in `docs/`. No CDN fonts, no
   chart libraries. Charts are hand-drawn inline SVG.
3. **Generated files are off-limits to hand editing**: `docs/data.json`, `stocks.json`,
   `universe.json`, `screener.json`, `crypto.json`, `global.json`, `indices.json`,
   `sectors.json`, `etf.json`, `mf.json`, `search.json`. Each is written by a script.
4. **Every new pipeline step ends with `|| true`** so one flaky source cannot fail the
   whole run:
   ```yaml
   - name: "7x. Something new"
     run: python scripts/whatever.py || true
   ```
   and the same step must be added to `scripts/run_pipeline.sh` so a local run matches CI.
5. **Python scripts that import pandas or pyarrow MUST end with the hard-exit guard.**
   pyarrow aborts during interpreter teardown on the CI runner
   (`terminate called without an active exception` → SIGABRT → exit 134). It fires
   *after* `main()` has finished, but it turned the whole pipeline red. Copy this exactly:
   ```python
   if __name__ == "__main__":
       _rc = main()
       import os as _os, sys as _sys
       _sys.stdout.flush(); _sys.stderr.flush()
       _os._exit(_rc)
   ```
6. **Never `eval()` anything from a JSON file.** Filters are real functions in a `PRED`
   object inside `docs/index.html`. A data file must never be able to execute code.
7. **Free data only. No API keys, no paid sources.** If a source needs a key, skip it and
   say so rather than adding a secret.
8. **Be honest in the UI.** If a number cannot be computed, omit the row rather than
   showing 0 or a guess. Every card has an `info` object with `what`, `source`, `updated`
   and usually `note` — fill those in truthfully.
9. **Do not break the tests.** CI runs `scripts/test_indicators.py`,
   `test_backtest.py`, `test_timesfm.py`, `test_mf.py`. All must still pass.
10. **Table contract**: a section object is
    `{"columns": ["a","b"], "rows": [["x",1],["y",2]], "total": 2}`. Row arrays must match
    the columns array in order.

## How the site loads (do not regress this)

The page used to fetch ~2.3 MB before showing anything, which looked like a hang. Now:

```js
var CORE  = ["data.json","config.json","learn.json","charges.json","crypto.json","etf.json"];
var HEAVY = ["stocks.json","universe.json","screener.json","indices.json","sectors.json","global.json","mf.json"];
// CORE renders the first paint. HEAVY loads behind it and re-renders.
// search.json (~240 KB) is fetched only when the search box is opened.
```

If you add a data file, decide which group it belongs to and register it in **both** the
loader and the `assign()` switch. A new heavy file must not go in `CORE`.

**A file that is generated but never fetched fails silently.** The page shows an empty
card, not an error. This has already happened once: `mf.json` was written by the pipeline
and committed, but it was in neither `CORE` nor `HEAVY`, so the Mutual Funds tab read
"No fund data yet" while the data sat there perfectly correct. Before you finish any task
that adds a JSON file, grep for it and confirm it appears in the loader list **and** in the
`assign()` switch. Two matches, not one.

## How a section is added

In `docs/index.html`, inside `build(d)`, each tab is an IIFE:

```js
(function(){
  var v = sec("mysection");              // creates #sec-mysection
  v.appendChild(card("Title", "subtitle", [ kids ], {
    what: "...", source: "...", updated: when, note: "..."
  }));
})();
```

and the tab is registered in the `SECTIONS` array. Cards that contain a table get a CSV
export button automatically.

## Pipeline order (do not reorder casually)

1 bhavcopy → 2 yahoo → 3 youtube → 4 brain → 5 candles → 5b corporate actions → 6 analytics
→ 7 features → 7b indicators → 7c forecasts → 7d crypto → 7f validate → 7g patterns/RS/screens
→ 7h backtest → 7i NSE extra → 7j AMFI → 7k news → 7l spikes → 7m universe → 7m1b indices
→ 7m1c sectors → 7m2 stock pages → 7m2b ETFs → 7m2c funds → 7m3 crypto pages → 7m4 global
→ 7n screener → 7n2 search index → 7o site data → 8 freshness → commit.

## Verified free sources (use these; they are known to work)

- NSE archives (works from CI and most networks):
  `https://nsearchives.nseindia.com/content/cm/BhavCopy_NSE_CM_0_0_0_YYYYMMDD_F_0000.csv.zip`
  `https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv` (symbol master)
  `https://nsearchives.nseindia.com/content/equities/eq_etfseclist.csv` (ETF list)
  `https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv` (and siblings)
- NSE `www.nseindia.com/api/*` (works from CI, needs a browser User-Agent):
  `fiidiiTradeReact`, `corporates-corporateActions?index=equities`
- Yahoo Finance chart API (works everywhere; no CORS header, so browser calls must go
  through the Cloudflare Worker in `worker/`)
- mfapi.in — mutual fund NAV history (works from CI)
- Publisher RSS for news

Known NOT to work: **BSE** (returns 403 to non-browser clients), **Binance** (HTTP 451
from US runners — use Yahoo `<COIN>-USD` instead), CoinGecko from some networks.

## Style of the code you are joining

Comments explain **why**, not what. Where a bug was fixed, the comment says what broke.
Keep that. Prefer a clear comment over a clever line.
