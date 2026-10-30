"""Round-3 European index strategies (UK100 FRA40/F40 IT40 DE40, +ESP35 cross-check).

All builders: build_<name>(df, **params) -> list[Entry|None] of len(df), causal
(bar i uses rows <= i only). Server time is EET: Xetra/Euronext cash
10:00-18:30, US cash open 16:30, US close 23:00.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from research.prop.harness import Entry

# --------------------------------------------------------------------------- context

def _ctx(df: pd.DataFrame, atr_n: int = 14, datr_n: int = 14) -> dict:
    t = pd.DatetimeIndex(df["time"])
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n = len(df)
    hm = (t.hour + t.minute / 60.0).to_numpy()
    day = t.normalize().to_numpy()
    new_day = np.r_[True, day[1:] != day[:-1]]
    day_id = np.cumsum(new_day) - 1
    wd = t.weekday.to_numpy()
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr = pd.Series(tr).rolling(atr_n, min_periods=atr_n).mean().to_numpy()
    s_day = pd.Series(day_id)
    dhi = pd.Series(h).groupby(s_day).cummax().to_numpy()
    dlo = pd.Series(l).groupby(s_day).cummin().to_numpy()
    first_idx = np.where(new_day)[0]
    d_open = o[first_idx][day_id]
    nd = len(first_idx)
    last_idx = np.r_[first_idx[1:] - 1, n - 1]
    dayH = np.array([h[a:b + 1].max() for a, b in zip(first_idx, last_idx)])
    dayL = np.array([l[a:b + 1].min() for a, b in zip(first_idx, last_idx)])
    dayC = c[last_idx]
    cashC = np.full(nd, np.nan)
    for k, (a, b) in enumerate(zip(first_idx, last_idx)):
        seg = hm[a:b + 1]
        m = np.where(seg <= 18.5)[0]
        if len(m):
            cashC[k] = c[a + m[-1]]
    rng = dayH - dayL
    datr_d = pd.Series(rng).rolling(datr_n, min_periods=5).mean().to_numpy()
    prev = day_id - 1
    ok = prev >= 0

    def al(arr):
        out = np.full(n, np.nan)
        out[ok] = arr[prev[ok]]
        return out
    ctx = dict(n=n, t=t, o=o, h=h, l=l, c=c, hm=hm, wd=wd, day_id=day_id, new_day=new_day,
               atr=atr, dhi=dhi, dlo=dlo, d_open=d_open,
               pdh=al(dayH), pdl=al(dayL), pdc=al(dayC), pcash=al(cashC), datr=al(datr_d),
               first_idx=first_idx)
    ema = pd.Series(dayC).ewm(span=50, adjust=False).mean().to_numpy()
    ctx["pd_trend"] = al(np.sign(dayC - ema))
    return ctx


def _trend_ok(ctx, i, side, trend):
    if trend is None:
        return True
    tr = ctx["pd_trend"][i]
    if np.isnan(tr):
        return False
    want = 1 if side == "long" else -1
    return (tr == want) if trend == "with" else (tr == -want)


def _session_open_idx(cx, i, from_hm=10.0):
    """Index of today's bar at from_hm (walking back from i), or None."""
    j = i
    while j > 0 and cx["day_id"][j - 1] == cx["day_id"][i] and cx["hm"][j - 1] >= from_hm:
        j -= 1
    return j if abs(cx["hm"][j] - from_hm) < 0.01 else None


def _bad(side, c, sl, tp):
    if side == "long":
        return sl >= c or (tp is not None and tp <= c)
    return sl <= c or (tp is not None and tp >= c)


# --------------------------------------------------------------------------- 1. gap fade / continuation

