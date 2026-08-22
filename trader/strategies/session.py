"""Session (time-of-day) strategy — the Tokyo-morning long drift.

Every trading day it enters ONE position, LONG, at the bar that opens on
`session_entry_hour` (broker server time), with a protective stop
`session_stop_atr_mult` × ATR away. It carries NO take-profit: the position is
closed by TIME after `session_hold_bars` bars (that exit is driven by the live
loop / backtest harness, not by a price level).

Why it exists: on the JPY complex the yen tends to weaken through the Asian /
early-European morning, so USD/JPY (and the crosses) drift up in those hours.
Validated out-of-sample and against real per-hour spreads in wf_search.py —
USDJPY at the liquid morning hours survives costs; the illiquid rollover hour on
the crosses does not. This module trades ONLY the liquid, cost-surviving version.

Pure function (candles in, signal out) so backtest and live share it. The stop
is a PRICE (far side, invalidation) and tp is None — the engine opens it with a
server-side SL and no TP, and the loop time-exits it.
"""
import numpy as np
import pandas as pd

from ..strategy import Setup, Signal

_TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30,
               "H1": 60, "H4": 240, "D1": 1440}


def lookback(cfg) -> int:
    # Enough bars to compute ATR at the entry bar, plus a little slack.
    return cfg.session_atr_n + 5


def _atr(candles: pd.DataFrame, n: int) -> float:
    """ATR of the most recent bar (Wilder-style simple mean of true range).
    Uses only closed bars in `candles`, so there is no lookahead."""
    high = candles["high"].values
    low = candles["low"].values
    close = candles["close"].values
    if len(close) < n + 1:
        return float("nan")
    prev_close = close[:-1]
    tr = np.maximum.reduce([
        high[1:] - low[1:],
        np.abs(high[1:] - prev_close),
        np.abs(low[1:] - prev_close),
    ])
    return float(tr[-n:].mean())


def compute_signal(candles: pd.DataFrame, cfg) -> Signal | Setup:
    """Fire once, on the bar that opens at session_entry_hour. Otherwise FLAT.

    The engine's max-1-position rule means a still-open position from an earlier
    day blocks a fresh entry, so this doesn't need to track state itself.
    """
    if len(candles) < cfg.session_atr_n + 1:
        return Signal.FLAT

    bar_time = candles["time"].iloc[-1]
    if int(pd.Timestamp(bar_time).hour) != cfg.session_entry_hour:
        return Signal.FLAT

    atr = _atr(candles, cfg.session_atr_n)
    if not np.isfinite(atr) or atr <= 0:
        return Signal.FLAT

    price = float(candles["close"].iloc[-1])
    stop = cfg.session_stop_atr_mult * atr
    side = cfg.session_side
    sl = price - stop if side == "long" else price + stop
    meta = {"entry_hour": cfg.session_entry_hour, "atr": round(atr, 5),
            "hold_bars": cfg.session_hold_bars, "tp_source": "time_exit"}
    # tp=None → engine opens with a server-side SL and NO take-profit; the loop
    # closes the position by time (see trader.live._session_time_exit).
    return Setup(side=side, sl=float(sl), tp=None, meta=meta)


def should_time_exit(open_time: pd.Timestamp, now: pd.Timestamp, cfg) -> bool:
    """True once the position has been held session_hold_bars bars. Bars are
    counted as elapsed timeframe-units between open and now, so it survives a
    bot restart (the open time is read back from the broker)."""
    if open_time is None:
        return False
    minutes = _TF_MINUTES[cfg.timeframe]
    bars_held = (pd.Timestamp(now) - pd.Timestamp(open_time)).total_seconds() / 60 / minutes
    return bars_held >= cfg.session_hold_bars
