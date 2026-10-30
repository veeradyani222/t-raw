"""Round-3 majors group (2026-10-30): STRUCTURE + SESSION ideas on
EURUSD GBPUSD USDCHF EURGBP EURCHF GBPCHF (M30 / H1 / H4 / D1).

Every build_* takes any df from research.prop.harness.load() (any symbol/tf)
and returns a list (len(df)) of H.Entry | None. Everything is causal: bar i
only uses rows <= i. Day/week levels come from COMPLETED previous server
days / weeks (EET); same-day stats (day open, running high/low, Asian range)
are cumulative up to bar i.

Server clock (EET, follows EU DST): London open 10:00, NY equities 16:30,
WM/Reuters 4pm-London fix = 18:00 (close of the 17:00 bar), US data 15:30,
rollover 00:00. Day = server day (the FundedNext daily-loss day).

Ideas (numbered as in NOTES.md):
 1 asia_breakout          London close beyond Asian (00-09) range, structure SL/TP
 2 asia_sweep_reversal    London 'Judas' sweep of Asian H/L + close back inside -> fade
 3 pd_sweep_reversal      sweep of prior-day H/L + close back inside -> fade
 4 pd_break_continuation  close through prior-day H/L -> continuation
 5 pw_sweep_reversal      sweep of prior-WEEK H/L + close back inside -> fade
 6 pivot_touch            floor-pivot S1/R1 (prev day OHLC) touch + close back -> fade
 7 monday_gap_fade        weekend gap (Mon open vs Fri close) -> trade toward fill
 8 fix_fade               fade the 15:00->18:00 run into the London fix
 9 london_open_reversal   fade an outsized first London bar (10:00)
10 trend_day_continuation  by hour H the day already ranged > k*ATR20d and closes at
                            the extreme -> hold with it into the close
11 range_day_fade          by hour >= H the day is tight (< f*ATR20d) and price sits at
                            the day extreme -> fade to the day mid
12 inside_nr_break         inside-day / NR7 range break (D1/H4)
13 d1_reversal             fade an outsized daily close-to-close move (CHF crosses
                            show ac1 ~ -0.15 on D1)
14 round_number_fade       touch of a 50-pip round level + close back -> fade
15 weekly_open_reversion   mid-week stretch from the Monday open -> fade toward it
16 day_open_reversion      afternoon stretch from the day open -> fade toward it
17 ny_overlap_continuation London-session direction carried into the NY overlap
18 friday_week_fade        Friday afternoon: fade the week's move
19 rollover_dip            23:00 bar dip / 00-01 recovery (CHF pairs) - liquidity
                            artefact, tested with spread_mult but NOT a candidate
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H


# ----------------------------------------------------------------- helpers
def _arr(df, k):
    return df[k].to_numpy(float)


def atr(df, n=14):
    h, l, c = (_arr(df, k) for k in ("high", "low", "close"))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


class Ctx:
    """Causal per-bar context: previous-day/week levels, same-day running stats."""

    def __init__(self, df, asia_end=10):
        t = pd.DatetimeIndex(df["time"])
        self.t = t
        self.hour = t.hour.to_numpy()
        self.minute = t.minute.to_numpy()
        self.wd = t.dayofweek.to_numpy()
        self.day = t.normalize().to_numpy()
        self.week = (t - pd.to_timedelta(t.dayofweek, unit="D")).normalize().to_numpy()
        self.o, self.h, self.l, self.c = (_arr(df, k) for k in ("open", "high", "low", "close"))
        n = len(df)
        self.n = n
        g = pd.DataFrame({"d": self.day, "w": self.week, "h": self.h, "l": self.l,
                          "o": self.o, "c": self.c})
        D = g.groupby("d").agg(h=("h", "max"), l=("l", "min"), o=("o", "first"), c=("c", "last"))
        P = D.shift(1)
        idx = pd.Index(self.day)
        self.pdh, self.pdl, self.pdo, self.pdc = (P[k].reindex(idx).to_numpy() for k in "hloc")
        rng = D.h - D.l
        self.atr_d = rng.rolling(20, min_periods=10).mean().shift(1).reindex(idx).to_numpy()
        self.nr7 = (rng.shift(1) <= rng.shift(1).rolling(7).min()).reindex(idx).to_numpy()
        self.inside = ((D.h.shift(1) < D.h.shift(2)) & (D.l.shift(1) > D.l.shift(2))).reindex(idx).to_numpy()
        W = g.groupby("w").agg(h=("h", "max"), l=("l", "min"), o=("o", "first"), c=("c", "last"))
        PW = W.shift(1)
        widx = pd.Index(self.week)
        self.pwh, self.pwl, self.pwc = (PW[k].reindex(widx).to_numpy() for k in "hlc")
        self.wk_open = W.o.reindex(widx).to_numpy()          # Monday open (known once week starts)
        # same-day running stats (cumulative, causal)
        self.day_open = D.o.reindex(idx).to_numpy()
        gb = g.groupby("d")
        self.run_h = gb["h"].cummax().to_numpy()
        self.run_l = gb["l"].cummin().to_numpy()
        self.bar_in_day = gb.cumcount().to_numpy()
        # Asian range: bars with hour < asia_end, carried forward through the day
        mask = self.hour < asia_end
        ah = pd.Series(np.where(mask, self.h, np.nan))
        al = pd.Series(np.where(mask, self.l, np.nan))
        self.asia_h = ah.groupby(self.day).cummax().groupby(self.day).ffill().to_numpy()
        self.asia_l = al.groupby(self.day).cummin().groupby(self.day).ffill().to_numpy()
        self.asia_done = ~mask & ~np.isnan(self.asia_h)
        # pivots from previous day
        p = (self.pdh + self.pdl + self.pdc) / 3.0
        self.piv, self.r1, self.s1 = p, 2 * p - self.pdl, 2 * p - self.pdh
        self.r2, self.s2 = p + (self.pdh - self.pdl), p - (self.pdh - self.pdl)
        # last bar of each clock hour -> "the close of hour H". Decided from the
        # clock (bar length), not from whether a later bar exists, so a truncated
        # df gives the same flag (look-ahead check).
        if n > 1:
            dm = np.diff(t.values).astype("timedelta64[m]").astype(int)
            bar_min = int(min(60, max(1, np.median(dm))))
        else:
            bar_min = 60
        self.hour_close = (self.minute + bar_min) >= 60


def _one_per_day(sigs, ctx):
    """Keep only the first signal per server day."""
    last = None
    for i, s in enumerate(sigs):
        if s is None:
            continue
        if last is not None and ctx.day[i] == last:
            sigs[i] = None
        else:
            last = ctx.day[i]
    return sigs


def _E(side, sl, tp=None, **kw):
    return H.Entry(side, float(sl), None if tp is None else float(tp), **kw)


# ------------------------------------------------------------- 1 asia breakout
def build_asia_breakout(df, start=10, end=13, buf=0.0, sl_mode="mid", rr=1.5,
                        tp_mode="rr", max_range=1.0, exit_hour=22, min_range=0.15):
    """First close beyond the Asian (00:00-09:59) range between `start` and `end`
    o'clock. buf = extra distance in ATR20d. sl_mode: 'mid' (range midpoint) or
    'opp' (opposite side) or 'half' (half the range beyond the level).
    tp_mode: 'rr' (rr x stop), 'range' (range height projected), 'pd' (prior-day H/L,
    fallback rr). Range must be < max_range x ATR20d and > min_range x ATR20d."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c, hr = ctx.c, ctx.hour
    for i in range(n):
        if not (start <= hr[i] <= end) or not ctx.asia_done[i] or np.isnan(ctx.atr_d[i]):
            continue
        ah, al, a = ctx.asia_h[i], ctx.asia_l[i], ctx.atr_d[i]
        width = ah - al
        if width > max_range * a or width < min_range * a:
            continue
        mid = (ah + al) / 2
        if c[i] > ah + buf * a:
            side, lvl, opp = "long", ah, al
        elif c[i] < al - buf * a:
            side, lvl, opp = "short", al, ah
        else:
            continue
        if sl_mode == "mid":
            sl = mid
        elif sl_mode == "opp":
            sl = opp
        else:
            sl = lvl - width / 2 if side == "long" else lvl + width / 2
        dist = abs(c[i] - sl)
        if dist <= 0:
            continue
        if tp_mode == "range":
            tp = lvl + width if side == "long" else lvl - width
        elif tp_mode == "pd":
            tgt = ctx.pdh[i] if side == "long" else ctx.pdl[i]
            ok = (tgt > c[i] + 0.5 * dist) if side == "long" else (tgt < c[i] - 0.5 * dist)
            tp = tgt if ok and not np.isnan(tgt) else (c[i] + rr * dist if side == "long" else c[i] - rr * dist)
        else:
            tp = c[i] + rr * dist if side == "long" else c[i] - rr * dist
        if (side == "long" and tp <= c[i]) or (side == "short" and tp >= c[i]):
            continue
        sigs[i] = _E(side, sl, tp, exit_hour=exit_hour, meta=dict(idea="asia_breakout"))
    return _one_per_day(sigs, ctx)


