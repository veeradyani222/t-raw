"""jpy_session family: time-of-day session entries (H1), re-implemented for
research.prop.harness.

Base rule (the live CHFJPY strategy): after the H1 bar labelled broker hour
`hour` CLOSES, enter `side` at that close, stop = sl_atr x simple ATR(atr_n)
(computed from completed bars incl. bar i), exit at the close `hold` bars
later. Everything here is causal: bar i only uses rows <= i; the daily trend
uses only days fully completed before bar i's day.

Every build_* returns a list (len(df)) of H.Entry | None and works on any
frame from H.load (is or oos).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H


# ---------------------------------------------------------------- helpers
def atr_simple(df: pd.DataFrame, n: int = 14) -> np.ndarray:
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.vstack([h - l, np.abs(h - pc), np.abs(l - pc)]), axis=0)
    tr[0] = h[0] - l[0]
    return pd.Series(tr).rolling(n, min_periods=n).mean().to_numpy()


def sma(x: np.ndarray, n: int) -> np.ndarray:
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()


def daily_prior(df: pd.DataFrame, n: int, kind: str = "ma") -> np.ndarray:
    """Per H1 bar: +1/-1/0 daily trend known BEFORE the bar's day started.

    kind="ma":  last completed daily close vs SMA(n) of completed daily closes.
    kind="mom": last completed daily close vs the daily close n days earlier.
    """
    t = pd.DatetimeIndex(df["time"])
    day = t.normalize()
    dc = pd.Series(df["close"].to_numpy(float), index=day).groupby(level=0).last()
    if kind == "ma":
        ref = dc.rolling(n, min_periods=n).mean()
    else:
        ref = dc.shift(n)
    sig = np.sign(dc - ref)                     # known at that day's close
    sig = sig.shift(1)                          # usable from the NEXT day on
    out = sig.reindex(day).to_numpy()
    return np.nan_to_num(out, nan=0.0)


def _hours(df):
    t = pd.DatetimeIndex(df["time"])
    return t.hour.to_numpy(), t.dayofweek.to_numpy()


# ---------------------------------------------------------------- core
def session_mask(df, hour=0, side="long", atr_n=14, sl_atr=2.0, ma_n=None,
                 d1_ma=None, d1_kind="ma", trend_mode="filter", weekdays=None,
                 vol_lo=None, vol_hi=None, vol_long=500, gap_max=None,
                 prior_n=None, prior_dir=None):
    """Return (side_arr[str|None], stop_dist) without building Entry objects.

    trend_mode: "filter" -> only trade `side` when trend agrees (if any trend
                filter is set); "follow" -> side taken from the trend sign
                (long when up, short when down), `side` ignored.
    """
    hr, wd = _hours(df)
    c = df["close"].to_numpy(float)
    a = atr_simple(df, atr_n)
    ok = (hr == hour) & np.isfinite(a) & (a > 0)
    if weekdays is not None:
        ok &= np.isin(wd, list(weekdays))
    if vol_lo is not None or vol_hi is not None:
        ref = sma(a, vol_long)
        ratio = a / ref
        if vol_lo is not None:
            ok &= ratio >= vol_lo
        if vol_hi is not None:
            ok &= ratio <= vol_hi
    if gap_max is not None:
        # skip if the previous bar->this bar time gap is large (Monday open)
        t = df["time"].to_numpy()
        gap = np.r_[np.timedelta64(1, "h"), np.diff(t)] / np.timedelta64(1, "h")
        ok &= gap <= gap_max
    if prior_n:
        # reversal/continuation filter on the move over the last prior_n bars
        mv = c - np.r_[np.full(prior_n, np.nan), c[:-prior_n]]
        ok &= (mv < 0) if prior_dir == "down" else (mv > 0)
    trend = np.zeros(len(df))
    have_trend = False
    if ma_n:
        m = sma(c, ma_n)
        trend = np.where(np.isfinite(m), np.sign(c - m), 0.0)
        have_trend = True
    if d1_ma:
        d = daily_prior(df, d1_ma, d1_kind)
        trend = d if not have_trend else np.where(trend == d, trend, 0.0)
        have_trend = True
    sides = np.full(len(df), None, dtype=object)
    if trend_mode == "follow" and have_trend:
        sides[ok & (trend > 0)] = "long"
        sides[ok & (trend < 0)] = "short"
    else:
        want = 1.0 if side == "long" else -1.0
        m = ok & ((trend == want) if have_trend else True)
        sides[m] = side
    return sides, sl_atr * a


def _entries(df, sides, dist, hold, tp_r=None):
    c = df["close"].to_numpy(float)
    out = [None] * len(df)
    for i in np.flatnonzero(sides != None):  # noqa: E711
        s = sides[i]
        d = dist[i]
        if s == "long":
            sl, tp = c[i] - d, (c[i] + tp_r * d if tp_r else None)
        else:
            sl, tp = c[i] + d, (c[i] - tp_r * d if tp_r else None)
        out[i] = H.Entry(s, float(sl), tp=None if tp is None else float(tp),
                         max_hold=int(hold), meta={"hour": int(pd.Timestamp(df.time.iat[i]).hour)})
    return out


def build_session(df, hour=0, hold=12, side="long", atr_n=14, sl_atr=2.0,
                  tp_r=None, **filters):
    """Generic time-of-day entry (base = live CHFJPY rule with defaults)."""
    sides, dist = session_mask(df, hour=hour, side=side, atr_n=atr_n,
                               sl_atr=sl_atr, **filters)
    return _entries(df, sides, dist, hold, tp_r)


def build_multi_session(df, legs=(), atr_n=14):
    """Several non-overlapping session legs in ONE strategy (one position at
    a time is enforced by the harness). legs = [dict(hour, hold, side,
    sl_atr, ...filters)]. Later legs never overwrite an earlier leg's bar."""
    out = [None] * len(df)
    for leg in legs:
        leg = dict(leg)
        hold = leg.pop("hold")
        tp_r = leg.pop("tp_r", None)
        sides, dist = session_mask(df, atr_n=atr_n, **leg)
        e = _entries(df, sides, dist, hold, tp_r)
        for i, x in enumerate(e):
            if x is not None and out[i] is None:
                out[i] = x
    return out


