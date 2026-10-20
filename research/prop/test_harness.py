"""Sanity tests for the prop harness: python -m pytest research/prop -q"""
import numpy as np
import pandas as pd
import pytest

from research.prop import harness as H


def frame(prices, sym="EURUSD", start="2020-01-06"):
    t = pd.date_range(start, periods=len(prices), freq="h")
    p = np.asarray(prices, float)
    op = np.r_[p[0], p[:-1]]                      # open = previous close
    df = pd.DataFrame(dict(time=t, open=op, high=np.maximum(op, p) + 0.0002,
                           low=np.minimum(op, p) - 0.0002, close=p,
                           tick_volume=100, spread=0, conv=1.0))
    df.attrs.update(symbol=sym, tf="H1", split="is", score_from=None)
    return df


def test_stop_loses_about_risk():
    # price drifts down so the stop is hit INTRABAR (no gap)
    df = frame([1.1000] * 5 + [1.0985, 1.0975, 1.0960, 1.0950, 1.0950])
    sig = [None] * 10
    sig[2] = H.Entry("long", sl=1.0970)
    t = H.simulate(df, sig, risk=0.01)["trades"]
    assert len(t) == 1 and t.reason[0] == "sl"
    assert -110 < t.profit[0] < -85        # ~1% of $10k incl. costs


def test_gap_through_stop_fills_worse():
    df = frame([1.1000] * 5 + [1.0950] * 5)
    df.loc[5, "open"] = 1.0950                    # weekend-style gap below the stop
    sig = [None] * 10
    sig[2] = H.Entry("long", sl=1.0970)
    t = H.simulate(df, sig, risk=0.01)["trades"]
    assert t.reason[0] == "gap_sl" and t.profit[0] < -120


def test_target_wins_and_costs_hurt():
    df = frame([1.1000] * 5 + [1.1100] * 5)
    sig = [None] * 10
    sig[2] = H.Entry("long", sl=1.0970, tp=1.1060)
    t = H.simulate(df, sig, risk=0.01)["trades"]
    assert t.reason[0] == "tp" and 150 < t.profit[0] < 200   # ~2R minus costs


def test_short_symmetry():
    df = frame([1.1000] * 5 + [1.0900] * 5)
    sig = [None] * 10
    sig[2] = H.Entry("short", sl=1.1030, tp=1.0940)
    t = H.simulate(df, sig, risk=0.01)["trades"]
    assert t.reason[0] == "tp" and t.profit[0] > 150


def test_oos_locked(monkeypatch):
    monkeypatch.delenv("PROP_OOS", raising=False)
    with pytest.raises(PermissionError):
        H.load("EURUSD", "H1", split="oos")


def test_daily_block_stops_new_entries():
    # three losing trades in one day at 1.6% risk: third must be blocked (past -3%)
    px = []
    for _ in range(3):
        px += [1.1000, 1.1000, 1.0900, 1.1000]
    df = frame(px)
    sig = [None] * len(px)
    for k in range(3):
        sig[k * 4] = H.Entry("long", sl=1.0950)
    t = H.simulate(df, sig, risk=0.016)["trades"]
    assert len(t) == 2


def test_score_runs_and_picks_safe_risk():
    rng = np.random.default_rng(0)
    p = 1.1 + np.cumsum(rng.normal(0, 0.0005, 3000))
    df = frame(p)
    sig = [H.Entry("long", sl=p[i] - 0.002, tp=p[i] + 0.004) if i % 24 == 0 else None
           for i in range(len(p))]
    s = H.score(df, sig, name="rand")
    assert "headline" in s and s["headline"]["trades"] > 0
