"""Causality and trendline timing checks for offline strategy candidates."""
import numpy as np
import pandas as pd
import pytest

from research.gold_intraday.candidates import CANDIDATES, build_signals, trendline_breaks, wilder


def candles(n=500):
    rng = np.random.default_rng(17)
    close = 2000 + np.cumsum(rng.normal(.05, 1.8, n))
    opens = np.r_[close[0], close[:-1]]
    return pd.DataFrame(dict(time=pd.date_range("2026-01-01", periods=n, freq="5min"),
                             open=opens, high=np.maximum(opens, close)+.7,
                             low=np.minimum(opens, close)-.7, close=close,
                             tick_volume=rng.integers(100, 1000, n), spread=12))


@pytest.mark.parametrize("name", CANDIDATES)
def test_appending_future_candles_cannot_change_existing_signals(name):
    df = candles()
    prefix = build_signals(df.iloc[:350].copy(), name, 5)
    full = build_signals(df, name, 5)
    pd.testing.assert_frame_equal(prefix, full.iloc[:350])
    assert (full.side.iloc[:200] == 0).all()
    active = full.side != 0
    assert full.loc[active, ["sl", "tp"]].notna().all().all()
    assert (full.loc[full.side == 1, "sl"] < df.loc[full.side == 1, "close"]).all()
    assert (full.loc[full.side == -1, "sl"] > df.loc[full.side == -1, "close"]).all()


def trend_candles():
    high = np.array([10, 11, 15, 12, 11, 13, 14, 14], dtype=float)
    return pd.DataFrame(dict(high=high, low=high-1, close=high-.5, open=high-.7))


def test_trendline_uses_pivot_only_when_right_hand_bars_exist():
    df = trend_candles()
    r = trendline_breaks(df, length=2)
    assert r.upper.iloc[:4].isna().all()
    assert r.pivot_high.iloc[4]
    assert r.long_break.iloc[5]
    assert r.long_break.sum() == 1
    pd.testing.assert_frame_equal(r.iloc[:5], trendline_breaks(df.iloc[:5], length=2))


@pytest.mark.parametrize("body_cross", [False, True])
def test_trendline_break_uses_body_close_not_wick(body_cross):
    df = trend_candles()
    boundary = trendline_breaks(df, length=2).upper.iloc[5]
    df.loc[5, ["open", "close", "high", "low"]] = [
        boundary-.2, boundary+.01 if body_cross else boundary-.01,
        boundary+2, boundary-.3]
    r = trendline_breaks(df, length=2)
    assert bool(r.long_break.iloc[5]) == body_cross


def test_wilder_average_starts_with_sma_seed():
    result = wilder(pd.Series([1., 2., 3., 10.]), 3)
    assert result.iloc[:2].isna().all()
    assert result.iloc[2] == 2.
    assert result.iloc[3] == pytest.approx(2 + (10-2)/3)
