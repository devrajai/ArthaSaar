#!/usr/bin/env python3
"""
test_timesfm.py - verify the TimesFM forecast pipeline WITHOUT loading the model.

The real checkpoint needs 3-4 GB of RAM, so it cannot run in a small container. That
leaves a gap: the script could be wrong and nobody would know until the nightly job.
This closes the gap by substituting a stub model that returns known numbers, then
checking the arithmetic and the output shape the site depends on.

It verifies:
  * series are picked up and the last CONTEXT points are fed to the model
  * median / low / high change percentages are computed from the right quantiles
  * confidence falls as the band widens
  * the JSON has the exact keys the website reads
  * a flat forecast does not produce a fake "up" direction

Usage: python scripts/test_timesfm.py
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path

import numpy as np

FAILS: list[str] = []


def check(name: str, cond: bool, detail: str = ""):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  ({detail})" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def install_stub(uplift: float, band: float, horizon: int, nq: int = 9):
    """A fake timesfm package: every series rises `uplift` with a symmetric band."""
    pkg = types.ModuleType("timesfm")
    sub = types.ModuleType("timesfm.timesfm_2p5")
    mod = types.ModuleType("timesfm.timesfm_2p5.timesfm_2p5_torch")
    cfg = types.ModuleType("timesfm.configs")

    class ForecastConfig:
        def __init__(self, **kw):
            self.__dict__.update(kw)

    class TimesFM_2p5_200M_torch:
        def __init__(self):
            self.compiled = None

        @classmethod
        def from_pretrained(cls, _id):
            return cls()

        def compile(self, config):
            self.compiled = config

        def forecast(self, horizon, inputs):
            n = len(inputs)
            pts = np.zeros((n, horizon))
            qs = np.zeros((n, horizon, nq))
            for i, s in enumerate(inputs):
                last = float(np.asarray(s, dtype=float)[-1])
                pts[i, :] = last * (1 + uplift)
                for j in range(nq):
                    frac = (j / (nq - 1)) * 2 - 1          # -1 .. +1
                    qs[i, :, j] = last * (1 + uplift + frac * band)
            return pts, qs

    mod.TimesFM_2p5_200M_torch = TimesFM_2p5_200M_torch
    cfg.ForecastConfig = ForecastConfig
    sys.modules["timesfm"] = pkg
    sys.modules["timesfm.timesfm_2p5"] = sub
    sys.modules["timesfm.timesfm_2p5.timesfm_2p5_torch"] = mod
    sys.modules["timesfm.configs"] = cfg


def load_script():
    path = Path(__file__).with_name("timesfm_forecast.py")
    spec = importlib.util.spec_from_file_location("tf_forecast", path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run_case(uplift, band, horizon, series, out_path):
    install_stub(uplift, band, horizon)
    m = load_script()
    m.load_series = lambda *a, **k: series          # bypass network / files
    sys.argv = ["timesfm_forecast.py", "--horizon", str(horizon),
                "--report-days", "21", "--out", out_path]
    rc = m.main()
    data = json.loads(Path(out_path).read_text())
    return rc, data


def main() -> int:
    print("=== TimesFM forecast logic (stub model) ===")

    series = {
        "^NSEI": np.linspace(20000, 25000, 600),      # last = 25000
        "RELIANCE": np.linspace(2000, 3000, 600),     # last = 3000
    }

    with tempfile.TemporaryDirectory() as td:
        # ---- case 1: +10% median, +-5% band ----
        out = str(Path(td) / "a.json")
        rc, d = run_case(0.10, 0.05, 63, series, out)
        check("exit code 0", rc == 0)
        check("has 'forecasts' list", isinstance(d.get("forecasts"), list) and len(d["forecasts"]) == 2,
              str(len(d.get("forecasts", []))))
        check("has 'model' and 'updated'", "model" in d and "updated" in d)
        check("horizon_days recorded", d.get("horizon_days") == 21)

        nif = d.get("nifty")
        check("nifty entry present", isinstance(nif, dict))
        if nif:
            check("median ~ +10%", abs(nif["median_chg_pct"] - 10.0) < 0.01, str(nif["median_chg_pct"]))
            check("low ~ +5%", abs(nif["low10_chg_pct"] - 5.0) < 0.01, str(nif["low10_chg_pct"]))
            check("high ~ +15%", abs(nif["high90_chg_pct"] - 15.0) < 0.01, str(nif["high90_chg_pct"]))
            check("confidence 60 (band 10%)", nif["confidence"] == 60, str(nif["confidence"]))
            check("direction up", nif["direction"] == "up", nif["direction"])

        # ---- case 2: wider band must mean LOWER confidence ----
        out2 = str(Path(td) / "b.json")
        _, d2 = run_case(0.10, 0.15, 63, series, out2)
        n2 = d2.get("nifty", {})
        check("wider band -> lower confidence",
              n2.get("confidence", 999) < nif["confidence"],
              f"{n2.get('confidence')} vs {nif['confidence']}")

        # ---- case 3: flat forecast must not claim a direction ----
        out3 = str(Path(td) / "c.json")
        _, d3 = run_case(0.0, 0.01, 63, series, out3)
        n3 = d3.get("nifty", {})
        check("flat -> direction 'flat'", n3.get("direction") == "flat", str(n3.get("direction")))
        check("flat -> median ~ 0", abs(n3.get("median_chg_pct", 9)) < 0.01, str(n3.get("median_chg_pct")))

        # ---- case 4: exact keys the website reads ----
        keys = {"symbol", "name", "last", "median_chg_pct", "low10_chg_pct", "high90_chg_pct",
                "confidence", "direction"}
        got = set(d["forecasts"][0].keys())
        check("site keys present", keys.issubset(got), str(keys - got))

        # ---- case 5: sorted best-first ----
        meds = [r["median_chg_pct"] for r in d["forecasts"]]
        check("sorted by median desc", meds == sorted(meds, reverse=True), str(meds))

    print()
    if FAILS:
        print(f"TIMESFM TEST FAILED ({len(FAILS)}): " + ", ".join(FAILS))
        return 1
    print("TIMESFM TEST PASSED - forecast maths and output shape are correct")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
