"""commodity_fx (round 3): from-scratch ideas for AUD / NZD / CAD majors and
crosses, scored by research.prop.harness on 2024-10-20..now.

Every builder: build_<name>(df, **params) -> list[Entry|None] of len(df),
causal (bar i uses rows <= i only; prior-day / prior-week levels come from
COMPLETED days / weeks). Every trade has a stop and a defined exit (tp,
time, trailing manage or opposite signal).

Server clock = EET-style (NY+7). Hours used:
  Sydney/Tokyo ("Asia") range  = bars 01..09 (01:00-09:59 server)
  London                       = from bar 10
  NY afternoon / day end       = 22-23 ; the 23:00 bar straddles rollover
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

from research.prop.harness import Entry, DATA


# ----------------------------------------------------------------- helpers
def atr(df, n=14):
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).rolling(n, min_periods=n).mean().to_numpy()


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def sma(x, n):
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()


def rsi(x, n=14):
    s = pd.Series(x)
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).to_numpy()


def adx(df, n=14):
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    up = np.r_[0, np.diff(h)]
    dn = np.r_[0, -np.diff(l)]
    pdm = np.where((up > dn) & (up > 0), up, 0.0)
    ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    a = 1 / n
    trs = pd.Series(tr).ewm(alpha=a, adjust=False, min_periods=n).mean()
    pdi = 100 * pd.Series(pdm).ewm(alpha=a, adjust=False, min_periods=n).mean() / trs
    ndi = 100 * pd.Series(ndm).ewm(alpha=a, adjust=False, min_periods=n).mean() / trs
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    return dx.ewm(alpha=a, adjust=False, min_periods=n).mean().to_numpy()


def _daily(df):
    """Per-bar arrays of the PRIOR completed day's high/low/close/open and
    today's open (known at the first bar of the day)."""
    t = pd.DatetimeIndex(df.time)
    day = t.normalize()
    g = pd.DataFrame({"day": day, "h": df.high.values, "l": df.low.values,
                      "c": df.close.values, "o": df.open.values}).groupby("day")
    agg = g.agg(h=("h", "max"), l=("l", "min"), c=("c", "last"), o=("o", "first"))
    prev = agg.shift(1)
    out = {k: prev[k].reindex(day).to_numpy() for k in ("h", "l", "c", "o")}
    out["today_open"] = agg["o"].reindex(day).to_numpy()
    return out


def _weekly(df):
    t = pd.DatetimeIndex(df.time)
    wk = (t - pd.to_timedelta(t.dayofweek, unit="D")).normalize()
    g = pd.DataFrame({"wk": wk, "h": df.high.values, "l": df.low.values,
                      "c": df.close.values}).groupby("wk")
    agg = g.agg(h=("h", "max"), l=("l", "min"), c=("c", "last")).shift(1)
    return {k: agg[k].reindex(wk).to_numpy() for k in ("h", "l", "c")}


def _asia_range(df, h0=1, h1=9):
    """High/low of today's bars with hour in [h0, h1], known from bar h1 on
    (NaN before the range is complete)."""
    t = pd.DatetimeIndex(df.time)
    hr = t.hour.to_numpy()
    day = t.normalize().to_numpy()
    n = len(df)
    hi = np.full(n, np.nan); lo = np.full(n, np.nan)
    h, l = df.high.to_numpy(float), df.low.to_numpy(float)
    cur_day = None; ch = -np.inf; cl = np.inf; done = False; cnt = 0
    for i in range(n):
        if day[i] != cur_day:
            cur_day = day[i]; ch = -np.inf; cl = np.inf; done = False; cnt = 0
        if h0 <= hr[i] <= h1:
            ch = max(ch, h[i]); cl = min(cl, l[i]); cnt += 1
        if hr[i] >= h1 and cnt >= 3:
            done = True
        if done:
            hi[i] = ch; lo[i] = cl
    return hi, lo


def _hours(df):
    return pd.DatetimeIndex(df.time).hour.to_numpy()


def _dow(df):
    return pd.DatetimeIndex(df.time).dayofweek.to_numpy()


def _chandelier(side, mult, a, h, l):
    """manage(): trail the stop at mult*ATR from the best price so far."""
    def manage(df, i, pos):
        if side == "long":
            new = h[i] - mult * a[i]
            return float(new) if new > pos["sl"] else None
        new = l[i] + mult * a[i]
        return float(new) if new < pos["sl"] else None
    return manage


