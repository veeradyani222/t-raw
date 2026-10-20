"""Other gold ideas (trend following, session breakout, pullback, hour hold).
All builders are causal and return list(len(df)) of H.Entry | None."""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H
from research.search.gold_fix import lib as L


def _bars_per_hour(df):
    t = pd.DatetimeIndex(df["time"])
    step = pd.Series(t[1:] - t[:-1]).median()
    return max(1, int(round(pd.Timedelta("1h") / step)))


# --------------------------------------------------------------------------- #
# Trend following: Donchian breakout with ATR stop + trailing exits             #
# --------------------------------------------------------------------------- #
def build_donchian(df, n_entry=20, n_exit=10, atr_n=20, atr_stop=2.0, trail_atr=None,
                   ma_n=None, sides=("long", "short"), adx_min=None, max_hold=None):
    """Close breaks the prior n_entry-bar high (low) -> long (short).
    Initial stop atr_stop x ATR. Exit: close beyond prior n_exit-bar opposite
    extreme (turtle style) and/or chandelier trail of trail_atr x ATR."""
    o, h, l, c = L.arr(df)
    n = len(df)
    a = L.atr(df, atr_n)
    hh = pd.Series(h).rolling(n_entry).max().shift(1).to_numpy()
    llo = pd.Series(l).rolling(n_entry).min().shift(1).to_numpy()
    xh = pd.Series(h).rolling(n_exit).max().to_numpy() if n_exit else None
    xl = pd.Series(l).rolling(n_exit).min().to_numpy() if n_exit else None
    ma = L.ema(c, ma_n) if ma_n else None
    ad = L.adx(df, 14)[0] if adx_min else None
    prev = np.r_[np.nan, c[:-1]]

    def manage(_df, i, pos):
        new = None
        if pos["side"] == "long":
            if n_exit and c[i] < xl[i - 1]:
                return "close"
            if trail_atr:
                st = h[pos["bar"]:i + 1].max() - trail_atr * a[i]
                if st > pos["sl"]:
                    new = st
        else:
            if n_exit and c[i] > xh[i - 1]:
                return "close"
            if trail_atr:
                st = l[pos["bar"]:i + 1].min() + trail_atr * a[i]
                if st < pos["sl"]:
                    new = st
        return new

    out = [None] * n
    with np.errstate(invalid="ignore"):
        lg = (c > hh) & (prev <= hh)
        sh = (c < llo) & (prev >= llo)
        if ma is not None:
            lg &= c > ma
            sh &= c < ma
        if ad is not None:
            lg &= ad >= adx_min
            sh &= ad >= adx_min
    for i in np.where(lg | sh)[0]:
        if not np.isfinite(a[i]) or a[i] <= 0:
            continue
        side = "long" if lg[i] else "short"
        if side not in sides:
            continue
        sl = c[i] - atr_stop * a[i] if side == "long" else c[i] + atr_stop * a[i]
        out[i] = H.Entry(side, sl=float(sl), max_hold=max_hold, manage=manage)
    return out


# --------------------------------------------------------------------------- #
# Session range breakout (Asia range -> London/NY breakout)                     #
# --------------------------------------------------------------------------- #
def build_session_break(df, range_start=0, range_end=8, entry_end=16, exit_hour=23,
                        tp_r=None, stop="range", atr_stop=1.0, sides=("long", "short"),
                        min_range_atr=0.0, max_range_atr=99.0, ma_n=None):
    """Range = high/low of bars with hour in [range_start, range_end) of the same
    server day. The first bar with hour in [range_end, entry_end) that CLOSES
    outside the range enters (one attempt per day). Stop = other side of range
    ('range'), range mid ('mid') or atr_stop x hourly ATR ('atr'). Exit at the
    close of the first bar with hour == exit_hour, or at tp_r x risk."""
    o, h, l, c = L.arr(df)
    n = len(df)
    t = pd.DatetimeIndex(df["time"])
    hr = t.hour.to_numpy()
    day = t.normalize().to_numpy()
    a = L.atr(df, 14 * _bars_per_hour(df))
    ma = L.ema(c, ma_n) if ma_n else None
    inr = (hr >= range_start) & (hr < range_end)
    g = pd.DataFrame({"day": day, "h": np.where(inr, h, np.nan), "l": np.where(inr, l, np.nan)})
    rh = g.groupby("day")["h"].cummax().to_numpy()
    rl = g.groupby("day")["l"].cummin().to_numpy()
    rh = pd.Series(rh).groupby(day).ffill().to_numpy()
    rl = pd.Series(rl).groupby(day).ffill().to_numpy()
    out = [None] * n
    used = None
    for i in range(1, n):
        if not (range_end <= hr[i] < entry_end) or used == day[i]:
            continue
        hi, lo = rh[i], rl[i]
        if not (np.isfinite(hi) and np.isfinite(lo) and np.isfinite(a[i])):
            continue
        rng = hi - lo
        if rng <= 0 or not (min_range_atr * a[i] <= rng <= max_range_atr * a[i]):
            continue
        if c[i] > hi:
            side = "long"
        elif c[i] < lo:
            side = "short"
        else:
            continue
        used = day[i]
        if side not in sides:
            continue
        if ma is not None and ((side == "long" and not c[i] > ma[i]) or (side == "short" and not c[i] < ma[i])):
            continue
        if stop == "range":
            sl = lo if side == "long" else hi
        elif stop == "mid":
            sl = (hi + lo) / 2
        else:
            sl = c[i] - atr_stop * a[i] if side == "long" else c[i] + atr_stop * a[i]
        risk = abs(c[i] - sl)
        if risk <= 0:
            continue
        tp = None
        if tp_r:
            tp = c[i] + tp_r * risk if side == "long" else c[i] - tp_r * risk
        out[i] = H.Entry(side, sl=float(sl), tp=tp, exit_hour=exit_hour)
    return out