# ------------------------------------------------------ 2 asia sweep reversal
def build_asia_sweep_reversal(df, start=10, end=12, pen=0.05, buf=0.1, tp_mode="opp",
                              rr=1.5, exit_hour=18, max_range=1.2):
    """London 'Judas swing': between start..end a bar trades beyond the Asian high
    (low) by >= pen x ATR20d and CLOSES back inside -> short (long). SL beyond the
    sweep extreme + buf x ATR20d. tp: 'opp' = other side of the Asian range (must be
    >= 1R, else rr), 'mid', or 'rr'."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c, h, l, hr = ctx.c, ctx.h, ctx.l, ctx.hour
    for i in range(n):
        if not (start <= hr[i] <= end) or not ctx.asia_done[i] or np.isnan(ctx.atr_d[i]):
            continue
        ah, al, a = ctx.asia_h[i], ctx.asia_l[i], ctx.atr_d[i]
        if ah - al > max_range * a:
            continue
        mid = (ah + al) / 2
        if h[i] >= ah + pen * a and c[i] < ah:
            side, sl = "short", h[i] + buf * a
            dist = sl - c[i]
            tgt = {"opp": al, "mid": mid}.get(tp_mode, c[i] - rr * dist)
            if tp_mode == "opp" and c[i] - tgt < dist:
                tgt = c[i] - rr * dist
        elif l[i] <= al - pen * a and c[i] > al:
            side, sl = "long", l[i] - buf * a
            dist = c[i] - sl
            tgt = {"opp": ah, "mid": mid}.get(tp_mode, c[i] + rr * dist)
            if tp_mode == "opp" and tgt - c[i] < dist:
                tgt = c[i] + rr * dist
        else:
            continue
        if dist <= 0 or (side == "long" and tgt <= c[i]) or (side == "short" and tgt >= c[i]):
            continue
        sigs[i] = _E(side, sl, tgt, exit_hour=exit_hour, meta=dict(idea="asia_sweep"))
    return _one_per_day(sigs, ctx)


# -------------------------------------------------------- 3 prior-day sweeps
def build_pd_sweep_reversal(df, hours=(8, 20), pen=0.0, buf=0.1, tp_mode="mid", rr=1.5,
                            max_hold=12, exit_hour=None, level="pd"):
    """Bar trades beyond prior-day high (low) [or prior-week with level='pw'] by
    >= pen x ATR20d and closes back inside (previous bar closed inside) -> fade.
    SL beyond the bar extreme + buf x ATR20d. tp: 'mid' (level-range midpoint),
    'opp' (other side), 'rr'."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c, h, l, hr = ctx.c, ctx.h, ctx.l, ctx.hour
    LH = ctx.pdh if level == "pd" else ctx.pwh
    LL = ctx.pdl if level == "pd" else ctx.pwl
    for i in range(1, n):
        if not (hours[0] <= hr[i] <= hours[1]) or np.isnan(ctx.atr_d[i]) or np.isnan(LH[i]):
            continue
        a = ctx.atr_d[i]
        ph, pl = LH[i], LL[i]
        mid = (ph + pl) / 2
        if h[i] >= ph + pen * a and c[i] < ph and c[i - 1] <= ph:
            side, sl = "short", h[i] + buf * a
            dist = sl - c[i]
            tgt = {"mid": mid, "opp": pl}.get(tp_mode, c[i] - rr * dist)
            if tp_mode != "rr" and c[i] - tgt < 0.5 * dist:
                tgt = c[i] - rr * dist
        elif l[i] <= pl - pen * a and c[i] > pl and c[i - 1] >= pl:
            side, sl = "long", l[i] - buf * a
            dist = c[i] - sl
            tgt = {"mid": mid, "opp": ph}.get(tp_mode, c[i] + rr * dist)
            if tp_mode != "rr" and tgt - c[i] < 0.5 * dist:
                tgt = c[i] + rr * dist
        else:
            continue
        if dist <= 0:
            continue
        sigs[i] = _E(side, sl, tgt, max_hold=max_hold, exit_hour=exit_hour,
                     meta=dict(idea=f"{level}_sweep"))
    return sigs