def _load_other(symbol, tf):
    p = DATA / f"{symbol.lower()}-{tf.lower()}.csv"
    x = pd.read_csv(p, usecols=["time", "close"], parse_dates=["time"])
    return x.drop_duplicates("time").sort_values("time")


# =========================================================== 1. Asia range break
def build_asia_break(df, last_hour=14, sl_mode="range", sl_atr=1.0, tp_r=1.5,
                     min_r=0.3, max_r=1.5, exit_hour=23, one_per_day=True):
    """Sydney/Tokyo range (01-09 server) breakout traded from the London
    open: first H1 close outside the range before `last_hour`. Stop at the
    other side of the range (or ATR), target tp_r x risk, flat at exit_hour."""
    hi, lo = _asia_range(df)
    a = atr(df, 14); c = df.close.to_numpy(float)
    hr = _hours(df); day = pd.DatetimeIndex(df.time).normalize().to_numpy()
    out = [None] * len(df); last_day = None
    for i in range(len(df)):
        if np.isnan(hi[i]) or np.isnan(a[i]) or not (10 <= hr[i] <= last_hour):
            continue
        if one_per_day and day[i] == last_day:
            continue
        rng = hi[i] - lo[i]
        if not (min_r * a[i] <= rng <= max_r * a[i]):
            continue
        if c[i] > hi[i]:
            sl = lo[i] if sl_mode == "range" else c[i] - sl_atr * a[i]
            risk = c[i] - sl
            out[i] = Entry("long", sl, tp=c[i] + tp_r * risk, exit_hour=exit_hour)
            last_day = day[i]
        elif c[i] < lo[i]:
            sl = hi[i] if sl_mode == "range" else c[i] + sl_atr * a[i]
            risk = sl - c[i]
            out[i] = Entry("short", sl, tp=c[i] - tp_r * risk, exit_hour=exit_hour)
            last_day = day[i]
    return out


# ============================================================ 2. Asia range fade
def build_asia_fade(df, last_hour=16, pen_atr=0.05, sl_atr=0.4, tp_mode="mid",
                    tp_r=1.0, exit_hour=23):
    """False break of the Asia range during London: bar trades beyond the
    range by >= pen_atr*ATR but CLOSES back inside -> fade toward the range
    midpoint (or tp_r x risk). Stop beyond the wick."""
    hi, lo = _asia_range(df)
    a = atr(df, 14)
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    hr = _hours(df)
    out = [None] * len(df)
    for i in range(len(df)):
        if np.isnan(hi[i]) or np.isnan(a[i]) or not (10 <= hr[i] <= last_hour):
            continue
        mid = (hi[i] + lo[i]) / 2
        if h[i] >= hi[i] + pen_atr * a[i] and c[i] < hi[i]:
            sl = h[i] + sl_atr * a[i]
            tp = mid if tp_mode == "mid" else c[i] - tp_r * (sl - c[i])
            if tp < c[i]:
                out[i] = Entry("short", sl, tp=tp, exit_hour=exit_hour)
        elif l[i] <= lo[i] - pen_atr * a[i] and c[i] > lo[i]:
            sl = l[i] - sl_atr * a[i]
            tp = mid if tp_mode == "mid" else c[i] + tp_r * (c[i] - sl)
            if tp > c[i]:
                out[i] = Entry("long", sl, tp=tp, exit_hour=exit_hour)
    return out


# ========================================================= 3. prior-day sweep
def build_pd_sweep(df, hours=(8, 20), pen_atr=0.1, sl_atr=0.5, tp_mode="pdc",
                   tp_r=1.5, max_hold=12):
    """Liquidity sweep of the prior day's high/low: wick beyond by
    >= pen_atr*ATR, close back inside -> reverse. Target = prior day close
    (tp_mode 'pdc') or tp_r x risk."""
    d = _daily(df); a = atr(df, 14)
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    hr = _hours(df)
    out = [None] * len(df)
    for i in range(len(df)):
        if np.isnan(d["h"][i]) or np.isnan(a[i]) or not (hours[0] <= hr[i] <= hours[1]):
            continue
        if h[i] >= d["h"][i] + pen_atr * a[i] and c[i] < d["h"][i]:
            sl = h[i] + sl_atr * a[i]
            tp = d["c"][i] if tp_mode == "pdc" else c[i] - tp_r * (sl - c[i])
            if tp < c[i] - 0.1 * a[i]:
                out[i] = Entry("short", sl, tp=tp, max_hold=max_hold)
        elif l[i] <= d["l"][i] - pen_atr * a[i] and c[i] > d["l"][i]:
            sl = l[i] - sl_atr * a[i]
            tp = d["c"][i] if tp_mode == "pdc" else c[i] + tp_r * (c[i] - sl)
            if tp > c[i] + 0.1 * a[i]:
                out[i] = Entry("long", sl, tp=tp, max_hold=max_hold)
    return out