def window_return(df, from_hour, entry_hour):
    """close(entry bar) - close(bar labelled from_hour on the same broker
    day), at bars whose hour == entry_hour; NaN elsewhere. Causal."""
    t = pd.DatetimeIndex(df["time"])
    c = df["close"].to_numpy(float)
    day = t.normalize().to_numpy()
    hr = t.hour.to_numpy()
    ref = pd.Series(np.where(hr == from_hour, c, np.nan))
    # forward-fill the from_hour close within each day only
    ref = ref.groupby(day).ffill().to_numpy()
    out = np.where(hr == entry_hour, c - ref, np.nan)
    return out


def momentum_mask(df, from_hour, entry_hour, mode="follow", min_atr=0.0,
                  atr_n=14, sl_atr=2.0, only=None, weekdays=None, d1_ma=None):
    """Intraday momentum / reversal: at the close of entry_hour, trade the
    sign (follow) or the opposite sign (fade) of the move since from_hour's
    close, if |move| >= min_atr x ATR. only='long'/'short' restricts side."""
    a = atr_simple(df, atr_n)
    r = window_return(df, from_hour, entry_hour)
    ok = np.isfinite(r) & np.isfinite(a) & (a > 0) & (np.abs(r) >= min_atr * a) & (r != 0)
    if weekdays is not None:
        ok &= np.isin(pd.DatetimeIndex(df["time"]).dayofweek, list(weekdays))
    sgn = np.sign(r) * (1 if mode == "follow" else -1)
    if d1_ma:
        d = daily_prior(df, d1_ma)
        ok &= d == sgn
    sides = np.full(len(df), None, dtype=object)
    sides[ok & (sgn > 0)] = "long"
    sides[ok & (sgn < 0)] = "short"
    if only:
        sides[sides != only] = None
    return sides, sl_atr * a


def build_intraday_momentum(df, from_hour=16, entry_hour=21, hold=1, mode="follow",
                            min_atr=0.0, sl_atr=2.0, atr_n=14, tp_r=None, **kw):
    sides, dist = momentum_mask(df, from_hour, entry_hour, mode, min_atr,
                                atr_n, sl_atr, **kw)
    return _entries(df, sides, dist, hold, tp_r)


# ---------------------------------------------------------------- candidates
def build_chfjpy_live(df, **kw):
    """Exact live rule: long after hour-0 bar, 2xATR14 stop, 12h hold."""
    p = dict(hour=0, hold=12, side="long", atr_n=14, sl_atr=2.0)
    p.update(kw)
    return build_session(df, **p)


def build_tokyo_long_d1trend(df, hour=0, hold=12, sl_atr=2.0, d1_ma=50, **kw):
    """Hour-0 long only when the daily close (completed days) is above its
    d1_ma-day SMA."""
    return build_session(df, hour=hour, hold=hold, side="long", sl_atr=sl_atr,
                         d1_ma=d1_ma, **kw)


def build_tokyo_follow_d1(df, hour=0, hold=12, sl_atr=2.0, d1_ma=50, **kw):
    """Hour-0 entry in the direction of the daily trend (long above the
    d1 SMA, short below)."""
    return build_session(df, hour=hour, hold=hold, sl_atr=sl_atr, d1_ma=d1_ma,
                         trend_mode="follow", **kw)


# ---------------------------------------------------------------- calendar
def bdays_to_month_end(df) -> np.ndarray:
    """Business days (Mon-Fri) remaining in the bar's month AFTER its date
    (0 on the last weekday of the month). Pure calendar -> known in advance."""
    t = pd.DatetimeIndex(df["time"]).normalize()
    u = t.unique()
    me = (u + pd.offsets.MonthEnd(0))
    rem = np.array([np.busday_count((d + pd.Timedelta(days=1)).date(), (m + pd.Timedelta(days=1)).date())
                    for d, m in zip(u, me)])
    return pd.Series(rem, index=u).reindex(t).to_numpy()


