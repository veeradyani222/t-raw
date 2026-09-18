"""Fixed, causal offline candidates. Nothing here is registered for live trading.

The ATR trendline recurrence is based on the mathematical rules published by
LuxAlgo: https://www.luxalgo.com/library/indicator/Trendlines-with-Breaks/ .
This is a Python research implementation, not a TradingView parity claim.
Pivots are recognized on their confirmation bar, never backpainted.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


CANDIDATES = {
    "channel_break": "20-bar channel breakout, MA200, 2 ATR stop, 2R target",
    "channel_long": "Same channel breakout, long only",
    "ema_pullback": "EMA20 reclaim within EMA50/200 trend, local stop, 2R",
    "range_reentry": "Bollinger20/2 re-entry, ADX14 below 20, mean target",
    "sweep_reclaim": "20-bar wick sweep and body reclaim, EMA200, 2R",
    "compression_break": "Compressed bands then 10-bar channel break, trend, 3R",
    "bos_baseline": "Existing BOS + CMF20 + SMA200 and structure exits",
    "lux_trendline": "ATR trendlines: length14, slope1, first close break, 2R",
    "lux_trendline_trend": "Same trendline break with EMA200 direction filter",
}


def wilder(series: pd.Series, n: int) -> pd.Series:
    """Wilder RMA with an arithmetic-mean seed, as used by ATR/ADX."""
    seed = series.rolling(n).mean()
    valid = np.flatnonzero(seed.notna().to_numpy())
    if not len(valid):
        return pd.Series(np.nan, index=series.index)
    first = valid[0]
    values = series.copy().astype(float)
    values.iloc[:first] = np.nan
    values.iloc[first] = seed.iloc[first]
    return values.ewm(alpha=1/n, adjust=False).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prev = df.close.shift(1)
    tr = pd.concat([df.high-df.low, (df.high-prev).abs(), (df.low-prev).abs()], axis=1).max(axis=1)
    return wilder(tr, n)


def trendline_breaks(df: pd.DataFrame, length: int = 14,
                    multiplier: float = 1.) -> pd.DataFrame:
    """ATR-based descending resistance and rising support at real-time positions.

    A pivot j becomes visible at j+length. Its slope is ATR at confirmation
    divided by length, times multiplier; the current boundary is projected
    length bars from the pivot. Each boundary emits only its first close break.
    Equal extremes use the latest tied pivot (left ties allowed, right ties not).
    """
    if length < 1 or multiplier < 0:
        raise ValueError("length must be positive and multiplier nonnegative")
    high, low, close = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    slope = atr(df, length).to_numpy()/length*multiplier
    n = len(df)
    upper, lower = np.full(n, np.nan), np.full(n, np.nan)
    ph, pl, long, short = (np.zeros(n, dtype=bool) for _ in range(4))
    upper_anchor = lower_anchor = np.nan
    upper_slope = lower_slope = 0.
    upper_broken = lower_broken = False
    for i in range(n):
        j = i-length
        if j >= length:
            ph[i] = high[j] >= high[j-length:j].max() and high[j] > high[j+1:i+1].max()
            pl[i] = low[j] <= low[j-length:j].min() and low[j] < low[j+1:i+1].min()
        if ph[i]:
            upper_anchor, upper_slope, upper_broken = high[j], slope[i], False
        else:
            upper_anchor -= upper_slope
        if pl[i]:
            lower_anchor, lower_slope, lower_broken = low[j], slope[i], False
        else:
            lower_anchor += lower_slope
        upper[i] = upper_anchor - upper_slope*length
        lower[i] = lower_anchor + lower_slope*length
        if not ph[i] and not upper_broken and close[i] > upper[i]:
            long[i], upper_broken = True, True
        if not pl[i] and not lower_broken and close[i] < lower[i]:
            short[i], lower_broken = True, True
    return pd.DataFrame(dict(upper=upper, lower=lower, pivot_high=ph,
                             pivot_low=pl, long_break=long, short_break=short), index=df.index)


def build_signals(df: pd.DataFrame, name: str, tf_minutes: int) -> pd.DataFrame:
    """Produce requests on CLOSED bars, to be filled by the simulator next bar."""
    if name not in CANDIDATES:
        raise ValueError(name)
    c, o, h, l = df.close, df.open, df.high, df.low
    a = atr(df)
    ema20, ema50, ema200 = (c.ewm(span=n, adjust=False).mean() for n in (20, 50, 200))
    ma200 = c.rolling(200).mean()
    hi20, lo20 = h.rolling(20).max().shift(1), l.rolling(20).min().shift(1)
    mid = c.rolling(20).mean()
    std = c.rolling(20).std(ddof=0)
    upper, lower = mid+2*std, mid-2*std
    long = pd.Series(False, index=df.index)
    short = long.copy()
    long_stop, short_stop = c-2*a, c+2*a
    rr, hold_minutes = 2., 120
    fixed_long_tp = fixed_short_tp = None
    if name in ("channel_break", "channel_long"):
        long = (c > hi20) & (c.shift(1) <= hi20.shift(1)) & (c > ma200) & (c > o)
        if name != "channel_long":
            short = (c < lo20) & (c.shift(1) >= lo20.shift(1)) & (c < ma200) & (c < o)
    elif name == "ema_pullback":
        long = (ema20 > ema50) & (ema50 > ema200) & (c > ema20) & (c.shift(1) <= ema20.shift(1)) & (c > o)
        short = (ema20 < ema50) & (ema50 < ema200) & (c < ema20) & (c.shift(1) >= ema20.shift(1)) & (c < o)
        long_stop = np.minimum(l.rolling(5).min()-.25*a, c-a)
        short_stop = np.maximum(h.rolling(5).max()+.25*a, c+a)
        long &= (c-long_stop) <= 3*a
        short &= (short_stop-c) <= 3*a
        hold_minutes = 180
    elif name == "range_reentry":
        up, down = h.diff(), -l.diff()
        plus = wilder(up.where((up > down) & (up > 0), 0.), 14)/a
        minus = wilder(down.where((down > up) & (down > 0), 0.), 14)/a
        dx = ((plus-minus).abs()/(plus+minus).replace(0., np.nan)*100)
        adx = wilder(dx, 14)
        long_stop, short_stop = c-1.5*a, c+1.5*a
        long = (c.shift(1) < lower.shift(1)) & (c > lower) & (c < mid) & (c > o) & (adx < 20) & ((mid-c) >= .9*a)
        short = (c.shift(1) > upper.shift(1)) & (c < upper) & (c > mid) & (c < o) & (adx < 20) & ((c-mid) >= .9*a)
        fixed_long_tp = fixed_short_tp = mid
    elif name == "sweep_reclaim":
        long = (l < lo20) & (c > lo20) & (c > o) & (c > ema200)
        short = (h > hi20) & (c < hi20) & (c < o) & (c < ema200)
        long_stop, short_stop = np.minimum(l-.25*a, c-a), np.maximum(h+.25*a, c+a)
        long &= (c-long_stop) <= 3*a
        short &= (short_stop-c) <= 3*a
    elif name == "compression_break":
        width = 4*std
        compressed = width.shift(1) < width.rolling(100).median().shift(1)*.8
        hi10, lo10 = h.rolling(10).max().shift(1), l.rolling(10).min().shift(1)
        long = compressed & (c > hi10) & (c.shift(1) <= hi10.shift(1)) & (ema50 > ema200) & (c > o)
        short = compressed & (c < lo10) & (c.shift(1) >= lo10.shift(1)) & (ema50 < ema200) & (c < o)
        rr, hold_minutes = 3., 180
    elif name.startswith("lux_trendline"):
        lines = trendline_breaks(df)
        long, short = lines.long_break, lines.short_break
        if name == "lux_trendline_trend":
            long = long & (c > ema200)
            short = short & (c < ema200)
        long_stop, short_stop = c-1.5*a, c+1.5*a
        hold_minutes = 180
    elif name == "bos_baseline":
        from bos_backtest import make_bos_signal
        raw = make_bos_signal(df, trend_ma=200)
        result = pd.DataFrame(dict(side=np.zeros(len(df), dtype=int), sl=np.nan,
                                   tp=np.nan, max_hold=max(1, 180//tf_minutes)), index=df.index)
        for i in range(200, len(df)):
            signal = raw(df, i)
            if signal is not None:
                result.iloc[i, :3] = (1 if signal.side == "long" else -1, signal.sl, signal.tp)
        return result

    # Conflicting simultaneous upper/lower trendline breaks are not tradable.
    conflict = long & short
    long, short = long & ~conflict, short & ~conflict
    long = long.fillna(False)
    short = short.fillna(False)
    long.iloc[:200] = False
    short.iloc[:200] = False
    side = np.where(long, 1, np.where(short, -1, 0))
    stop = np.where(long, long_stop, np.where(short, short_stop, np.nan))
    long_tp = c+rr*(c-long_stop) if fixed_long_tp is None else fixed_long_tp
    short_tp = c-rr*(short_stop-c) if fixed_short_tp is None else fixed_short_tp
    target = np.where(long, long_tp, np.where(short, short_tp, np.nan))
    return pd.DataFrame(dict(side=side, sl=stop, tp=target,
                             max_hold=max(1, hold_minutes//tf_minutes)), index=df.index)
