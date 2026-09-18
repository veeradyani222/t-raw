"""Signal and diagnostic value types shared by BOS and the trading engine."""
from dataclasses import dataclass
from enum import Enum


class Signal(Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


@dataclass(frozen=True)
class Setup:
    """A signal that carries its own structure-derived exit levels.

    A strategy may return this instead of a bare Signal when the chart
    dictates where the stop belongs (the opposing confirmed swing). `sl`/`tp` are PRICES, not pips; `sl=None` uses the fixed-pip stop;
    `tp=None` means no take-profit. The engine sizes the position from the
    actual stop distance, so risk per trade stays constant regardless of how
    wide the setup is.

    `meta` carries diagnostics for the trade log (swing levels, CMF,
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