def build_pw_sweep_reversal(df, **kw):
    kw.setdefault("max_hold", 24)
    return build_pd_sweep_reversal(df, level="pw", **kw)


# ---------------------------------------------- 4 prior-day break continuation
def build_pd_break_continuation(df, hours=(10, 18), buf=0.05, sl_mode="level", sl_atr=0.3,
                                rr=1.5, tp_mode="rr", exit_hour=23, max_hold=None):
    """First close of the day beyond prior-day high/low by buf x ATR20d (previous
    bar closed inside) -> go with it. SL: 'level' = back inside by sl_atr x ATR20d,
    'bar' = this bar's opposite extreme. TP: rr x stop or 'atr' = 1 ATR20d from level."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c, h, l, hr = ctx.c, ctx.h, ctx.l, ctx.hour
    for i in range(1, n):
        if not (hours[0] <= hr[i] <= hours[1]) or np.isnan(ctx.atr_d[i]) or np.isnan(ctx.pdh[i]):
            continue
        a, ph, pl = ctx.atr_d[i], ctx.pdh[i], ctx.pdl[i]
        if c[i] > ph + buf * a and c[i - 1] <= ph:
            side, lvl = "long", ph
            sl = lvl - sl_atr * a if sl_mode == "level" else l[i] - 0.05 * a
        elif c[i] < pl - buf * a and c[i - 1] >= pl:
            side, lvl = "short", pl
            sl = lvl + sl_atr * a if sl_mode == "level" else h[i] + 0.05 * a
        else:
            continue
        dist = abs(c[i] - sl)
        if dist <= 0:
            continue
        if tp_mode == "atr":
            tp = lvl + a if side == "long" else lvl - a
        else:
            tp = c[i] + rr * dist if side == "long" else c[i] - rr * dist
        if (side == "long" and tp <= c[i]) or (side == "short" and tp >= c[i]):
            continue
        sigs[i] = _E(side, sl, tp, exit_hour=exit_hour, max_hold=max_hold, meta=dict(idea="pd_break"))
    return _one_per_day(sigs, ctx)


# ------------------------------------------------------------- 6 pivot touch
def build_pivot_touch(df, hours=(8, 20), tol=0.05, buf=0.15, lvl="r1s1", tp_mode="piv",
                      rr=1.5, max_hold=12):
    """Floor pivots from prior-day OHLC. Bar touches R1 (S1) [or R2/S2] within tol x
    ATR20d and closes back below (above) it -> fade toward the central pivot P
    (tp 'piv', must be >= 0.5R else rr), or rr x stop."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c, h, l, hr = ctx.c, ctx.h, ctx.l, ctx.hour
    R = ctx.r1 if lvl == "r1s1" else ctx.r2
    S = ctx.s1 if lvl == "r1s1" else ctx.s2
    for i in range(1, n):
        if not (hours[0] <= hr[i] <= hours[1]) or np.isnan(ctx.atr_d[i]) or np.isnan(R[i]):
            continue
        a = ctx.atr_d[i]
        if h[i] >= R[i] - tol * a and c[i] < R[i] and c[i - 1] < R[i]:
            side, sl = "short", max(h[i], R[i]) + buf * a
            dist = sl - c[i]
            tp = ctx.piv[i] if tp_mode == "piv" else c[i] - rr * dist
            if c[i] - tp < 0.5 * dist:
                tp = c[i] - rr * dist
        elif l[i] <= S[i] + tol * a and c[i] > S[i] and c[i - 1] > S[i]:
            side, sl = "long", min(l[i], S[i]) - buf * a
            dist = c[i] - sl
            tp = ctx.piv[i] if tp_mode == "piv" else c[i] + rr * dist
            if tp - c[i] < 0.5 * dist:
                tp = c[i] + rr * dist
        else:
            continue
        if dist <= 0:
            continue
        sigs[i] = _E(side, sl, tp, max_hold=max_hold, meta=dict(idea="pivot_touch"))
    return _one_per_day(sigs, ctx)