# ===================================================== 4. prior-day break & go
def build_pd_break(df, hours=(10, 18), sl_mode="mid", sl_atr=1.0, tp_r=1.5,
                   max_hold=12, one_per_day=True):
    """Continuation: first H1 close beyond the prior day high/low inside the
    London/NY window. Stop at the prior-day midpoint (or ATR)."""
    d = _daily(df); a = atr(df, 14)
    c = df.close.to_numpy(float); hr = _hours(df)
    day = pd.DatetimeIndex(df.time).normalize().to_numpy()
    out = [None] * len(df); last = None
    for i in range(len(df)):
        if np.isnan(d["h"][i]) or np.isnan(a[i]) or not (hours[0] <= hr[i] <= hours[1]):
            continue
        if one_per_day and day[i] == last:
            continue
        mid = (d["h"][i] + d["l"][i]) / 2
        if c[i] > d["h"][i]:
            sl = mid if sl_mode == "mid" else c[i] - sl_atr * a[i]
            sl = min(sl, c[i] - 0.3 * a[i])
            out[i] = Entry("long", sl, tp=c[i] + tp_r * (c[i] - sl), max_hold=max_hold)
            last = day[i]
        elif c[i] < d["l"][i]:
            sl = mid if sl_mode == "mid" else c[i] + sl_atr * a[i]
            sl = max(sl, c[i] + 0.3 * a[i])
            out[i] = Entry("short", sl, tp=c[i] - tp_r * (sl - c[i]), max_hold=max_hold)
            last = day[i]
    return out


# ======================================================== 5. D1 mean reversion
def build_d1_meanrev(df, z_n=20, z_thr=1.5, sl_atr=1.5, tp_r=1.0, max_hold=3,
                     need_streak=0):
    """Fade an outsized daily move (z-score of the daily log return over
    z_n days beyond z_thr), optionally only after a streak of same-colour
    days. Hold max_hold bars. D1 (or H4 with daily-return proxy of 6 bars)."""
    c = df.close.to_numpy(float)
    tf = str(df.attrs.get("tf", "D1")).upper()
    step = {"D1": 1, "H4": 6, "H1": 24}.get(tf, 1)
    r = np.log(c) - np.log(np.r_[[c[0]] * step, c[:-step]])
    s = pd.Series(r)
    z = ((s - s.rolling(z_n * step).mean()) / s.rolling(z_n * step).std()).to_numpy()
    a = atr(df, 14 * step)
    col = np.sign(np.r_[0, np.diff(c)])
    out = [None] * len(df)
    for i in range(len(df)):
        if np.isnan(z[i]) or np.isnan(a[i]):
            continue
        if need_streak:
            seg = col[max(0, i - need_streak + 1): i + 1]
            if len(seg) < need_streak or not (np.all(seg > 0) or np.all(seg < 0)):
                continue
        if z[i] > z_thr:
            sl = c[i] + sl_atr * a[i]
            out[i] = Entry("short", sl, tp=c[i] - tp_r * (sl - c[i]), max_hold=max_hold * step)
        elif z[i] < -z_thr:
            sl = c[i] - sl_atr * a[i]
            out[i] = Entry("long", sl, tp=c[i] + tp_r * (c[i] - sl), max_hold=max_hold * step)
    return out