def build_gap(df, mode="fade", gmin=0.25, gmax=1.5, sl_mult=1.0, tp="fill", tp_r=1.5,
              entry_hm=10.0, exit_hour=18, trend=None, sides="both"):
    """Cash-open gap vs yesterday's cash close (18:30) in daily-ATR units.
    fade: trade toward the fill, TP = prev cash close (or tp_r R); cont: with
    the gap. Enter at the close of the entry_hm bar, flat at exit_hour."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    for i in range(cx["n"]):
        if abs(cx["hm"][i] - entry_hm) > 0.01:
            continue
        pc, da = cx["pcash"][i], cx["datr"][i]
        if np.isnan(pc) or np.isnan(da) or da <= 0:
            continue
        j = _session_open_idx(cx, i)
        if j is None:
            continue
        gap = cx["o"][j] - pc
        g = abs(gap) / da
        if g < gmin or g > gmax:
            continue
        if mode == "fade":
            side = "short" if gap > 0 else "long"
        else:
            side = "long" if gap > 0 else "short"
        if sides != "both" and side != sides:
            continue
        if not _trend_ok(cx, i, side, trend):
            continue
        c = cx["c"][i]
        dist = max(abs(gap), 0.3 * da) * sl_mult
        if mode == "fade":
            sl = c + dist if side == "short" else c - dist
            tpv = pc if tp == "fill" else (c - tp_r * dist if side == "short" else c + tp_r * dist)
        else:
            sl = c - dist if side == "long" else c + dist
            tpv = (c + tp_r * dist if side == "long" else c - tp_r * dist) if tp_r else None
        if _bad(side, c, sl, tpv):
            continue
        out[i] = Entry(side, float(sl), None if tpv is None else float(tpv),
                       exit_hour=exit_hour, meta=dict(gap=round(g, 2)))
    return out


# --------------------------------------------------------------------------- 2. US-open shock fade

def build_us_open_fade(df, k=1.0, bar_hm=16.5, sl_mult=1.0, tp="retrace", tp_r=1.0,
                       exit_hour=18, trend=None, sides="both", mode="fade"):
    """The bar containing the 16:30 US cash open moves > k x bar ATR; at its
    close fade it (TP = that bar's open, SL beyond its extreme)."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    for i in range(cx["n"]):
        if abs(cx["hm"][i] - bar_hm) > 0.01:
            continue
        a = cx["atr"][i]
        if np.isnan(a) or a <= 0:
            continue
        mv = cx["c"][i] - cx["o"][i]
        if abs(mv) < k * a:
            continue
        up = mv > 0
        side = ("short" if up else "long") if mode == "fade" else ("long" if up else "short")
        if sides != "both" and side != sides:
            continue
        if not _trend_ok(cx, i, side, trend):
            continue
        c = cx["c"][i]
        ext = cx["h"][i] if up else cx["l"][i]
        dist = max(abs(ext - c), 0.3 * a) * sl_mult + 0.25 * a
        if mode == "fade":
            sl = c + dist if side == "short" else c - dist
            tpv = cx["o"][i] if tp == "retrace" else (c - tp_r * dist if side == "short" else c + tp_r * dist)
        else:
            sl = c - dist if side == "long" else c + dist
            tpv = c + tp_r * dist if side == "long" else c - tp_r * dist
        if _bad(side, c, sl, tpv):
            continue
        out[i] = Entry(side, float(sl), float(tpv), exit_hour=exit_hour)
    return out


# --------------------------------------------------------------------------- 3. closing-auction fade / follow of the day's drift

def build_close_fade(df, k=0.3, entry_hm=17.5, hold=1, sl_datr=0.5, mode="fade", trend=None,
                     sides="both", from_hm=10.0):
    """At the close of the entry_hm bar the cash session has drifted (10:00
    open -> now) by > k daily ATR. fade: against it into the 18:30 close;
    follow: with it. Pure time exit (hold bars)."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    for i in range(cx["n"]):
        if abs(cx["hm"][i] - entry_hm) > 0.01:
            continue
        da = cx["datr"][i]
        if np.isnan(da) or da <= 0:
            continue
        j = _session_open_idx(cx, i, from_hm)
        if j is None:
            continue
        drift = cx["c"][i] - cx["o"][j]
        if abs(drift) < k * da:
            continue
        up = drift > 0
        side = ("short" if up else "long") if mode == "fade" else ("long" if up else "short")
        if sides != "both" and side != sides:
            continue
        if not _trend_ok(cx, i, side, trend):
            continue
        c = cx["c"][i]
        sl = c + sl_datr * da if side == "short" else c - sl_datr * da
        out[i] = Entry(side, float(sl), None, max_hold=hold, meta=dict(drift=round(drift / da, 2)))
    return out


# --------------------------------------------------------------------------- 4. overnight bias (Unger-style)

def build_overnight(df, entry_hm=18.5, exit_hour=10, side="long", sl_datr=1.0, skip_wd=(4,),
                    cond=None, tp_datr=None, trend=None):
    """Long (or short) at the close of the entry_hm bar, flat at the close of
    the next day's exit_hour bar. cond: down_day / up_day (today's cash
    session), down_vs_pdc / up_vs_pdc (vs yesterday's close)."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    for i in range(cx["n"]):
        if abs(cx["hm"][i] - entry_hm) > 0.01 or cx["wd"][i] in skip_wd:
            continue
        da = cx["datr"][i]
        if np.isnan(da) or da <= 0:
            continue
        if cond is not None:
            j = _session_open_idx(cx, i)
            if j is None:
                continue
            ses = cx["c"][i] - cx["o"][j]
            if cond == "down_day" and ses >= 0:
                continue
            if cond == "up_day" and ses <= 0:
                continue
            if cond == "down_vs_pdc" and not cx["c"][i] < cx["pdc"][i]:
                continue
            if cond == "up_vs_pdc" and not cx["c"][i] > cx["pdc"][i]:
                continue
        if not _trend_ok(cx, i, side, trend):
            continue
        c = cx["c"][i]
        sl = c - sl_datr * da if side == "long" else c + sl_datr * da
        tp = None
        if tp_datr:
            tp = c + tp_datr * da if side == "long" else c - tp_datr * da
        out[i] = Entry(side, float(sl), tp, exit_hour=exit_hour)
    return out


# --------------------------------------------------------------------------- 5. opening range breakout (generic, Klatt-style)

def build_orb(df, rs=10.0, re=10.5, te=12.5, exit_hour=18, sl="far", sl_frac=1.0, tp_r=2.0,
              trend=None, sides="both", min_rng=0.0, max_rng=9.0):
    """Range = bars with rs <= hm < re. First close beyond the range (until te)
    enters; SL far side / midpoint / sl_frac x range; TP tp_r x risk; flat at
    exit_hour. One trade per day."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    cur_day, rh, rl, traded = -1, -np.inf, np.inf, False
    for i in range(cx["n"]):
        if cx["day_id"][i] != cur_day:
            cur_day, rh, rl, traded = cx["day_id"][i], -np.inf, np.inf, False
        hm = cx["hm"][i]
        if rs <= hm < re:
            rh, rl = max(rh, cx["h"][i]), min(rl, cx["l"][i])
            continue
        if hm < re or hm > te or traded or not np.isfinite(rh):
            continue
        da = cx["datr"][i]
        if np.isnan(da) or da <= 0:
            continue
        rng = rh - rl
        if rng < min_rng * da or rng > max_rng * da:
            continue
        c = cx["c"][i]
        side = "long" if c > rh else ("short" if c < rl else None)
        if side is None:
            continue
        traded = True
        if sides != "both" and side != sides:
            continue
        if not _trend_ok(cx, i, side, trend):
            continue
        if sl == "far":
            slv = rl if side == "long" else rh
        elif sl == "mid":
            slv = (rh + rl) / 2
        else:
            slv = c - sl_frac * rng if side == "long" else c + sl_frac * rng
        risk = abs(c - slv)
        if risk <= 0:
            continue
        tp = (c + tp_r * risk if side == "long" else c - tp_r * risk) if tp_r else None
        if _bad(side, c, slv, tp):
            continue
        out[i] = Entry(side, float(slv), tp, exit_hour=exit_hour)
    return out


# --------------------------------------------------------------------------- 6. opening-range failure (10-11 reversal)

def build_or_fail(df, rs=10.0, re=10.5, te=12.0, exit_hour=18, tp="far", tp_r=1.5, sl_pad=0.25,
                  trend=None, sides="both"):
    """Price closes outside the opening range, then a later bar (by te) closes
    back inside: fade toward the far edge of the range."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    cur_day, rh, rl, brk, ext, traded = -1, -np.inf, np.inf, None, None, False
    for i in range(cx["n"]):
        if cx["day_id"][i] != cur_day:
            cur_day, rh, rl, brk, ext, traded = cx["day_id"][i], -np.inf, np.inf, None, None, False
        hm = cx["hm"][i]
        if rs <= hm < re:
            rh, rl = max(rh, cx["h"][i]), min(rl, cx["l"][i]); continue
        if hm < re or hm > te or traded or not np.isfinite(rh):
            continue
        c = cx["c"][i]
        a = cx["atr"][i]
        if np.isnan(a):
            continue
        if brk is None:
            if c > rh:
                brk, ext = "up", cx["h"][i]
            elif c < rl:
                brk, ext = "down", cx["l"][i]
            continue
        ext = max(ext, cx["h"][i]) if brk == "up" else min(ext, cx["l"][i])
        if rl <= c <= rh:
            traded = True
            side = "short" if brk == "up" else "long"
            if sides != "both" and side != sides:
                continue
            if not _trend_ok(cx, i, side, trend):
                continue
            sl = ext + sl_pad * a if side == "short" else ext - sl_pad * a
            risk = abs(c - sl)
            if tp == "far":
                tpv = rl if side == "short" else rh
            elif tp == "mid":
                tpv = (rh + rl) / 2
            else:
                tpv = c - tp_r * risk if side == "short" else c + tp_r * risk
            if _bad(side, c, sl, tpv):
                continue
            out[i] = Entry(side, float(sl), float(tpv), exit_hour=exit_hour)
    return out


# --------------------------------------------------------------------------- 7. prior-day high/low: rejection fade or break

def build_pdhl(df, mode="reject", ts=10.0, te=17.0, exit_hour=18, sl_atr=1.0, tp="mid", tp_r=1.5,
               trend=None, sides="both", pad_atr=0.0):
    """reject: a bar trades through yesterday's high (low) but closes back
    inside -> fade, TP = yesterday's midpoint / far side / R multiple.
    break: a bar closes beyond yesterday's high/low -> go with it, SL at the
    level -/+ sl_atr x ATR. One trade per day."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    cur_day, traded = -1, False
    for i in range(cx["n"]):
        if cx["day_id"][i] != cur_day:
            cur_day, traded = cx["day_id"][i], False
        hm = cx["hm"][i]
        if hm < ts or hm > te or traded:
            continue
        pdh, pdl, a = cx["pdh"][i], cx["pdl"][i], cx["atr"][i]
        if np.isnan(pdh) or np.isnan(a) or a <= 0:
            continue
        c, h, l, o = cx["c"][i], cx["h"][i], cx["l"][i], cx["o"][i]
        side = None
        if mode == "reject":
            if h > pdh + pad_atr * a and c < pdh:
                side, lvl = "short", pdh
            elif l < pdl - pad_atr * a and c > pdl:
                side, lvl = "long", pdl
            if side is None:
                continue
            sl = h + sl_atr * a * 0.5 if side == "short" else l - sl_atr * a * 0.5
            risk = abs(c - sl)
            if tp == "mid":
                tpv = (pdh + pdl) / 2
            elif tp == "far":
                tpv = pdl if side == "short" else pdh
            else:
                tpv = c - tp_r * risk if side == "short" else c + tp_r * risk
        else:
            if c > pdh + pad_atr * a and o <= pdh:
                side, lvl = "long", pdh
            elif c < pdl - pad_atr * a and o >= pdl:
                side, lvl = "short", pdl
            if side is None:
                continue
            sl = lvl - sl_atr * a if side == "long" else lvl + sl_atr * a
            risk = abs(c - sl)
            tpv = (c + tp_r * risk if side == "long" else c - tp_r * risk) if tp_r else None
        traded = True
        if sides != "both" and side != sides:
            continue
        if not _trend_ok(cx, i, side, trend):
            continue
        if _bad(side, c, sl, tpv):
            continue
        out[i] = Entry(side, float(sl), None if tpv is None else float(tpv), exit_hour=exit_hour)
    return out


# --------------------------------------------------------------------------- 8. round-number levels

def build_round(df, step=100.0, ts=10.0, te=17.0, exit_hour=18, sl_frac=0.5, tp_frac=1.0,
                trend=None, sides="both", min_body=0.0):
    """Round levels every `step` points. A bar opens on one side of a level
    and closes beyond it by >= min_body x ATR -> continuation, SL sl_frac x
    step back, TP tp_frac x step ahead. One trade per day."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    cur_day, traded = -1, False
    for i in range(cx["n"]):
        if cx["day_id"][i] != cur_day:
            cur_day, traded = cx["day_id"][i], False
        hm = cx["hm"][i]
        if hm < ts or hm > te or traded:
            continue
        a = cx["atr"][i]
        if np.isnan(a) or a <= 0:
            continue
        o, c = cx["o"][i], cx["c"][i]
        lo, hi = min(o, c), max(o, c)
        lvl = np.floor(hi / step) * step
        if not (lo < lvl <= hi):
            continue
        if c > lvl and o < lvl and (c - lvl) >= min_body * a:
            side = "long"
        elif c < lvl and o > lvl and (lvl - c) >= min_body * a:
            side = "short"
        else:
            continue
        traded = True
        if sides != "both" and side != sides:
            continue
        if not _trend_ok(cx, i, side, trend):
            continue
        sl = lvl - sl_frac * step if side == "long" else lvl + sl_frac * step
        tpv = lvl + tp_frac * step if side == "long" else lvl - tp_frac * step
        if _bad(side, c, sl, tpv):
            continue
        out[i] = Entry(side, float(sl), float(tpv), exit_hour=exit_hour)
    return out


def build_round_fade(df, step=100.0, ts=10.0, te=17.0, exit_hour=18, touch_atr=0.1, sl_atr=0.75,
                     tp="step", tp_r=1.0, trend=None, sides="both"):
    """A bar reaches a round level from below (above) but closes back on the
    near side (failed test) -> fade toward level -/+ step/2 (or R multiple)."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    cur_day, traded = -1, False
    for i in range(cx["n"]):
        if cx["day_id"][i] != cur_day:
            cur_day, traded = cx["day_id"][i], False
        hm = cx["hm"][i]
        if hm < ts or hm > te or traded:
            continue
        a = cx["atr"][i]
        if np.isnan(a) or a <= 0:
            continue
        o, c, h, l = cx["o"][i], cx["c"][i], cx["h"][i], cx["l"][i]
        lvl_up = np.ceil(c / step) * step
        lvl_dn = np.floor(c / step) * step
        side = None
        if h >= lvl_up - touch_atr * a and c < lvl_up and o < lvl_up and h < lvl_up + 0.5 * a:
            side, lvl = "short", lvl_up
        elif l <= lvl_dn + touch_atr * a and c > lvl_dn and o > lvl_dn and l > lvl_dn - 0.5 * a:
            side, lvl = "long", lvl_dn
        if side is None:
            continue
        traded = True
        if sides != "both" and side != sides:
            continue
        if not _trend_ok(cx, i, side, trend):
            continue
        sl = lvl + sl_atr * a if side == "short" else lvl - sl_atr * a
        risk = abs(c - sl)
        if tp == "step":
            tpv = lvl - step / 2 if side == "short" else lvl + step / 2
        else:
            tpv = c - tp_r * risk if side == "short" else c + tp_r * risk
        if _bad(side, c, sl, tpv):
            continue
        out[i] = Entry(side, float(sl), float(tpv), exit_hour=exit_hour)
    return out


# --------------------------------------------------------------------------- 9. late-day momentum and pure time windows

def build_late_momentum(df, bar_hm=19.0, k=0.5, hold=1, sl_atr=1.0, mode="follow", sides="both",
                        tp_r=None):
    """The bar at bar_hm moved > k x ATR: follow (or fade) it for `hold` bars."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    for i in range(cx["n"]):
        if abs(cx["hm"][i] - bar_hm) > 0.01:
            continue
        a = cx["atr"][i]
        if np.isnan(a) or a <= 0:
            continue
        mv = cx["c"][i] - cx["o"][i]
        if abs(mv) < k * a:
            continue
        up = mv > 0
        side = ("long" if up else "short") if mode == "follow" else ("short" if up else "long")
        if sides != "both" and side != sides:
            continue
        c = cx["c"][i]
        sl = c - sl_atr * a if side == "long" else c + sl_atr * a
        tp = None
        if tp_r:
            tp = c + tp_r * sl_atr * a if side == "long" else c - tp_r * sl_atr * a
        out[i] = Entry(side, float(sl), tp, max_hold=hold)
    return out


def build_time_window(df, entry_hm=19.0, exit_hour=22, side="long", sl_datr=0.5, wds=(0, 1, 2, 3, 4),
                      cond=None, trend=None, tp_datr=None):
    """Pure session drift: enter at the close of the entry_hm bar, exit at the
    close of the exit_hour bar. cond: session_up/session_down (10:00 open ->
    now), above_pdc/below_pdc."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    for i in range(cx["n"]):
        if abs(cx["hm"][i] - entry_hm) > 0.01 or cx["wd"][i] not in wds:
            continue
        da = cx["datr"][i]
        if np.isnan(da) or da <= 0:
            continue
        if cond in ("session_up", "session_down"):
            j = _session_open_idx(cx, i)
            if j is None:
                continue
            ses = cx["c"][i] - cx["o"][j]
            if (cond == "session_up" and ses <= 0) or (cond == "session_down" and ses >= 0):
                continue
        elif cond == "above_pdc" and not cx["c"][i] > cx["pdc"][i]:
            continue
        elif cond == "below_pdc" and not cx["c"][i] < cx["pdc"][i]:
            continue
        if not _trend_ok(cx, i, side, trend):
            continue
        c = cx["c"][i]
        sl = c - sl_datr * da if side == "long" else c + sl_datr * da
        tp = None
        if tp_datr:
            tp = c + tp_datr * da if side == "long" else c - tp_datr * da
        out[i] = Entry(side, float(sl), tp, exit_hour=exit_hour)
    return out


# --------------------------------------------------------------------------- 10. lunch range -> US open breakout

def build_lunch_break(df, rs=12.5, re=15.5, te=17.5, exit_hour=18, sl="far", tp_r=1.5, trend=None,
                      sides="both", max_rng=0.6):
    """European lunch range (rs..re), break before te, flat at exit_hour."""
    return build_orb(df, rs=rs, re=re, te=te, exit_hour=exit_hour, sl=sl, tp_r=tp_r, trend=trend,
                     sides=sides, max_rng=max_rng)


# --------------------------------------------------------------------------- 11. trend pullback (swing, H1/H4)

def build_pullback(df, ema_fast=20, ema_slow=50, rsi_n=3, rsi_buy=25, rsi_sell=75, sl_atr=2.0,
                   tp_r=2.0, max_hold=30, sides="both", trail_atr=None):
    """Trend = EMA fast vs slow. Pullback = RSI(rsi_n) extreme against it.
    Enter at close; SL = recent 3-bar extreme - 0.25 ATR, no wider than
    sl_atr x ATR; TP tp_r R; time stop max_hold bars; optional ATR trail."""
    c = df["close"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
    s = pd.Series(c)
    ef = s.ewm(span=ema_fast, adjust=False).mean().to_numpy()
    es = s.ewm(span=ema_slow, adjust=False).mean().to_numpy()
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / rsi_n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / rsi_n, adjust=False).mean()
    rsi = (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).to_numpy()
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr = pd.Series(tr).rolling(14).mean().to_numpy()
    lo3 = pd.Series(l).rolling(3).min().to_numpy(); hi3 = pd.Series(h).rolling(3).max().to_numpy()
    n = len(c); out = [None] * n

    def mk_manage(side, k):
        def manage(d_, i, pos):
            a = atr[i]
            if np.isnan(a):
                return None
            if side == "long":
                ns = c[i] - k * a
                return ns if ns > pos["sl"] else None
            ns = c[i] + k * a
            return ns if ns < pos["sl"] else None
        return manage

    for i in range(max(ema_slow, 20), n):
        a = atr[i]
        if np.isnan(a) or a <= 0:
            continue
        if ef[i] > es[i] and rsi[i] < rsi_buy and sides in ("both", "long"):
            sl = max(lo3[i] - 0.25 * a, c[i] - sl_atr * a)
            risk = c[i] - sl
            if risk <= 0:
                continue
            tp = c[i] + tp_r * risk if tp_r else None
            out[i] = Entry("long", float(sl), tp, max_hold=max_hold,
                           manage=mk_manage("long", trail_atr) if trail_atr else None)
        elif ef[i] < es[i] and rsi[i] > rsi_sell and sides in ("both", "short"):
            sl = min(hi3[i] + 0.25 * a, c[i] + sl_atr * a)
            risk = sl - c[i]
            if risk <= 0:
                continue
            tp = c[i] - tp_r * risk if tp_r else None
            out[i] = Entry("short", float(sl), tp, max_hold=max_hold,
                           manage=mk_manage("short", trail_atr) if trail_atr else None)
    return out


# --------------------------------------------------------------------------- 12. daily mean reversion (Connors-style) on D1

def build_d1_meanrev(df, n_down=3, ma=200, sl_atr=2.0, exit="ma5", max_hold=10, side="long",
                     rsi2_max=None, use_trend=True):
    """D1: after n_down consecutive lower closes (and/or RSI2 < rsi2_max) while
    above the ma-day SMA, buy at the close; exit when close > SMA5 (manage)
    or after max_hold days; SL sl_atr x ATR20."""
    c = df["close"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
    s = pd.Series(c)
    sma = s.rolling(ma).mean().to_numpy()
    sma5 = s.rolling(5).mean().to_numpy()
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr = pd.Series(tr).rolling(20).mean().to_numpy()
    d = s.diff()
    up = d.clip(lower=0).ewm(alpha=1 / 2, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / 2, adjust=False).mean()
    rsi2 = (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).to_numpy()
    down = (d < 0).to_numpy(); upk = (d > 0).to_numpy()
    streak = np.zeros(len(c), int); ustreak = np.zeros(len(c), int)
    for i in range(1, len(c)):
        streak[i] = streak[i - 1] + 1 if down[i] else 0
        ustreak[i] = ustreak[i - 1] + 1 if upk[i] else 0
    n = len(c); out = [None] * n

    def manage_long(d_, i, pos):
        return "close" if c[i] > sma5[i] else None

    def manage_short(d_, i, pos):
        return "close" if c[i] < sma5[i] else None

    for i in range(max(ma, 25), n):
        a = atr[i]
        if np.isnan(a) or a <= 0 or np.isnan(sma[i]):
            continue
        if side == "long":
            ok = (streak[i] >= n_down) if n_down else True
            if rsi2_max is not None:
                ok = ok and rsi2[i] < rsi2_max
            if use_trend and not c[i] > sma[i]:
                ok = False
            if ok:
                out[i] = Entry("long", float(c[i] - sl_atr * a), None, max_hold=max_hold,
                               manage=manage_long if exit == "ma5" else None)
        else:
            ok = (ustreak[i] >= n_down) if n_down else True
            if rsi2_max is not None:
                ok = ok and rsi2[i] > 100 - rsi2_max
            if use_trend and not c[i] < sma[i]:
                ok = False
            if ok:
                out[i] = Entry("short", float(c[i] + sl_atr * a), None, max_hold=max_hold,
                               manage=manage_short if exit == "ma5" else None)
    return out


# --------------------------------------------------------------------------- 13. previous-week high/low break with trail

def build_prev_week(df, sl_atr=1.5, trail_atr=3.0, tp_r=None, trend=None, sides="both",
                    friday_flat=True, entry_hours=(10, 18)):
    """First close beyond last week's high/low during cash hours -> go with
    it; SL sl_atr x ATR(14); chandelier trail; Friday flat at 18:00. One
    trade per week per side."""
    t = pd.DatetimeIndex(df["time"])
    c = df["close"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
    iso = t.isocalendar()
    wk = (iso.year.to_numpy() * 100 + iso.week.to_numpy())
    new_wk = np.r_[True, wk[1:] != wk[:-1]]
    wk_id = np.cumsum(new_wk) - 1
    first = np.where(new_wk)[0]; last = np.r_[first[1:] - 1, len(c) - 1]
    wH = np.array([h[a:b + 1].max() for a, b in zip(first, last)])
    wL = np.array([l[a:b + 1].min() for a, b in zip(first, last)])
    prev = wk_id - 1
    pwh = np.full(len(c), np.nan); pwl = np.full(len(c), np.nan)
    ok = prev >= 0
    pwh[ok] = wH[prev[ok]]; pwl[ok] = wL[prev[ok]]
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr = pd.Series(tr).rolling(14).mean().to_numpy()
    hrs = t.hour.to_numpy(); wd = t.weekday.to_numpy()
    cx_tr = _ctx(df)["pd_trend"] if trend else None
    n = len(c); out = [None] * n
    done = {}

    def mk(side):
        def manage(d_, i, pos):
            if friday_flat and wd[i] == 4 and hrs[i] >= 18:
                return "close"
            a = atr[i]
            if np.isnan(a):
                return None
            if side == "long":
                ns = c[i] - trail_atr * a
                return ns if ns > pos["sl"] else None
            ns = c[i] + trail_atr * a
            return ns if ns < pos["sl"] else None
        return manage

    for i in range(n):
        if np.isnan(pwh[i]) or np.isnan(atr[i]) or not (entry_hours[0] <= hrs[i] <= entry_hours[1]):
            continue
        side = "long" if c[i] > pwh[i] else ("short" if c[i] < pwl[i] else None)
        if side is None or (sides != "both" and side != sides):
            continue
        if done.get((wk_id[i], side)):
            continue
        if trend:
            want = 1 if side == "long" else -1
            tr_ = cx_tr[i]
            if np.isnan(tr_) or (trend == "with" and tr_ != want) or (trend == "against" and tr_ != -want):
                continue
        a = atr[i]
        sl = c[i] - sl_atr * a if side == "long" else c[i] + sl_atr * a
        tp = None
        if tp_r:
            tp = c[i] + tp_r * sl_atr * a if side == "long" else c[i] - tp_r * sl_atr * a
        out[i] = Entry(side, float(sl), tp, manage=mk(side))
        done[(wk_id[i], side)] = True
    return out


# --------------------------------------------------------------------------- 14. calendar: Monday session, turn of month

def build_calendar(df, kind="monday", entry_hm=10.0, exit_hour=18, side="long", sl_datr=0.75,
                   tom_days=(-1, 0, 1, 2), hold_days=1, wd=0):
    """kind='weekday': trade weekday `wd`'s cash session. kind='tom': enter at
    entry_hm on trading day k in tom_days (0 = first trading day of the month,
    -1 = last of the previous month, found from the calendar), exit at
    exit_hour `hold_days` trading days later."""
    cx = _ctx(df)
    n = cx["n"]; out = [None] * n
    t = cx["t"]
    if kind in ("monday", "weekday"):
        for i in range(n):
            if cx["wd"][i] != wd or abs(cx["hm"][i] - entry_hm) > 0.01:
                continue
            da = cx["datr"][i]
            if np.isnan(da) or da <= 0:
                continue
            c = cx["c"][i]
            sl = c - sl_datr * da if side == "long" else c + sl_datr * da
            out[i] = Entry(side, float(sl), None, exit_hour=exit_hour)
        return out
    first_idx = cx["first_idx"]
    day_dates = t[first_idx]
    months = (day_dates.year * 12 + day_dates.month).to_numpy()
    new_m = np.r_[True, months[1:] != months[:-1]]
    tdn = np.zeros(len(first_idx), int)
    for k in range(1, len(first_idx)):
        tdn[k] = 0 if new_m[k] else tdn[k - 1] + 1
    day_tag = np.full(len(first_idx), 99, int)
    for k in range(len(first_idx)):
        d0 = day_dates[k]
        if (d0 + pd.offsets.BDay(1)).month != d0.month:
            day_tag[k] = -1
        elif tdn[k] <= 5:
            day_tag[k] = tdn[k]
    day_id = cx["day_id"]
    for i in range(n):
        if abs(cx["hm"][i] - entry_hm) > 0.01:
            continue
        k = day_id[i]
        if day_tag[k] not in tom_days:
            continue
        da = cx["datr"][i]
        if np.isnan(da) or da <= 0:
            continue
        c = cx["c"][i]
        sl = c - sl_datr * da if side == "long" else c + sl_datr * da
        target_day = k + hold_days

        def manage(d_, j, pos, _td=target_day):
            return "close" if (day_id[j] >= _td and cx["hm"][j] >= exit_hour) else None
        out[i] = Entry(side, float(sl), None, manage=manage, max_hold=hold_days * 60)
    return out


# --------------------------------------------------------------------------- 15. compression-day break (NR4 / NR7 / inside day)

def build_compression_break(df, kind="nr4", ts=10.0, te=16.0, exit_hour=18, sl="mid", tp_r=2.0,
                            trend=None, sides="both"):
    """Yesterday was the narrowest of the last 4 (7) days, or an inside day.
    Today, the first cash-hours close beyond yesterday's high/low -> go with
    it. SL at yesterday's midpoint or far side."""
    cx = _ctx(df)
    first_idx = cx["first_idx"]; n = cx["n"]
    h, l = cx["h"], cx["l"]
    last_idx = np.r_[first_idx[1:] - 1, n - 1]
    dayH = np.array([h[a:b + 1].max() for a, b in zip(first_idx, last_idx)])
    dayL = np.array([l[a:b + 1].min() for a, b in zip(first_idx, last_idx)])
    rng = dayH - dayL
    nd = len(rng)
    flag = np.zeros(nd, bool)
    look = 4 if kind == "nr4" else 7
    for k in range(look, nd):
        if kind in ("nr4", "nr7"):
            flag[k] = rng[k] <= rng[k - look + 1:k + 1].min()
        else:
            flag[k] = dayH[k] < dayH[k - 1] and dayL[k] > dayL[k - 1]
    out = [None] * n
    cur_day, traded = -1, False
    for i in range(n):
        k = cx["day_id"][i]
        if k != cur_day:
            cur_day, traded = k, False
        if traded or k - 1 < 0 or not flag[k - 1]:
            continue
        hm = cx["hm"][i]
        if hm < ts or hm > te:
            continue
        pdh, pdl = cx["pdh"][i], cx["pdl"][i]
        c = cx["c"][i]
        side = "long" if c > pdh else ("short" if c < pdl else None)
        if side is None:
            continue
        traded = True
        if sides != "both" and side != sides:
            continue
        if not _trend_ok(cx, i, side, trend):
            continue
        slv = (pdh + pdl) / 2 if sl == "mid" else (pdl if side == "long" else pdh)
        risk = abs(c - slv)
        if risk <= 0:
            continue
        tp = (c + tp_r * risk if side == "long" else c - tp_r * risk) if tp_r else None
        if _bad(side, c, slv, tp):
            continue
        out[i] = Entry(side, float(slv), tp, exit_hour=exit_hour)
    return out


# --------------------------------------------------------------------------- 16. big-day fade / follow on D1

def build_big_day(df, k=1.5, mode="fade", sl_atr=1.5, tp_r=1.0, max_hold=3, sides="both"):
    """D1: today's close-to-close move > k x ATR20 -> fade (or follow) at the
    close, SL sl_atr ATR, TP tp_r R, max_hold days."""
    c = df["close"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr = pd.Series(tr).rolling(20).mean().to_numpy()
    n = len(c); out = [None] * n
    for i in range(21, n):
        a = atr[i]
        if np.isnan(a) or a <= 0:
            continue
        mv = c[i] - c[i - 1]
        if abs(mv) < k * a:
            continue
        up = mv > 0
        side = ("short" if up else "long") if mode == "fade" else ("long" if up else "short")
        if sides != "both" and side != sides:
            continue
        sl = c[i] + sl_atr * a if side == "short" else c[i] - sl_atr * a
        tp = None
        if tp_r:
            tp = c[i] - tp_r * sl_atr * a if side == "short" else c[i] + tp_r * sl_atr * a
        out[i] = Entry(side, float(sl), tp, max_hold=max_hold)
    return out


# --------------------------------------------------------------------------- 17. first-hour break + retest

def build_fh_retest(df, fh_end=11.0, te=16.0, exit_hour=18, mm=1.5, sl="far", trend=None, sides="both"):
    """Range 10:00..fh_end. After a close beyond it, wait for price to come
    back and touch the broken level and close on the breakout side: enter
    there. TP = level +/- mm x range; SL far side or mid."""
    cx = _ctx(df)
    n = cx["n"]; out = [None] * n
    cur_day, rh, rl, brk, traded = -1, -np.inf, np.inf, None, False
    for i in range(n):
        if cx["day_id"][i] != cur_day:
            cur_day, rh, rl, brk, traded = cx["day_id"][i], -np.inf, np.inf, None, False
        hm = cx["hm"][i]
        if 10.0 <= hm < fh_end:
            rh, rl = max(rh, cx["h"][i]), min(rl, cx["l"][i]); continue
        if hm < fh_end or hm > te or traded or not np.isfinite(rh):
            continue
        c, h, l = cx["c"][i], cx["h"][i], cx["l"][i]
        rng = rh - rl
        if brk is None:
            if c > rh:
                brk = "up"
            elif c < rl:
                brk = "down"
            continue
        if brk == "up" and l <= rh and c > rh:
            side, lvl = "long", rh
        elif brk == "down" and h >= rl and c < rl:
            side, lvl = "short", rl
        else:
            if (brk == "up" and c < rl) or (brk == "down" and c > rh):
                brk = None
            continue
        traded = True
        if sides != "both" and side != sides:
            continue
        if not _trend_ok(cx, i, side, trend):
            continue
        slv = (rl if side == "long" else rh) if sl == "far" else (rh + rl) / 2
        tpv = lvl + mm * rng if side == "long" else lvl - mm * rng
        if _bad(side, c, slv, tpv):
            continue
        out[i] = Entry(side, float(slv), float(tpv), exit_hour=exit_hour)
    return out


# --------------------------------------------------------------------------- 18. Donchian trend follow (H4 / D1)

def build_donchian(df, n_ch=40, sl_atr=2.5, trail_atr=3.0, trend=None, sides="both", tp_r=None):
    c = df["close"].to_numpy(float); h = df["high"].to_numpy(float); l = df["low"].to_numpy(float)
    hh = pd.Series(h).rolling(n_ch).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n_ch).min().shift(1).to_numpy()
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    atr = pd.Series(tr).rolling(14).mean().to_numpy()
    ema = pd.Series(c).ewm(span=200, adjust=False).mean().to_numpy()
    n = len(c); out = [None] * n

    def mk(side):
        def manage(d_, i, pos):
            a = atr[i]
            if np.isnan(a):
                return None
            if side == "long":
                ns = c[i] - trail_atr * a
                return ns if ns > pos["sl"] else None
            ns = c[i] + trail_atr * a
            return ns if ns < pos["sl"] else None
        return manage

    for i in range(n_ch + 1, n):
        a = atr[i]
        if np.isnan(a) or np.isnan(hh[i]) or a <= 0:
            continue
        side = "long" if c[i] > hh[i] else ("short" if c[i] < ll[i] else None)
        if side is None or (sides != "both" and side != sides):
            continue
        if trend == "with" and ((side == "long" and c[i] < ema[i]) or (side == "short" and c[i] > ema[i])):
            continue
        sl = c[i] - sl_atr * a if side == "long" else c[i] + sl_atr * a
        tp = None
        if tp_r:
            tp = c[i] + tp_r * sl_atr * a if side == "long" else c[i] - tp_r * sl_atr * a
        out[i] = Entry(side, float(sl), tp, manage=mk(side))
    return out


# --------------------------------------------------------------------------- 18. Kagels "09:15 candle" breakout (practitioner rule set)

def build_kagels_915(df, bar_hm=10.25, bar_len=0.25, te=14.0, exit_hour=18, tp_pts=None, tp_r=1.5,
                     sl="far", sides="both", trend=None, wds=(0, 1, 2, 3, 4)):
    """Rule set from kagels-trading.de (DAX futures, 15-min chart): the 09:15 CET
    candle (10:15 server) high/low become breakout levels; buy stop at the high,
    sell stop at the low, no new orders after 13:00 CET (14:00 server). Our
    version: first close beyond the candle enters (bar-close fills), stop at the
    opposite side of the candle (the "classic" variant) or its midpoint, target
    tp_pts points or tp_r x risk, flat at exit_hour. One trade per day. On M30
    data the reference bar is 10:00-10:30 (bar_hm=10.0, bar_len=0.5)."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    cur, rh, rl, traded = -1, np.nan, np.nan, False
    for i in range(cx["n"]):
        if cx["day_id"][i] != cur:
            cur, rh, rl, traded = cx["day_id"][i], np.nan, np.nan, False
        hm = cx["hm"][i]
        if abs(hm - bar_hm) < 0.01:
            rh, rl = cx["h"][i], cx["l"][i]
            continue
        if traded or np.isnan(rh) or hm < bar_hm + bar_len - 0.01 or hm > te or cx["wd"][i] not in wds:
            continue
        c = cx["c"][i]
        side = "long" if c > rh else ("short" if c < rl else None)
        if side is None:
            continue
        traded = True
        if sides != "both" and side != sides:
            continue
        if not _trend_ok(cx, i, side, trend):
            continue
        slv = (rl if side == "long" else rh) if sl == "far" else (rh + rl) / 2
        risk = abs(c - slv)
        da = cx["datr"][i]
        if risk <= 0 or np.isnan(da) or risk < 0.05 * da:
            continue
        if tp_pts:
            tp = c + tp_pts if side == "long" else c - tp_pts
        elif tp_r:
            tp = c + tp_r * risk if side == "long" else c - tp_r * risk
        else:
            tp = None
        if _bad(side, c, slv, tp):
            continue
        out[i] = Entry(side, float(slv), tp, exit_hour=exit_hour)
    return out


# --------------------------------------------------------------------------- 19. first-hour range multiplier breakout (Benzinga/PyQuant style)

def build_fh_mult(df, rs=10.0, re=11.0, mult=0.5, te=16.0, exit_hour=18, sl="opp", tp_r=None,
                  sides="both", trend=None):
    """Range = first cash hour (10:00-11:00 server). Reference = open of the
    first bar after the range. Long when a close > ref + mult x range, short
    when a close < ref - mult x range (until te). Stop at the opposite level
    (ref -/+ mult x range) or at ref; optional TP tp_r x risk; flat at exit_hour."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    cur, rh, rl, ref, traded = -1, -np.inf, np.inf, np.nan, False
    for i in range(cx["n"]):
        if cx["day_id"][i] != cur:
            cur, rh, rl, ref, traded = cx["day_id"][i], -np.inf, np.inf, np.nan, False
        hm = cx["hm"][i]
        if rs <= hm < re:
            rh, rl = max(rh, cx["h"][i]), min(rl, cx["l"][i])
            continue
        if hm < re or not np.isfinite(rh) or traded or hm > te:
            continue
        if np.isnan(ref):
            ref = cx["o"][i]
        rng = rh - rl
        if rng <= 0:
            continue
        up, dn = ref + mult * rng, ref - mult * rng
        c = cx["c"][i]
        side = "long" if c > up else ("short" if c < dn else None)
        if side is None:
            continue
        traded = True
        if sides != "both" and side != sides:
            continue
        if not _trend_ok(cx, i, side, trend):
            continue
        slv = (dn if side == "long" else up) if sl == "opp" else ref
        risk = abs(c - slv)
        da = cx["datr"][i]
        if risk <= 0 or np.isnan(da) or risk < 0.05 * da:
            continue
        tp = (c + tp_r * risk if side == "long" else c - tp_r * risk) if tp_r else None
        if _bad(side, c, slv, tp):
            continue
        out[i] = Entry(side, float(slv), tp, exit_hour=exit_hour)
    return out


# --------------------------------------------------------------------------- 20. overnight drift with day filter (STOXX overnight-effect paper)

def build_close_to_open(df, entry_hm=18.0, exit_hm=10.0, side="long", sl_datr=1.0, cond=None,
                        wds=(0, 1, 2, 3), tp_datr=None):
    """STOXX 'overnight effect': long at the 18:00 bar close (last bar before
    the 18:30 cash close), flat at the close of the 10:00 bar (first cash bar).
    cond: 'down_cash' = only after a down cash session (10:00 open -> 18:00 close),
    'up_cash', 'below_pdc', 'above_pdc'. Default skips Friday (weekend risk)."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    for i in range(cx["n"]):
        if abs(cx["hm"][i] - entry_hm) > 0.01 or cx["wd"][i] not in wds:
            continue
        da = cx["datr"][i]
        if np.isnan(da) or da <= 0:
            continue
        c = cx["c"][i]
        if cond in ("down_cash", "up_cash"):
            j = _session_open_idx(cx, i)
            if j is None:
                continue
            ses = c - cx["o"][j]
            if (cond == "down_cash" and ses >= 0) or (cond == "up_cash" and ses <= 0):
                continue
        elif cond == "below_pdc" and not c < cx["pdc"][i]:
            continue
        elif cond == "above_pdc" and not c > cx["pdc"][i]:
            continue
        sl = c - sl_datr * da if side == "long" else c + sl_datr * da
        tp = None
        if tp_datr:
            tp = c + tp_datr * da if side == "long" else c - tp_datr * da
        # exit: first bar of the next day at/after exit_hm, via manage
        def mg(df_, k, pos, _eh=exit_hm, _d=cx["day_id"][i], _cx=cx):
            if _cx["day_id"][k] != _d and _cx["hm"][k] >= _eh - 0.01:
                return "close"
            return None
        out[i] = Entry(side, float(sl), tp, manage=mg)
    return out


# --------------------------------------------------------------------------- 21. intraday momentum (Gao, Han, Li, Zhou 2018: first half-hour predicts last half-hour)

def build_intraday_mom(df, first_hm=10.0, entry_hm=17.5, exit_hour=18, sl_datr=0.5, agree_prev=False,
                       min_move_datr=0.0, mode="follow", sides="both", wds=(0, 1, 2, 3, 4)):
    """Gao et al. (JFE 2018) report that the first half-hour return predicts the
    last half-hour return, including on FTSE 100 and Euro Stoxx 50 futures.
    Here: direction = sign of the first_hm bar (10:00-10:30 server) move; enter at
    the close of the entry_hm bar (17:30 -> 18:00) and exit at the close of the
    exit_hour bar (18:00 bar closes 18:30 = cash close). agree_prev also requires
    the bar before entry to point the same way (the paper's second predictor).
    mode='fade' takes the opposite side. Stop sl_datr x daily ATR."""
    cx = _ctx(df)
    out = [None] * cx["n"]
    for i in range(cx["n"]):
        if abs(cx["hm"][i] - entry_hm) > 0.01 or cx["wd"][i] not in wds:
            continue
        j = _session_open_idx(cx, i, first_hm)
        if j is None or j >= i:
            continue
        da = cx["datr"][i]
        if np.isnan(da) or da <= 0:
            continue
        mv = cx["c"][j] - cx["o"][j]
        if abs(mv) < min_move_datr * da or mv == 0:
            continue
        d = 1 if mv > 0 else -1
        if agree_prev:
            pm = cx["c"][i] - cx["o"][i]
            if pm == 0 or (pm > 0) != (d > 0):
                continue
        if mode == "fade":
            d = -d
        side = "long" if d > 0 else "short"
        if sides != "both" and side != sides:
            continue
        c = cx["c"][i]
        sl = c - sl_datr * da if side == "long" else c + sl_datr * da
        out[i] = Entry(side, float(sl), None, exit_hour=exit_hour)
    return out


BUILDERS = {k[6:]: v for k, v in globals().items() if k.startswith("build_")}
