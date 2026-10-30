"""Round-3 crypto group (BTCUSD ETHUSD XRPUSD LTCUSD [+SOL ADA BNB DOT if data arrives]).

Every build_<name>(df, **params) takes any df from research.prop.harness.load() and
returns a list (len(df)) of H.Entry | None. Causal: bar i uses rows <= i only; daily /
weekly levels come from COMPLETED previous periods (server EET days, weeks start Monday).
Every entry has a stop >= `MIN_STOP_SPREADS` x the symbol's spread floor and a defined
exit (tp, trailing stop via manage(), max_hold, exit_hour or opposite-signal flip).

Ideas (market-structure first, indicators second):
  tsmom          time-series momentum (sign of N-bar return), re-entering, ATR / chandelier stop
  donchian       N-bar high/low breakout, exit on M-bar opposite extreme (turtle)
  compress_bo    range compression (5-bar range / 20-bar range < r) then break of the box
  weekend_bo     Monday break of the Sat+Sun range (nothing else in the book trades weekends)
  session_bo     Asian-range (02-09 EET) breakout in London / US hours, flat by 23:00
  us_open_mom    direction of the 16-18 EET (US equity open) move -> hold into the US afternoon
  weekday        calendar: long Mon/Wed, short Thu (study: Thu negative on BTC/ETH/XRP)
  overnight      calendar slice: enter weekday/hour, hold N hours (Sunday-night fiat on-ramp etc.)
  pd_break       prior-day high/low break (first per day) or swing-failure (sweep + close back)
  pw_sfp         prior-WEEK high/low sweep and reclaim (or break)
  pdc_revert     fade a stretch of > z day-ATRs away from prior-day close, target = PDC
  rsi2_mr        Connors RSI(2) mean reversion with optional trend filter
  ema_pullback   trend (EMA slow > EMA trend) + pullback to EMA fast + resume
  squeeze        Bollinger inside Keltner for k bars, then close outside the band
  round_bounce   touch of a round number and close back -> fade
  weekly_open    after Monday noon trade the side of the weekly open, flat at week end
  rel_strength   alt vs BTC relative strength + BTC momentum agree -> trade the alt
  vol_spike      bar range > k ATR: fade or follow
  day_orb        server-day opening range (00-0N EET) breakout, flat by 23:00
  inside_day     inside day then break of the mother day
  supertrend     ATR supertrend flip, stop rides the line
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H

MIN_STOP_SPREADS = 4.0
ROUND_STEP = {"BTCUSD": 1000.0, "ETHUSD": 100.0, "LTCUSD": 5.0, "XRPUSD": 0.10,
              "SOLUSD": 10.0, "ADAUSD": 0.05, "BNBUSD": 50.0, "DOTUSD": 0.5}


# ----------------------------------------------------------------- helpers
def _a(df, k):
    return df[k].to_numpy(float)


def atr(df, n=14):
    h, l, c = (_a(df, k) for k in ("high", "low", "close"))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def _min_stop(df):
    sym = df.attrs.get("symbol", "")
    return MIN_STOP_SPREADS * H.SPREAD_FLOOR.get(sym, 0.0)


def _entry(df, i, side, sl, tp=None, max_hold=None, exit_hour=None, manage=None, meta=None):
    """Entry with the stop pushed to at least MIN_STOP_SPREADS x spread floor."""
    c = float(df["close"].iat[i])
    ms = _min_stop(df)
    if side == "long":
        sl = min(sl, c - ms)
        if sl >= c or (tp is not None and tp <= c):
            return None
    else:
        sl = max(sl, c + ms)
        if sl <= c or (tp is not None and tp >= c):
            return None
    return H.Entry(side, float(sl), None if tp is None else float(tp), max_hold, exit_hour,
                   manage, meta or {})


def _prev_period(df, freq):
    """Per-bar high/low/close/open of the PREVIOUS completed day ('D') or week ('W')."""
    t = pd.DatetimeIndex(df["time"])
    key = t.normalize() if freq == "D" else (t - pd.to_timedelta(t.dayofweek, unit="D")).normalize()
    g = pd.DataFrame({"k": key.to_numpy(), "h": _a(df, "high"), "l": _a(df, "low"),
                      "c": _a(df, "close"), "o": _a(df, "open")})
    d = g.groupby("k").agg(h=("h", "max"), l=("l", "min"), c=("c", "last"), o=("o", "first"))
    prev = d.shift(1)
    out = {k: prev[k].reindex(key).to_numpy() for k in ("h", "l", "c", "o")}
    out["key"] = key.to_numpy()
    out["cur_open"] = d["o"].reindex(key).to_numpy()      # this period's open: known at its 1st bar
    return out


def _day_atr(df, n=14):
    """Previous-completed-days ATR mapped to every bar (for intraday z-scores)."""
    t = pd.DatetimeIndex(df["time"]).normalize()
    g = pd.DataFrame({"k": t.to_numpy(), "h": _a(df, "high"), "l": _a(df, "low"), "c": _a(df, "close")})
    d = g.groupby("k").agg(h=("h", "max"), l=("l", "min"), c=("c", "last"))
    pc = d.c.shift(1)
    tr = np.maximum(d.h - d.l, np.maximum((d.h - pc).abs(), (d.l - pc).abs()))
    datr = tr.ewm(alpha=1.0 / n, adjust=False).mean().shift(1)
    return datr.reindex(t).to_numpy()


def _chandelier(mult, atr_arr):
    """manage(): trail the stop `mult` ATR behind the latest close (never loosens)."""
    def manage(df, i, pos):
        c = float(df["close"].iat[i])
        a = atr_arr[i]
        if pos["side"] == "long":
            new = c - mult * a
            return new if new > pos["sl"] else None
        new = c + mult * a
        return new if new < pos["sl"] else None
    return manage


def _bars_per_day(df):
    t = df["time"]
    if len(t) < 3:
        return 24
    step = (t.iloc[-1] - t.iloc[-2]).total_seconds() / 3600
    return int(round(24 / max(step, 1)))


# ------------------------------------------------------------------ 1 tsmom
def build_tsmom(df, lb=20, atr_n=14, atr_mult=2.0, trail=True, reenter=True, long_only=False,
                max_hold=None):
    c = _a(df, "close")
    a = atr(df, atr_n)
    n = len(df)
    mom = np.full(n, np.nan)
    mom[lb:] = c[lb:] - c[:-lb]
    sgn = np.sign(mom)
    out = [None] * n
    mg = _chandelier(atr_mult, a) if trail else None
    for i in range(lb + atr_n, n):
        if sgn[i] == 0 or np.isnan(sgn[i]):
            continue
        flip = sgn[i] != sgn[i - 1]
        if not (reenter or flip):
            continue
        if sgn[i] > 0:
            out[i] = _entry(df, i, "long", c[i] - atr_mult * a[i], max_hold=max_hold, manage=mg, meta=dict(lb=lb))
        elif not long_only:
            out[i] = _entry(df, i, "short", c[i] + atr_mult * a[i], max_hold=max_hold, manage=mg, meta=dict(lb=lb))
    return out


# --------------------------------------------------------------- 2 donchian
def build_donchian(df, n=20, exit_n=10, atr_n=14, atr_mult=2.0, long_only=False):
    h, l, c = (_a(df, k) for k in ("high", "low", "close"))
    a = atr(df, atr_n)
    hh = pd.Series(h).rolling(n).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n).min().shift(1).to_numpy()
    ex_lo = pd.Series(l).rolling(exit_n).min().to_numpy()   # includes bar i
    ex_hi = pd.Series(h).rolling(exit_n).max().to_numpy()

    def manage(df_, i, pos):
        if pos["side"] == "long":
            new = ex_lo[i]
            return new if new > pos["sl"] else None
        new = ex_hi[i]
        return new if new < pos["sl"] else None

    out = [None] * len(df)
    for i in range(n + 1, len(df)):
        if np.isnan(hh[i]):
            continue
        if c[i] > hh[i]:
            sl = max(c[i] - atr_mult * a[i], ex_lo[i]) if atr_mult else ex_lo[i]
            out[i] = _entry(df, i, "long", sl, manage=manage, meta=dict(n=n))
        elif c[i] < ll[i] and not long_only:
            sl = min(c[i] + atr_mult * a[i], ex_hi[i]) if atr_mult else ex_hi[i]
            out[i] = _entry(df, i, "short", sl, manage=manage, meta=dict(n=n))
    return out


# ------------------------------------------------------------ 3 compress_bo
def build_compress_bo(df, n_rng=5, n_base=20, ratio=0.7, rr=2.0, atr_mult=1.5, atr_n=14, trail=False):
    h, l, c = (_a(df, k) for k in ("high", "low", "close"))
    a = atr(df, atr_n)
    rng = h - l
    comp = pd.Series(rng).rolling(n_rng).mean() / pd.Series(rng).rolling(n_base).mean()
    comp = comp.shift(1).to_numpy()                      # compression measured on bars < i
    bh = pd.Series(h).rolling(n_rng).max().shift(1).to_numpy()
    bl = pd.Series(l).rolling(n_rng).min().shift(1).to_numpy()
    mg = _chandelier(atr_mult, a) if trail else None
    out = [None] * len(df)
    for i in range(n_base + 1, len(df)):
        if np.isnan(comp[i]) or comp[i] >= ratio:
            continue
        if c[i] > bh[i]:
            sl = max(bl[i], c[i] - atr_mult * a[i])
            risk = c[i] - sl
            out[i] = _entry(df, i, "long", sl, None if trail else c[i] + rr * risk, manage=mg)
        elif c[i] < bl[i]:
            sl = min(bh[i], c[i] + atr_mult * a[i])
            risk = sl - c[i]
            out[i] = _entry(df, i, "short", sl, None if trail else c[i] - rr * risk, manage=mg)
    return out


# ------------------------------------------------------------- 4 weekend_bo
def build_weekend_bo(df, days=(0,), rr=None, hold=24, atr_mult=1.5, atr_n=14, stop="mid"):
    """Sat 00:00 .. Sun 23:59 range; first break on `days` (0=Mon) -> trade it."""
    t = pd.DatetimeIndex(df["time"])
    h, l, c = (_a(df, k) for k in ("high", "low", "close"))
    a = atr(df, atr_n)
    wd = t.dayofweek.to_numpy()
    wk = (t - pd.to_timedelta(t.dayofweek, unit="D")).normalize().to_numpy()
    n = len(df)
    out = [None] * n
    we_h = we_l = np.nan
    cur_wk = None
    done = False
    for i in range(n):
        if wk[i] != cur_wk:
            cur_wk, done = wk[i], False
        if wd[i] >= 5:
            if wd[i] == 5 and (i == 0 or wd[i - 1] != 5):
                we_h, we_l = h[i], l[i]
            else:
                we_h, we_l = max(we_h, h[i]), min(we_l, l[i])
            continue
        if done or wd[i] not in days or np.isnan(we_h):
            continue
        mid = 0.5 * (we_h + we_l)
        if c[i] > we_h:
            sl = max(mid, c[i] - 3 * a[i]) if stop == "mid" else c[i] - atr_mult * a[i]
            risk = c[i] - sl
            out[i] = _entry(df, i, "long", sl, None if rr is None else c[i] + rr * risk, max_hold=hold)
            done = True
        elif c[i] < we_l:
            sl = min(mid, c[i] + 3 * a[i]) if stop == "mid" else c[i] + atr_mult * a[i]
            risk = sl - c[i]
            out[i] = _entry(df, i, "short", sl, None if rr is None else c[i] - rr * risk, max_hold=hold)
            done = True
    return out


# ------------------------------------------------------------- 5 session_bo
def build_session_bo(df, start=2, end=9, trade_until=18, rr=1.5, atr_mult=1.0, atr_n=14,
                     exit_hour=23, stop="atr", weekdays_only=False):
    """Range of bars with hour in [start, end) (EET); break on close in [end, trade_until]."""
    t = pd.DatetimeIndex(df["time"])
    hr = t.hour.to_numpy(); day = t.normalize().to_numpy(); wd = t.dayofweek.to_numpy()
    h, l, c = (_a(df, k) for k in ("high", "low", "close"))
    a = atr(df, atr_n)
    n = len(df)
    out = [None] * n
    rh = rl = np.nan; cur = None; done = False
    for i in range(n):
        if day[i] != cur:
            cur, done, rh, rl = day[i], False, np.nan, np.nan
        if start <= hr[i] < end:
            rh = h[i] if np.isnan(rh) else max(rh, h[i])
            rl = l[i] if np.isnan(rl) else min(rl, l[i])
            continue
        if done or np.isnan(rh) or not (end <= hr[i] <= trade_until):
            continue
        if weekdays_only and wd[i] >= 5:
            continue
        if c[i] > rh:
            sl = c[i] - atr_mult * a[i] if stop == "atr" else rl
            risk = c[i] - sl
            out[i] = _entry(df, i, "long", sl, None if rr is None else c[i] + rr * risk, exit_hour=exit_hour)
            done = True
        elif c[i] < rl:
            sl = c[i] + atr_mult * a[i] if stop == "atr" else rh
            risk = sl - c[i]
            out[i] = _entry(df, i, "short", sl, None if rr is None else c[i] - rr * risk, exit_hour=exit_hour)
            done = True
    return out


# ------------------------------------------------------------ 6 us_open_mom
def build_us_open_mom(df, t0=16, t1=18, thresh=0.75, atr_mult=1.5, atr_n=14, exit_hour=23,
                      rr=None, fade=False):
    """At the close of the bar whose hour is t1, measure open[t0] -> close[t1]; if > thresh ATR
    follow it (or fade it) until exit_hour."""
    t = pd.DatetimeIndex(df["time"])
    hr = t.hour.to_numpy(); day = t.normalize().to_numpy()
    o, c = _a(df, "open"), _a(df, "close")
    a = atr(df, atr_n)
    n = len(df)
    out = [None] * n
    o0 = np.nan; cur = None
    for i in range(n):
        if day[i] != cur:
            cur, o0 = day[i], np.nan
        if hr[i] == t0:
            o0 = o[i]
        if hr[i] != t1 or np.isnan(o0):
            continue
        mv = c[i] - o0
        if abs(mv) < thresh * a[i]:
            continue
        side = ("long" if mv > 0 else "short")
        if fade:
            side = "short" if side == "long" else "long"
        sl = c[i] - atr_mult * a[i] if side == "long" else c[i] + atr_mult * a[i]
        tp = None if rr is None else (c[i] + rr * atr_mult * a[i] if side == "long" else c[i] - rr * atr_mult * a[i])
        out[i] = _entry(df, i, side, sl, tp, exit_hour=exit_hour)
    return out


# ---------------------------------------------------------------- 7 weekday
def build_weekday(df, long_days=(0, 2), short_days=(3,), atr_mult=2.0, atr_n=14, entry_hour=23):
    """Hold a full server day. On D1 the signal bar is the day BEFORE (closes at its end);
    on intraday data the signal is the bar with hour `entry_hour` of the day before."""
    t = pd.DatetimeIndex(df["time"])
    wd_next = ((t + pd.Timedelta(days=1)).dayofweek).to_numpy()
    hr = t.hour.to_numpy()
    c = _a(df, "close"); a = atr(df, atr_n)
    bpd = _bars_per_day(df)
    n = len(df)
    out = [None] * n
    for i in range(atr_n, n):
        if bpd > 1 and hr[i] != entry_hour:
            continue
        if wd_next[i] in long_days:
            out[i] = _entry(df, i, "long", c[i] - atr_mult * a[i], max_hold=bpd)
        elif wd_next[i] in short_days:
            out[i] = _entry(df, i, "short", c[i] + atr_mult * a[i], max_hold=bpd)
    return out


# -------------------------------------------------------------- 8 overnight
def build_overnight(df, side="long", entry_wd=6, entry_hour=20, hold=12, atr_mult=2.0, atr_n=14):
    """Calendar slice: enter at the close of (weekday, hour), hold `hold` bars."""
    t = pd.DatetimeIndex(df["time"])
    wd = t.dayofweek.to_numpy(); hr = t.hour.to_numpy()
    c = _a(df, "close"); a = atr(df, atr_n)
    out = [None] * len(df)
    for i in range(atr_n, len(df)):
        if wd[i] == entry_wd and hr[i] == entry_hour:
            sl = c[i] - atr_mult * a[i] if side == "long" else c[i] + atr_mult * a[i]
            out[i] = _entry(df, i, side, sl, max_hold=hold)
    return out


# --------------------------------------------------------------- 9 pd_break
def build_pd_break(df, mode="break", rr=2.0, atr_mult=1.0, atr_n=14, exit_hour=None, max_hold=None,
                   hours=None, tp_level=False):
    """mode='break': first close beyond prior-day high/low each day -> follow.
    mode='sfp': bar trades through PDL/PDH but closes back inside -> fade (stop beyond wick)."""
    p = _prev_period(df, "D")
    h, l, c = (_a(df, k) for k in ("high", "low", "close"))
    a = atr(df, atr_n)
    t = pd.DatetimeIndex(df["time"]); hr = t.hour.to_numpy()
    n = len(df)
    out = [None] * n
    cur = None; used_up = used_dn = False
    for i in range(atr_n, n):
        if p["key"][i] != cur:
            cur, used_up, used_dn = p["key"][i], False, False
        if np.isnan(p["h"][i]) or (hours is not None and hr[i] not in hours):
            continue
        pdh, pdl = p["h"][i], p["l"][i]
        if mode == "break":
            if c[i] > pdh and not used_up:
                used_up = True
                sl = c[i] - atr_mult * a[i]
                out[i] = _entry(df, i, "long", sl, c[i] + rr * (c[i] - sl), max_hold=max_hold, exit_hour=exit_hour)
            elif c[i] < pdl and not used_dn:
                used_dn = True
                sl = c[i] + atr_mult * a[i]
                out[i] = _entry(df, i, "short", sl, c[i] - rr * (sl - c[i]), max_hold=max_hold, exit_hour=exit_hour)
        else:  # sfp
            if l[i] < pdl and c[i] > pdl and not used_dn:
                used_dn = True
                sl = l[i] - 0.1 * a[i]
                tp = pdh if tp_level else c[i] + rr * (c[i] - sl)
                out[i] = _entry(df, i, "long", sl, tp, max_hold=max_hold, exit_hour=exit_hour)
            elif h[i] > pdh and c[i] < pdh and not used_up:
                used_up = True
                sl = h[i] + 0.1 * a[i]
                tp = pdl if tp_level else c[i] - rr * (sl - c[i])
                out[i] = _entry(df, i, "short", sl, tp, max_hold=max_hold, exit_hour=exit_hour)
    return out


# ----------------------------------------------------------------- 10 pw_sfp
def build_pw_sfp(df, rr=2.0, atr_n=14, max_hold=None, trail_mult=None, mode="sfp"):
    p = _prev_period(df, "W")
    h, l, c = (_a(df, k) for k in ("high", "low", "close"))
    a = atr(df, atr_n)
    mg = _chandelier(trail_mult, a) if trail_mult else None
    n = len(df)
    out = [None] * n
    cur = None; used_up = used_dn = False
    for i in range(atr_n, n):
        if p["key"][i] != cur:
            cur, used_up, used_dn = p["key"][i], False, False
        if np.isnan(p["h"][i]):
            continue
        pwh, pwl = p["h"][i], p["l"][i]
        if mode == "sfp":
            if l[i] < pwl and c[i] > pwl and not used_dn:
                used_dn = True
                sl = l[i] - 0.1 * a[i]
                out[i] = _entry(df, i, "long", sl, None if mg else c[i] + rr * (c[i] - sl), max_hold=max_hold, manage=mg)
            elif h[i] > pwh and c[i] < pwh and not used_up:
                used_up = True
                sl = h[i] + 0.1 * a[i]
                out[i] = _entry(df, i, "short", sl, None if mg else c[i] - rr * (sl - c[i]), max_hold=max_hold, manage=mg)
        else:  # break of prior-week extreme
            if c[i] > pwh and not used_up:
                used_up = True
                sl = c[i] - 1.5 * a[i]
                out[i] = _entry(df, i, "long", sl, None if mg else c[i] + rr * (c[i] - sl), max_hold=max_hold, manage=mg)
            elif c[i] < pwl and not used_dn:
                used_dn = True
                sl = c[i] + 1.5 * a[i]
                out[i] = _entry(df, i, "short", sl, None if mg else c[i] - rr * (sl - c[i]), max_hold=max_hold, manage=mg)
    return out


# ------------------------------------------------------------- 11 pdc_revert
def build_pdc_revert(df, z=1.5, atr_mult=1.0, hold=12, tp="pdc", hours=None):
    p = _prev_period(df, "D")
    datr = _day_atr(df)
    c = _a(df, "close")
    t = pd.DatetimeIndex(df["time"]); hr = t.hour.to_numpy()
    n = len(df)
    out = [None] * n
    cur = None; used = False
    for i in range(30, n):
        if p["key"][i] != cur:
            cur, used = p["key"][i], False
        if used or np.isnan(p["c"][i]) or np.isnan(datr[i]) or (hours is not None and hr[i] not in hours):
            continue
        d = (c[i] - p["c"][i]) / datr[i]
        if d > z:
            used = True
            sl = c[i] + atr_mult * datr[i]
            out[i] = _entry(df, i, "short", sl, p["c"][i] if tp == "pdc" else None, max_hold=hold)
        elif d < -z:
            used = True
            sl = c[i] - atr_mult * datr[i]
            out[i] = _entry(df, i, "long", sl, p["c"][i] if tp == "pdc" else None, max_hold=hold)
    return out


# ---------------------------------------------------------------- 12 rsi2_mr
def _rsi(c, n):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.where(d > 0, d, 0.0)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.where(d < 0, -d, 0.0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50).to_numpy()


def build_rsi2_mr(df, rsi_n=2, lo=10, hi=90, trend_n=200, atr_mult=2.0, hold=10, exit_rsi=50, use_trend=True):
    c = _a(df, "close"); a = atr(df, 14)
    r = _rsi(c, rsi_n)
    tr = pd.Series(c).rolling(trend_n).mean().to_numpy()

    def manage(df_, i, pos):
        if pos["side"] == "long" and r[i] > exit_rsi:
            return "close"
        if pos["side"] == "short" and r[i] < 100 - exit_rsi:
            return "close"
        return None

    out = [None] * len(df)
    for i in range(max(trend_n, 20), len(df)):
        if r[i] < lo and (not use_trend or c[i] > tr[i]):
            out[i] = _entry(df, i, "long", c[i] - atr_mult * a[i], max_hold=hold, manage=manage)
        elif r[i] > hi and (not use_trend or c[i] < tr[i]):
            out[i] = _entry(df, i, "short", c[i] + atr_mult * a[i], max_hold=hold, manage=manage)
    return out


# ----------------------------------------------------------- 13 ema_pullback
def build_ema_pullback(df, fast=20, slow=50, trend=200, atr_mult=1.5, rr=2.0, trail=False, long_only=False):
    h, l, c = (_a(df, k) for k in ("high", "low", "close"))
    a = atr(df, 14)
    ef, es, et = _ema(c, fast), _ema(c, slow), _ema(c, trend)
    mg = _chandelier(atr_mult, a) if trail else None
    out = [None] * len(df)
    for i in range(trend, len(df)):
        if es[i] > et[i] and l[i] <= ef[i] and c[i] > ef[i] and c[i] > c[i - 1]:
            sl = min(l[i], c[i] - atr_mult * a[i])
            out[i] = _entry(df, i, "long", sl, None if trail else c[i] + rr * (c[i] - sl), manage=mg)
        elif not long_only and es[i] < et[i] and h[i] >= ef[i] and c[i] < ef[i] and c[i] < c[i - 1]:
            sl = max(h[i], c[i] + atr_mult * a[i])
            out[i] = _entry(df, i, "short", sl, None if trail else c[i] - rr * (sl - c[i]), manage=mg)
    return out


# ---------------------------------------------------------------- 14 squeeze
def build_squeeze(df, bb_n=20, bb_k=2.0, kc_mult=1.5, min_bars=6, atr_mult=1.5, rr=2.0, trail=True):
    c = _a(df, "close"); a = atr(df, bb_n)
    s = pd.Series(c)
    ma = s.rolling(bb_n).mean().to_numpy(); sd = s.rolling(bb_n).std().to_numpy()
    ub, lb_ = ma + bb_k * sd, ma - bb_k * sd
    ku, kl = ma + kc_mult * a, ma - kc_mult * a
    inside = (ub < ku) & (lb_ > kl)
    cnt = np.zeros(len(df), int)
    for i in range(1, len(df)):
        cnt[i] = cnt[i - 1] + 1 if inside[i] else 0
    mg = _chandelier(atr_mult, a) if trail else None
    out = [None] * len(df)
    for i in range(bb_n + 1, len(df)):
        if cnt[i - 1] < min_bars or inside[i]:
            continue
        if c[i] > ub[i]:
            sl = c[i] - atr_mult * a[i]
            out[i] = _entry(df, i, "long", sl, None if trail else c[i] + rr * atr_mult * a[i], manage=mg)
        elif c[i] < lb_[i]:
            sl = c[i] + atr_mult * a[i]
            out[i] = _entry(df, i, "short", sl, None if trail else c[i] - rr * atr_mult * a[i], manage=mg)
    return out


# ----------------------------------------------------------- 15 round_bounce
def build_round_bounce(df, tol=0.2, rr=2.0, atr_mult=1.0, step=None, hold=24):
    sym = df.attrs.get("symbol", "")
    step = step or ROUND_STEP.get(sym, 1.0)
    h, l, c, o = (_a(df, k) for k in ("high", "low", "close", "open"))
    a = atr(df, 14)
    out = [None] * len(df)
    for i in range(20, len(df)):
        lv_lo = np.floor(l[i] / step) * step        # round level at/below the low
        lv_hi = np.ceil(h[i] / step) * step
        if abs(l[i] - lv_lo) <= tol * a[i] and c[i] > lv_lo + 0.1 * a[i] and c[i] > o[i] and l[i] - lv_lo < 0.5 * a[i]:
            sl = min(l[i], lv_lo) - atr_mult * 0.5 * a[i]
            out[i] = _entry(df, i, "long", sl, c[i] + rr * (c[i] - sl), max_hold=hold)
        elif abs(lv_hi - h[i]) <= tol * a[i] and c[i] < lv_hi - 0.1 * a[i] and c[i] < o[i] and lv_hi - h[i] < 0.5 * a[i]:
            sl = max(h[i], lv_hi) + atr_mult * 0.5 * a[i]
            out[i] = _entry(df, i, "short", sl, c[i] - rr * (sl - c[i]), max_hold=hold)
    return out


# ------------------------------------------------------------ 16 weekly_open
def build_weekly_open(df, from_hour=12, from_wd=0, min_dist=0.5, atr_mult=2.0, trail=True, exit_wd=6):
    """From Monday `from_hour` on: if close is > min_dist x ATR above the week's open -> long
    (below -> short). Flat at the start of the next week (max_hold = bars left in the week)."""
    p = _prev_period(df, "W")
    t = pd.DatetimeIndex(df["time"])
    wd = t.dayofweek.to_numpy(); hr = t.hour.to_numpy()
    c = _a(df, "close"); a = atr(df, 14)
    bpd = _bars_per_day(df)
    step_h = 24 // bpd
    mg = _chandelier(atr_mult, a) if trail else None
    n = len(df)
    out = [None] * n
    cur = None; done = False
    for i in range(20, n):
        if p["key"][i] != cur:
            cur, done = p["key"][i], False
        if done or np.isnan(p["cur_open"][i]):
            continue
        if wd[i] < from_wd or (wd[i] == from_wd and hr[i] < from_hour) or wd[i] > exit_wd:
            continue
        hours_left = ((exit_wd - wd[i]) * 24 + (24 - hr[i] - step_h))
        hold = max(1, hours_left // step_h)
        d = c[i] - p["cur_open"][i]
        if d > min_dist * a[i]:
            out[i] = _entry(df, i, "long", c[i] - atr_mult * a[i], max_hold=hold, manage=mg); done = True
        elif d < -min_dist * a[i]:
            out[i] = _entry(df, i, "short", c[i] + atr_mult * a[i], max_hold=hold, manage=mg); done = True
    return out


# ----------------------------------------------------------- 17 rel_strength
def build_rel_strength(df, lb=120, atr_mult=2.0, hold=24, need_btc=True, reenter=False):
    sym = df.attrs.get("symbol", "")
    if sym == "BTCUSD":
        return [None] * len(df)
    tf = df.attrs.get("tf", "H1")
    btc = pd.read_csv(H.DATA / f"btcusd-{tf.lower()}.csv", usecols=["time", "close"], parse_dates=["time"])
    btc = btc.drop_duplicates("time").sort_values("time").rename(columns={"close": "btc"})
    m = pd.merge_asof(df[["time"]], btc, on="time", direction="backward")
    b = m["btc"].to_numpy(float)
    c = _a(df, "close"); a = atr(df, 14)
    n = len(df)
    rel = np.full(n, np.nan); bm = np.full(n, np.nan)
    rel[lb:] = np.log(c[lb:] / c[:-lb]) - np.log(b[lb:] / b[:-lb])
    bm[lb:] = b[lb:] - b[:-lb]
    out = [None] * n
    prev = 0
    for i in range(lb + 14, n):
        if np.isnan(rel[i]) or np.isnan(bm[i]):
            continue
        s = 1 if (rel[i] > 0 and (bm[i] > 0 or not need_btc)) else (-1 if (rel[i] < 0 and (bm[i] < 0 or not need_btc)) else 0)
        if s != 0 and (reenter or s != prev):
            side = "long" if s > 0 else "short"
            sl = c[i] - atr_mult * a[i] if s > 0 else c[i] + atr_mult * a[i]
            out[i] = _entry(df, i, side, sl, max_hold=hold)
        prev = s
    return out


# -------------------------------------------------------------- 18 vol_spike
def build_vol_spike(df, k=3.0, mode="fade", atr_mult=1.5, hold=6, rr=1.0, close_pos=0.7):
    h, l, c = (_a(df, k_) for k_ in ("high", "low", "close"))
    a = atr(df, 14)
    a_prev = np.r_[a[0], a[:-1]]
    out = [None] * len(df)
    for i in range(20, len(df)):
        rng = h[i] - l[i]
        if rng < k * a_prev[i] or rng <= 0:
            continue
        pos = (c[i] - l[i]) / rng
        if pos >= close_pos:          # strong up bar
            side = "short" if mode == "fade" else "long"
        elif pos <= 1 - close_pos:
            side = "long" if mode == "fade" else "short"
        else:
            continue
        if side == "long":
            sl = c[i] - atr_mult * a[i]; tp = c[i] + rr * atr_mult * a[i] if rr else None
        else:
            sl = c[i] + atr_mult * a[i]; tp = c[i] - rr * atr_mult * a[i] if rr else None
        out[i] = _entry(df, i, side, sl, tp, max_hold=hold)
    return out


# ---------------------------------------------------------------- 19 day_orb
def build_day_orb(df, n_hours=4, rr=2.0, atr_mult=1.0, exit_hour=23, stop="range", trade_until=20):
    return build_session_bo(df, start=0, end=n_hours, trade_until=trade_until, rr=rr, atr_mult=atr_mult,
                            exit_hour=exit_hour, stop=stop)


# ------------------------------------------------------------- 20 inside_day
def build_inside_day(df, rr=2.0, atr_mult=1.0, max_hold=None, trail=False):
    """Prior day inside the day before it (daily compression); trade the first close beyond the
    mother day's high/low. Works on H1/H4 (intraday break) and D1 (bar i breaks)."""
    t = pd.DatetimeIndex(df["time"]).normalize()
    g = pd.DataFrame({"k": t.to_numpy(), "h": _a(df, "high"), "l": _a(df, "low")})
    d = g.groupby("k").agg(h=("h", "max"), l=("l", "min"))
    ins = (d.h < d.h.shift(1)) & (d.l > d.l.shift(1))
    mh = d.h.shift(1).where(ins); ml = d.l.shift(1).where(ins)   # mother day levels when inside
    mh = mh.shift(1).reindex(t).to_numpy(); ml = ml.shift(1).reindex(t).to_numpy()  # available next day
    c = _a(df, "close"); a = atr(df, 14)
    mg = _chandelier(atr_mult * 1.5, a) if trail else None
    n = len(df)
    out = [None] * n
    cur = None; done = False
    key = t.to_numpy()
    for i in range(30, n):
        if key[i] != cur:
            cur, done = key[i], False
        if done or np.isnan(mh[i]):
            continue
        if c[i] > mh[i]:
            sl = max(ml[i], c[i] - 2 * atr_mult * a[i]) if not trail else c[i] - atr_mult * 1.5 * a[i]
            sl = min(sl, c[i] - atr_mult * a[i])
            out[i] = _entry(df, i, "long", sl, None if trail else c[i] + rr * (c[i] - sl), max_hold=max_hold, manage=mg); done = True
        elif c[i] < ml[i]:
            sl = min(mh[i], c[i] + 2 * atr_mult * a[i]) if not trail else c[i] + atr_mult * 1.5 * a[i]
            sl = max(sl, c[i] + atr_mult * a[i])
            out[i] = _entry(df, i, "short", sl, None if trail else c[i] - rr * (sl - c[i]), max_hold=max_hold, manage=mg); done = True
    return out