# --------------------------------------------------------- 7 monday gap fade
def build_monday_gap_fade(df, min_gap=0.15, max_gap=1.5, sl_mult=1.0, max_hold=24,
                          tp_frac=1.0, bars_after=0):
    """Monday's first bar opens >= min_gap x ATR20d away from Friday's close -> trade
    toward the fill at the close of bar `bars_after` of the day. TP = Friday close
    (tp_frac of the remaining gap), SL = sl_mult x gap beyond the Monday open."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c = ctx.c
    for i in range(n):
        if ctx.wd[i] != 0 or ctx.bar_in_day[i] != bars_after or np.isnan(ctx.atr_d[i]) or np.isnan(ctx.pdc[i]):
            continue
        gap = ctx.day_open[i] - ctx.pdc[i]
        a = ctx.atr_d[i]
        if abs(gap) < min_gap * a or abs(gap) > max_gap * a:
            continue
        if gap > 0:   # gap up -> short toward Friday close
            side = "short"
            tp = c[i] - tp_frac * (c[i] - ctx.pdc[i])
            sl = ctx.day_open[i] + sl_mult * abs(gap)
            if tp >= c[i] or sl <= c[i]:
                continue
        else:
            side = "long"
            tp = c[i] + tp_frac * (ctx.pdc[i] - c[i])
            sl = ctx.day_open[i] - sl_mult * abs(gap)
            if tp <= c[i] or sl >= c[i]:
                continue
        sigs[i] = _E(side, sl, tp, max_hold=max_hold, meta=dict(idea="monday_gap"))
    return sigs


# ---------------------------------------------------------------- 8 fix fade
def build_fix_fade(df, run_start=15, fix_bar=17, thr=0.3, sl_atr=0.3, tp_mode="half",
                   rr=1.0, exit_hour=22):
    """Move from the open of the run_start bar to the close of the fix bar (17:00
    bar closes at 18:00 = 4pm London fix). If > thr x ATR20d, fade it at the fix
    close. SL = sl_atr x ATR20d beyond entry. TP: 'half' = half the run retraced,
    'full', or rr x stop."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c, hr, mn = ctx.c, ctx.hour, ctx.minute
    run_open = np.full(n, np.nan)
    cur = np.nan; cur_day = None
    for i in range(n):
        if ctx.day[i] != cur_day:
            cur_day = ctx.day[i]; cur = np.nan
        if hr[i] == run_start and mn[i] == 0:
            cur = ctx.o[i]
        run_open[i] = cur
    for i in range(1, n):
        if hr[i] != fix_bar or not ctx.hour_close[i] or np.isnan(run_open[i]) or np.isnan(ctx.atr_d[i]):
            continue
        a = ctx.atr_d[i]
        move = c[i] - run_open[i]
        if abs(move) < thr * a:
            continue
        if move > 0:
            side = "short"; sl = c[i] + sl_atr * a
            tp = c[i] - (0.5 * move if tp_mode == "half" else move if tp_mode == "full" else rr * sl_atr * a)
        else:
            side = "long"; sl = c[i] - sl_atr * a
            tp = c[i] + (0.5 * -move if tp_mode == "half" else -move if tp_mode == "full" else rr * sl_atr * a)
        sigs[i] = _E(side, sl, tp, exit_hour=exit_hour, meta=dict(idea="fix_fade"))
    return sigs


