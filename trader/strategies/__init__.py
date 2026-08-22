"""Strategy registry. Every strategy is a module with two callables:

    lookback(cfg) -> int              # how many candles compute_signal needs
    compute_signal(candles, cfg) -> Signal

All strategies are pure (candles in, signal out — no MT5, no I/O) so backtest
and live run the exact same code. Select one with Config.strategy.
"""
from . import orb, session, sma_cross

STRATEGIES = {
    "sma_cross": sma_cross,
    "orb": orb,
    "session": session,
}


def get_strategy(name: str):
    try:
        return STRATEGIES[name]
    except KeyError:
        raise ValueError(
            f"unknown strategy {name!r}; available: {', '.join(sorted(STRATEGIES))}"
        ) from None