# ================================================= 6. D1/H4 trend + pullback
def build_trend_pullback(df, fast=20, slow=50, bias=200, sl_atr=1.0, tp_r=2.0,
                         trail_atr=None, max_hold=15, rsi_n=14, rsi_lo=50):
    """EMA stack (fast>slow>bias = up). Pullback: bar LOW touches the fast
    EMA (or below) and the bar closes back above it, bullish close.
    Stop = min(bar low, slow EMA) - sl_atr*ATR; target tp_r x risk or
    chandelier trail when trail_atr is set."""
    c, h, l, o = (df[k].to_numpy(float) for k in ("close", "high", "low", "open"))
    ef, es, eb = ema(c, fast), ema(c, slow), ema(c, bias)
    a = atr(df, 14); r = rsi(c, rsi_n)
    out = [None] * len(df)
    for i in range(1, len(df)):
        if np.isnan(eb[i]) or np.isnan(a[i]) or np.isnan(r[i]):
            continue
        if ef[i] > es[i] > eb[i] and l[i] <= ef[i] and c[i] > ef[i] and c[i] > o[i] and r[i] >= rsi_lo:
            sl = min(l[i], es[i]) - sl_atr * a[i]
            tp = None if trail_atr else c[i] + tp_r * (c[i] - sl)
            out[i] = Entry("long", sl, tp=tp, max_hold=max_hold,
                           manage=_chandelier("long", trail_atr, a, h, l) if trail_atr else None)
        elif ef[i] < es[i] < eb[i] and h[i] >= ef[i] and c[i] < ef[i] and c[i] < o[i] and r[i] <= 100 - rsi_lo:
            sl = max(h[i], es[i]) + sl_atr * a[i]
            tp = None if trail_atr else c[i] - tp_r * (sl - c[i])
            out[i] = Entry("short", sl, tp=tp, max_hold=max_hold,
                           manage=_chandelier("short", trail_atr, a, h, l) if trail_atr else None)
    return out


# ============================================================ 7. BB re-entry
def build_bb_reentry(df, n=20, k=2.0, rsi_n=14, rsi_thr=35, sl_atr=0.5,
                     lookback=3, max_hold=30, adx_max=None, tp_mode="mid"):
    """Range tool for AUDNZD-type pairs: previous bar closed outside the
    Bollinger band, this bar closes back inside, RSI still stretched ->
    trade back to the mid band. Stop beyond the extreme of the last
    `lookback` bars. Optional ADX ceiling (only in non-trending regimes)."""
    c, h, l = (df[k2].to_numpy(float) for k2 in ("close", "high", "low"))
    m = sma(c, n); sd = pd.Series(c).rolling(n).std().to_numpy()
    up, dn = m + k * sd, m - k * sd
    r = rsi(c, rsi_n); a = atr(df, 14)
    ax = adx(df, 14) if adx_max else None
    out = [None] * len(df)
    for i in range(lookback + 1, len(df)):
        if np.isnan(m[i]) or np.isnan(a[i]) or np.isnan(r[i]):
            continue
        if ax is not None and (np.isnan(ax[i]) or ax[i] > adx_max):
            continue
        if c[i - 1] < dn[i - 1] and c[i] > dn[i] and r[i] < rsi_thr:
            sl = l[i - lookback: i + 1].min() - sl_atr * a[i]
            tp = m[i] if tp_mode == "mid" else c[i] + 1.0 * (c[i] - sl)
            if tp > c[i] + 0.1 * a[i]:
                out[i] = Entry("long", sl, tp=tp, max_hold=max_hold)
        elif c[i - 1] > up[i - 1] and c[i] < up[i] and r[i] > 100 - rsi_thr:
            sl = h[i - lookback: i + 1].max() + sl_atr * a[i]
            tp = m[i] if tp_mode == "mid" else c[i] - 1.0 * (sl - c[i])
            if tp < c[i] - 0.1 * a[i]:
                out[i] = Entry("short", sl, tp=tp, max_hold=max_hold)
    return out


# ============================================================= 8. weekday bias
def build_weekday(df, long_days=(0,), short_days=(4,), entry_hour=1, exit_hour=22,
                  sl_atr=1.5, tp_atr=None):
    """Calendar bias seen in the study (AUD/NZD up Mondays, down Fridays):
    enter at the close of `entry_hour` on those weekdays, flat at exit_hour
    the same day, ATR stop (and optional ATR target)."""
    a = atr(df, 24); c = df.close.to_numpy(float)
    hr = _hours(df); dw = _dow(df)
    out = [None] * len(df)
    for i in range(len(df)):
        if np.isnan(a[i]) or hr[i] != entry_hour:
            continue
        if dw[i] in long_days:
            out[i] = Entry("long", c[i] - sl_atr * a[i],
                           tp=(c[i] + tp_atr * a[i]) if tp_atr else None, exit_hour=exit_hour)
        elif dw[i] in short_days:
            out[i] = Entry("short", c[i] + sl_atr * a[i],
                           tp=(c[i] - tp_atr * a[i]) if tp_atr else None, exit_hour=exit_hour)
    return out


