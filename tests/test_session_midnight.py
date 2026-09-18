from dataclasses import replace

import pandas as pd
from trader.strategies import session
from trader.strategy import Setup, Signal
from tests.test_session import candles, config


def test_midnight_open_uses_preceding_completed_bar():
    cfg = config(session_entry_at_open=True)
    result = session.compute_signal(candles(hour=23), cfg)
    assert isinstance(result, Setup)
    assert result.sl == 186.
    assert session.compute_signal(candles(hour=0), cfg) is Signal.FLAT


def test_live_config_selects_completed_midnight_candle():
    from run_live import CHFJPY
    assert CHFJPY.session_entry_at_open is False
    assert CHFJPY.session_hour == 0
    assert CHFJPY.session_hold_hours == 12


def test_monday_signal_uses_friday_atr_with_current_entry_clock():
    cfg = config(session_entry_at_open=True)
    bars = candles(hour=23)
    monday = bars.time.iloc[-1] + pd.Timedelta(days=3, hours=1)
    assert isinstance(session.compute_signal(bars, cfg, entry_time=monday), Setup)


def test_open_replay_enters_after_weekend_gap():
    from research.jpy_guarded_session import simulate
    bars = candles(40, hour=13)
    # Keep sufficient warmup, then insert a weekend between 23:00 and 00:00.
    boundary = bars.index[bars.time.dt.hour == 0][-1]
    bars.loc[boundary:, 'time'] += pd.Timedelta(days=2)
    bars['fx'] = bars['fx_previous'] = 150.
    start = bars.time.iloc[boundary]
    _, trades = simulate(bars, start, start + pd.Timedelta(days=1), entry_at_open=True)
    assert len(trades) == 1
    assert trades.iloc[0].entry_time == start


def test_open_replay_stops_within_entry_candle_without_using_its_atr():
    from research.jpy_guarded_session import simulate
    bars = candles(30, hour=13)
    bars['fx'] = bars['fx_previous'] = 150.
    midnight = bars.time.dt.hour == 0
    bars.loc[midnight, 'low'] = 180.
    start = bars.loc[midnight, 'time'].iloc[0]
    _, trades = simulate(bars, start, start + pd.Timedelta(days=1), entry_at_open=True)
    assert len(trades) == 1
    assert trades.iloc[0].sl == 186.
    assert trades.iloc[0].entry_time == start
    assert trades.iloc[0].exit_time == start
    assert trades.iloc[0].reason == 'sl'


def test_open_replay_exits_before_noon_candle_low():
    from research.jpy_guarded_session import simulate
    bars = candles(30, hour=13)
    bars['fx'] = bars['fx_previous'] = 150.
    bars.loc[bars.time.dt.hour == 12, 'low'] = 180.
    start = bars.loc[bars.time.dt.hour == 0, 'time'].iloc[0]
    _, trades = simulate(bars, start, start + pd.Timedelta(days=1), entry_at_open=True)
    assert len(trades) == 1
    assert trades.iloc[0].reason == 'time'
    assert trades.iloc[0].exit_time == start + pd.Timedelta(hours=12)
