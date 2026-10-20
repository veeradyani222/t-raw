"""Mean-reversion family for the 2026-10 prop-challenge strategy search.

Every builder: build_<name>(df, **params) -> list[Entry|None] with len(df).
All indicators are causal (rolling/ewm over rows <= i only). Each trade has
an ATR stop, a time exit (max_hold) and a reversion exit via `manage`
(closes the trade at the bar close when the reversion condition is met).

Common params
    sides      "long" | "short" | "both"   (trend filter decides the side)
    trend      length of the SMA trend filter on the SAME timeframe (0 = off)
    atr_n      ATR length, stop_atr = stop distance in ATRs
    max_hold   bars before a forced time exit
    hours      optional (start, end) server-hour window for entries (intraday tfs)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H


# ----------------------------------------------------------------- indicators
def sma(x, n):
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()


def atr(df, n=14):
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy()


def rsi(c, n=2):
    d = np.diff(np.asarray(c, float), prepend=np.nan)
    up = pd.Series(np.where(d > 0, d, 0.0))
    dn = pd.Series(np.where(d < 0, -d, 0.0))
    au = up.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    ad = dn.ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean()
    rs = au / ad.replace(0, np.nan)
    out = 100 - 100 / (1 + rs)
    out[(ad == 0) & (au > 0)] = 100.0
    return out.to_numpy()


def connors_rsi(c, n_rsi=3, n_streak=2, n_rank=100):
    c = np.asarray(c, float)
    streak = np.zeros(len(c))
    for i in range(1, len(c)):
        if c[i] > c[i - 1]:
            streak[i] = streak[i - 1] + 1 if streak[i - 1] > 0 else 1
        elif c[i] < c[i - 1]:
            streak[i] = streak[i - 1] - 1 if streak[i - 1] < 0 else -1
    roc = pd.Series(c).pct_change().to_numpy()
    rank = np.full(len(c), np.nan)
    cur = roc[n_rank:]
    cnt = np.zeros(len(cur))
    for k in range(1, n_rank + 1):          # compare with each of the previous n_rank values
        cnt += roc[n_rank - k:len(roc) - k] < cur
    rank[n_rank:] = cnt / n_rank * 100
    return (rsi(c, n_rsi) + rsi(streak + 1000.0, n_streak) + rank) / 3.0


def williams_r(df, n=14):
    hh = df["high"].rolling(n).max().to_numpy()
    ll = df["low"].rolling(n).min().to_numpy()
    return -100 * (hh - df["close"].to_numpy()) / (hh - ll)


def stoch_k(df, n=14, smooth=3):
    hh = df["high"].rolling(n).max()
    ll = df["low"].rolling(n).min()
    k = 100 * (df["close"] - ll) / (hh - ll)
    return k.rolling(smooth).mean().to_numpy()


def ibs(df):
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    rng = h - l
    return np.where(rng > 0, (c - l) / np.where(rng > 0, rng, 1), 0.5)


def session_vwap(df):
    """Volume (tick) weighted typical price, reset every server day; value at
    bar i uses bars of the same day up to and including i."""
    tp = (df["high"] + df["low"] + df["close"]).to_numpy(float) / 3
    v = df["tick_volume"].to_numpy(float) + 1e-9
    day = pd.DatetimeIndex(df["time"]).normalize()
    g = pd.Series(tp * v).groupby(day).cumsum().to_numpy()
    gv = pd.Series(v).groupby(day).cumsum().to_numpy()
    return g / gv


# ----------------------------------------------------------------- assembly
def adx(df, n=14):
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    up = np.r_[np.nan, h[1:] - h[:-1]]
    dn = np.r_[np.nan, l[:-1] - l[1:]]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(df, n)
    f = lambda x: pd.Series(x).ewm(alpha=1.0 / n, adjust=False, min_periods=n).mean().to_numpy()
    pdi, ndi = 100 * f(pdm) / a, 100 * f(ndm) / a
    dx = 100 * np.abs(pdi - ndi) / np.where(pdi + ndi > 0, pdi + ndi, np.nan)
    return f(np.nan_to_num(dx))


def _hour_ok(df, hours):
    if hours is None:
        return np.ones(len(df), bool)
    a, b = hours
    h = pd.DatetimeIndex(df["time"]).hour.to_numpy()
    return (h >= a) & (h < b) if a <= b else ((h >= a) | (h < b))


def _assemble(df, long_sig, short_sig, exit_long, exit_short, *, atr_n=14,
              stop_atr=2.0, max_hold=10, sides="long", trend=200, tp_atr=None,
              hours=None, exit_hour=None, adx_max=None, tag="mr", _raw=False):
    c = df["close"].to_numpy(float)
    a = atr(df, atr_n)
    ok = np.isfinite(a) & (a > 0) & _hour_ok(df, hours)
    if adx_max is not None:   # range regime only
        ok &= np.nan_to_num(adx(df, 14), nan=999) < adx_max
    if trend:
        ma = sma(c, trend)
        up, dn = c > ma, c < ma
    else:
        up = dn = np.ones(len(c), bool)
    L = np.asarray(long_sig, bool) & up & ok & (sides in ("long", "both"))
    S = np.asarray(short_sig, bool) & dn & ok & (sides in ("short", "both"))
    xl = np.nan_to_num(np.asarray(exit_long, float)).astype(bool)
    xs = np.nan_to_num(np.asarray(exit_short, float)).astype(bool)

    if _raw:  # arrays for the fast screener (screen.py); not used by the judge
        return dict(L=L & ~S, S=S & ~L, xl=xl, xs=xs, atr=a, stop_atr=stop_atr,
                    tp_atr=tp_atr, max_hold=max_hold, exit_hour=exit_hour)

    def manage(_df, i, pos):
        if pos["side"] == "long":
            return "close" if xl[i] else None
        return "close" if xs[i] else None

    out = [None] * len(c)
    for i in np.flatnonzero(L & ~S):
        out[i] = H.Entry("long", c[i] - stop_atr * a[i],
                         tp=None if tp_atr is None else c[i] + tp_atr * a[i],
                         max_hold=max_hold, exit_hour=exit_hour, manage=manage,
                         meta={"tag": tag})
    for i in np.flatnonzero(S & ~L):
        out[i] = H.Entry("short", c[i] + stop_atr * a[i],
                         tp=None if tp_atr is None else c[i] - tp_atr * a[i],
                         max_hold=max_hold, exit_hour=exit_hour, manage=manage,
                         meta={"tag": tag})
    return out


# ----------------------------------------------------------------- builders
def build_rsi2(df, n=2, lo=10, hi=90, exit_ma=5, **kw):
    """Larry Connors RSI(2): buy oversold above the trend MA, exit when the
    close crosses back above a short MA (exit_ma) or RSI > 50 if exit_ma=0."""
    c = df["close"].to_numpy(float)
    r = rsi(c, n)
    if exit_ma:
        m = sma(c, exit_ma)
        xl, xs = c > m, c < m
    else:
        xl, xs = r > 50, r < 50
    return _assemble(df, r < lo, r > hi, xl, xs, tag="rsi2", **kw)


def build_crsi(df, lo=10, hi=90, exit_lvl=60, **kw):
    """Connors RSI (RSI3 + streak RSI2 + 100-bar ROC rank)."""
    c = df["close"].to_numpy(float)
    r = connors_rsi(c)
    return _assemble(df, r < lo, r > hi, r > exit_lvl, r < 100 - exit_lvl, tag="crsi", **kw)


def build_bb_fade(df, n=20, k=2.0, **kw):
    """Close outside the Bollinger band -> fade back to the middle band."""
    c = df["close"].to_numpy(float)
    m = sma(c, n)
    sd = pd.Series(c).rolling(n).std().to_numpy()
    return _assemble(df, c < m - k * sd, c > m + k * sd, c > m, c < m, tag="bb", **kw)


def build_zscore(df, n=50, z_in=2.0, z_out=0.0, **kw):
    c = df["close"].to_numpy(float)
    m = sma(c, n)
    sd = pd.Series(c).rolling(n).std().to_numpy()
    z = (c - m) / sd
    return _assemble(df, z < -z_in, z > z_in, z > -z_out, z < z_out, tag="z", **kw)


def build_ibs(df, lo=0.2, hi=0.8, **kw):
    """Internal bar strength: close near the low of the bar -> long, exit
    when a later bar closes near its high (or previous-high break)."""
    v = ibs(df)
    c = df["close"].to_numpy(float)
    ph = np.r_[np.nan, df["high"].to_numpy(float)[:-1]]
    pl = np.r_[np.nan, df["low"].to_numpy(float)[:-1]]
    return _assemble(df, v < lo, v > hi, (v > hi) | (c > ph), (v < lo) | (c < pl), tag="ibs", **kw)


def build_nlow(df, n=10, **kw):
    """Close at an N-bar low (in an uptrend) -> long; exit on close above the
    previous bar's high. Mirror for shorts."""
    c = df["close"].to_numpy(float)
    lo = pd.Series(c).rolling(n).min().to_numpy()
    hi = pd.Series(c).rolling(n).max().to_numpy()
    ph = np.r_[np.nan, df["high"].to_numpy(float)[:-1]]
    pl = np.r_[np.nan, df["low"].to_numpy(float)[:-1]]
    return _assemble(df, c <= lo, c >= hi, c > ph, c < pl, tag="nlow", **kw)


