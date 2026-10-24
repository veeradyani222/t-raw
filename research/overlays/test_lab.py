"""Overlay lab tests: factor mechanics on a toy account, rule decisions, and
(when the cache is present) the baseline reproducing the known numbers.

    OVERLAY_CACHE=<dir built by research.overlays.runs> pytest research/overlays
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research.overlays import lab


def _strat(name, close, worst, trades, tf="H1"):
    e = np.array([t[0] for t in trades], int)
    x = np.array([t[1] for t in trades], int)
    p = np.array([t[2] for t in trades], float)
    rb = np.r_[0.0, np.cumsum(p)[:-1]] if len(p) else np.zeros(0)
    return lab.Strat(name, "XAUUSD", tf, np.asarray(close, float), np.asarray(worst, float),
                     e, x, p, rb, np.zeros(len(p), bool))


IDX = pd.DatetimeIndex(pd.date_range("2025-01-06 01:00", periods=10, freq="h"))  # 1 day (Monday)
IDX2 = pd.DatetimeIndex(list(pd.date_range("2025-01-06 01:00", periods=5, freq="h")) +
                        list(pd.date_range("2025-01-07 01:00", periods=5, freq="h")))  # 2 days


class Const(lab.Rule):
    def __init__(self, f):
        self.f = f

    def factor(self, a):
        return self.f


def test_factor_scales_trade_and_floating():
    # one trade: enters bar 1, exits bar 3 with +100; floating +20 then +60
    close = [0, 20, 60, 100, 100, 100, 100, 100, 100, 100]
    worst = [0, -30, 10, 100, 100, 100, 100, 100, 100, 100]
    s = _strat("s", close, worst, [(1, 3, 100.0)])
    rp = lab.Replay([s], IDX)
    base = rp.run(None)
    assert np.allclose(base.C, close) and np.allclose(base.W, worst)
    half = rp.run(Const(0.5))
    assert np.allclose(half.C, np.array(close) * 0.5)
    assert np.allclose(half.W, np.array(worst) * 0.5)
    assert half.n_scaled == 1 and half.n_taken == 1
    skip = rp.run(Const(0.0))
    assert np.allclose(skip.C, 0) and np.allclose(skip.W, 0) and skip.n_taken == 0


def test_two_strategies_sum_and_realized_carry():
    s1 = _strat("a", [0, 10, 50, 50, 50, 50, 50, 50, 50, 50], [0, -5, 50, 50, 50, 50, 50, 50, 50, 50], [(1, 2, 50.0)])
    s2 = _strat("b", [0, 0, 0, -20, -40, -40, -40, -40, -40, -40], [0, 0, 0, -30, -40, -40, -40, -40, -40, -40], [(3, 4, -40.0)])
    rp = lab.Replay([s1, s2], IDX)
    r = rp.run(Const(2.0))
    assert np.allclose(r.C, 2 * (s1.close + s2.close))
    assert np.allclose(r.W, 2 * (s1.worst + s2.worst))
    assert r.C[-1] == pytest.approx(20.0)


def test_daily_halt_closes_all_and_pins_the_day():
    # the trade sinks to -400 intrabar at bar 2 and would have recovered to +50
    close = [0, -100, -350, -200, 50, 50, 50, 50, 50, 50]
    worst = [0, -150, -400, -250, 0, 50, 50, 50, 50, 50]
    s = _strat("s", close, worst, [(1, 4, 50.0)])
    rp = lab.Replay([s], IDX)
    r = rp.run(None, halt=300.0, slip=25.0)
    assert r.halts == 1
    assert np.allclose(r.C, [0, -100, -325, -325, -325, -325, -325, -325, -325, -325])
    assert np.allclose(r.W, [0, -150, -325, -325, -325, -325, -325, -325, -325, -325])
    # an entry later the same day is blocked; one the next day is not
    s2 = _strat("t", [0, 0, 0, 10, 30, 30, 40, 80, 80, 80], [0, 0, 0, 5, 30, 30, 20, 80, 80, 80],
                [(3, 4, 30.0), (6, 7, 50.0)])
    rp2 = lab.Replay([s, s2], IDX2)
    r2 = rp2.run(None, halt=300.0, slip=25.0)
    assert r2.halts == 1 and r2.n_taken == 2 and r2.C[-1] == pytest.approx(-325 + 50)


def test_rules_decide_from_account_state():
    a = lab.Account(IDX)
    a.eq_prev, a.month_start = -600.0, 0.0
    assert lab.MonthlyStop(500).factor(a) == 0.0 and lab.MonthlyStop(750).factor(a) == 1.0
    dd = lab.DrawdownScale(9700, 9900, 0.5)
    a.eq_prev = -350.0
    assert dd.factor(a) == 0.5
    a.eq_prev = -150.0            # between the bands: stays halved
    assert dd.factor(a) == 0.5
    a.eq_prev = -50.0             # back above 9,900
    assert dd.factor(a) == 1.0
    a.month_halts = 2
    assert lab.HaltStop(2).factor(a) == 0.0 and lab.HaltStop(3).factor(a) == 1.0
    vt = lab.VolTarget(200, n=20, lo=0.5, hi=1.5)
    a.day_closes = list(np.cumsum([400, -400] * 10))     # daily std ~ 410 -> ~0.49 -> capped 0.5
    assert vt.factor(a) == 0.5
    a.day_closes = list(np.cumsum([10, -10] * 10))
    assert vt.factor(a) == 1.5
    assert lab.VolTarget(200, hi=1.0).factor(a) == 1.0
    a.day_closes = [1.0, 2.0]                          # too little history
    assert vt.factor(a) == 1.0


def test_equity_filter_pauses_and_resumes():
    p = [-10, -10, -10, 5, -10, -10, -10, -10, -10, -10, 20, 1, 1]
    s = _strat("s", np.zeros(20), np.zeros(20), [(i, i + 1, v) for i, v in enumerate(p)])
    f = lab.EquityFilter(10)
    a = lab.Account(IDX); a.strat = s
    out = []
    for k in range(len(p)):
        a.k = k
        out.append(f.factor(a))
    # trades 0..9 are taken (not enough history), 10 is paused (last 10 net -85),
    # trade 10 would have won (+20) so 11 resumes; 12 pauses again (last 10 still negative)
    assert out == [1.0] * 10 + [0.0, 1.0, 0.0]


def test_clock_rules():
    a = lab.Account(IDX)
    a.strat = _strat("s", np.zeros(2), np.zeros(2), [])  # H1
    a.time = pd.Timestamp("2025-03-19 19:00")          # fill 20:00, FOMC 21:00 that day
    assert lab.EventBlackout(60).factor(a) == 0.0
    assert lab.EventBlackout(30).factor(a) == 1.0
    a.time = pd.Timestamp("2025-03-07 14:00")          # fill 15:00, NFP 15:30 (first Friday)
    assert lab.EventBlackout(30).factor(a) == 0.0
    a.time = pd.Timestamp("2025-03-07 19:00")          # Friday fill 20:00
    assert lab.FridayCutoff(20).factor(a) == 0.0
    a.time = pd.Timestamp("2025-03-07 18:00")          # Friday fill 19:00
    assert lab.FridayCutoff(20).factor(a) == 1.0
    a.time = pd.Timestamp("2025-03-06 19:00")          # Thursday
    assert lab.FridayCutoff(20).factor(a) == 1.0


def test_combo_multiplies_and_short_circuits():
    c = lab.Combo(Const(0.5), Const(0.5))
    a = lab.Account(IDX)
    assert c.factor(a) == 0.25
    assert lab.Combo(Const(0.0), Const(0.5)).factor(a) == 0.0


def test_perm_halt_freezes():
    C = np.array([0, -300, -720, -100, 500.0]); W = np.array([0, -400, -750, -200, 400.0])
    C2, W2, t = lab.apply_perm_halt(C, W)
    assert t == 2 and np.allclose(C2, [0, -300, -750, -750, -750])


CACHE = os.environ.get("OVERLAY_CACHE")


@pytest.mark.skipif(not CACHE or not (Path(CACHE) / "A").exists(), reason="needs OVERLAY_CACHE from research.overlays.runs")
def test_baseline_reproduces_known_numbers():
    mix, strats, idx = lab.load_window(Path(CACHE), "A")
    j = lab.judge(idx, lab.Replay(strats, idx).run(None), "A")
    assert j["net"] == pytest.approx(47844.6, abs=2)
    assert j["worst_day"] == pytest.approx(-298.7, abs=1)
    assert j["lowest_equity"] == pytest.approx(9809.2, abs=2)
    assert j["halts"] == 0
    mix, strats, idx = lab.load_window(Path(CACHE), "B")
    j = lab.judge(idx, lab.Replay(strats, idx).run(None), "B")
    assert j["net"] == pytest.approx(44986.4, abs=2)
    assert j["lowest_equity"] == pytest.approx(5609.2, abs=2)
    assert j["halts"] == 38 and j["taken"] == 6982
