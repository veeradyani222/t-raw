"""Round-3 JPY-cross builders (USDJPY EURJPY GBPJPY AUDJPY CADJPY CHFJPY NZDJPY).

Structure-first ideas, designed after the market study in study.py / NOTES.md:
the scoring window (2024-10-20..) shows D1 variance ratios of 0.82-0.93 on
every pair (daily-scale MEAN REVERSION), Monday gaps that half-fill the same
day, prior-day extremes touched ~50% of days but closed beyond only ~25%,
and a rollover dip (23:00-01:00) followed by a Tokyo pre-open rebound.

Every builder: build_<name>(df, **params) -> list[H.Entry | None], len(df),
causal (bar i uses rows <= i only; daily/weekly levels come from COMPLETED
days/weeks), works on any frame from H.load. Every Entry has a stop and a
defined exit (tp, max_hold, exit_hour or manage). Holiday bars (Dec 24-26,
Dec 31-Jan 2: the only flat days found in the data check) never open trades.

Server clock = broker EET (UTC+2/+3). Tokyo 00-09, London 09-16, NY 16-23.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H

ALL_JPY = ["USDJPY", "EURJPY", "GBPJPY", "AUDJPY", "CADJPY", "CHFJPY", "NZDJPY"]


# ----------------------------------------------------------------- helpers
def _clock(df):
    t = pd.DatetimeIndex(df["time"])
    hr = (t.hour + t.minute / 60.0).to_numpy(float)
    day = t.normalize().to_numpy()
    return hr, day, t.dayofweek.to_numpy(), t.day.to_numpy()


def _ohlc(df):
    return (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))


def _holiday_mask(df):
    t = pd.DatetimeIndex(df["time"])
    m, d = t.month.to_numpy(), t.day.to_numpy()
    return ((m == 12) & (d >= 24) & (d <= 26)) | ((m == 12) & (d == 31)) | ((m == 1) & (d <= 2))


def _clean(df, sigs):
    bad = _holiday_mask(df)
    return [None if bad[i] else s for i, s in enumerate(sigs)]


def _daily(df):
    """Completed-day OHLC table indexed by day, plus the bar->day array."""
    _, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    g = pd.DataFrame({"day": day, "o": o, "h": h, "l": l, "c": c})
    d = g.groupby("day").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
    return d, day


def prev_day(df):
    """Per bar: O/H/L/C of the most recent COMPLETED day before the bar's day."""
    d, day = _daily(df)
    p = d.shift(1)
    return {k: p[k].reindex(day).to_numpy() for k in ("o", "h", "l", "c")}


def daily_atr(df, n=14):
    d, day = _daily(df)
    pc = d.c.shift()
    tr = np.maximum(d.h - d.l, np.maximum((d.h - pc).abs(), (d.l - pc).abs()))
    return tr.ewm(alpha=1.0 / n, adjust=False).mean().shift(1).reindex(day).to_numpy()


def prev_week(df):
    """Per bar: H/L/C of the most recent COMPLETED ISO week."""
    t = pd.DatetimeIndex(df["time"])
    wk = (t - pd.to_timedelta(t.dayofweek, unit="D")).normalize().to_numpy()
    o, h, l, c = _ohlc(df)
    g = pd.DataFrame({"wk": wk, "o": o, "h": h, "l": l, "c": c})
    w = g.groupby("wk").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last")).shift(1)
    return {k: w[k].reindex(wk).to_numpy() for k in ("o", "h", "l", "c")}, wk


def week_open(df):
    t = pd.DatetimeIndex(df["time"])
    wk = (t - pd.to_timedelta(t.dayofweek, unit="D")).normalize().to_numpy()
    o = pd.Series(df.open.to_numpy(float))
    return o.groupby(wk).transform("first").to_numpy(), wk


def day_open(df):
    _, day, _, _ = _clock(df)
    return pd.Series(df.open.to_numpy(float)).groupby(day).transform("first").to_numpy()


def session_hl(df, rs, re):
    """Running high/low of same-day bars with clock in [rs, re), carried after re."""
    hr, day, _, _ = _clock(df)
    _, h, l, _ = _ohlc(df)
    inr = (hr >= rs) & (hr < re)
    hh = pd.Series(np.where(inr, h, np.nan)).groupby(day).cummax().groupby(day).ffill()
    ll = pd.Series(np.where(inr, l, np.nan)).groupby(day).cummin().groupby(day).ffill()
    return hh.to_numpy(), ll.to_numpy()