# --------------------------------------------------------------------------- #
# Pullback in trend (RSI dip inside an EMA trend)                               #
# --------------------------------------------------------------------------- #
def build_pullback(df, fast=50, slow=200, rsi_n=2, rsi_lo=10, rsi_exit=70, atr_stop=2.0,
                   max_hold=24, sides=("long", "short"), tp_atr=None):
    o, h, l, c = L.arr(df)
    n = len(df)
    a = L.atr(df, 14)
    ef, es = L.ema(c, fast), L.ema(c, slow)
    r = L.rsi(c, rsi_n)

    def manage(_df, i, pos):
        if pos["side"] == "long" and r[i] > rsi_exit:
            return "close"
        if pos["side"] == "short" and r[i] < 100 - rsi_exit:
            return "close"
        return None

    out = [None] * n
    with np.errstate(invalid="ignore"):
        lg = (ef > es) & (c > es) & (r < rsi_lo)
        sh = (ef < es) & (c < es) & (r > 100 - rsi_lo)
    for i in np.where(lg | sh)[0]:
        if not np.isfinite(a[i]):
            continue
        side = "long" if lg[i] else "short"
        if side not in sides:
            continue
        sl = c[i] - atr_stop * a[i] if side == "long" else c[i] + atr_stop * a[i]
        tp = None
        if tp_atr:
            tp = c[i] + tp_atr * a[i] if side == "long" else c[i] - tp_atr * a[i]
        out[i] = H.Entry(side, sl=float(sl), tp=tp, max_hold=max_hold, manage=manage)
    return out


# --------------------------------------------------------------------------- #
# Time-of-day hold (session drift)                                              #
# --------------------------------------------------------------------------- #
def build_hour_hold(df, hour=1, side="long", hold=6, atr_n=24, atr_stop=2.0, weekdays=None,
                    ma_n=None):
    """Enter at the close of the bar whose hour == hour, hold `hold` bars, ATR stop.
    Optional trend gate: close on the trade side of EMA(ma_n)."""
    o, h, l, c = L.arr(df)
    n = len(df)
    t = pd.DatetimeIndex(df["time"])
    a = L.atr(df, atr_n)
    ma = L.ema(c, ma_n) if ma_n else None
    m = t.hour.to_numpy() == hour
    if weekdays is not None:
        m &= np.isin(t.weekday.to_numpy(), list(weekdays))
    out = [None] * n
    for i in np.where(m)[0]:
        if not np.isfinite(a[i]):
            continue
        if ma is not None:
            if side == "long" and not c[i] > ma[i]:
                continue
            if side == "short" and not c[i] < ma[i]:
                continue
        sl = c[i] - atr_stop * a[i] if side == "long" else c[i] + atr_stop * a[i]
        out[i] = H.Entry(side, sl=float(sl), max_hold=hold)
    return out


# --------------------------------------------------------------------------- #
# Generic regime wrapper + volatility-squeeze breakout                          #
# --------------------------------------------------------------------------- #
def build_regime(df, base="build_session_break", base_params=None, atrp_min=None, atrp_max=None,
                 atrp_window=2000, adx_min=None, adx_max=None):
    """Run another builder, then drop entries outside a volatility / trend regime
    (ATR14 trailing percentile over atrp_window bars; ADX14)."""
    import research.search.gold_fix.strategies as S
    sig = getattr(S, base)(df, **(base_params or {}))
    ap = L.rolling_pct_rank(L.atr(df, 14), atrp_window)
    ad = L.adx(df, 14)[0]
    out = []
    for i, e in enumerate(sig):
        if e is not None:
            if atrp_min is not None and not ap[i] >= atrp_min:
                e = None
            elif atrp_max is not None and not ap[i] <= atrp_max:
                e = None
            elif adx_min is not None and not ad[i] >= adx_min:
                e = None
            elif adx_max is not None and not ad[i] <= adx_max:
                e = None
        out.append(e)
    return out