# ------------------------------------------------------------- 21 supertrend
def build_supertrend(df, n=10, mult=3.0, long_only=False, reenter=True):
    h, l, c = (_a(df, k) for k in ("high", "low", "close"))
    a = atr(df, n)
    hl2 = 0.5 * (h + l)
    N = len(df)
    up = hl2 + mult * a; dn = hl2 - mult * a
    fu = up.copy(); fd = dn.copy(); trend = np.ones(N, int)
    for i in range(1, N):
        fu[i] = up[i] if (up[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fd[i] = dn[i] if (dn[i] > fd[i - 1] or c[i - 1] < fd[i - 1]) else fd[i - 1]
        if trend[i - 1] == 1:
            trend[i] = -1 if c[i] < fd[i] else 1
        else:
            trend[i] = 1 if c[i] > fu[i] else -1
    line = np.where(trend == 1, fd, fu)

    def manage(df_, i, pos):
        if pos["side"] == "long":
            if trend[i] == -1:
                return "close"
            return line[i] if line[i] > pos["sl"] else None
        if trend[i] == 1:
            return "close"
        return line[i] if line[i] < pos["sl"] else None

    out = [None] * N
    for i in range(n + 2, N):
        flip = trend[i] != trend[i - 1]
        if not (reenter or flip):
            continue
        if trend[i] == 1:
            out[i] = _entry(df, i, "long", line[i], manage=manage)
        elif not long_only:
            out[i] = _entry(df, i, "short", line[i], manage=manage)
    return out


# ======================================================= round-3b additions
# ------------------------------------------------------------ 22 hour_slice
def build_hour_slice(df, hour=0, side="long", hold=8, days=None, atr_mult=2.0, atr_n=14):
    """Calendar slice on any day: enter at the close of bar `hour` (EET), hold `hold` bars.
    `days` = tuple of weekdays (0=Mon..6=Sun) or None for every day."""
    t = pd.DatetimeIndex(df["time"])
    hr = t.hour.to_numpy(); wd = t.dayofweek.to_numpy()
    c = _a(df, "close"); a = atr(df, atr_n)
    out = [None] * len(df)
    for i in range(atr_n, len(df)):
        if hr[i] != hour or (days is not None and wd[i] not in days):
            continue
        sl = c[i] - atr_mult * a[i] if side == "long" else c[i] + atr_mult * a[i]
        out[i] = _entry(df, i, side, sl, max_hold=hold)
    return out


# --------------------------------------------------------- 23 funding_cycle
def build_funding_cycle(df, hours=(2, 10, 18), lb=8, thresh=0.5, hold=8, atr_mult=1.5, atr_n=14,
                        fade=False):
    """Perp funding settles 00/08/16 UTC (= 02/10/18 EET). At those bar closes take the sign of
    the last `lb`-bar move if it exceeds thresh x ATR; follow (or fade) it for `hold` bars."""
    t = pd.DatetimeIndex(df["time"])
    hr = t.hour.to_numpy()
    c = _a(df, "close"); a = atr(df, atr_n)
    out = [None] * len(df)
    for i in range(max(lb, atr_n), len(df)):
        if hr[i] not in hours:
            continue
        mv = c[i] - c[i - lb]
        if abs(mv) < thresh * a[i]:
            continue
        side = "long" if mv > 0 else "short"
        if fade:
            side = "short" if side == "long" else "long"
        sl = c[i] - atr_mult * a[i] if side == "long" else c[i] + atr_mult * a[i]
        out[i] = _entry(df, i, side, sl, max_hold=hold)
    return out


# -------------------------------------------------------------- 24 btc_lead
def build_btc_lead(df, lb=4, btc_thresh=1.0, alt_max=0.5, hold=12, atr_mult=1.5, atr_n=14, rr=None):
    """BTC leads, alt lags: BTC moved > btc_thresh x its ATR over `lb` bars while the alt moved
    < alt_max x its own ATR in that direction -> trade the alt in BTC direction."""
    sym = df.attrs.get("symbol", "")
    if sym == "BTCUSD":
        return [None] * len(df)
    tf = df.attrs.get("tf", "H1")
    btc = pd.read_csv(H.DATA / f"btcusd-{tf.lower()}.csv", parse_dates=["time"])
    btc = btc.drop_duplicates("time").sort_values("time").reset_index(drop=True)
    ab = atr(btc, atr_n)
    btc = btc[["time", "close"]].assign(atr=ab).rename(columns={"close": "btc"})
    m = pd.merge_asof(df[["time"]], btc, on="time", direction="backward")
    b = m["btc"].to_numpy(float); ba = m["atr"].to_numpy(float)
    c = _a(df, "close"); a = atr(df, atr_n)
    out = [None] * len(df)
    for i in range(max(lb, atr_n) + 1, len(df)):
        if np.isnan(b[i]) or np.isnan(ba[i]):
            continue
        bm = b[i] - b[i - lb]; am = c[i] - c[i - lb]
        if abs(bm) < btc_thresh * ba[i]:
            continue
        side = "long" if bm > 0 else "short"
        if (am if side == "long" else -am) > alt_max * a[i]:
            continue                      # alt already moved: no lag to catch
        sl = c[i] - atr_mult * a[i] if side == "long" else c[i] + atr_mult * a[i]
        tp = None if rr is None else (c[i] + rr * atr_mult * a[i] if side == "long" else c[i] - rr * atr_mult * a[i])
        out[i] = _entry(df, i, side, sl, tp, max_hold=hold)
    return out


# --------------------------------------------------------------- 25 nday_bo
def build_nday_bo(df, n=10, hold_days=5, atr_mult=2.0, atr_n=14, long_only=False, trail=False):
    """Multi-day range breakout: close above the prior n-bar high (below the low) -> enter,
    hold at most hold_days server days (time exit), ATR stop (or chandelier trail)."""
    h, l, c = (_a(df, k) for k in ("high", "low", "close"))
    a = atr(df, atr_n)
    bpd = _bars_per_day(df)
    hh = pd.Series(h).rolling(n).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n).min().shift(1).to_numpy()
    mg = _chandelier(atr_mult, a) if trail else None
    out = [None] * len(df)
    in_side = 0; until = -1
    for i in range(max(n, atr_n) + 1, len(df)):
        if i < until:
            continue
        if c[i] > hh[i] and in_side <= 0:
            out[i] = _entry(df, i, "long", c[i] - atr_mult * a[i], max_hold=hold_days * bpd, manage=mg)
            in_side, until = 1, i + hold_days * bpd
        elif c[i] < ll[i] and in_side >= 0 and not long_only:
            out[i] = _entry(df, i, "short", c[i] + atr_mult * a[i], max_hold=hold_days * bpd, manage=mg)
            in_side, until = -1, i + hold_days * bpd
        elif c[i] < ll[i] and long_only:
            in_side = -1
    return out


# ------------------------------------------------------------ 26 weekend_mr
def build_weekend_mr(df, thresh=1.0, hold=24, atr_mult=1.5, entry_wd=6, entry_hour=23, follow=False,
                     atr_n=14):
    """Weekend move (Fri 23:00 close -> Sun `entry_hour` close) > thresh x day-ATR: fade it into
    Monday (or follow it)."""
    t = pd.DatetimeIndex(df["time"])
    hr = t.hour.to_numpy(); wd = t.dayofweek.to_numpy()
    c = _a(df, "close"); a = atr(df, atr_n); da = _day_atr(df, atr_n)
    out = [None] * len(df)
    fri = np.nan
    for i in range(atr_n, len(df)):
        if wd[i] == 4 and hr[i] == 23:
            fri = c[i]
        if wd[i] == entry_wd and hr[i] == entry_hour and not np.isnan(fri) and not np.isnan(da[i]):
            mv = c[i] - fri
            fri = np.nan
            if abs(mv) < thresh * da[i]:
                continue
            side = ("long" if mv > 0 else "short") if follow else ("short" if mv > 0 else "long")
            sl = c[i] - atr_mult * a[i] if side == "long" else c[i] + atr_mult * a[i]
            out[i] = _entry(df, i, side, sl, max_hold=hold)
    return out


# ----------------------------------------------------------- 27 pd_mom_hold
def build_pd_mom(df, hour=23, thresh=0.5, hold=24, atr_mult=2.0, atr_n=14, fade=False):
    """Daily follow-through: at `hour` compare close with the prior-day close; if the move is
    > thresh x day-ATR, hold that direction for `hold` bars (or fade)."""
    t = pd.DatetimeIndex(df["time"])
    hr = t.hour.to_numpy()
    p = _prev_period(df, "D")
    c = _a(df, "close"); a = atr(df, atr_n); da = _day_atr(df, atr_n)
    out = [None] * len(df)
    for i in range(atr_n, len(df)):
        if hr[i] != hour or np.isnan(p["c"][i]) or np.isnan(da[i]):
            continue
        mv = c[i] - p["c"][i]
        if abs(mv) < thresh * da[i]:
            continue
        side = "long" if mv > 0 else "short"
        if fade:
            side = "short" if side == "long" else "long"
        sl = c[i] - atr_mult * a[i] if side == "long" else c[i] + atr_mult * a[i]
        out[i] = _entry(df, i, side, sl, max_hold=hold)
    return out