def bar_atr(df, n=14):
    o, h, l, c = _ohlc(df)
    pc = np.r_[np.nan, c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def sma(x, n):
    return pd.Series(x).rolling(n).mean().to_numpy()


def rsi(x, n=2):
    d = np.diff(x, prepend=x[0])
    up = pd.Series(np.where(d > 0, d, 0.0)).ewm(alpha=1.0 / n, adjust=False).mean()
    dn = pd.Series(np.where(d < 0, -d, 0.0)).ewm(alpha=1.0 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(100).to_numpy()


def _entry(side, close, sl, tp=None, exit_h=None, max_hold=None, manage=None, meta=None):
    if not np.isfinite(sl) or (tp is not None and not np.isfinite(tp)):
        return None
    if side == "long" and not (sl < close and (tp is None or tp > close)):
        return None
    if side == "short" and not (sl > close and (tp is None or tp < close)):
        return None
    return H.Entry(side, sl=float(sl), tp=None if tp is None else float(tp),
                   exit_hour=exit_h, max_hold=max_hold, manage=manage, meta=meta or {})


def _trail(atr_mult, atr_arr):
    """Chandelier-style trailing stop manager (uses bars <= i only)."""
    def manage(df, i, pos):
        a = atr_arr[i]
        if not np.isfinite(a):
            return None
        if pos["side"] == "long":
            new = df.close.iat[i] - atr_mult * a
            return new if new > pos["sl"] else None
        new = df.close.iat[i] + atr_mult * a
        return new if new < pos["sl"] else None
    return manage


# ============================================================ 1. prior-day extreme sweep & reclaim
def build_pdh_sweep(df, start=9.0, end=21.0, pierce=0.0, sl_buf=0.15, min_sl=0.25,
                    tp="mid", exit_h=23, one_per_day=True, side="both"):
    """Price trades beyond yesterday's high/low (by `pierce` x daily ATR) but the
    bar CLOSES back inside -> fade toward yesterday's mid (or close). Stop beyond
    the sweep bar's extreme (+sl_buf ATR, at least min_sl ATR). Flat at exit_h."""
    hr, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    p, atr = prev_day(df), daily_atr(df)
    out = [None] * len(df)
    last_day, used = None, set()
    for i in range(len(df)):
        if day[i] != last_day:
            last_day, used = day[i], set()
        if not (start <= hr[i] < end) or not np.isfinite(atr[i]) or not np.isfinite(p["h"][i]):
            continue
        a = atr[i]
        mid = (p["h"][i] + p["l"][i]) / 2
        if side != "long" and "s" not in used and h[i] > p["h"][i] + pierce * a and c[i] < p["h"][i]:
            tgt = mid if tp == "mid" else p["c"][i] if tp == "pdc" else c[i] - float(tp) * a
            sl = max(h[i] + sl_buf * a, c[i] + min_sl * a)
            e = _entry("short", c[i], sl, tgt, exit_h, meta=dict(kind="pdh"))
            if e:
                out[i] = e
                if one_per_day:
                    used.add("s")
                continue
        if side != "short" and "l" not in used and l[i] < p["l"][i] - pierce * a and c[i] > p["l"][i]:
            tgt = mid if tp == "mid" else p["c"][i] if tp == "pdc" else c[i] + float(tp) * a
            sl = min(l[i] - sl_buf * a, c[i] - min_sl * a)
            e = _entry("long", c[i], sl, tgt, exit_h, meta=dict(kind="pdl"))
            if e:
                out[i] = e
                if one_per_day:
                    used.add("l")
    return _clean(df, out)


# ============================================================ 2. prior-day extreme breakout (momentum control)
def build_pdh_break(df, start=9.0, end=16.0, buf=0.05, sl_atr=0.4, tp_atr=0.8, exit_h=23):
    """First close beyond yesterday's high/low (+buf ATR) in the London window.
    SL sl_atr below the broken level, TP tp_atr beyond entry, flat at exit_h."""
    hr, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    p, atr = prev_day(df), daily_atr(df)
    out = [None] * len(df)
    last_day, done = None, False
    for i in range(len(df)):
        if day[i] != last_day:
            last_day, done = day[i], False
        if done or not (start <= hr[i] < end) or not np.isfinite(atr[i]) or not np.isfinite(p["h"][i]):
            continue
        a = atr[i]
        if c[i] > p["h"][i] + buf * a:
            e = _entry("long", c[i], p["h"][i] - sl_atr * a, c[i] + tp_atr * a, exit_h, meta=dict(kind="pdh_brk"))
        elif c[i] < p["l"][i] - buf * a:
            e = _entry("short", c[i], p["l"][i] + sl_atr * a, c[i] - tp_atr * a, exit_h, meta=dict(kind="pdl_brk"))
        else:
            continue
        if e:
            out[i] = e
            done = True
    return _clean(df, out)


# ============================================================ 3. Tokyo-range sweep (London "Judas swing")
def build_tokyo_sweep(df, rs=0.0, re=9.0, ws=9.0, we=14.0, sl_buf=0.1, min_sl=0.2,
                      tp="range", tp_frac=1.0, exit_h=23, min_range=0.2, max_range=1.2):
    """London takes out the Tokyo high (low) and the bar closes back inside the
    Tokyo range -> fade to the other side of the range (tp_frac of the range) or
    to the range mid. Only ranges between min_range and max_range x daily ATR."""
    hr, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    th, tl = session_hl(df, rs, re)
    atr = daily_atr(df)
    out = [None] * len(df)
    last_day, done = None, False
    for i in range(len(df)):
        if day[i] != last_day:
            last_day, done = day[i], False
        if done or not (ws <= hr[i] < we) or not np.isfinite(atr[i]) or not np.isfinite(th[i]):
            continue
        a, rng = atr[i], th[i] - tl[i]
        if not (min_range * a <= rng <= max_range * a):
            continue
        mid = (th[i] + tl[i]) / 2
        if h[i] > th[i] and c[i] < th[i]:
            tgt = mid if tp == "mid" else th[i] - tp_frac * rng
            e = _entry("short", c[i], max(h[i] + sl_buf * a, c[i] + min_sl * a), tgt, exit_h, meta=dict(kind="tok_sweep_hi"))
        elif l[i] < tl[i] and c[i] > tl[i]:
            tgt = mid if tp == "mid" else tl[i] + tp_frac * rng
            e = _entry("long", c[i], min(l[i] - sl_buf * a, c[i] - min_sl * a), tgt, exit_h, meta=dict(kind="tok_sweep_lo"))
        else:
            continue
        if e:
            out[i] = e
            done = True
    return _clean(df, out)


# ============================================================ 4. Monday weekend-gap fade
def build_gap_fade(df, min_gap=0.15, max_gap=2.0, sl_mult=1.0, min_sl=0.3, max_hold=24, tp="fill"):
    """First bar of Monday opens min_gap..max_gap x daily ATR away from Friday's
    close -> trade back toward Friday's close (tp='fill') or half the gap.
    SL = sl_mult x gap beyond the open (at least min_sl ATR)."""
    hr, day, dow, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    p, atr = prev_day(df), daily_atr(df)
    out = [None] * len(df)
    first = np.r_[True, day[1:] != day[:-1]]
    for i in np.where(first & (dow == 0))[0]:
        if not np.isfinite(atr[i]) or not np.isfinite(p["c"][i]):
            continue
        a = atr[i]
        gap = o[i] - p["c"][i]
        if not (min_gap * a <= abs(gap) <= max_gap * a):
            continue
        tgt = p["c"][i] if tp == "fill" else o[i] - gap / 2
        if gap > 0:
            sl = max(o[i] + sl_mult * abs(gap), c[i] + min_sl * a)
            e = _entry("short", c[i], sl, tgt, None, max_hold, meta=dict(kind="gap_dn"))
        else:
            sl = min(o[i] - sl_mult * abs(gap), c[i] - min_sl * a)
            e = _entry("long", c[i], sl, tgt, None, max_hold, meta=dict(kind="gap_up"))
        if e:
            out[i] = e
    return _clean(df, out)


# ============================================================ 5. big-day fade (D1 mean reversion, intraday execution)
def build_bigday_fade(df, k=1.3, entry_h=0.0, tp_frac=0.5, sl_atr=0.7, max_hold=24, exit_h=None, mode="fade"):
    """Yesterday's body (close-open) >= k x daily ATR -> at the close of the
    bar starting entry_h fade it (mode='follow' continues), TP = tp_frac of the
    body retraced, SL sl_atr ATR, out after max_hold bars or at exit_h."""
    hr, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    p, atr = prev_day(df), daily_atr(df)
    out = [None] * len(df)
    last_day, done = None, False
    for i in range(len(df)):
        if day[i] != last_day:
            last_day, done = day[i], False
        if done or hr[i] != entry_h or not np.isfinite(atr[i]) or not np.isfinite(p["c"][i]):
            continue
        a = atr[i]
        body = p["c"][i] - p["o"][i]
        if abs(body) < k * a:
            continue
        done = True
        up = body > 0
        if mode == "follow":
            up = not up
        if up:
            e = _entry("short", c[i], c[i] + sl_atr * a, c[i] - tp_frac * abs(body), exit_h, max_hold, meta=dict(kind="bigday"))
        else:
            e = _entry("long", c[i], c[i] - sl_atr * a, c[i] + tp_frac * abs(body), exit_h, max_hold, meta=dict(kind="bigday"))
        if e:
            out[i] = e
    return _clean(df, out)


# ============================================================ 6. RSI(2) pullback (Connors-style) on D1/H4 bars
def build_rsi2(df, n=2, lo=10, hi=90, trend_n=200, exit_n=5, sl_atr=2.0, max_hold=10, counter=False, side="both"):
    """Bars of the frame itself (D1 or H4). Long when close > SMA(trend_n) and
    RSI(n) < lo; exit when close > SMA(exit_n) (manage) or after max_hold bars.
    counter=True ignores the trend filter. Mirror for shorts."""
    o, h, l, c = _ohlc(df)
    r = rsi(c, n)
    tr = sma(c, trend_n)
    ex = sma(c, exit_n)
    atr = bar_atr(df, 14)
    out = [None] * len(df)

    def mk(side):
        def manage(df_, i, pos):
            if not np.isfinite(ex[i]):
                return None
            if side == "long" and c[i] > ex[i]:
                return "close"
            if side == "short" and c[i] < ex[i]:
                return "close"
            return None
        return manage
    for i in range(len(df)):
        if not np.isfinite(atr[i]) or not np.isfinite(r[i]) or (not counter and not np.isfinite(tr[i])):
            continue
        if side != "short" and r[i] < lo and (counter or c[i] > tr[i]):
            out[i] = _entry("long", c[i], c[i] - sl_atr * atr[i], None, None, max_hold, mk("long"), dict(kind="rsi2_l"))
        elif side != "long" and r[i] > hi and (counter or c[i] < tr[i]):
            out[i] = _entry("short", c[i], c[i] + sl_atr * atr[i], None, None, max_hold, mk("short"), dict(kind="rsi2_s"))
    return _clean(df, out)


# ============================================================ 7. prior-week extreme sweep & reclaim (H4/H1)
def build_pwh_sweep(df, sl_buf=0.2, min_sl=0.4, tp="mid", max_hold=30, min_dow=0):
    """Bar pierces last week's high/low and closes back inside -> fade toward
    last week's mid (or close). Only from weekday min_dow on."""
    hr, day, dow, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    w, wk = prev_week(df)
    atr = daily_atr(df)
    out = [None] * len(df)
    last_wk, used = None, set()
    for i in range(len(df)):
        if wk[i] != last_wk:
            last_wk, used = wk[i], set()
        if dow[i] < min_dow or not np.isfinite(atr[i]) or not np.isfinite(w["h"][i]):
            continue
        a = atr[i]
        mid = (w["h"][i] + w["l"][i]) / 2
        if "s" not in used and h[i] > w["h"][i] and c[i] < w["h"][i]:
            tgt = mid if tp == "mid" else w["c"][i]
            e = _entry("short", c[i], max(h[i] + sl_buf * a, c[i] + min_sl * a), tgt, None, max_hold, meta=dict(kind="pwh"))
            if e:
                out[i] = e; used.add("s")
        elif "l" not in used and l[i] < w["l"][i] and c[i] > w["l"][i]:
            tgt = mid if tp == "mid" else w["c"][i]
            e = _entry("long", c[i], min(l[i] - sl_buf * a, c[i] - min_sl * a), tgt, None, max_hold, meta=dict(kind="pwl"))
            if e:
                out[i] = e; used.add("l")
    return _clean(df, out)


# ============================================================ 8. round-number (big figure) rejection
def build_round_number(df, step=1.0, max_pierce=0.15, sl_atr=0.3, tp_atr=0.6, start=7.0, end=21.0, max_hold=12):
    """Bar wicks through a round level (xx.000 for step=1, also .500 for step=0.5)
    by <= max_pierce ATR and closes back on the far side -> trade the rejection
    (long if the level held as support). SL beyond the level, TP tp_atr ATR."""
    hr, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    atr = daily_atr(df)
    out = [None] * len(df)
    for i in range(1, len(df)):
        if not (start <= hr[i] < end) or not np.isfinite(atr[i]):
            continue
        a = atr[i]
        lvl_dn = np.floor(c[i] / step) * step        # nearest level below close
        lvl_up = lvl_dn + step
        # support test: low below level, close above, pierce small, previous close above level
        if l[i] < lvl_dn < c[i] and lvl_dn - l[i] <= max_pierce * a and c[i - 1] > lvl_dn:
            out[i] = _entry("long", c[i], lvl_dn - sl_atr * a, c[i] + tp_atr * a, None, max_hold, meta=dict(kind="rn_sup", lvl=lvl_dn))
        elif h[i] > lvl_up > c[i] and h[i] - lvl_up <= max_pierce * a and c[i - 1] < lvl_up:
            out[i] = _entry("short", c[i], lvl_up + sl_atr * a, c[i] - tp_atr * a, None, max_hold, meta=dict(kind="rn_res", lvl=lvl_up))
    return _clean(df, out)


# ============================================================ 9. narrow-range day breakout (NR7 / inside day), session-gated
def build_nr_break(df, n=7, inside=False, start=9.0, end=16.0, sl="opp", tp_mult=1.0, exit_h=23):
    """Yesterday was the narrowest range of the last n days (or an inside day):
    first close beyond its high/low in the London window follows the break.
    SL at the opposite side of the NR day (sl='opp') or its mid; TP = tp_mult x
    the NR range beyond the level."""
    hr, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    d, _ = _daily(df)
    rng = d.h - d.l
    nr = (rng == rng.rolling(n).min()) if not inside else ((d.h < d.h.shift()) & (d.l > d.l.shift()))
    nr_flag = nr.shift(1).reindex(day).fillna(False).to_numpy()
    p = prev_day(df)
    out = [None] * len(df)
    last_day, done = None, False
    for i in range(len(df)):
        if day[i] != last_day:
            last_day, done = day[i], False
        if done or not nr_flag[i] or not (start <= hr[i] < end) or not np.isfinite(p["h"][i]):
            continue
        r = p["h"][i] - p["l"][i]
        mid = (p["h"][i] + p["l"][i]) / 2
        if c[i] > p["h"][i]:
            e = _entry("long", c[i], p["l"][i] if sl == "opp" else mid, p["h"][i] + tp_mult * r, exit_h, meta=dict(kind="nr_up"))
        elif c[i] < p["l"][i]:
            e = _entry("short", c[i], p["h"][i] if sl == "opp" else mid, p["l"][i] - tp_mult * r, exit_h, meta=dict(kind="nr_dn"))
        else:
            continue
        if e:
            out[i] = e; done = True
    return _clean(df, out)


# ============================================================ 10. Donchian breakout with chandelier trail (trend following)
def build_donchian(df, n=20, trail=3.0, sl_atr=2.0, atr_n=14, side="both"):
    """Close above the prior n-bar high -> long, SL sl_atr ATR, chandelier trail
    trail x ATR. Mirror for shorts. Frame = H4 or D1."""
    o, h, l, c = _ohlc(df)
    atr = bar_atr(df, atr_n)
    hh = pd.Series(h).rolling(n).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n).min().shift(1).to_numpy()
    out = [None] * len(df)
    mg = _trail(trail, atr)
    for i in range(len(df)):
        if not np.isfinite(atr[i]) or not np.isfinite(hh[i]):
            continue
        if side != "short" and c[i] > hh[i]:
            out[i] = _entry("long", c[i], c[i] - sl_atr * atr[i], None, None, None, mg, dict(kind="don_l"))
        elif side != "long" and c[i] < ll[i]:
            out[i] = _entry("short", c[i], c[i] + sl_atr * atr[i], None, None, None, mg, dict(kind="don_s"))
    return _clean(df, out)


# ============================================================ 11. EMA pullback in trend (H4/H1)
def build_ema_pullback(df, fast=20, slow=50, tp_r=2.0, sl_buf=0.3, atr_n=14, max_hold=40, side="both"):
    """Trend: close > EMA(slow) and EMA(fast) > EMA(slow). Pullback: the bar's low
    touches EMA(fast) (previous close was above it) and the bar closes above it.
    SL = min(bar low, EMA slow) - sl_buf ATR, TP = tp_r x risk."""
    o, h, l, c = _ohlc(df)
    ef, es = ema(c, fast), ema(c, slow)
    atr = bar_atr(df, atr_n)
    out = [None] * len(df)
    for i in range(slow + 1, len(df)):
        if not np.isfinite(atr[i]):
            continue
        a = atr[i]
        if side != "short" and c[i] > es[i] and ef[i] > es[i] and l[i] <= ef[i] < c[i] and c[i - 1] > ef[i - 1]:
            sl = min(l[i], es[i]) - sl_buf * a
            out[i] = _entry("long", c[i], sl, c[i] + tp_r * (c[i] - sl), None, max_hold, meta=dict(kind="ema_pb_l"))
        elif side != "long" and c[i] < es[i] and ef[i] < es[i] and h[i] >= ef[i] > c[i] and c[i - 1] < ef[i - 1]:
            sl = max(h[i], es[i]) + sl_buf * a
            out[i] = _entry("short", c[i], sl, c[i] - tp_r * (sl - c[i]), None, max_hold, meta=dict(kind="ema_pb_s"))
    return _clean(df, out)


# ============================================================ 12. shock day (intervention-size range) follow / fade
def build_shock_day(df, k=2.2, mode="fade", hold_days=3, sl_atr=1.0, tp_atr=None, entry_h=0.0):
    """Yesterday's RANGE >= k x daily ATR (intervention / flash moves). At the
    first bar of today: fade the close direction (mode='fade') or follow it.
    SL sl_atr ATR, optional TP, out after hold_days (in bars of the frame)."""
    hr, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    p, atr = prev_day(df), daily_atr(df)
    steps = (hr[1:] - hr[:-1])[(hr[1:] - hr[:-1]) > 0] if len(hr) > 1 else np.array([])
    bars_per_day = max(1, int(round(24 / steps.min()))) if len(steps) else 1   # D1 frame -> 1
    out = [None] * len(df)
    last_day, done = None, False
    for i in range(len(df)):
        if day[i] != last_day:
            last_day, done = day[i], False
        if done or not np.isfinite(atr[i]) or not np.isfinite(p["h"][i]):
            continue
        if bars_per_day > 1 and hr[i] != entry_h:
            continue
        a = atr[i]
        if p["h"][i] - p["l"][i] < k * a:
            continue
        done = True
        up = p["c"][i] > p["o"][i]
        go_long = (not up) if mode == "fade" else up
        tp = None if tp_atr is None else (c[i] + tp_atr * a if go_long else c[i] - tp_atr * a)
        if go_long:
            e = _entry("long", c[i], c[i] - sl_atr * a, tp, None, hold_days * bars_per_day, meta=dict(kind="shock"))
        else:
            e = _entry("short", c[i], c[i] + sl_atr * a, tp, None, hold_days * bars_per_day, meta=dict(kind="shock"))
        if e:
            out[i] = e
    return _clean(df, out)


# ============================================================ 13. Tokyo fix (02:55 server) / gotobi
def build_tokyo_fix(df, entry_h=0.0, exit_h=2, side="long", gotobi_only=True, sl_atr=0.4, tp_atr=None):
    """Enter at the close of the bar starting entry_h, exit at the close of the
    first later bar with hour exit_h (exit_h=2 -> out at 03:00, just after the
    02:55 fix). gotobi_only: days 5/10/15/20/25/30 (or the prior weekday)."""
    hr, day, dow, dom = _clock(df)
    o, h, l, c = _ohlc(df)
    atr = daily_atr(df)
    t = pd.DatetimeIndex(df["time"])
    # gotobi day: the date is a multiple of 5, or the date+1 / +2 is a weekend multiple of 5
    g = np.isin(dom, [5, 10, 15, 20, 25, 30])
    nxt1 = (t + pd.Timedelta(days=1)); nxt2 = (t + pd.Timedelta(days=2))
    g |= (dow == 4) & (np.isin(nxt1.day.to_numpy(), [5, 10, 15, 20, 25, 30]) | np.isin(nxt2.day.to_numpy(), [5, 10, 15, 20, 25, 30]))
    out = [None] * len(df)
    for i in range(len(df)):
        if hr[i] != entry_h or dow[i] > 4 or not np.isfinite(atr[i]):
            continue
        if gotobi_only and not g[i]:
            continue
        a = atr[i]
        if side == "long":
            out[i] = _entry("long", c[i], c[i] - sl_atr * a, None if tp_atr is None else c[i] + tp_atr * a, exit_h, meta=dict(kind="fix"))
        else:
            out[i] = _entry("short", c[i], c[i] + sl_atr * a, None if tp_atr is None else c[i] - tp_atr * a, exit_h, meta=dict(kind="fix"))
    return _clean(df, out)


# ============================================================ 14. London-session fade at the NY open
def build_london_fade(df, ls=9.0, decide_h=15.0, k=0.6, tp_frac=0.5, sl_atr=0.5, exit_h=23, mode="fade"):
    """At the close of the bar starting decide_h, the London move (close minus the
    ls open) is >= k x daily ATR -> fade it (TP tp_frac of the move retraced) or
    follow (mode='follow'). SL sl_atr ATR. Flat at exit_h."""
    hr, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    atr = daily_atr(df)
    lo_open = pd.Series(np.where(hr == ls, o, np.nan)).groupby(day).ffill().to_numpy()
    out = [None] * len(df)
    for i in range(len(df)):
        if hr[i] != decide_h or not np.isfinite(atr[i]) or not np.isfinite(lo_open[i]):
            continue
        a = atr[i]
        mv = c[i] - lo_open[i]
        if abs(mv) < k * a:
            continue
        fade = mode == "fade"
        if (mv > 0) == fade:
            out[i] = _entry("short", c[i], c[i] + sl_atr * a, c[i] - tp_frac * abs(mv), exit_h, meta=dict(kind="ldn"))
        else:
            out[i] = _entry("long", c[i], c[i] - sl_atr * a, c[i] + tp_frac * abs(mv), exit_h, meta=dict(kind="ldn"))
    return _clean(df, out)


# ============================================================ 15. yen-basket shock (risk-off day) -> next-day trade
_BASKET_CACHE = {}


def _basket_daily(df):
    """Equal-weight daily log return of the 7 JPY crosses (completed days),
    z-scored over 60 days, aligned to the frame's bar days (yesterday's value)."""
    key = "basket"
    if key not in _BASKET_CACHE:
        rets = []
        for s in ALL_JPY:
            p = H.DATA / f"{s.lower()}-d1.csv"
            if not p.exists():
                continue
            x = pd.read_csv(p, parse_dates=["time"]).drop_duplicates("time").sort_values("time")
            r = np.log(x.close).diff()
            rets.append(pd.Series(r.values, index=pd.DatetimeIndex(x.time).normalize()))
        b = pd.concat(rets, axis=1).mean(axis=1)
        z = (b - b.rolling(60).mean()) / b.rolling(60).std()
        _BASKET_CACHE[key] = (b, z)
    b, z = _BASKET_CACHE[key]
    _, day, _, _ = _clock(df)
    idx = pd.DatetimeIndex(day)
    # value of the last completed day strictly BEFORE the bar's day
    pos = np.searchsorted(b.index.values, idx.values, side="left") - 1
    ok = pos >= 0
    bz = np.full(len(df), np.nan); bb = np.full(len(df), np.nan)
    bz[ok] = z.values[pos[ok]]; bb[ok] = b.values[pos[ok]]
    return bb, bz


def build_yen_basket(df, z=1.5, mode="fade", entry_h=0.0, sl_atr=0.8, tp_atr=None, max_hold=24):
    """Yesterday the whole JPY complex moved |z| sigma (broad yen move). At the
    first bar of today fade it (buy the carry dip after yen strength) or follow."""
    hr, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    atr = daily_atr(df)
    _, bz = _basket_daily(df)
    out = [None] * len(df)
    for i in range(len(df)):
        if hr[i] != entry_h or not np.isfinite(atr[i]) or not np.isfinite(bz[i]) or abs(bz[i]) < z:
            continue
        a = atr[i]
        yen_strong = bz[i] < 0
        go_long = yen_strong if mode == "fade" else not yen_strong
        if go_long:
            out[i] = _entry("long", c[i], c[i] - sl_atr * a, None if tp_atr is None else c[i] + tp_atr * a, None, max_hold, meta=dict(kind="basket"))
        else:
            out[i] = _entry("short", c[i], c[i] + sl_atr * a, None if tp_atr is None else c[i] - tp_atr * a, None, max_hold, meta=dict(kind="basket"))
    return _clean(df, out)


# ============================================================ 16. carry dip: buy the n-day low inside a D1 uptrend
def build_carry_dip(df, trend_n=100, dip_n=5, sl_atr=1.5, tp="hh20", max_hold=10, trail=None):
    """D1 frame. Close > SMA(trend_n) and close is the lowest of the last dip_n
    closes -> long next bar. TP = prior 20-day high (tp='hh20') or none with a
    trailing stop. SL sl_atr ATR. Shorts mirrored below SMA."""
    o, h, l, c = _ohlc(df)
    tr = sma(c, trend_n)
    atr = bar_atr(df, 14)
    lo_n = pd.Series(c).rolling(dip_n).min().to_numpy()
    hi_n = pd.Series(c).rolling(dip_n).max().to_numpy()
    hh20 = pd.Series(h).rolling(20).max().shift(1).to_numpy()
    ll20 = pd.Series(l).rolling(20).min().shift(1).to_numpy()
    mg = _trail(trail, atr) if trail else None
    out = [None] * len(df)
    for i in range(len(df)):
        if not np.isfinite(tr[i]) or not np.isfinite(atr[i]):
            continue
        a = atr[i]
        if c[i] > tr[i] and c[i] <= lo_n[i]:
            out[i] = _entry("long", c[i], c[i] - sl_atr * a, hh20[i] if tp == "hh20" else None, None, max_hold, mg, dict(kind="dip_l"))
        elif c[i] < tr[i] and c[i] >= hi_n[i]:
            out[i] = _entry("short", c[i], c[i] + sl_atr * a, ll20[i] if tp == "hh20" else None, None, max_hold, mg, dict(kind="dip_s"))
    return _clean(df, out)


# ============================================================ 17. rollover dip / Tokyo pre-open rebound (hour effects)
def build_rollover(df, entry_h=22.0, exit_h=0, side="short", sl_atr=0.4, dow_max=4, min_atr=None):
    """Enter at the close of the bar starting entry_h, flat at the close of the
    first later bar with hour exit_h. Default: short into the NY close / rollover
    dip (23:00-01:00). side='long' with entry_h=0, exit_h=1 trades the rebound."""
    hr, day, dow, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    atr = daily_atr(df)
    out = [None] * len(df)
    for i in range(len(df)):
        if hr[i] != entry_h or dow[i] > dow_max or not np.isfinite(atr[i]):
            continue
        if min_atr is not None and atr[i] / c[i] * 1e4 < min_atr:
            continue
        a = atr[i]
        if side == "short":
            out[i] = _entry("short", c[i], c[i] + sl_atr * a, None, exit_h, meta=dict(kind="roll"))
        else:
            out[i] = _entry("long", c[i], c[i] - sl_atr * a, None, exit_h, meta=dict(kind="roll"))
    return _clean(df, out)


# ============================================================ 18. Bollinger stretch fade (H4/H1 mean reversion)
def build_band_fade(df, n=20, k=2.5, sl_atr=1.2, tp="mid", max_hold=24, trend_n=None):
    """Close outside the k-sigma Bollinger band -> fade to the middle band
    (manage closes when the mid is crossed) with a hard SL. trend_n: only fade
    toward the SMA(trend_n) side (e.g. only buy dips above the 200)."""
    o, h, l, c = _ohlc(df)
    m = sma(c, n); sd = pd.Series(c).rolling(n).std().to_numpy()
    atr = bar_atr(df, 14)
    tr = sma(c, trend_n) if trend_n else None
    out = [None] * len(df)

    def mk(side):
        def manage(df_, i, pos):
            if side == "long" and c[i] >= m[i]:
                return "close"
            if side == "short" and c[i] <= m[i]:
                return "close"
            return None
        return manage
    for i in range(len(df)):
        if not np.isfinite(sd[i]) or not np.isfinite(atr[i]) or (tr is not None and not np.isfinite(tr[i])):
            continue
        a = atr[i]
        if c[i] < m[i] - k * sd[i] and (tr is None or c[i] > tr[i]):
            out[i] = _entry("long", c[i], c[i] - sl_atr * a, m[i] if tp == "mid" else None, None, max_hold, mk("long") if tp != "mid" else None, dict(kind="band_l"))
        elif c[i] > m[i] + k * sd[i] and (tr is None or c[i] < tr[i]):
            out[i] = _entry("short", c[i], c[i] + sl_atr * a, m[i] if tp == "mid" else None, None, max_hold, mk("short") if tp != "mid" else None, dict(kind="band_s"))
    return _clean(df, out)


# ============================================================ 19. weekly-open stretch fade (late week)
def build_week_open_fade(df, k=1.5, from_dow=2, sl_atr=0.7, tp_frac=0.5, exit_dow=4, exit_h=21, start=9.0, end=21.0):
    """From weekday from_dow (0=Mon), when price is >= k x daily ATR away from the
    WEEK OPEN, fade back toward it (TP tp_frac of the stretch). SL sl_atr ATR.
    Closed by Friday exit_h via manage. One trade per week per side."""
    hr, day, dow, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    wo, wk = week_open(df)
    atr = daily_atr(df)
    out = [None] * len(df)

    def manage(df_, i, pos):
        if dow[i] >= exit_dow and hr[i] >= exit_h:
            return "close"
        return None
    last_wk, used = None, set()
    for i in range(len(df)):
        if wk[i] != last_wk:
            last_wk, used = wk[i], set()
        if dow[i] < from_dow or dow[i] > 4 or not (start <= hr[i] < end) or not np.isfinite(atr[i]):
            continue
        if dow[i] >= exit_dow and hr[i] >= exit_h:
            continue
        a = atr[i]
        d = c[i] - wo[i]
        if abs(d) < k * a:
            continue
        if d > 0 and "s" not in used:
            e = _entry("short", c[i], c[i] + sl_atr * a, c[i] - tp_frac * abs(d), None, None, manage, dict(kind="wo_s"))
            if e:
                out[i] = e; used.add("s")
        elif d < 0 and "l" not in used:
            e = _entry("long", c[i], c[i] - sl_atr * a, c[i] + tp_frac * abs(d), None, None, manage, dict(kind="wo_l"))
            if e:
                out[i] = e; used.add("l")
    return _clean(df, out)


# ============================================================ 20. day-open / Tokyo-close positioning fade (NY mean reversion to day open)
def build_day_open_fade(df, decide_s=16.0, decide_e=20.0, k=0.8, sl_atr=0.5, tp_frac=0.6, exit_h=23):
    """During NY (decide_s..decide_e) the close is >= k x daily ATR from the DAY
    OPEN (00:00) -> fade back toward the day open (tp_frac of the stretch).
    One per day. Day-scale mean reversion executed intraday."""
    hr, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    do = day_open(df)
    atr = daily_atr(df)
    out = [None] * len(df)
    last_day, done = None, False
    for i in range(len(df)):
        if day[i] != last_day:
            last_day, done = day[i], False
        if done or not (decide_s <= hr[i] < decide_e) or not np.isfinite(atr[i]):
            continue
        a = atr[i]
        d = c[i] - do[i]
        if abs(d) < k * a:
            continue
        done = True
        if d > 0:
            out[i] = _entry("short", c[i], c[i] + sl_atr * a, c[i] - tp_frac * abs(d), exit_h, meta=dict(kind="do_s"))
        else:
            out[i] = _entry("long", c[i], c[i] - sl_atr * a, c[i] + tp_frac * abs(d), exit_h, meta=dict(kind="do_l"))
    return _clean(df, out)


# ============================================================ 21. consecutive-day fade (D1 mean reversion, pure structure)
def build_streak_fade(df, n=3, sl_atr=1.2, tp_atr=None, max_hold=3, min_move=0.0, mode="fade"):
    """Bars of the frame (D1/H4/H1): after n consecutive closes in one direction
    (and the streak's net move >= min_move x ATR14) fade it at the close (mode
    'follow' continues). SL sl_atr ATR, TP tp_atr ATR or none, out after max_hold bars."""
    o, h, l, c = _ohlc(df)
    atr = bar_atr(df, 14)
    d = np.sign(np.diff(c, prepend=c[0]))
    out = [None] * len(df)
    for i in range(n, len(df)):
        if not np.isfinite(atr[i]):
            continue
        seg = d[i - n + 1:i + 1]
        if not (np.all(seg > 0) or np.all(seg < 0)):
            continue
        if abs(c[i] - c[i - n]) < min_move * atr[i]:
            continue
        up = seg[0] > 0
        if mode == "follow":
            up = not up
        a = atr[i]
        if up:
            out[i] = _entry("short", c[i], c[i] + sl_atr * a, None if tp_atr is None else c[i] - tp_atr * a,
                            None, max_hold, meta=dict(kind="streak_s"))
        else:
            out[i] = _entry("long", c[i], c[i] - sl_atr * a, None if tp_atr is None else c[i] + tp_atr * a,
                            None, max_hold, meta=dict(kind="streak_l"))
    return _clean(df, out)


# ============================================================ 22. close-vs-SMA stretch fade on the frame's own bars
def build_zfade(df, n=10, z=2.0, sl_atr=1.5, max_hold=5, exit="sma"):
    """Close more than z standard deviations (of close-SMA(n), rolling 5n) from
    SMA(n) -> fade back; exit when close crosses the SMA (manage) or after max_hold.
    exit='tp' uses the SMA value at entry as a fixed target instead."""
    o, h, l, c = _ohlc(df)
    m = sma(c, n)
    dev = c - m
    sd = pd.Series(dev).rolling(n * 5).std().to_numpy()
    atr = bar_atr(df, 14)
    out = [None] * len(df)

    def manage(df_, i, pos):
        if not np.isfinite(m[i]):
            return None
        if pos["side"] == "long" and c[i] > m[i]:
            return "close"
        if pos["side"] == "short" and c[i] < m[i]:
            return "close"
        return None
    mg = manage if exit == "sma" else None
    for i in range(len(df)):
        if not (np.isfinite(sd[i]) and np.isfinite(atr[i]) and sd[i] > 0):
            continue
        zz = dev[i] / sd[i]
        if zz > z:
            out[i] = _entry("short", c[i], c[i] + sl_atr * atr[i], None if mg else m[i], None, max_hold, mg, dict(kind="z_s"))
        elif zz < -z:
            out[i] = _entry("long", c[i], c[i] - sl_atr * atr[i], None if mg else m[i], None, max_hold, mg, dict(kind="z_l"))
    return _clean(df, out)


# ============================================================ 23. London-open fakeout (first London bar fade)
def build_london_fakeout(df, open_h=9.0, k=0.35, sl_buf=0.1, tp="open", exit_h=16, max_hold=None):
    """The first London bar (clock open_h) has range >= k x daily ATR and closes
    in its top/bottom third -> fade it at that bar's close: SL beyond the bar's
    extreme (+sl_buf ATR), TP the bar's open (tp='open') or the Tokyo mid (tp='tokyo')."""
    hr, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    atr = daily_atr(df)
    th, tl = session_hl(df, 0.0, open_h)
    out = [None] * len(df)
    for i in np.where(hr == open_h)[0]:
        a = atr[i]
        rng = h[i] - l[i]
        if not np.isfinite(a) or rng < k * a or rng <= 0:
            continue
        pos_in = (c[i] - l[i]) / rng
        tgt = o[i] if tp == "open" else (th[i] + tl[i]) / 2
        if pos_in >= 0.67:
            out[i] = _entry("short", c[i], h[i] + sl_buf * a, tgt, exit_h, max_hold, meta=dict(kind="ldn_fake_s"))
        elif pos_in <= 0.33:
            out[i] = _entry("long", c[i], l[i] - sl_buf * a, tgt, exit_h, max_hold, meta=dict(kind="ldn_fake_l"))
    return _clean(df, out)


# ============================================================ 24. Tokyo-range break in London, D1-trend filtered
def build_tokyo_break_trend(df, rs=0.0, re=9.0, ws=9.0, we=13.0, trend_n=20, sl="opp", tp_mult=1.0,
                            exit_h=23, min_rng=0.2, max_rng=0.8, trail=None):
    """Tokyo range (rs..re). In the London window (ws..we) a bar CLOSES above/below
    the range in the direction of the daily trend (prior day close vs SMA(trend_n)
    of completed daily closes) -> go with it. SL = other side of the range (or its
    mid), TP = tp_mult x range (or ATR trail), flat at exit_h. Range must be
    min_rng..max_rng x daily ATR."""
    hr, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    atr = daily_atr(df)
    th, tl = session_hl(df, rs, re)
    d, _ = _daily(df)
    dtrend = (d.c.shift(1) - d.c.rolling(trend_n).mean().shift(1)).reindex(day).to_numpy()
    batr = bar_atr(df, 14)
    out = [None] * len(df)
    last_day, done = None, False
    for i in range(len(df)):
        if day[i] != last_day:
            last_day, done = day[i], False
        if done or not (ws <= hr[i] < we) or not np.isfinite(atr[i]) or not np.isfinite(dtrend[i]):
            continue
        if not (np.isfinite(th[i]) and np.isfinite(tl[i])):
            continue
        rng = th[i] - tl[i]
        if not (min_rng * atr[i] <= rng <= max_rng * atr[i]):
            continue
        mg = _trail(trail, batr) if trail else None
        if c[i] > th[i] and dtrend[i] > 0:
            s = tl[i] if sl == "opp" else (th[i] + tl[i]) / 2
            out[i] = _entry("long", c[i], s, None if trail else c[i] + tp_mult * rng, exit_h, None, mg, dict(kind="tb_l"))
            done = True
        elif c[i] < tl[i] and dtrend[i] < 0:
            s = th[i] if sl == "opp" else (th[i] + tl[i]) / 2
            out[i] = _entry("short", c[i], s, None if trail else c[i] - tp_mult * rng, exit_h, None, mg, dict(kind="tb_s"))
            done = True
    return _clean(df, out)


# ============================================================ 25. NY-session continuation of the day's move (or fade)
def build_ny_follow(df, decide_h=16.0, k=0.5, sl_atr=0.5, tp_atr=0.5, exit_h=23, mode="follow"):
    """At decide_h (NY open) the move from the day open is >= k x daily ATR ->
    follow it (mode='fade' reverses) with an ATR-sized bracket, flat at exit_h."""
    hr, day, _, _ = _clock(df)
    o, h, l, c = _ohlc(df)
    atr = daily_atr(df)
    do = day_open(df)
    out = [None] * len(df)
    for i in np.where(hr == decide_h)[0]:
        a = atr[i]
        if not np.isfinite(a):
            continue
        mv = c[i] - do[i]
        if abs(mv) < k * a:
            continue
        up = mv > 0
        if mode == "fade":
            up = not up
        if up:
            out[i] = _entry("long", c[i], c[i] - sl_atr * a, c[i] + tp_atr * a, exit_h, None, meta=dict(kind="ny_l"))
        else:
            out[i] = _entry("short", c[i], c[i] + sl_atr * a, c[i] - tp_atr * a, exit_h, None, meta=dict(kind="ny_s"))
    return _clean(df, out)
