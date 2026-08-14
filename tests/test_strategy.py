import numpy as np
import pandas as pd

from trader.strategy import Signal, compute_signal


def make_candles(closes):
    closes = pd.Series(closes, dtype=float)
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=len(closes), freq="h"),
        "open": closes, "high": closes + 0.0005,
        "low": closes - 0.0005, "close": closes,
    })


def test_flat_without_enough_history():
    assert compute_signal(make_candles([1.1] * 10), 20, 50) is Signal.FLAT


def test_long_on_upward_cross():
    # Long decline (fast SMA below slow), then a sharp rally forces the cross.
    closes = list(np.linspace(1.20, 1.10, 60)) + list(np.linspace(1.10, 1.25, 25))
    candles = make_candles(closes)
    signals = [compute_signal(candles.iloc[:i], 20, 50)
               for i in range(51, len(candles) + 1)]
    assert Signal.LONG in signals
    assert Signal.SHORT not in signals


def test_short_on_downward_cross():
    closes = list(np.linspace(1.10, 1.20, 60)) + list(np.linspace(1.20, 1.05, 25))
    candles = make_candles(closes)
    signals = [compute_signal(candles.iloc[:i], 20, 50)
               for i in range(51, len(candles) + 1)]
    assert Signal.SHORT in signals
    assert Signal.LONG not in signals


def test_no_signal_repeats_after_cross():
    # After a cross fires once, continued trend must not fire again.
    closes = list(np.linspace(1.20, 1.10, 60)) + list(np.linspace(1.10, 1.30, 60))
    candles = make_candles(closes)
    signals = [compute_signal(candles.iloc[:i], 20, 50)
               for i in range(51, len(candles) + 1)]
    assert signals.count(Signal.LONG) == 1
