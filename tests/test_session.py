"""Tests for the session (time-of-day) strategy and the engine's no-TP path."""
import pandas as pd
import pytest

from trader.config import Config
from trader.sim import run_backtest
from trader.strategies import get_strategy, session
from trader.strategy import Setup, Signal


def hourly(closes, start, spread=0.1):
    closes = pd.Series(closes, dtype=float)
    opens = closes.shift(1).fillna(closes.iloc[0])
    return pd.DataFrame({
        "time": pd.date_range(start, periods=len(closes), freq="h"),
        "open": opens,
        "high": pd.concat([opens, closes], axis=1).max(axis=1) + spread,
        "low": pd.concat([opens, closes], axis=1).min(axis=1) - spread,
        "close": closes,
    })


def session_cfg():
    return Config(symbol="USDJPY", timeframe="H1", strategy="session",
                  session_entry_hour=6, session_hold_bars=12,
                  session_atr_n=5, session_stop_atr_mult=2.0,
                  pip_size=0.01, pip_value_per_lot=10.0, max_lot=100.0)


def test_session_enters_long_at_entry_hour_with_no_tp():
    strat = get_strategy("session")
    cfg = session_cfg()
    # 7 bars from 00:00 → last bar at 06:00 (the entry hour).
    candles = hourly([150.0, 150.1, 149.9, 150.2, 150.0, 150.1, 150.3],
                     start="2026-01-05 00:00")
    setup = strat.compute_signal(candles, cfg)
    assert isinstance(setup, Setup)
    assert setup.side == "long"
    assert setup.tp is None                       # no take-profit — exits by time
    assert setup.sl < candles["close"].iloc[-1]   # protective stop below entry


def test_session_flat_off_the_entry_hour():
    strat = get_strategy("session")
    cfg = session_cfg()
    candles = hourly([150.0] * 7, start="2026-01-05 01:00")  # last bar 07:00
    assert strat.compute_signal(candles, cfg) is Signal.FLAT


def test_should_time_exit_after_hold_bars():
    cfg = session_cfg()  # H1, hold 12 bars
    opened = pd.Timestamp("2026-01-05 06:00")
    assert session.should_time_exit(opened, pd.Timestamp("2026-01-05 18:00"), cfg)      # 12 bars
    assert not session.should_time_exit(opened, pd.Timestamp("2026-01-05 17:00"), cfg)  # 11 bars
    assert not session.should_time_exit(None, pd.Timestamp("2026-01-05 18:00"), cfg)    # unknown


def test_session_opens_position_and_never_exits_by_tp():
    """Through the real engine + sim: a session entry opens with tp=0 (no target)
    and is never closed by a take-profit."""
    cfg = session_cfg()
    closes = [150.0] * 6 + [150.2] + [150.2] * 20      # entry at 06:00, then flat
    candles = hourly(closes, start="2026-01-05 00:00")
    result = run_backtest(candles, cfg, starting_equity=10_000.0)
    trades = result["trade_log"]
    assert not trades.empty
    assert (trades["tp"] == 0.0).all()                 # opened with no take-profit
    assert "tp" not in set(trades["reason"])           # never exits via TP