# -------------------------------------------------- 9 london open reversal
def build_london_open_reversal(df, bar_hour=10, thr=0.35, buf=0.1, tp_mode="half",
                               rr=1.0, exit_hour=18, nbars=1):
    """The first `nbars` bars from bar_hour (London open) move > thr x ATR20d from
    their open -> fade at the close of the last one. SL beyond the move's extreme
    + buf x ATR20d. TP: 'half' / 'full' retrace of the move, or rr x stop."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c, h, l, hr, mn = ctx.c, ctx.h, ctx.l, ctx.hour, ctx.minute
    bpb = 2 if (ctx.minute != 0).any() else 1     # bars per hour (M30 vs H1)
    for i in range(n):
        if not (hr[i] == bar_hour and mn[i] == 0):
            continue
        j = i + nbars * bpb - 1
        if j >= n or ctx.day[j] != ctx.day[i] or np.isnan(ctx.atr_d[j]):
            continue
        a = ctx.atr_d[j]
        move = c[j] - ctx.o[i]
        if abs(move) < thr * a:
            continue
        hi, lo = h[i:j + 1].max(), l[i:j + 1].min()
        if move > 0:
            side = "short"; sl = hi + buf * a
            dist = sl - c[j]
            tp = c[j] - (0.5 * move if tp_mode == "half" else move if tp_mode == "full" else rr * dist)
        else:
            side = "long"; sl = lo - buf * a
            dist = c[j] - sl
            tp = c[j] + (0.5 * -move if tp_mode == "half" else -move if tp_mode == "full" else rr * dist)
        if dist <= 0:
            continue
        sigs[j] = _E(side, sl, tp, exit_hour=exit_hour, meta=dict(idea="ldn_open_rev"))
    return sigs


# ---------------------------------------------- 10 trend day continuation
def build_trend_day_continuation(df, hour=15, k=1.0, pos=0.8, sl_mode="mid", exit_hour=23,
                                 tp_rr=None):
    """At the close of the `hour` bar, if today's range so far > k x ATR20d and the
    close sits in the top (bottom) `pos` fraction of the day range -> go with the
    trend. SL = day midpoint ('mid') or the day open ('open'). Exit at exit_hour
    (end of the server day) or tp_rr x stop."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c, hr = ctx.c, ctx.hour
    for i in range(n):
        if hr[i] != hour or not ctx.hour_close[i] or np.isnan(ctx.atr_d[i]):
            continue
        a = ctx.atr_d[i]
        rh, rl = ctx.run_h[i], ctx.run_l[i]
        rng = rh - rl
        if rng < k * a:
            continue
        where = (c[i] - rl) / rng
        if where >= pos:
            side = "long"
            sl = (rh + rl) / 2 if sl_mode == "mid" else min(ctx.day_open[i], c[i] - 0.1 * a)
        elif where <= 1 - pos:
            side = "short"
            sl = (rh + rl) / 2 if sl_mode == "mid" else max(ctx.day_open[i], c[i] + 0.1 * a)
        else:
            continue
        dist = abs(c[i] - sl)
        if dist <= 0:
            continue
        tp = None
        if tp_rr:
            tp = c[i] + tp_rr * dist if side == "long" else c[i] - tp_rr * dist
        sigs[i] = _E(side, sl, tp, exit_hour=exit_hour, meta=dict(idea="trend_day"))
    return sigs


