"""Placeholder strategy: SMA crossover. Pure function — no MT5, no I/O.

The point of this strategy is to exercise the pipeline, not to make money.
Replace compute_signal() with a real strategy once the infrastructure is proven.
"""
from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Signal(Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


@dataclass(frozen=True)
class Setup:
    """A signal that carries its own structure-derived exit levels.

    A strategy may return this instead of a bare Signal when the chart
    dictates where the stop belongs (e.g. the far side of an opening-range
    box). `sl`/`tp` are PRICES, not pips; either may be None to fall back to
    the fixed-pip levels in Config. The engine sizes the position from the
    actual stop distance, so risk per trade stays constant regardless of how
    wide the setup is.

    `meta` carries diagnostics for the trade log (box levels, volume ratio,
    structure state, tp_source) — the engine never acts on it.
    """
    side: str                # "long" | "short"
    sl: float | None = None
    tp: float | None = None
    meta: dict | None = None


@dataclass(frozen=True)
class Blocked:
    """A raw signal existed but a confirmation filter vetoed it.

    The engine treats this exactly like FLAT except that it is reported, so
    backtest logs show WHY the strategy stayed out — without this, a filter
    that quietly kills every good trade is indistinguishable from no signal.
    """
    side: str                # the side the raw breakout wanted
    reason: str              # e.g. "volume 0.8x below 1.2x threshold"
    meta: dict | None = None


def compute_signal(candles: pd.DataFrame, fast: int = 20, slow: int = 50) -> Signal:
    """Signal from the most recent *closed* candle.

    candles: DataFrame with a 'close' column, oldest row first.
    Returns FLAT until there is enough history.
    """
    if len(candles) < slow + 1:
        return Signal.FLAT

    close = candles["close"]
    fast_now = close.iloc[-fast:].mean()
    slow_now = close.iloc[-slow:].mean()
    fast_prev = close.iloc[-fast - 1:-1].mean()
    slow_prev = close.iloc[-slow - 1:-1].mean()

    crossed_up = fast_prev <= slow_prev and fast_now > slow_now
    crossed_down = fast_prev >= slow_prev and fast_now < slow_now

    if crossed_up:
        return Signal.LONG
    if crossed_down:
        return Signal.SHORT
    return Signal.FLAT
