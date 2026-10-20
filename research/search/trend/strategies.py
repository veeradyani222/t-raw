"""Trend-following family for the 2026-10 prop search.

Every build_<name>(df, **params) returns a list (len(df)) of H.Entry | None.
All signals are CAUSAL: the Entry at bar i only uses rows <= i (indicators are
ewm / rolling windows ending at i; Donchian / Ichimoku levels use shift(+k)).

Shared exit machinery (_emit):
  * initial stop  = entry close -/+ sl_mult * ATR(atr_n)
  * trailing stop = chandelier: highest high since entry - trail_mult * ATR
                    (lowest low + ... for shorts); trail_mult=None disables
  * optional rule exit (exit_long / exit_short boolean arrays) -> "close"
  * optional tp_mult (fixed target in ATR) and max_hold (bars)
  * opposite entry signal flips the position (harness allow_flip)
mode="event": entry only on the bar the condition turns on.
mode="state": entry on every bar the condition holds (re-enters after a stop
              while the trend is still on; harness ignores it while in a trade).
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from research.prop import harness as H


# ----------------------------------------------------------------- indicators
def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def wilder(x, n):
    return pd.Series(x).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def _hlc(df):
    return (df["high"].to_numpy(float), df["low"].to_numpy(float),
            df["close"].to_numpy(float))


def atr(df, n=14):
    h, l, c = _hlc(df)
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return wilder(tr, n)


def adx(df, n=14):
    h, l, c = _hlc(df)
    up = np.r_[0.0, h[1:] - h[:-1]]
    dn = np.r_[0.0, l[:-1] - l[1:]]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(df, n)
    pdi = 100 * wilder(pdm, n) / np.where(a > 0, a, np.nan)
    ndi = 100 * wilder(ndm, n) / np.where(a > 0, a, np.nan)
    dx = 100 * abs(pdi - ndi) / np.where(pdi + ndi > 0, pdi + ndi, np.nan)
    return np.nan_to_num(wilder(np.nan_to_num(dx), n)), pdi, ndi


def supertrend(df, n=10, mult=3.0):
    """Returns direction array (+1/-1). Loop is causal (uses i-1 state)."""
    h, l, c = _hlc(df)
    a = atr(df, n)
    mid = (h + l) / 2
    ub, lb = mid + mult * a, mid - mult * a
    fu, fl = ub.copy(), lb.copy()
    d = np.ones(len(c))
    for i in range(1, len(c)):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if d[i - 1] == 1:
            d[i] = -1 if c[i] < fl[i] else 1
        else:
            d[i] = 1 if c[i] > fu[i] else -1
    return d


def psar(df, step=0.02, mx=0.2):
    h, l, _ = _hlc(df)
    n = len(h)
    d = np.ones(n)
    sar = np.empty(n)
    up, af, ep, s = True, step, h[0], l[0]
    sar[0] = s
    for i in range(1, n):
        s = s + af * (ep - s)
        if up:
            s = min(s, l[i - 1], l[i - 2] if i > 1 else l[i - 1])
            if l[i] < s:
                up, s, ep, af = False, ep, l[i], step
            elif h[i] > ep:
                ep, af = h[i], min(af + step, mx)
        else:
            s = max(s, h[i - 1], h[i - 2] if i > 1 else h[i - 1])
            if h[i] > s:
                up, s, ep, af = True, ep, h[i], step
            elif l[i] < ep:
                ep, af = l[i], min(af + step, mx)
        sar[i] = s
        d[i] = 1 if up else -1
    return d, sar


def _cross_up(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    return np.r_[False, (a[1:] > b[1:]) & (a[:-1] <= b[:-1])]


def _onset(state):
    s = np.asarray(state, bool)
    return np.r_[s[:1], s[1:] & ~s[:-1]]


# ------------------------------------------------------------ common emitter
def _emit(df, long_on, short_on, *, atr_n=14, sl_mult=2.0, trail_mult=3.0,
          tp_mult=None, max_hold=None, exit_long=None, exit_short=None,
          mode="event", long_only=False, short_only=False, hours=None,
          adx_min=None, adx_n=14, trend_ema=None, warm=250):
    n = len(df)
    h, l, c = _hlc(df)
    a = atr(df, atr_n)
    long_on = np.asarray(long_on, bool).copy()
    short_on = np.asarray(short_on, bool).copy()
    if mode == "event":
        long_on, short_on = _onset(long_on), _onset(short_on)
    filt = np.ones(n, bool)
    if adx_min:
        filt &= adx(df, adx_n)[0] >= adx_min
    if hours is not None:
        hr = pd.DatetimeIndex(df["time"]).hour.to_numpy()
        a0, a1 = hours
        filt &= (hr >= a0) & (hr < a1) if a0 < a1 else ((hr >= a0) | (hr < a1))
    lf, sf = filt.copy(), filt.copy()
    if trend_ema:
        te = ema(c, trend_ema)
        lf &= c > te
        sf &= c < te
    long_on &= lf
    short_on &= sf
    if long_only:
        short_on[:] = False
    if short_only:
        long_on[:] = False
    long_on[:warm] = False
    short_on[:warm] = False
    exl = np.zeros(n, bool) if exit_long is None else np.asarray(exit_long, bool)
    exs = np.zeros(n, bool) if exit_short is None else np.asarray(exit_short, bool)

    def manage(_df, i, pos):
        if pos["side"] == "long":
            if exl[i]:
                return "close"
            if trail_mult is None:
                return None
            pos["ext"] = max(pos.get("ext", -math.inf), h[i])
            ns = pos["ext"] - trail_mult * a[i]
            if ns > pos["sl"]:
                return "close" if ns >= c[i] else ns
        else:
            if exs[i]:
                return "close"
            if trail_mult is None:
                return None
            pos["ext"] = min(pos.get("ext", math.inf), l[i])
            ns = pos["ext"] + trail_mult * a[i]
            if ns < pos["sl"]:
                return "close" if ns <= c[i] else ns
        return None

    use_manage = trail_mult is not None or exit_long is not None or exit_short is not None
    out = [None] * n
    for i in np.flatnonzero(long_on | short_on):
        if not (a[i] > 0):
            continue
        side = "long" if long_on[i] else "short"
        sgn = 1 if side == "long" else -1
        out[i] = H.Entry(side, sl=c[i] - sgn * sl_mult * a[i],
                         tp=None if tp_mult is None else c[i] + sgn * tp_mult * a[i],
                         max_hold=max_hold, manage=manage if use_manage else None)
    return out


# ---------------------------------------------------------------- strategies
def build_ma_cross(df, fast=20, slow=100, kind="ema", **kw):
    """Fast/slow MA regime. Opposite cross flips."""
    c = df["close"].to_numpy(float)
    f = (ema if kind == "ema" else sma)(c, fast)
    s = (ema if kind == "ema" else sma)(c, slow)
    up = f > s
    kw.setdefault("exit_long", ~up)
    kw.setdefault("exit_short", up)
    return _emit(df, up, ~up & ~np.isnan(s), **kw)


def build_donchian(df, n_entry=55, n_exit=20, **kw):
    """Turtle: close beyond prior n_entry-bar high/low; exit on n_exit opposite break."""
    h, l, c = _hlc(df)
    hi = pd.Series(h).rolling(n_entry).max().shift(1).to_numpy()
    lo = pd.Series(l).rolling(n_entry).min().shift(1).to_numpy()
    xlo = pd.Series(l).rolling(n_exit).min().shift(1).to_numpy()
    xhi = pd.Series(h).rolling(n_exit).max().shift(1).to_numpy()
    kw.setdefault("exit_long", c < xlo)
    kw.setdefault("exit_short", c > xhi)
    kw.setdefault("mode", "event")
    return _emit(df, c > hi, c < lo, **kw)


def build_supertrend(df, st_n=10, st_mult=3.0, **kw):
    d = supertrend(df, st_n, st_mult)
    kw.setdefault("exit_long", d < 0)
    kw.setdefault("exit_short", d > 0)
    return _emit(df, d > 0, d < 0, **kw)


def build_keltner_bo(df, n=20, k=2.0, **kw):
    """Close beyond EMA(n) +/- k*ATR(n); exit back through the EMA."""
    c = df["close"].to_numpy(float)
    m = ema(c, n)
    a = atr(df, n)
    kw.setdefault("exit_long", c < m)
    kw.setdefault("exit_short", c > m)
    return _emit(df, c > m + k * a, c < m - k * a, **kw)


def build_bollinger_bo(df, n=20, k=2.0, **kw):
    c = df["close"].to_numpy(float)
    s = pd.Series(c)
    m = s.rolling(n).mean().to_numpy()
    sd = s.rolling(n).std().to_numpy()
    kw.setdefault("exit_long", c < m)
    kw.setdefault("exit_short", c > m)
    return _emit(df, c > m + k * sd, c < m - k * sd, **kw)


def build_macd(df, f=12, s=26, sig=9, zero_filter=True, **kw):
    c = df["close"].to_numpy(float)
    line = ema(c, f) - ema(c, s)
    sl = ema(line, sig)
    up = line > sl
    if zero_filter:
        lon, sho = up & (line > 0), ~up & (line < 0)
    else:
        lon, sho = up, ~up
    kw.setdefault("exit_long", ~up)
    kw.setdefault("exit_short", up)
    return _emit(df, lon, sho, **kw)


def build_ichimoku(df, t=9, k=26, b=52, **kw):
    """Close above the (already-projected, so causal) cloud with tenkan>kijun."""
    h, l, c = _hlc(df)
    H_ = pd.Series(h)
    L_ = pd.Series(l)
    ten = ((H_.rolling(t).max() + L_.rolling(t).min()) / 2).to_numpy()
    kij = ((H_.rolling(k).max() + L_.rolling(k).min()) / 2).to_numpy()
    sa = pd.Series((ten + kij) / 2).shift(k).to_numpy()
    sb = ((H_.rolling(b).max() + L_.rolling(b).min()) / 2).shift(k).to_numpy()
    top, bot = np.fmax(sa, sb), np.fmin(sa, sb)
    lon = (c > top) & (ten > kij)
    sho = (c < bot) & (ten < kij)
    kw.setdefault("exit_long", c < kij)
    kw.setdefault("exit_short", c > kij)
    return _emit(df, lon, sho, **kw)


def build_psar(df, step=0.02, mx=0.2, **kw):
    d, _ = psar(df, step, mx)
    kw.setdefault("exit_long", d < 0)
    kw.setdefault("exit_short", d > 0)
    return _emit(df, d > 0, d < 0, **kw)


def build_tsmom(df, lookback=20, **kw):
    """Time-series momentum: sign of the close-to-close return over `lookback` bars."""
    c = df["close"].to_numpy(float)
    r = c / np.r_[np.full(lookback, np.nan), c[:-lookback]] - 1
    up, dn = r > 0, r < 0
    kw.setdefault("exit_long", dn)
    kw.setdefault("exit_short", up)
    return _emit(df, up, dn, **kw)


def build_adx_di(df, n=14, adx_th=25, **kw):
    """DI+/DI- regime entered only while ADX >= adx_th."""
    a, pdi, ndi = adx(df, n)
    up = pdi > ndi
    kw.setdefault("exit_long", ~up)
    kw.setdefault("exit_short", up)
    return _emit(df, up & (a >= adx_th), ~up & (a >= adx_th), **kw)


# ------------------------------------------------- higher-timeframe trend helpers
def daily_trend(df, kind="tsmom", n=50):
    """+1/-1/0 daily trend known at each bar, from FULLY CLOSED prior days only.
    Built from df's own bars grouped by broker day; the value for day D comes
    from days <= D-1, so an intraday bar never sees its own day's close."""
    t = pd.DatetimeIndex(df["time"])
    day = t.normalize()
    dc = pd.Series(df["close"].to_numpy(float), index=day).groupby(level=0).last()
    if kind == "tsmom":
        sig = np.sign(dc / dc.shift(n) - 1)
    elif kind == "ema":
        sig = np.sign(dc - dc.ewm(span=n, adjust=False).mean())
    else:
        raise ValueError(kind)
    sig = sig.shift(1)                     # known only after that day closed
    return np.nan_to_num(sig.reindex(day).to_numpy())


