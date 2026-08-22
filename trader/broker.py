"""Broker interface shared by the simulator (backtest) and MT5 (live).

Anything that talks to a market implements this. Strategy/risk code only
ever sees these types, so backtest and live behave identically.
"""
from dataclasses import dataclass
from typing import Protocol

import pandas as pd


@dataclass
class Position:
    side: str            # "long" | "short"
    lots: float
    entry_price: float
    sl: float
    tp: float
    ticket: int = 0
    open_time: object = None   # pd.Timestamp when opened (broker time); None if unknown


class Broker(Protocol):
    def candles(self, count: int) -> pd.DataFrame:
        """Most recent `count` closed candles, oldest first.
        Columns: time, open, high, low, close."""
        ...

    def equity(self) -> float: ...

    def open_positions(self) -> list[Position]: ...

    def open_position(self, side: str, lots: float, sl: float, tp: float) -> Position:
        """Market order with attached SL/TP. Raises on rejection."""
        ...

    def close_position(self, position: Position) -> float:
        """Close at market. Returns realized profit."""
        ...
