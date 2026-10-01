import time
import pandas as pd
from scripts.history_collect import universe_build, BATCH

# Mock yfinance
import yfinance as yf
def mock_download(tickers, *args, **kwargs):
    time.sleep(1) # simulate network delay
    return pd.DataFrame()

yf.download = mock_download

from scripts.history_collect import collect

def main():
    universe = [("SYM" + str(i), "SYM" + str(i) + ".NS", "Name" + str(i)) for i in range(1000)]
    names = {}

    print(f"Benchmarking collect for {len(universe)} items...")
    start_time = time.time()
    got = collect(universe, "1mo", "daily", names)
    end_time = time.time()

    print(f"Time taken: {end_time - start_time:.2f} seconds")
    print(f"Items collected: {len(got)}")

if __name__ == "__main__":
    main()