def rsi(x, n=14):
    d = np.diff(np.asarray(x, float), prepend=x[0])
    up = wilder(np.where(d > 0, d, 0.0), n)
    dn = wilder(np.where(d < 0, -d, 0.0), n)
    return 100 - 100 / (1 + up / np.where(dn > 0, dn, np.nan))


def build_htf_breakout(df, d_kind="tsmom", d_n=50, n_entry=20, n_exit=None, **kw):
    """Intraday Donchian breakout taken ONLY in the direction of the closed-day
    trend (sign of d_n-day return or price vs d_n-day EMA). Exit when the day
    trend flips, or (n_exit) on an opposite n_exit-bar break."""
    h, l, c = _hlc(df)
    tr = daily_trend(df, d_kind, d_n)
    hi = pd.Series(h).rolling(n_entry).max().shift(1).to_numpy()
    lo = pd.Series(l).rolling(n_entry).min().shift(1).to_numpy()
    exl, exs = tr < 0, tr > 0
    if n_exit:
        exl = exl | (c < pd.Series(l).rolling(n_exit).min().shift(1).to_numpy())
        exs = exs | (c > pd.Series(h).rolling(n_exit).max().shift(1).to_numpy())
    kw.setdefault("exit_long", exl)
    kw.setdefault("exit_short", exs)
    return _emit(df, (c > hi) & (tr > 0), (c < lo) & (tr < 0), **kw)


