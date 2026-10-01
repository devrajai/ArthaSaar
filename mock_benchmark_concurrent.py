import time
import pandas as pd
from scripts.history_collect import universe_build, BATCH

# Mock yfinance
import yfinance as yf
def mock_download(tickers, *args, **kwargs):
    time.sleep(1) # simulate network delay
    return pd.DataFrame()

yf.download = mock_download

import concurrent.futures

def to_bars(sub):
    return None

def collect_concurrent(universe, period, prefix, names):
    got = {}
    batches = []
    for i in range(0, len(universe), BATCH):
        batches.append((i, universe[i:i + BATCH]))

    def fetch_batch(args):
        i, batch = args
        tickers = [ys for _, ys, _ in batch]
        df = None
        for attempt in range(2):
            try:
                df = yf.download(tickers, interval="1d", period=period,
                                 progress=False, auto_adjust=False, group_by="ticker",
                                 threads=True, timeout=60)
                break
            except Exception as e:
                print("batch fail @", i, e, "- retry")
                time.sleep(5)
        return i, batch, df

    completed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_batch, b): b for b in batches}
        for future in concurrent.futures.as_completed(futures):
            i, batch, df = future.result()
            tickers = [ys for _, ys, _ in batch]
            if df is not None and not df.empty:
                single = len(tickers) == 1
                for disp, ys, name in batch:
                    try:
                        sub = df[ys] if not single else df
                    except KeyError:
                        continue
                    if sub is None:
                        continue
                    try:
                        bars = to_bars(sub)
                    except Exception:
                        bars = None
                    if bars and len(bars["t"]) >= 30:
                        got[disp] = bars
                        names[disp] = name
            completed += len(batch)
            print(f"  {prefix} {completed}/{len(universe)} -> {len(got)} ok", flush=True)
    return got

def main():
    universe = [("SYM" + str(i), "SYM" + str(i) + ".NS", "Name" + str(i)) for i in range(1000)]
    names = {}

    print(f"Benchmarking concurrent collect for {len(universe)} items...")
    start_time = time.time()
    got = collect_concurrent(universe, "1mo", "daily", names)
    end_time = time.time()

    print(f"Time taken: {end_time - start_time:.2f} seconds")
    print(f"Items collected: {len(got)}")

if __name__ == "__main__":
    main()