# -------------------------------------------------------- 11 range day fade
def build_range_day_fade(df, start=13, end=20, f=0.6, tol=0.1, buf=0.15, tp_mode="mid",
                         exit_hour=23, max_hold=None):
    """Between start..end o'clock the day's range so far is < f x ATR20d (a range
    day) and the bar closes within tol x range of the day high (low) -> fade to the
    day midpoint ('mid') or the opposite extreme ('opp'). SL beyond the day extreme
    + buf x ATR20d."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c, hr = ctx.c, ctx.hour
    for i in range(n):
        if not (start <= hr[i] <= end) or np.isnan(ctx.atr_d[i]):
            continue
        a = ctx.atr_d[i]
        rh, rl = ctx.run_h[i], ctx.run_l[i]
        rng = rh - rl
        if rng > f * a or rng < 0.2 * a:
            continue
        mid = (rh + rl) / 2
        if c[i] >= rh - tol * rng:
            side, sl = "short", rh + buf * a
            tp = mid if tp_mode == "mid" else rl
        elif c[i] <= rl + tol * rng:
            side, sl = "long", rl - buf * a
            tp = mid if tp_mode == "mid" else rh
        else:
            continue
        dist = abs(c[i] - sl)
        if dist <= 0 or abs(tp - c[i]) < 0.3 * dist:
            continue
        sigs[i] = _E(side, sl, tp, exit_hour=exit_hour, max_hold=max_hold, meta=dict(idea="range_day"))
    return _one_per_day(sigs, ctx)


# ------------------------------------------------------ 12 inside / NR break
def build_inside_nr_break(df, kind="inside", sl_mode="opp", rr=2.0, max_hold=3, trail=None):
    """After an inside day (kind='inside') or NR7 day (kind='nr7'), the first close
    beyond that day's high/low -> breakout (works on D1 and intraday via daily
    levels). SL = opposite side of the narrow day ('opp') or its midpoint ('mid').
    TP = rr x stop, or None with trail = ATR14-multiple trailing stop."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c = ctx.c
    a14 = atr(df, 14)
    flag = ctx.inside if kind == "inside" else ctx.nr7
    for i in range(1, n):
        if not flag[i] or np.isnan(ctx.pdh[i]):
            continue
        ph, pl = ctx.pdh[i], ctx.pdl[i]
        if c[i] > ph and c[i - 1] <= ph:
            side = "long"; sl = pl if sl_mode == "opp" else (ph + pl) / 2
        elif c[i] < pl and c[i - 1] >= pl:
            side = "short"; sl = ph if sl_mode == "opp" else (ph + pl) / 2
        else:
            continue
        dist = abs(c[i] - sl)
        if dist <= 0:
            continue
        tp = None if trail else (c[i] + rr * dist if side == "long" else c[i] - rr * dist)
        mg = _trail(a14, trail) if trail else None
        sigs[i] = _E(side, sl, tp, max_hold=max_hold, manage=mg, meta=dict(idea=f"{kind}_break"))
    return _one_per_day(sigs, ctx)


def _trail(a14, mult):
    def manage(df, i, pos):
        c = float(df["close"].iloc[i])
        if pos["side"] == "long":
            ns = c - mult * a14[i]
            return ns if ns > pos["sl"] else None
        ns = c + mult * a14[i]
        return ns if ns < pos["sl"] else None
    return manage


