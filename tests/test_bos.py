"""Break-of-Structure + CMF strategy (trader.strategies.bos).

All offline — synthetic candles. Two layers:
  1. Unit tests of compute_signal: a clean break returns a structure Setup, CMF
     and trend filters veto with a Blocked, a stale (non-fresh) cross stays FLAT.
  2. An EQUIVALENCE test: the live compute_signal (windowed) reproduces the fast
     research signal bos_backtest.make_bos_signal decision-for-decision on a long
     synthetic series — the guarantee that the walk-forward/prop numbers and the
     live signals are the same strategy.
"""
import numpy as np
import pandas as pd

from trader.config import Config
from trader.strategies import bos, get_strategy
from trader.strategy import Blocked, Setup, Signal


def cfg(**kw):
    base = dict(strategy="bos", symbol="XAUUSD", timeframe="M30",
                pip_size=0.1, pip_value_per_lot=10.0,
                bos_swing_window=2, bos_cmf_n=5, bos_lookback=2000,
                bos_tp_mode="structure", bos_tp_r=3.0, bos_tp_min_r=1.0)
    base.update(kw)
    return Config(**base)


def frame(closes, pos, vol=1000.0, rng=2.0):
    """Candles from a close path. `pos` (0=at low, 1=at high; scalar or list)
    places the close within each bar's range, which sets the sign of that bar's
    money-flow contribution (mfm = 2*pos - 1). Highs/lows track the close so
    fractal swings sit at the close extrema."""
    closes = np.asarray(closes, float)
    pos = np.full(len(closes), pos, float) if np.isscalar(pos) else np.asarray(pos, float)
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=len(closes), freq="30min"),
        "open": np.concatenate([[closes[0]], closes[:-1]]),
        "high": closes + rng * (1 - pos),
        "low": closes - rng * pos,
        "close": closes,
        "tick_volume": np.full(len(closes), vol, float) if np.isscalar(vol) else np.asarray(vol, float),
    })


# A swing high at idx2 (103), a pullback low, then bar 11 CLOSES above 103.
LONG_CLOSES = [100, 101, 103, 101, 100, 99, 100, 101, 100, 99, 100, 104]


def test_insufficient_bars_is_flat():
    assert bos.compute_signal(frame([100, 101, 102], 0.9), cfg()) is Signal.FLAT


def test_fresh_break_with_cmf_returns_structure_setup():
    # Last 5 bars close near their highs → CMF > 0 → the long break is taken.
    pos = [0.5] * 7 + [0.9] * 5
    r = bos.compute_signal(frame(LONG_CLOSES, pos), cfg())
    assert isinstance(r, Setup)
    assert r.side == "long"
    assert r.sl < 104 < r.tp                 # stop below entry, target above
    assert r.meta["tp_source"] in ("structure", "r_multiple")


def test_cmf_disagrees_blocks_the_break():
    # Same break, but recent closes sit near their LOWs → CMF < 0 → vetoed.
    pos = [0.5] * 7 + [0.1] * 5
    r = bos.compute_signal(frame(LONG_CLOSES, pos), cfg())
    assert isinstance(r, Blocked)
    assert r.side == "long"


def test_trend_filter_blocks_counter_trend_break():
    # A recent high plateau keeps the 10-bar MA above the breakout price, so the
    # up-break (104, above swing high 103) is still BELOW the MA → trend vetoes.
    closes = [120, 118, 116, 114, 101, 102, 100, 103, 101, 100, 101, 104]
    pos = [0.5] * 7 + [0.9] * 5
    r = bos.compute_signal(frame(closes, pos), cfg(bos_trend_ma=10))
    assert isinstance(r, Blocked)
    assert "MA" in r.reason
    # ...and with the trend filter off, the same bar IS a valid long setup.
    assert isinstance(bos.compute_signal(frame(closes, pos), cfg()), Setup)


def test_stale_cross_is_flat():
    # Bar 10 already closed above the swing high, so bar 11 is not a FRESH cross.
    closes = [100, 101, 103, 101, 100, 99, 100, 101, 100, 99, 104, 104]
    pos = [0.5] * 7 + [0.9] * 5
    assert bos.compute_signal(frame(closes, pos), cfg()) is Signal.FLAT


def test_registered_in_strategy_registry():
    assert get_strategy("bos") is bos
    assert bos.lookback(cfg()) >= cfg().bos_lookback


# --------------------------------------------------------------------------- #
# EQUIVALENCE: live compute_signal == fast research make_bos_signal            #
# --------------------------------------------------------------------------- #
def _synthetic(n=400):
    t = np.arange(n)
    close = 2000 + 0.4 * t + 40 * np.sin(t / 11.0) + 15 * np.sin(t / 3.3)
    ret = np.concatenate([[0.0], np.diff(close)])
    pos = np.clip(0.5 + 0.5 * np.tanh(ret * 0.6), 0.05, 0.95)  # rising bar closes high
    rng = 3.0
    return pd.DataFrame({
        "time": pd.date_range("2026-01-01", periods=n, freq="30min"),
        "open": np.concatenate([[close[0]], close[:-1]]),
        "high": close + rng * (1 - pos),
        "low": close - rng * pos,
        "close": close,
        "tick_volume": 1000 + 300 * np.sin(t / 2.0) + 200 * np.cos(t / 5.0),
    })


def test_live_signal_matches_research_path():
    """bos.compute_signal on a rolling window reproduces the fast vectorized
    research signal exactly — same side, stop and target on every bar."""
    import bos_backtest as bt

    df = _synthetic(400)
    L = 40  # small window to exercise the bounded structure-target search
    fast = bt.make_bos_signal(df, swing_window=2, cmf_n=20, tp_mode="structure",
                              tp_r=3.0, tp_min_r=1.0, lookback=L)
    c = cfg(bos_cmf_n=20, bos_lookback=L)

    fires = diffs = 0
    for i in range(len(df)):
        f = fast(df, i)
        window = df.iloc[max(0, i + 1 - L):i + 1]
        r = bos.compute_signal(window, c)
        live = r if isinstance(r, Setup) else None
        if (f is None) != (live is None):
            diffs += 1
        elif f is not None:
            fires += 1
            if f.side != live.side or abs(f.sl - live.sl) > 1e-6 or abs(f.tp - live.tp) > 1e-6:
                diffs += 1
    assert fires >= 10, f"synthetic series produced too few signals ({fires}) to be meaningful"
    assert diffs == 0, f"live compute_signal diverged from research path on {diffs} bars"