def build_htf_pullback(df, d_kind="tsmom", d_n=50, rsi_n=2, rsi_lo=10, **kw):
    """Buy the dip in a closed-day uptrend (sell the rip in a downtrend):
    RSI(rsi_n) drops below rsi_lo (above 100-rsi_lo for shorts) while the
    daily trend is on. Entry fires on the bar the condition starts."""
    c = df["close"].to_numpy(float)
    tr = daily_trend(df, d_kind, d_n)
    r = rsi(c, rsi_n)
    kw.setdefault("exit_long", tr < 0)
    kw.setdefault("exit_short", tr > 0)
    return _emit(df, (r < rsi_lo) & (tr > 0), (r > 100 - rsi_lo) & (tr < 0), **kw)


def build_donchian_volx(df, n_entry=80, n_exit=20, fast=14, slow=100, ratio=1.0, **kw):
    """Donchian breakout only when volatility is expanding: ATR(fast)/ATR(slow) > ratio."""
    a = atr(df, fast) / np.where(atr(df, slow) > 0, atr(df, slow), np.nan)
    h, l, c = _hlc(df)
    hi = pd.Series(h).rolling(n_entry).max().shift(1).to_numpy()
    lo = pd.Series(l).rolling(n_entry).min().shift(1).to_numpy()
    kw.setdefault("exit_long", c < pd.Series(l).rolling(n_exit).min().shift(1).to_numpy())
    kw.setdefault("exit_short", c > pd.Series(h).rolling(n_exit).max().shift(1).to_numpy())
    ok = a > ratio
    return _emit(df, (c > hi) & ok, (c < lo) & ok, **kw)