# ========================================================== 9. Monday gap fade
def build_monday_gap(df, min_gap_atr=0.15, sl_mult=1.5, exit_hour=23, max_wait=3):
    """Weekend gap fade: Monday's first bars open away from Friday's close by
    >= min_gap_atr x ATR(H1). Fade toward the Friday close (target = fill),
    stop = sl_mult x gap beyond the entry, flat at exit_hour Monday."""
    d = _daily(df); a = atr(df, 24)
    c = df.close.to_numpy(float)
    hr = _hours(df); dw = _dow(df)
    t = pd.DatetimeIndex(df.time); day = t.normalize().to_numpy()
    out = [None] * len(df); done = None
    for i in range(len(df)):
        if dw[i] != 0 or hr[i] > max_wait or np.isnan(d["c"][i]) or np.isnan(a[i]):
            continue
        if day[i] == done:
            continue
        gap = c[i] - d["c"][i]
        if abs(gap) < min_gap_atr * a[i]:
            continue
        if gap > 0:
            out[i] = Entry("short", c[i] + sl_mult * gap, tp=d["c"][i], exit_hour=exit_hour)
        else:
            out[i] = Entry("long", c[i] - sl_mult * abs(gap), tp=d["c"][i], exit_hour=exit_hour)
        done = day[i]
    return out


# ===================================================== 10. AUD vs gold divergence
def build_gold_div(df, other="XAUUSD", n=5, z_n=60, z_thr=1.0, sl_atr=1.5,
                   tp_r=1.5, max_hold=5, mode="follow"):
    """Correlation-driven: rolling n-bar return of gold minus beta x the
    pair's return (beta from z_n bars). When gold has run far ahead
    (z >= z_thr) the pair is expected to catch up (mode 'follow' -> long);
    'fade' trades the opposite. Gold closes are merged backward in time so
    only completed gold bars are used."""
    tf = df.attrs.get("tf", "H1")
    g = _load_other(other, tf)
    m = pd.merge_asof(df[["time"]], g, on="time", direction="backward")
    gc = m.close.ffill().to_numpy(float)
    c = df.close.to_numpy(float)
    rg = pd.Series(np.log(gc)).diff(n); rp = pd.Series(np.log(c)).diff(n)
    cov = rg.rolling(z_n).cov(rp); var = rg.rolling(z_n).var()
    beta = (cov / var).to_numpy()
    resid = (rp - pd.Series(beta) * rg)
    z = ((resid - resid.rolling(z_n).mean()) / resid.rolling(z_n).std()).to_numpy()
    a = atr(df, 14)
    out = [None] * len(df)
    sign = -1 if mode == "follow" else 1   # follow: pair lagging (resid<0) -> long
    for i in range(len(df)):
        if np.isnan(z[i]) or np.isnan(a[i]):
            continue
        if sign * z[i] >= z_thr:
            sl = c[i] - sl_atr * a[i]
            out[i] = Entry("long", sl, tp=c[i] + tp_r * (c[i] - sl), max_hold=max_hold)
        elif sign * z[i] <= -z_thr:
            sl = c[i] + sl_atr * a[i]
            out[i] = Entry("short", sl, tp=c[i] - tp_r * (sl - c[i]), max_hold=max_hold)
    return out


# ===================================================== 11. London open reversal
def build_london_rev(df, from_hour=9, at_hour=11, move_atr=0.8, sl_atr=0.6,
                     tp_mode="back", tp_r=1.0, exit_hour=17):
    """Fade an over-extended London open: move from the `from_hour` close
    to the `at_hour` close >= move_atr x ATR -> trade back toward the
    from_hour close (or tp_r x risk). Flat at exit_hour."""
    a = atr(df, 14); c = df.close.to_numpy(float)
    hr = _hours(df); day = pd.DatetimeIndex(df.time).normalize().to_numpy()
    out = [None] * len(df); ref = {}
    for i in range(len(df)):
        if hr[i] == from_hour:
            ref[day[i]] = c[i]
        if hr[i] != at_hour or day[i] not in ref or np.isnan(a[i]):
            continue
        mv = c[i] - ref[day[i]]
        if abs(mv) < move_atr * a[i]:
            continue
        if mv > 0:
            sl = c[i] + sl_atr * a[i]
            tp = ref[day[i]] if tp_mode == "back" else c[i] - tp_r * (sl - c[i])
            out[i] = Entry("short", sl, tp=tp, exit_hour=exit_hour)
        else:
            sl = c[i] - sl_atr * a[i]
            tp = ref[day[i]] if tp_mode == "back" else c[i] + tp_r * (c[i] - sl)
            out[i] = Entry("long", sl, tp=tp, exit_hour=exit_hour)
    return out


