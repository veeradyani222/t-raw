"""Pure H1 session signals and their configuration contract."""
from dataclasses import replace

import numpy as np
import pandas as pd
import pytest

from trader.config import Config
from trader.strategies import get_strategy
from trader.strategy import Setup, Signal


def config(**kwargs):
    return replace(Config(), strategy="session", timeframe="H1", **kwargs)


def candles(n=15, hour=0):
    index = pd.date_range(end=pd.Timestamp("2026-09-16") + pd.Timedelta(hours=hour), periods=n, freq="h")
    return pd.DataFrame({"time": index, "open": 190.0, "high": 191.0, "low": 189.0, "close": 190.0})


def test_session_defaults_and_lookback():
    cfg = config()
    assert (cfg.session_hour, cfg.session_atr_n, cfg.session_sl_atr) == (0, 14, 2.0)
    assert cfg.session_hold_hours == 12.0
    assert cfg.session_entry_window_seconds == 60
    assert cfg.session_commission_per_lot == 14.0
    assert cfg.session_slippage_pips == 0.1
    assert get_strategy("session").lookback(cfg) == 15


def test_session_long_uses_simple_true_range_atr_and_has_no_target():
    bars = candles()
    bars.iloc[0, bars.columns.get_loc("close")] = 185.0
    result = get_strategy("session").compute_signal(bars, config())
    assert isinstance(result, Setup)
    assert result.side == "long"
    assert result.sl == pytest.approx(190 - 2 * (6 + 13 * 2) / 14)
    assert result.tp is None


@pytest.mark.parametrize("n", [0, 1, 14])
def test_warmup_is_flat(n):
    assert get_strategy("session").compute_signal(candles(n), config()) is Signal.FLAT


def test_hour_is_completed_candle_opening_label():
    strategy = get_strategy("session")
    assert strategy.compute_signal(candles(hour=1), config()) is Signal.FLAT
    assert isinstance(strategy.compute_signal(candles(hour=1), config(session_hour=1)), Setup)


@pytest.mark.parametrize("field,value", [
    ("timeframe", "M30"), ("session_hour", -1), ("session_hour", 24),
    ("session_hour", 0.5), ("session_atr_n", 0), ("session_atr_n", 1.5),
    ("session_sl_atr", 0), ("session_sl_atr", float("nan")),
    ("session_hold_hours", -1), ("session_hold_hours", float("inf")),
    ("session_entry_window_seconds", 0), ("session_entry_window_seconds", float("nan")),
    ("session_commission_per_lot", -1), ("session_slippage_pips", -1),
])
def test_invalid_parameters_are_rejected(field, value):
    cfg = replace(config(), **{field: value})
    with pytest.raises(ValueError):
        get_strategy("session").compute_signal(candles(), cfg)


@pytest.mark.parametrize("column", ["open", "high", "low", "close"])
@pytest.mark.parametrize("value", [float("nan"), float("inf")])
def test_nonfinite_ohlc_is_flat(column, value):
    bars = candles()
    bars.loc[bars.index[-2], column] = value
    assert get_strategy("session").compute_signal(bars, config()) is Signal.FLAT


def test_previous_close_must_be_finite():
    bars = candles()
    bars.iloc[0, bars.columns.get_loc("close")] = np.nan
    assert get_strategy("session").compute_signal(bars, config()) is Signal.FLAT


def test_zero_atr_is_flat():
    bars = candles()
    bars.loc[:, ["open", "high", "low", "close"]] = 190.0
    assert get_strategy("session").compute_signal(bars, config()) is Signal.FLAT


def test_atr_only_uses_the_required_trailing_window():
    bars = candles(20)
    bars.loc[0, ["open", "high", "low", "close"]] = np.nan
    result = get_strategy("session").compute_signal(bars, config())
    assert isinstance(result, Setup)
    assert result.sl == 186.0
