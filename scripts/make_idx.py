"""make_idx.py -- data/full-00.json se per-index chhote idx-<SYM>.json banao.
Monday ki history.yml run apne aap fresh bana legi; ye interim + fallback hai."""
import json
import pathlib

GRID_IDX = ["NIFTY", "BANKNIFTY", "SENSEX", "FINNIFTY", "MIDCPNIFTY", "NIFTYIT"]

src = json.loads(pathlib.Path("data/full-00.json").read_text())["syms"]
out = pathlib.Path("data")
n = 0
for s in GRID_IDX:
    b = src.get(s)
    if not b or len(b["t"]) < 30:
        print("skip (no data):", s)
        continue
    (out / ("idx-" + s + ".json")).write_text(
        json.dumps(b, separators=(",", ":")), encoding="utf-8")
    n += 1
    print("idx file:", s, len(b["t"]), "bars")
print("total:", n)