# ======================================================= 12. squeeze breakout
def build_squeeze(df, n=20, pct_n=100, pct=0.2, brk_n=20, sl_atr=1.5, trail_atr=3.0,
                  max_hold=60, tp_r=None):
    """Volatility regime: Bollinger width in the bottom `pct` of its last
    pct_n values (squeeze), then a close beyond the brk_n-bar high/low ->
    breakout in that direction, ATR stop, chandelier trail (or tp_r)."""
    c, h, l = (df[k].to_numpy(float) for k in ("close", "high", "low"))
    m = sma(c, n); sd = pd.Series(c).rolling(n).std()
    width = (2 * sd / pd.Series(m))
    rank = width.rolling(pct_n).rank(pct=True).to_numpy()
    hh = pd.Series(h).rolling(brk_n).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(brk_n).min().shift(1).to_numpy()
    a = atr(df, 14)
    out = [None] * len(df)
    for i in range(1, len(df)):
        if np.isnan(rank[i - 1]) or np.isnan(a[i]) or np.isnan(hh[i]):
            continue
        if rank[i - 1] > pct:
            continue
        if c[i] > hh[i]:
            sl = c[i] - sl_atr * a[i]
            out[i] = Entry("long", sl, tp=(c[i] + tp_r * (c[i] - sl)) if tp_r else None,
                           max_hold=max_hold,
                           manage=_chandelier("long", trail_atr, a, h, l) if trail_atr else None)
        elif c[i] < ll[i]:
            sl = c[i] + sl_atr * a[i]
            out[i] = Entry("short", sl, tp=(c[i] - tp_r * (sl - c[i])) if tp_r else None,
                           max_hold=max_hold,
                           manage=_chandelier("short", trail_atr, a, h, l) if trail_atr else None)
    return out