def build_wpr(df, n=14, lo=-90, hi=-10, exit_lvl=-50, **kw):
    w = williams_r(df, n)
    return _assemble(df, w < lo, w > hi, w > exit_lvl, w < exit_lvl, tag="wpr", **kw)


def build_stoch(df, n=14, smooth=3, lo=15, hi=85, exit_lvl=50, **kw):
    k = stoch_k(df, n, smooth)
    return _assemble(df, k < lo, k > hi, k > exit_lvl, k < exit_lvl, tag="stoch", **kw)


def build_vwap(df, dev_atr=1.5, **kw):
    """Intraday: price stretched dev_atr ATRs from the session VWAP -> fade
    back to VWAP; forced flat at exit_hour (default 23) server time."""
    c = df["close"].to_numpy(float)
    vw = session_vwap(df)
    a = atr(df, kw.get("atr_n", 14))
    kw.setdefault("exit_hour", 23)
    kw.setdefault("trend", 0)
    return _assemble(df, c < vw - dev_atr * a, c > vw + dev_atr * a, c >= vw, c <= vw,
                     tag="vwap", **kw)


def build_rsi2_dip_htf(df, n=2, lo=10, exit_ma=5, htf_trend=50, **kw):
    """RSI(2) dip-buy with the trend measured on DAILY closes (completed days
    only) instead of the bar timeframe; for H1/H4 data."""
    c = df["close"].to_numpy(float)
    t = pd.DatetimeIndex(df["time"])
    day = t.normalize()
    dclose = pd.Series(c).groupby(day).last()
    dma = dclose.rolling(htf_trend).mean()
    # value usable on day D = MA through day D-1 (completed)
    prev = dma.shift(1)
    dprev_close = dclose.shift(1)
    up = (dprev_close > prev).reindex(day).to_numpy()
    dn = (dprev_close < prev).reindex(day).to_numpy()
    r = rsi(c, n)
    m = sma(c, exit_ma)
    kw["trend"] = 0
    up = np.nan_to_num(up.astype(float)).astype(bool)
    dn = np.nan_to_num(dn.astype(float)).astype(bool)
    return _assemble(df, (r < lo) & up, (r > 100 - lo) & dn, c > m, c < m, tag="rsi2htf", **kw)


