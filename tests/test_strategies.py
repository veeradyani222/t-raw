"""Tests for the ported ea-library strategies (bbrsi, orb) and the registry."""
import numpy as np
import pandas as pd
import pytest

from trader.config import Config
from trader.sim import run_backtest
from trader.strategies import get_strategy
from trader.strategy import Signal


def hourly(closes, opens=None, start="2026-01-05 00:00", spread=0.5):
    closes = pd.Series(closes, dtype=float)
    opens = closes.shift(1).fillna(closes.iloc[0]) if opens is None else pd.Series(opens, dtype=float)
    return pd.DataFrame({
        "time": pd.date_range(start, periods=len(closes), freq="h"),
        "open": opens,
        "high": pd.concat([opens, closes], axis=1).max(axis=1) + spread,
        "low": pd.concat([opens, closes], axis=1).min(axis=1) - spread,
        "close": closes,
    })


def test_registry_rejects_unknown_name():
    with pytest.raises(ValueError, match="unknown strategy"):
        get_strategy("nope")


# --- orb ------------------------------------------------------------------

def orb_cfg():
    return Config(strategy="orb", orb_session_start_hour=1, orb_box_candles=3)


def orb_day(post_box):
    """One trading day: 3 box bars (100 ± 0.5 range), then `post_box` closes."""
    closes = [100.0, 100.3, 99.8] + list(post_box)
    return hourly(closes, start="2026-01-05 01:00", spread=0.2)


def test_orb_long_setup_has_box_stop_and_r_multiple_target():
    strat = get_strategy("orb")
    cfg = orb_cfg()
    candles = orb_day([100.1, 100.2, 101.5])  # last bar closes above box high
    setup = strat.compute_signal(candles, cfg)
    assert setup.side == "long"
    box_low = candles.iloc[:3]["low"].min()
    assert setup.sl == box_low                      # stop = far side of the box
    risk = 101.5 - box_low
    assert setup.tp == pytest.approx(101.5 + cfg.orb_tp_r * risk)


def test_orb_short_setup_mirrors():
    strat = get_strategy("orb")
    cfg = orb_cfg()
    candles = orb_day([100.1, 100.0, 98.5])
    setup = strat.compute_signal(candles, cfg)
    assert setup.side == "short"
    box_high = candles.iloc[:3]["high"].max()
    assert setup.sl == box_high
    risk = box_high - 98.5
    assert setup.tp == pytest.approx(98.5 - cfg.orb_tp_r * risk)


def test_orb_fires_only_on_first_breakout_bar():
    strat = get_strategy("orb")
    candles = orb_day([100.1, 101.5, 102.5])  # breakout already happened
    assert strat.compute_signal(candles, orb_cfg()) is Signal.FLAT


def test_orb_no_signal_inside_box():
    strat = get_strategy("orb")
    candles = orb_day([100.1, 99.9, 100.2])
    assert strat.compute_signal(candles, orb_cfg()) is Signal.FLAT


# --- end-to-end through the engine ---------------------------------------

def test_setup_levels_reach_the_sim_broker():
    """The sim's trade log must show exits at the box-derived SL, not the
    fixed-pip SL, and the loss must be ~risk_per_trade of equity."""
    day1 = [100.0, 100.3, 99.8, 100.1, 100.2, 101.5]      # breakout long...
    day2 = [95.0] * 18                                     # ...then collapse to SL
    closes = day1 + day2
    candles = hourly(closes, start="2026-01-05 01:00", spread=0.2)
    cfg = Config(strategy="orb", orb_session_start_hour=1, orb_box_candles=3,
                 pip_size=0.1, pip_value_per_lot=10.0, max_lot=100.0)
    result = run_backtest(candles, cfg)
    trades = result["trade_log"]
    sl_exits = trades[trades["reason"] == "sl"]
    assert not sl_exits.empty
    box_low = 99.8 - 0.2  # low of the widest box bar (close - spread band)
    assert sl_exits["exit"].iloc[0] == pytest.approx(box_low)
    # Sizing came from the actual stop distance: loss ≈ 1% of 10k.
    assert abs(sl_exits["profit"].iloc[0]) == pytest.approx(100, rel=0.15)


def test_backtest_runs_each_strategy():
    rng = np.random.default_rng(7)
    closes = 2000 + np.cumsum(rng.normal(0, 2.0, 900))
    history = hourly(closes)
    for name in ("sma_cross", "orb"):
        cfg = Config(strategy=name)
        result = run_backtest(history, cfg)
        assert result["final_equity"] > 0
        assert abs((result["final_equity"] - 10_000) - result["net_profit"]) < 1e-6
