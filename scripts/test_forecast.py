#!/usr/bin/env python3
"""
test_forecast.py - the walk-forward has to behave the way the theory says it should.

Two synthetic series with known properties:
  * a random walk, where the last close is the best available guess, so naive should not lose
    by much to anything else;
  * a steady trend, where a drift model should beat naive clearly.

If either of those fails, the scoring is broken - not the market.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("fc", ROOT / "forecast.py")
fc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fc)


def random_walk(n=400, seed=7):
    rng = np.random.default_rng(seed)
    return 100 * np.exp(np.cumsum(rng.normal(0, 0.01, n)))


def steady_trend(n=400, rate=0.002):
    return 100 * np.exp(np.arange(n) * rate)


def test_walk_forward_returns_origins():
    y = random_walk()
    runs = fc.walk_forward(y, fc.m_naive, horizon=21, season=5, origins=6, min_train=60)
    assert len(runs) >= 6, f"expected at least 6 origins, got {len(runs)}"
    # origins must be strictly increasing, oldest first
    cuts = [r["origin"] for r in runs]
    assert cuts == sorted(cuts), f"origins out of order: {cuts}"
    # every run must carry the fields the report needs
    for r in runs:
        for k in ("mape", "hit", "cover80", "n_train"):
            assert k in r, f"missing {k}"


def test_hit_rate_is_defined():
    y = steady_trend()
    runs = fc.walk_forward(y, fc.m_drift, horizon=21, season=5, origins=6, min_train=60)
    assert runs, "no origins produced"
    hits = [r["hit"] for r in runs if np.isfinite(r["hit"])]
    assert hits, "hit rate never computed"
    # in a clean uptrend a drift model should get the sign right nearly always
    assert np.mean(hits) >= 50, f"drift hit rate too low in a trend: {np.mean(hits)}"


def test_naive_is_competitive_on_a_random_walk():
    """On a random walk the last close is the honest guess. Naive should not be beaten by much."""
    y = random_walk()
    res = {}
    for name in ("naive", "drift", "mean"):
        runs = fc.walk_forward(y, fc.MODELS[name], horizon=21, season=5, origins=6, min_train=60)
        vals = [r["mape"] for r in runs if np.isfinite(r["mape"])]
        res[name] = float(np.mean(vals)) if vals else float("nan")
    assert np.isfinite(res["naive"]), "naive produced no score"
    for other in ("drift", "mean"):
        if np.isfinite(res[other]):
            assert res[other] >= res["naive"] - 1.0, (
                f"{other} beat naive by more than a point on a random walk "
                f"({res[other]:.2f} vs {res['naive']:.2f}) - the scoring is wrong")


def test_drift_wins_on_a_trend():
    y = steady_trend()
    out = {}
    for name in ("naive", "drift"):
        runs = fc.walk_forward(y, fc.MODELS[name], horizon=21, season=5, min_train=60, origins=6)
        vals = [r["mape"] for r in runs if np.isfinite(r["mape"])]
        out[name] = float(np.mean(vals)) if vals else float("nan")
    assert np.isfinite(out["drift"]) and np.isfinite(out["naive"])
    assert out["drift"] < out["naive"], (
        f"drift did not beat naive on a steady trend ({out['drift']:.2f} vs {out['naive']:.2f})")


def test_band_coverage_is_a_percentage():
    y = random_walk()
    runs = fc.walk_forward(y, fc.m_naive, horizon=21, season=5, origins=6, min_train=60)
    cov = [r["cover80"] for r in runs if np.isfinite(r["cover80"])]
    assert cov, "coverage never computed"
    assert all(0 <= c <= 100 for c in cov), f"coverage outside 0-100: {cov}"


def test_too_short_returns_nothing():
    y = np.linspace(100, 110, 40)
    assert fc.walk_forward(y, fc.m_naive, 21, 5, origins=6, min_train=60) == []


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL  {t.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