# ======================================================== 13. round-number bounce
def build_round_bounce(df, step=0.005, tol_atr=0.15, wick_ratio=1.5, sl_atr=0.4,
                       tp_r=1.5, max_hold=12, hours=(2, 20)):
    """Bar wicks through a round level (multiple of `step`) and closes back
    on the original side with a long rejection wick (wick >= wick_ratio x
    body) -> bounce trade away from the level. Stop beyond the wick."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    a = atr(df, 14); hr = _hours(df)
    out = [None] * len(df)
    for i in range(len(df)):
        if np.isnan(a[i]) or not (hours[0] <= hr[i] <= hours[1]):
            continue
        body = abs(c[i] - o[i]) + 1e-9
        # nearest level below the high / above the low
        lvl_dn = np.floor(l[i] / step) * step          # level at or below the low
        lvl_up = np.ceil(h[i] / step) * step           # level at or above the high
        # bullish rejection: low pierced a level, close back above it
        lvl = np.round(np.floor(c[i] / step) * step, 6)
        if l[i] < lvl <= c[i] and (c[i] - l[i]) >= wick_ratio * body and (lvl - l[i]) <= tol_atr * a[i] \
                and c[i] - lvl <= 0.5 * a[i]:
            sl = l[i] - sl_atr * a[i]
            out[i] = Entry("long", sl, tp=c[i] + tp_r * (c[i] - sl), max_hold=max_hold)
            continue
        lvl = np.round(np.ceil(c[i] / step) * step, 6)
        if h[i] > lvl >= c[i] and (h[i] - c[i]) >= wick_ratio * body and (h[i] - lvl) <= tol_atr * a[i] \
                and lvl - c[i] <= 0.5 * a[i]:
            sl = h[i] + sl_atr * a[i]
            out[i] = Entry("short", sl, tp=c[i] - tp_r * (sl - c[i]), max_hold=max_hold)
    return out


# ===================================================== 14. prior-week level fade
def build_week_fade(df, adx_n=14, adx_max=25, pen_atr=0.0, sl_atr=0.7, tp_mode="mid",
                    tp_r=1.5, max_hold=24):
    """Prior WEEK high/low as range edges in a non-trending regime (ADX
    <= adx_max): bar reaches the level and closes back inside -> fade
    toward the prior-week midpoint."""
    w = _weekly(df); a = atr(df, 14); ax = adx(df, adx_n)
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    out = [None] * len(df)
    for i in range(len(df)):
        if np.isnan(w["h"][i]) or np.isnan(a[i]) or np.isnan(ax[i]) or ax[i] > adx_max:
            continue
        mid = (w["h"][i] + w["l"][i]) / 2
        if h[i] >= w["h"][i] + pen_atr * a[i] and c[i] < w["h"][i]:
            sl = h[i] + sl_atr * a[i]
            tp = mid if tp_mode == "mid" else c[i] - tp_r * (sl - c[i])
            if tp < c[i] - 0.2 * a[i]:
                out[i] = Entry("short", sl, tp=tp, max_hold=max_hold)
        elif l[i] <= w["l"][i] - pen_atr * a[i] and c[i] > w["l"][i]:
            sl = l[i] - sl_atr * a[i]
            tp = mid if tp_mode == "mid" else c[i] + tp_r * (c[i] - sl)
            if tp > c[i] + 0.2 * a[i]:
                out[i] = Entry("long", sl, tp=tp, max_hold=max_hold)
    return out


# ============================================================ 15. Donchian trend
def build_donchian(df, n_in=20, n_out=10, sl_atr=2.0, adx_min=None, max_hold=None):
    """Turtle-style: close above the n_in-bar high -> long (below low ->
    short), initial ATR stop, exit when close crosses the n_out-bar
    opposite extreme (manage) or stop. Optional ADX floor."""
    c, h, l = (df[k].to_numpy(float) for k in ("close", "high", "low"))
    hh = pd.Series(h).rolling(n_in).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n_in).min().shift(1).to_numpy()
    xh = pd.Series(h).rolling(n_out).max().shift(1).to_numpy()
    xl = pd.Series(l).rolling(n_out).min().shift(1).to_numpy()
    a = atr(df, 20)
    ax = adx(df, 14) if adx_min else None

    def mk(side):
        def manage(df_, i, pos):
            if side == "long":
                if c[i] < xl[i]:
                    return "close"
                new = xl[i]
                return float(new) if new > pos["sl"] else None
            if c[i] > xh[i]:
                return "close"
            new = xh[i]
            return float(new) if new < pos["sl"] else None
        return manage

    out = [None] * len(df)
    for i in range(len(df)):
        if np.isnan(hh[i]) or np.isnan(a[i]):
            continue
        if ax is not None and (np.isnan(ax[i]) or ax[i] < adx_min):
            continue
        if c[i] > hh[i]:
            out[i] = Entry("long", c[i] - sl_atr * a[i], max_hold=max_hold, manage=mk("long"))
        elif c[i] < ll[i]:
            out[i] = Entry("short", c[i] + sl_atr * a[i], max_hold=max_hold, manage=mk("short"))
    return out


# ============================================================== 16. Connors RSI2
def build_rsi2(df, rsi_thr=10, ma_n=200, exit_ma=5, sl_atr=2.0, max_hold=10, both=True):
    """Connors RSI(2): close above SMA200 and RSI(2) < thr -> long; exit when
    close > SMA(exit_ma) (manage) or stop/time. Mirror for shorts if both."""
    c = df.close.to_numpy(float)
    r = rsi(c, 2); m = sma(c, ma_n); x = sma(c, exit_ma); a = atr(df, 14)

    def mk(side):
        def manage(df_, i, pos):
            if side == "long" and c[i] > x[i]:
                return "close"
            if side == "short" and c[i] < x[i]:
                return "close"
            return None
        return manage

    out = [None] * len(df)
    for i in range(len(df)):
        if np.isnan(m[i]) or np.isnan(r[i]) or np.isnan(a[i]):
            continue
        if c[i] > m[i] and r[i] < rsi_thr:
            out[i] = Entry("long", c[i] - sl_atr * a[i], max_hold=max_hold, manage=mk("long"))
        elif both and c[i] < m[i] and r[i] > 100 - rsi_thr:
            out[i] = Entry("short", c[i] + sl_atr * a[i], max_hold=max_hold, manage=mk("short"))
    return out


# ========================================================== 17. inside-day / NR
def build_inside_break(df, mode="inside", nr_n=7, tp_r=1.5, max_hold=3, trend_n=None):
    """D1 compression then expansion: after an inside day (or the narrowest
    range of nr_n days) a close beyond the compression bar's range -> go
    with it, stop at the other side of that bar. Optional direction filter
    (close vs SMA(trend_n))."""
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    rng = h - l
    m = sma(c, trend_n) if trend_n else None
    out = [None] * len(df)
    ref = None  # (hi, lo) of the compression bar, armed for the next bars
    armed_at = -1
    for i in range(nr_n + 1, len(df)):
        # resolve an armed setup first (uses bar i close vs levels fixed earlier)
        if ref is not None and i - armed_at <= 2:
            hi, lo = ref
            if c[i] > hi and (m is None or np.isnan(m[i]) or c[i] > m[i]):
                out[i] = Entry("long", lo, tp=c[i] + tp_r * (c[i] - lo), max_hold=max_hold)
                ref = None
            elif c[i] < lo and (m is None or np.isnan(m[i]) or c[i] < m[i]):
                out[i] = Entry("short", hi, tp=c[i] - tp_r * (hi - c[i]), max_hold=max_hold)
                ref = None
        else:
            ref = None
        if ref is None and out[i] is None:
            if mode == "inside":
                ok = h[i] < h[i - 1] and l[i] > l[i - 1]
            else:
                ok = rng[i] <= rng[i - nr_n + 1: i + 1].min()
            if ok:
                ref = (h[i], l[i]); armed_at = i
    return out


# ================================================= 18. z-score to rolling mean
def build_zmean(df, n=100, z_in=2.0, z_out=0.0, sl_atr=2.0, max_hold=100, adx_max=None):
    """AUDNZD-style range pair: close is z_in standard deviations from its
    n-bar mean -> fade; exit when z crosses z_out (manage), ATR stop."""
    c = df.close.to_numpy(float)
    s = pd.Series(c)
    m = s.rolling(n).mean(); sd = s.rolling(n).std()
    z = ((s - m) / sd).to_numpy()
    a = atr(df, 14)
    ax = adx(df, 14) if adx_max else None

    def mk(side):
        def manage(df_, i, pos):
            if side == "long" and z[i] >= -z_out:
                return "close"
            if side == "short" and z[i] <= z_out:
                return "close"
            return None
        return manage

    out = [None] * len(df)
    for i in range(len(df)):
        if np.isnan(z[i]) or np.isnan(a[i]):
            continue
        if ax is not None and (np.isnan(ax[i]) or ax[i] > adx_max):
            continue
        if z[i] <= -z_in:
            out[i] = Entry("long", c[i] - sl_atr * a[i], max_hold=max_hold, manage=mk("long"))
        elif z[i] >= z_in:
            out[i] = Entry("short", c[i] + sl_atr * a[i], max_hold=max_hold, manage=mk("short"))
    return out


# ======================================================= 19. Asia drift to London
def build_asia_drift(df, entry_hour=1, exit_hour=9, lookback_days=10, sl_atr=1.0,
                     mode="follow"):
    """Sydney/Tokyo session drift: trade the Asia session (entry_hour ->
    exit_hour) in the direction of the average Asia-session return over the
    last lookback_days ('follow') or against it ('fade'). ATR stop."""
    c = df.close.to_numpy(float); hr = _hours(df)
    day = pd.DatetimeIndex(df.time).normalize().to_numpy()
    a = atr(df, 24)
    out = [None] * len(df)
    hist = []  # completed asia-session returns
    open_c = None; cur = None
    for i in range(len(df)):
        if day[i] != cur:
            cur = day[i]; open_c = None
        if hr[i] == entry_hour:
            open_c = c[i]
            if len(hist) >= lookback_days and not np.isnan(a[i]):
                mu = float(np.mean(hist[-lookback_days:]))
                side = ("long" if mu > 0 else "short") if mode == "follow" else ("short" if mu > 0 else "long")
                sl = c[i] - sl_atr * a[i] if side == "long" else c[i] + sl_atr * a[i]
                out[i] = Entry(side, sl, exit_hour=exit_hour)
        if hr[i] == exit_hour and open_c is not None:
            hist.append(np.log(c[i] / open_c)); open_c = None
    return out


# ================================================ 20. prior-day close magnet
def build_pdc_magnet(df, hours=(10, 16), dist_atr=0.6, sl_atr=0.8, max_hold=10):
    """When price sits far from yesterday's close (>= dist_atr x ATR(D))
    in the London morning and the bar closes back toward it, trade to the
    prior-day close (the 'magnet'); stop beyond the bar's extreme."""
    d = _daily(df); a = atr(df, 14)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    hr = _hours(df)
    out = [None] * len(df)
    for i in range(len(df)):
        if np.isnan(d["c"][i]) or np.isnan(a[i]) or not (hours[0] <= hr[i] <= hours[1]):
            continue
        pdc = d["c"][i]
        if c[i] <= pdc - dist_atr * a[i] * 4 and c[i] > o[i]:     # below, turning up
            sl = l[i] - sl_atr * a[i]
            out[i] = Entry("long", sl, tp=pdc, max_hold=max_hold)
        elif c[i] >= pdc + dist_atr * a[i] * 4 and c[i] < o[i]:   # above, turning down
            sl = h[i] + sl_atr * a[i]
            out[i] = Entry("short", sl, tp=pdc, max_hold=max_hold)
    return out
