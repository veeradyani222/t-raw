"""Long H1 session signal using completed candles for ATR.

The caller supplies completed candles with a broker-time ``time`` column.
Opening-entry mode uses a separate current entry clock, including across weekends.
Execution freshness, duplicate
entries and timed exits belong to the engine and broker, not this pure signal.
"""
from numbers import Integral, Real

import numpy as np
import pandas as pd

from ..strategy import Setup, Signal


def _validate(cfg) -> None:
    if cfg.timeframe != "H1":
        raise ValueError("session requires H1 candles")
    if (isinstance(cfg.session_hour, bool)
            or not isinstance(cfg.session_hour, Integral)
            or not 0 <= cfg.session_hour <= 23):
        raise ValueError("session_hour must be an integer from 0 to 23")
    if (isinstance(cfg.session_atr_n, bool)
            or not isinstance(cfg.session_atr_n, Integral)
            or cfg.session_atr_n < 1):
        raise ValueError("session_atr_n must be a positive integer")
    for name in ("session_sl_atr", "session_hold_hours", "session_entry_window_seconds",
                 "session_commission_per_lot", "session_slippage_pips"):
        value = getattr(cfg, name)
        allow_zero = name in ("session_commission_per_lot", "session_slippage_pips")
        if (isinstance(value, bool) or not isinstance(value, Real)
                or not np.isfinite(value) or value < 0
                or (value == 0 and not allow_zero)):
            raise ValueError(f"{name} must be finite and {'nonnegative' if allow_zero else 'positive'}")


def lookback(cfg) -> int:
    """ATR needs n true ranges plus one preceding close."""
    _validate(cfg)
    return cfg.session_atr_n + 1


def compute_signal(candles: pd.DataFrame, cfg, *, entry_time=None) -> Signal | Setup:
    required = lookback(cfg)
    if len(candles) < required:
        return Signal.FLAT
    stamp = pd.Timestamp(candles["time"].iloc[-1])
    if cfg.session_entry_at_open:
        boundary = (pd.Timestamp(entry_time) if entry_time is not None
                    else stamp + pd.Timedelta(hours=1))
        if stamp + pd.Timedelta(hours=1) > boundary:
            return Signal.FLAT
        stamp = boundary
    if pd.isna(stamp) or stamp.hour != cfg.session_hour:
        return Signal.FLAT

    bars = candles.iloc[-required:]
    ohlc = bars[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(ohlc).all():
        return Signal.FLAT
    high, low = ohlc[1:, 1], ohlc[1:, 2]
    previous_close = ohlc[:-1, 3]
    ranges = np.maximum.reduce((high - low, abs(high - previous_close),
                                abs(low - previous_close)))
    atr = float(ranges.mean())
    stop = float(ohlc[-1, 3] - cfg.session_sl_atr * atr)
    if not np.isfinite(atr) or atr <= 0 or not np.isfinite(stop) or stop <= 0:
        return Signal.FLAT
    return Setup("long", sl=stop, tp=None)