def build_squeeze(df, bb_n=20, bb_k=2.0, sq_window=500, sq_pct=0.2, lookback=5, atr_stop=2.0,
                  n_exit=10, trail_atr=None, sides=("long", "short")):
    """Bollinger squeeze: band width was in its bottom sq_pct percentile within the
    last `lookback` bars, then a close outside the band enters in that direction.
    Stop atr_stop x ATR14; exit on close beyond the n_exit-bar opposite extreme
    and/or chandelier trail."""
    o, h, l, c = L.arr(df)
    n = len(df)
    a = L.atr(df, 14)
    m = pd.Series(c).rolling(bb_n).mean().to_numpy()
    sd = pd.Series(c).rolling(bb_n).std().to_numpy()
    up, dn = m + bb_k * sd, m - bb_k * sd
    wp = L.rolling_pct_rank(sd / m, sq_window)
    was_sq = pd.Series(wp <= sq_pct).rolling(lookback, min_periods=1).max().to_numpy() > 0
    xh = pd.Series(h).rolling(n_exit).max().to_numpy()
    xl = pd.Series(l).rolling(n_exit).min().to_numpy()

    def manage(_df, i, pos):
        if pos["side"] == "long":
            if c[i] < xl[i - 1]:
                return "close"
            if trail_atr:
                st = h[pos["bar"]:i + 1].max() - trail_atr * a[i]
                return st if st > pos["sl"] else None
        else:
            if c[i] > xh[i - 1]:
                return "close"
            if trail_atr:
                st = l[pos["bar"]:i + 1].min() + trail_atr * a[i]
                return st if st < pos["sl"] else None
        return None

    prev = np.r_[np.nan, c[:-1]]
    pup = np.r_[np.nan, up[:-1]]
    pdn = np.r_[np.nan, dn[:-1]]
    out = [None] * n
    with np.errstate(invalid="ignore"):
        lg = was_sq & (c > up) & (prev <= pup)
        sh = was_sq & (c < dn) & (prev >= pdn)
    for i in np.where(lg | sh)[0]:
        if not np.isfinite(a[i]):
            continue
        side = "long" if lg[i] else "short"
        if side not in sides:
            continue
        sl = c[i] - atr_stop * a[i] if side == "long" else c[i] + atr_stop * a[i]
        out[i] = H.Entry(side, sl=float(sl), manage=manage)
    return out


# --------------------------------------------------------------------------- #
# Multi-timeframe: run a builder on a resampled higher timeframe, place its     #
# entries on the base bar that CLOSES that HTF bar; manage only at HTF closes.  #
# --------------------------------------------------------------------------- #
def _resample(df, rule):
    g = df.set_index("time").resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last",
         "tick_volume": "sum", "spread": "max"}).dropna(subset=["close"]).reset_index()
    return g


def build_mtf(df, rule="4h", base="build_donchian", base_params=None):
    import research.search.gold_fix.strategies as S
    t = pd.DatetimeIndex(df["time"])
    step = pd.Series(t[1:] - t[:-1]).median()
    g = _resample(df, rule)
    end = (pd.DatetimeIndex(g["time"]) + pd.Timedelta(rule)).to_numpy()
    base_close = (t + step).to_numpy()
    # base bar i closes HTF bar k iff its close time == end[k]
    k_of = np.searchsorted(end, base_close, side="left")
    ok = (k_of < len(end)) & (end[np.minimum(k_of, len(end) - 1)] == base_close)
    last_of = np.where(ok, k_of, -1)                     # HTF index closed at bar i, else -1
    # HTF index in force at bar i (the bar that contains i) for entry-bar translation
    cont = np.searchsorted(pd.DatetimeIndex(g["time"]).to_numpy(), t.to_numpy(), side="right") - 1
    sig = getattr(S, base)(g, **(base_params or {}))
    n = len(df)
    out = [None] * n
    for i in np.where(last_of >= 0)[0]:
        e = sig[last_of[i]]
        if e is None:
            continue
        man = None
        if e.manage is not None:
            man = _wrap_manage(e.manage, g, last_of, cont)
        out[i] = H.Entry(e.side, sl=e.sl, tp=e.tp, max_hold=None, exit_hour=e.exit_hour,
                         manage=man, meta=dict(e.meta))
    return out


def _wrap_manage(fn, g, last_of, cont):
    def m(_df, i, pos):
        k = last_of[i]
        if k < 0:
            return None
        p2 = dict(pos)
        p2["bar"] = int(cont[pos["bar"]])
        if p2["bar"] >= k:
            return None
        return fn(g, k, p2)
    return m


def build_combo(df, parts=()):
    """parts = [(builder_name, params), ...] all on this df; at each bar the first
    part with an entry wins. One position overall (harness), opposite signals flip."""
    import research.search.gold_fix.strategies as S
    sigs = [getattr(S, b)(df, **p) for b, p in parts]
    out = []
    for i in range(len(df)):
        e = None
        for s in sigs:
            if s[i] is not None:
                e = s[i]
                break
        out.append(e)
    return out
