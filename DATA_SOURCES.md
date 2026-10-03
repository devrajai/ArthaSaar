# ArthaSaar free-data policy

ArthaSaar is designed around public/free snapshots hosted on GitHub Pages.

## Primary public sources

- NSE India: equity reports, security delivery, F&O UDiFF/bhavcopy, index snapshots, all-index daily close, circulars and filings.
- AMFI: daily mutual-fund NAV download.
- Google News RSS: headline aggregation and news-volume counts.
- Yahoo Finance/yfinance: secondary historical-price source and fallback where an official daily file is not practical.
- CoinGecko: free-tier crypto snapshot, cached by GitHub Actions.
- ArthaSaar calculations: breadth, GTI, X-Ray and other derived analytics.

## Freshness rules

A browser refresh only reloads the latest committed JSON files. It does not turn the site into a live exchange feed.

Each card should identify whether data is LIVE/INTRADAY, EOD, PROVISIONAL, DERIVED/MODEL, or STALE.

## Important limitations

- NSE public files are trading-day/EOD data and can be revised.
- Yahoo/yfinance is a third-party source and can be rate-limited.
- Google News RSS is an aggregator; headline sentiment is heuristic.
- CoinGecko's free tier has request/usage limits, so ArthaSaar caches it serverlessly through GitHub Actions.
- Derived analytics are calculations, not exchange-provided recommendations.

## Source links

- https://www.nseindia.com/all-reports
- https://www.nseindia.com/all-reports-derivatives
- https://www.nseindia.com/reports-indices-historical-index-data
- https://www.amfiindia.com/net-asset-value/nav-download
- https://news.google.com/rss
- https://finance.yahoo.com/
- https://www.coingecko.com/en/api/pricing


## Research Lab architecture

Research Radar / Research Lab separates:
- **Observed** — directly published by NSE/public sources.
- **Calculated** — computed by ArthaSaar from committed snapshots.
- **Historical** — event-study and signal-outcome calculations using only dates after each recorded signal.
- **Unavailable** — shown explicitly when required fields (for example true session-open gaps or OHLC-based ATR) are not present.

The Research Lab also stores daily market-replay snapshots, research-signal outcomes, NIFTY 50 membership history and a free GitHub Actions alert feed. General historical studies can still have survivorship bias; NIFTY 50-aware companion statistics use the stored membership snapshot nearest to each event date.