def build_turn_of_month(df, k=1, hour=20, hold=72, side="long", sl_atr=3.0,
                        atr_n=14, d1_ma=None, tp_r=None, ks=None, **kw):
    """Enter at the close of the bar labelled `hour` on the weekday that has
    k business days left in the month (k=0 = last weekday); exit after
    `hold` bars. Classic equity turn-of-month window."""
    hr, wd = _hours(df)
    a = atr_simple(df, atr_n)
    n = bdays_to_month_end(df)
    ok = (hr == hour) & np.isin(n, list(ks) if ks else [k]) & np.isfinite(a) & (a > 0)
    sides = np.full(len(df), None, dtype=object)
    if d1_ma:
        d = daily_prior(df, d1_ma)
        ok &= d == (1 if side == "long" else -1)
    sides[ok] = side
    return _entries(df, sides, sl_atr * a, hold, tp_r)


# ---------------------------------------------------------------- session breakout
def build_session_breakout(df, range_start=0, range_end=6, last_entry=14, exit_hour=21,
                           tp_r=None, sl_frac=1.0, both=True, only=None,
                           max_range_atr=None, d1_ma=None, atr_n=14):
    """Asian-range breakout: range = high/low of same-day bars with hours in
    [range_start, range_end] (known once the range_end bar has closed).
    First close outside the range between range_end+1 and last_entry enters;
    stop = sl_frac of the range back from the breakout side (1.0 = other
    side of range), optional target tp_r x stop distance, exit at the close
    of the exit_hour bar. One trade per day."""
    t = pd.DatetimeIndex(df["time"])
    hr = t.hour.to_numpy()
    day = t.normalize().to_numpy()
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    a = atr_simple(df, atr_n)
    inr = (hr >= range_start) & (hr <= range_end)
    hh = pd.Series(np.where(inr, h, np.nan)).groupby(day).cummax()
    ll = pd.Series(np.where(inr, l, np.nan)).groupby(day).cummin()
    hh = hh.groupby(day).ffill().to_numpy()
    ll = ll.groupby(day).ffill().to_numpy()
    d1 = daily_prior(df, d1_ma) if d1_ma else None
    out = [None] * len(df)
    traded = None
    for i in np.flatnonzero((hr > range_end) & (hr <= last_entry)):
        if day[i] == traded or not np.isfinite(hh[i]) or not np.isfinite(ll[i]):
            continue
        rng = hh[i] - ll[i]
        if rng <= 0 or not np.isfinite(a[i]):
            continue
        if max_range_atr is not None and rng > max_range_atr * a[i] * 4:
            continue
        side = "long" if c[i] > hh[i] else ("short" if c[i] < ll[i] else None)
        if side is None or (only and side != only):
            continue
        if d1 is not None and d1[i] != (1 if side == "long" else -1):
            continue
        if side == "long":
            sl = hh[i] - sl_frac * rng
            tp = c[i] + tp_r * (c[i] - sl) if tp_r else None
        else:
            sl = ll[i] + sl_frac * rng
            tp = c[i] - tp_r * (sl - c[i]) if tp_r else None
        out[i] = H.Entry(side, float(sl), tp=None if tp is None else float(tp),
                         exit_hour=exit_hour, meta={"rng": float(rng)})
        traded = day[i]
    return out


def build_gold_turn_of_month(df, hour=14, hold=96, sl_atr=3.0, **kw):
    """XAUUSD: buy the close of the broker-hour-14 bar on the LAST weekday
    of the month, stop 3 x ATR14(H1), exit after 96 H1 bars (~4 trading
    days into the new month)."""
    return build_turn_of_month(df, k=0, hour=hour, hold=hold, sl_atr=sl_atr, **kw)


def build_index_turn_of_month(df, hour=22, hold=24, sl_atr=3.0, **kw):
    """Equity indices: buy the hour-22 close (NY cash close) on the last
    weekday of the month, stop 3 x ATR14(H1), exit after `hold` H1 bars."""
    return build_turn_of_month(df, k=0, hour=hour, hold=hold, sl_atr=sl_atr, **kw)


def build_monday_long(df, hour=0, hold=36, sl_atr=2.0, prior_n=None, prior_dir=None, **kw):
    """JPY crosses: long after the Monday broker-hour-0 bar, 2xATR14 stop,
    ~1.5-day hold. Optional: only after a down week (prior_n=120, 'down')."""
    return build_session(df, hour=hour, hold=hold, side="long", sl_atr=sl_atr,
                         weekdays=(0,), prior_n=prior_n, prior_dir=prior_dir, **kw)


def build_jpy_week_cycle(df, mon_hold=36, fri_hold=22, d1_ma=200, sl_atr=2.0):
    """Monday-long (hour 0, hold mon_hold) + Friday-short (hour 1, hold
    fri_hold) only when the daily trend is down (close < d1_ma SMA)."""
    return build_multi_session(df, legs=[
        dict(hour=0, hold=mon_hold, side="long", weekdays=(0,), sl_atr=sl_atr),
        dict(hour=1, hold=fri_hold, side="short", weekdays=(4,), d1_ma=d1_ma, sl_atr=sl_atr)])
