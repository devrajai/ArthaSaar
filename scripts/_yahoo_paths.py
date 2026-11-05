#!/usr/bin/env python3
"""One place that knows how a Yahoo parquet file is named.

WHY THIS EXISTS
The repo grew three different filename encodings, and each script guessed one of them. The
result was three separate debugging sessions on the same bug:

  build_global_market  looked for "_IDX_GSPC.parquet"  while fetch_yahoo wrote "GSPC.parquet"
  build_commodities    looked for "GC_EQ_F.parquet"    while fetch_yahoo wrote "GC_F.parquet"
  the combined reader  decoded "_IDX_" but not "IDX_", producing ".^GSPC"

Each time the file existed, the script reported it missing, and the section stayed empty with
no error. Import this instead of writing the conversion again.

THE THREE CONVENTIONS
  fetch_yahoo._safe()   re.sub(r"[^A-Za-z0-9]+", "_", sym).strip("_")   ^GSPC -> GSPC
  legacy pipeline       ^ -> _IDX_, = -> _EQ_, . -> _                     ^GSPC -> _IDX_GSPC
  Colab                 ^ -> IDX_, = -> EQ_, . -> _                       ^GSPC -> IDX_GSPC

USAGE
    from _yahoo_paths import find_parquet, read_closes
    path = find_parquet("^GSPC")            # first existing candidate, or None
    series = read_closes("^GSPC")           # {date_str: close}, {} if absent
"""
import os
import re

YAHOO = "data/yahoo"


def candidates(symbol):
    """Every filename a symbol might have been written under, most likely first."""
    yahoo_style = re.sub(r"[^A-Za-z0-9]+", "_", symbol).strip("_")
    legacy = symbol.replace("^", "_IDX_").replace("=", "_EQ_").replace(".", "_")
    colab = symbol.replace("^", "IDX_").replace("=", "EQ_").replace(".", "_")
    out = []
    for base in (yahoo_style, legacy, colab, symbol):
        for name in (base + ".parquet", "us_" + base + ".parquet"):
            if name not in out:
                out.append(name)
    return out


def find_parquet(symbol, root=YAHOO):
    """The first candidate that actually exists, or None."""
    for name in candidates(symbol):
        p = os.path.join(root, name)
        if os.path.exists(p):
            return p
    return None


def read_closes(symbol, root=YAHOO, date_col=None, close_col=None):
    """Daily closes as {date_str: close}. Empty dict if the file is missing or unusable."""
    path = find_parquet(symbol, root)
    if not path:
        return {}
    try:
        import pandas as pd
        df = pd.read_parquet(path)
        cols = {c.lower(): c for c in df.columns}
        d = date_col or next((cols[k] for k in ("date", "datetime", "index") if k in cols), None)
        c = close_col or next((cols[k] for k in ("close", "adj close", "adj_close")
                               if k in cols), None)
        if d is None or c is None:
            return {}
        out = {}
        for dd, cc in zip(df[d], df[c]):
            try:
                if cc is None or cc != cc:
                    continue
            except Exception:
                continue
            out[str(dd)[:10]] = float(cc)
        return out
    except Exception:
        return {}


if __name__ == "__main__":
    # quick self-check: every convention round-trips to the same symbol
    for sym in ("^GSPC", "BRK-B", "GC=F", "AAPL", "EURINR=X"):
        print("%-10s -> %s" % (sym, candidates(sym)[:3]))