# ---------------------------------------------------------- 13 D1 reversal
def build_d1_reversal(df, thr=1.2, sl_atr=1.0, hold=2, tp_atr=None, use_range=False):
    """Fade an outsized bar: |close - prev close| > thr x ATR14 (or the bar closes
    in the extreme 20% of a range > thr x ATR14 when use_range) -> enter the other
    way at the close. SL = sl_atr x ATR14; exit after `hold` bars or tp_atr."""
    a14 = atr(df, 14)
    c, h, l = _arr(df, "close"), _arr(df, "high"), _arr(df, "low")
    n = len(df)
    sigs = [None] * n
    for i in range(15, n):
        a = a14[i - 1]
        if use_range:
            rng = h[i] - l[i]
            if rng < thr * a:
                continue
            where = (c[i] - l[i]) / rng
            if where < 0.2:
                side = "long"
            elif where > 0.8:
                side = "short"
            else:
                continue
        else:
            mv = c[i] - c[i - 1]
            if abs(mv) < thr * a:
                continue
            side = "long" if mv < 0 else "short"
        sl = c[i] - sl_atr * a if side == "long" else c[i] + sl_atr * a
        tp = None
        if tp_atr:
            tp = c[i] + tp_atr * a if side == "long" else c[i] - tp_atr * a
        sigs[i] = _E(side, sl, tp, max_hold=hold, meta=dict(idea="d1_reversal"))
    return sigs


# ------------------------------------------------------ 14 round number fade
def build_round_number_fade(df, step=0.005, tol=0.05, buf=0.15, rr=1.0, max_hold=8,
                            hours=(8, 20), approach=0.3):
    """Price approaches a round level (multiples of `step`, e.g. 00/50 pips) from
    >= approach x ATR20d away over the last 3 bars, touches it within tol x ATR20d
    and closes back on the near side -> fade. SL beyond the level + buf x ATR20d."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c, h, l, hr = ctx.c, ctx.h, ctx.l, ctx.hour
    for i in range(3, n):
        if not (hours[0] <= hr[i] <= hours[1]) or np.isnan(ctx.atr_d[i]):
            continue
        a = ctx.atr_d[i]
        up = np.ceil(c[i] / step) * step
        dn = np.floor(c[i] / step) * step
        if h[i] >= up - tol * a and c[i] < up and c[i - 3] <= up - approach * a:
            side, sl = "short", max(h[i], up) + buf * a
            dist = sl - c[i]; tp = c[i] - rr * dist
        elif l[i] <= dn + tol * a and c[i] > dn and c[i - 3] >= dn + approach * a:
            side, sl = "long", min(l[i], dn) - buf * a
            dist = c[i] - sl; tp = c[i] + rr * dist
        else:
            continue
        if dist <= 0:
            continue
        sigs[i] = _E(side, sl, tp, max_hold=max_hold, meta=dict(idea="round_fade"))
    return sigs


# ------------------------------------------------- 15 weekly open reversion
def build_weekly_open_reversion(df, days=(2, 3), thr=1.5, sl_atr=1.0, tp_frac=1.0,
                                hour=None, max_hold=48):
    """On weekday in `days` (0=Mon) [at `hour` if given, else every bar] price is
    > thr x ATR20d from the Monday open -> fade toward the weekly open (TP = tp_frac
    of the distance). SL = sl_atr x ATR20d. One trade per week."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c = ctx.c
    last_week = None
    for i in range(n):
        if ctx.wd[i] not in days or np.isnan(ctx.atr_d[i]) or np.isnan(ctx.wk_open[i]):
            continue
        if hour is not None and ctx.hour[i] != hour:
            continue
        if ctx.week[i] == last_week:
            continue
        a = ctx.atr_d[i]
        d = c[i] - ctx.wk_open[i]
        if abs(d) < thr * a:
            continue
        if d > 0:
            side = "short"; sl = c[i] + sl_atr * a; tp = c[i] - tp_frac * d
        else:
            side = "long"; sl = c[i] - sl_atr * a; tp = c[i] - tp_frac * d
        sigs[i] = _E(side, sl, tp, max_hold=max_hold, meta=dict(idea="wk_open_rev"))
        last_week = ctx.week[i]
    return sigs