def build_dip_combo(df, wpr_n=10, wpr_lo=-85, nlow_n=10, ibs_lo=0.15, need=1,
                    exit_mode="prev_high", **kw):
    """Index dip-buy ensemble: count how many of three independent oversold
    conditions fire (Williams %R extreme, close at an N-bar low, close in the
    bottom of its bar); go long when at least `need` agree. Exit on a close
    above the previous bar's high (exit_mode="prev_high") or when %R
    recovers above -30 ("wpr")."""
    c = df["close"].to_numpy(float)
    w = williams_r(df, wpr_n)
    lo = pd.Series(c).rolling(nlow_n).min().to_numpy()
    votes = (np.nan_to_num(w, nan=0) < wpr_lo).astype(int) + (c <= lo).astype(int) \
        + (ibs(df) < ibs_lo).astype(int)
    ph = np.r_[np.nan, df["high"].to_numpy(float)[:-1]]
    if exit_mode == "prev_high":
        xl = c > ph
    elif exit_mode == "wpr":
        xl = w > -30
    elif exit_mode.startswith("ma"):          # e.g. "ma5": close back above SMA(5)
        xl = c > sma(c, int(exit_mode[2:]))
    else:                                     # "time": stop / max_hold only
        xl = np.zeros(len(c), bool)
    kw.setdefault("sides", "long")
    return _assemble(df, votes >= need, np.zeros(len(c), bool), xl, np.zeros(len(c), bool),
                     tag="dipcombo", **kw)