# ------------------------------------------------------- candidate entry points
# Thin wrappers with the in-sample candidate settings baked in as defaults
# (any default can still be overridden by keyword for neighbourhood checks).
def build_gold_boll80(df, n=80, k=2.5, sl_mult=3.0, **kw):
    """C1  XAUUSD H4: close beyond 80-bar Bollinger(2.5); exit back through the
    mid-band, 3xATR chandelier trail, initial stop 3xATR; opposite break flips."""
    return build_bollinger_bo(df, n=n, k=k, sl_mult=sl_mult, **kw)


def build_gold_boll50(df, n=50, k=2.0, sl_mult=2.0, **kw):
    """C2  XAUUSD H4: Bollinger(50, 2.0) breakout, 2xATR initial stop."""
    return build_bollinger_bo(df, n=n, k=k, sl_mult=sl_mult, **kw)


def build_gold_boll200_h1(df, n=200, k=2.0, sl_mult=3.0, **kw):
    """C3  XAUUSD H1: same horizon as C2 on H1 bars (200 H1 ~ 50 H4)."""
    return build_bollinger_bo(df, n=n, k=k, sl_mult=sl_mult, **kw)


def build_gold_donch80(df, n_entry=80, n_exit=20, sl_mult=3.0, **kw):
    """C4  XAUUSD H4: turtle-style 80-bar Donchian breakout, 20-bar exit, 3xATR stop/trail."""
    return build_donchian(df, n_entry=n_entry, n_exit=n_exit, sl_mult=sl_mult, **kw)


def build_audjpy_boll20(df, n=20, k=2.0, sl_mult=2.0, **kw):
    """C5  AUDJPY H4: Bollinger(20, 2.0) breakout (only non-gold candidate)."""
    return build_bollinger_bo(df, n=n, k=k, sl_mult=sl_mult, **kw)
