"""SMA crossover — the original pipeline-proving strategy, unchanged."""
import pandas as pd

from ..strategy import Signal, compute_signal as _sma_signal


def lookback(cfg) -> int:
    return cfg.slow_sma + 2


def compute_signal(candles: pd.DataFrame, cfg) -> Signal:
    return _sma_signal(candles, cfg.fast_sma, cfg.slow_sma)
