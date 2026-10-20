"""Causal indicator helpers for the gold_fix family (research only).

Every array returned here at index i uses only rows <= i.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def arr(df):
    return (df["open"].to_numpy(float), df["high"].to_numpy(float),
            df["low"].to_numpy(float), df["close"].to_numpy(float))


def atr(df, n=14):
    o, h, l, c = arr(df)
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy()


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def adx(df, n=14):
    o, h, l, c = arr(df)
    up = np.r_[0, h[1:] - h[:-1]]
    dn = np.r_[0, l[:-1] - l[1:]]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    a = 1.0 / n
    trs = pd.Series(tr).ewm(alpha=a, adjust=False, min_periods=n).mean()
    pdi = 100 * pd.Series(pdm).ewm(alpha=a, adjust=False, min_periods=n).mean() / trs
    ndi = 100 * pd.Series(ndm).ewm(alpha=a, adjust=False, min_periods=n).mean() / trs
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    return dx.ewm(alpha=a, adjust=False, min_periods=n).mean().to_numpy(), pdi.to_numpy(), ndi.to_numpy()


def cmf(df, n=20):
    o, h, l, c = arr(df)
    v = df["tick_volume"].to_numpy(float)
    rng = h - l
    mfm = np.where(rng > 0, ((c - l) - (h - c)) / np.where(rng > 0, rng, 1.0), 0.0)
    s = pd.Series(mfm * v).rolling(n).sum().to_numpy()
    sv = pd.Series(v).rolling(n).sum().to_numpy()
    return np.where(sv > 0, s / np.where(sv > 0, sv, 1), np.nan)


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.maximum(d, 0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = pd.Series(np.maximum(-d, 0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return (100 - 100 / (1 + up / dn.replace(0, np.nan))).to_numpy()


def rolling_pct_rank(x, n):
    """Percentile of x[i] within the trailing window x[i-n+1..i] (causal)."""
    s = pd.Series(x)
    return s.rolling(n, min_periods=n // 2).rank(pct=True).to_numpy()


def swings(h, l, w):
    """Fractal swing indices (strict, as trader.strategies.structure). A swing at
    j is only CONFIRMED at bar j+w."""
    n = len(h)
    hm = pd.Series(h)
    lm = pd.Series(l)
    left_h = hm.shift(1).rolling(w).max().to_numpy()
    right_h = hm[::-1].shift(1).rolling(w).max().to_numpy()[::-1]
    left_l = lm.shift(1).rolling(w).min().to_numpy()
    right_l = lm[::-1].shift(1).rolling(w).min().to_numpy()[::-1]
    sh = np.where((h > left_h) & (h > right_h))[0]
    sl = np.where((l < left_l) & (l < right_l))[0]
    sh = sh[(sh >= w) & (sh < n - w)]
    sl = sl[(sl >= w) & (sl < n - w)]
    return sh, sl


def confirmed_last(sw, w, n):
    """last[i] = most recent swing j with j + w <= i, else -1."""
    last = np.full(n, -1, dtype=int)
    if len(sw) == 0:
        return last
    conf = sw + w
    pos = np.searchsorted(conf, np.arange(n), side="right") - 1
    ok = pos >= 0
    last[ok] = sw[pos[ok]]
    return last


def htf_close_aligned(df, rule, func):
    """Compute `func(htf_df) -> array` on a resample of df to `rule` (e.g. '4h',
    '1D') and map back so bar i sees only HTF bars that CLOSED at or before
    bar i's close. Returns array len(df)."""
    t = df["time"]
    g = df.set_index("time").resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last",
         "tick_volume": "sum"}).dropna().reset_index()
    vals = func(g)
    # bar duration of base tf
    step = (t.iloc[1:].reset_index(drop=True) - t.iloc[:-1].reset_index(drop=True)).median()
    htf_close_time = g["time"] + pd.Timedelta(rule)
    base_close = t + step
    idx = np.searchsorted(htf_close_time.to_numpy(), base_close.to_numpy(), side="right") - 1
    out = np.full(len(df), np.nan)
    ok = idx >= 0
    out[ok] = np.asarray(vals, float)[idx[ok]]
    return out


def first_friday_mask(times):
    t = pd.DatetimeIndex(times)
    return (t.weekday == 4) & (t.day <= 7)