# ---------------------------------------------------- 16 day open reversion
def build_day_open_reversion(df, start=12, end=19, thr=0.8, sl_atr=0.4, tp_frac=1.0,
                             exit_hour=23):
    """Between start..end the close is > thr x ATR20d from the day open -> fade back
    toward the day open (TP = tp_frac of the distance). SL = sl_atr x ATR20d.
    One trade per day; exit at exit_hour."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c, hr = ctx.c, ctx.hour
    for i in range(n):
        if not (start <= hr[i] <= end) or np.isnan(ctx.atr_d[i]):
            continue
        a = ctx.atr_d[i]
        d = c[i] - ctx.day_open[i]
        if abs(d) < thr * a:
            continue
        if d > 0:
            side = "short"; sl = c[i] + sl_atr * a; tp = c[i] - tp_frac * d
        else:
            side = "long"; sl = c[i] - sl_atr * a; tp = c[i] - tp_frac * d
        sigs[i] = _E(side, sl, tp, exit_hour=exit_hour, meta=dict(idea="day_open_rev"))
    return _one_per_day(sigs, ctx)


# ------------------------------------------- 17 NY overlap continuation
def build_ny_overlap_continuation(df, ldn_start=10, entry_hour=15, thr=0.4, sl_mode="mid",
                                  sl_atr=0.3, exit_hour=20, tp_rr=None):
    """London-session direction (open of the ldn_start bar -> close of the
    entry_hour bar) > thr x ATR20d -> carry it into the NY overlap. SL = midpoint of
    the London move ('mid') or sl_atr x ATR20d ('atr'). Exit at exit_hour or tp_rr."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c, hr, mn = ctx.c, ctx.hour, ctx.minute
    ldn_open = np.full(n, np.nan); cur = np.nan; cd = None
    for i in range(n):
        if ctx.day[i] != cd:
            cd = ctx.day[i]; cur = np.nan
        if hr[i] == ldn_start and mn[i] == 0:
            cur = ctx.o[i]
        ldn_open[i] = cur
    for i in range(n):
        if hr[i] != entry_hour or not ctx.hour_close[i] or np.isnan(ldn_open[i]) or np.isnan(ctx.atr_d[i]):
            continue
        a = ctx.atr_d[i]
        mv = c[i] - ldn_open[i]
        if abs(mv) < thr * a:
            continue
        side = "long" if mv > 0 else "short"
        if sl_mode == "mid":
            sl = ldn_open[i] + mv / 2
        else:
            sl = c[i] - sl_atr * a if side == "long" else c[i] + sl_atr * a
        dist = abs(c[i] - sl)
        if dist <= 0:
            continue
        tp = None
        if tp_rr:
            tp = c[i] + tp_rr * dist if side == "long" else c[i] - tp_rr * dist
        sigs[i] = _E(side, sl, tp, exit_hour=exit_hour, meta=dict(idea="ny_overlap"))
    return sigs


# ----------------------------------------------------- 18 friday week fade
def build_friday_week_fade(df, hour=16, thr=1.0, sl_atr=0.6, tp_frac=0.5, exit_hour=23):
    """Friday at `hour`: the week's move (Monday open -> now) exceeds thr x ATR20d
    -> fade it into the weekly close (TP = tp_frac of the move, SL sl_atr x ATR20d,
    flat at exit_hour Friday)."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    c = ctx.c
    for i in range(n):
        if ctx.wd[i] != 4 or ctx.hour[i] != hour or not ctx.hour_close[i]:
            continue
        if np.isnan(ctx.atr_d[i]) or np.isnan(ctx.wk_open[i]):
            continue
        a = ctx.atr_d[i]
        d = c[i] - ctx.wk_open[i]
        if abs(d) < thr * a:
            continue
        if d > 0:
            side = "short"; sl = c[i] + sl_atr * a; tp = c[i] - tp_frac * d
        else:
            side = "long"; sl = c[i] - sl_atr * a; tp = c[i] - tp_frac * d
        sigs[i] = _E(side, sl, tp, exit_hour=exit_hour, meta=dict(idea="friday_fade"))
    return sigs


# ----------------------------------------------------------- 19 rollover dip
def build_rollover_dip(df, entry_hour=23, exit_hour=1, sl_atr=0.5, min_drop=0.0):
    """Buy the close of the 23:00 bar (if it fell >= min_drop x ATR20d) and sell at
    the close of the 01:00 bar. SL = sl_atr x ATR20d. A thin-liquidity artefact
    (bid dips into rollover); kept to show it is NOT executable at real spreads."""
    ctx = Ctx(df)
    n = len(df)
    sigs = [None] * n
    for i in range(n):
        if ctx.hour[i] != entry_hour or not ctx.hour_close[i] or np.isnan(ctx.atr_d[i]):
            continue
        if ctx.o[i] - ctx.c[i] < min_drop * ctx.atr_d[i]:
            continue
        sigs[i] = _E("long", ctx.c[i] - sl_atr * ctx.atr_d[i], None, exit_hour=exit_hour,
                     meta=dict(idea="rollover"))
    return sigs


BUILDERS = {k[6:]: v for k, v in list(globals().items()) if k.startswith("build_") and callable(v)}
