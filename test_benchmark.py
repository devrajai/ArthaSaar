import time
from scripts.history_collect import universe_build, collect, BATCH

def main():
    print("Building universe...")
    universe = universe_build()

    # Take a smaller universe for benchmarking to save time, e.g. 300 stocks (3 batches)
    test_universe = universe[:500]
    names = {}

    print(f"Benchmarking collect for {len(test_universe)} items...")
    start_time = time.time()
    got = collect(test_universe, "1mo", "daily", names)
    end_time = time.time()

    print(f"Time taken: {end_time - start_time:.2f} seconds")
    print(f"Items collected: {len(got)}")

if __name__ == "__main__":
    main()
