"""search3 / metals (round 3, 2026-10-30): XAUUSD XAGUSD XPTUSD XPDUSD.

Every build_<name>(df, **params) -> list[H.Entry | None] of len(df), causal
(bar i uses rows <= i only; cross-symbol series are as-of merged on bar time
so the other symbol's bar has closed at the same instant), works on any df
from research.prop.harness.load. Every entry has a stop AND a defined exit
(tp, exit_hour, max_hold or manage()).

Hours are SERVER (EET) bar-OPEN hours, as harness.exit_hour uses them.
London open = 10:00, London AM fix = 12:30, NY open = 16:30, PM fix = 17:00.

Ideas (market-structure first, see NOTES.md):
  asia_break     Asian-range breakout (mql5 "London breakout on gold" rules:
                 03-08 range, SL opposite side capped 0.6%, TP 2.5R, BE at 1.5R,
                 range filter 0.30-1.60%, flat 21:00) + structure-target variants
                 (prior-day H/L, 1x range projection); also the London-open and
                 NY-open opening-range breakout via the window params.
  asia_fade      failed Asian-range poke: wick beyond the range, close back in.
  pd_sweep       prior-day / prior-week high-low sweep reversal (Unger-style
                 false break of PDH/PDL), TP mid / other side / R.
  pd_break       first close of the day beyond PDH/PDL: continuation with
                 measured-move or R target.
  session_hold   calendar/clock drift: long (or short) from hour h_in to h_out,
                 ATR stop; optional weekday filter (Asia-up / NY-down pattern,
                 Monday effect in silver/PGMs).
  ratio_z        metal/metal ratio z-score reversion (gold-silver, pt-pd,
                 gold-platinum); trades the df symbol only.
  lag_catchup    leader (gold) made an n-bar z-move, this metal did not: follow
                 (catch-up) or fade.
  round_level    round-number break-and-go to the next level, or first-touch fade.
  nr_break       NR-n / inside-day contraction, next-day breakout of that range.
  fix_fade       run into the London AM/PM fix: fade or follow after the fix.
  late_day       17:00 position in the day's range + above PDH: momentum into
                 the close or fade.
  gap_fade       day-open gap vs prior close beyond k ATR: fade to the close /
                 follow.
  asia_dip       uptrend (PDC at n-day high): buy the Asian dip below PDC, TP PDH.
  d1_reversal    D1 big down/up day, hold 1-3 days (PGM daily anti-persistence).
  wopen_retest   weekly open retest in the direction of the week so far.
  channel_pt     Unger platinum H1 6-bar channel long / 2-bar short breakout
                 (ATR stop, R target, time exit).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H

# ----------------------------------------------------------------------- #
# helpers                                                                  #
# ----------------------------------------------------------------------- #
_OTHER_CACHE: dict = {}


def _ohlc(df):
    return (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))


def _atr(df, n=14):
    h, l, c = df.high.to_numpy(float), df.low.to_numpy(float), df.close.to_numpy(float)
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1)
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False, min_periods=n).mean().to_numpy()


def _ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def _step(df):
    t = df["time"]
    if len(t) < 3:
        return pd.Timedelta("1h")
    return (t.iloc[1:].reset_index(drop=True) - t.iloc[:-1].reset_index(drop=True)).median()


def _hours(df):
    return df["time"].dt.hour.to_numpy()


def _day_codes(df):
    return pd.factorize(df["time"].dt.normalize())[0]


def _week_codes(df):
    iso = df["time"].dt.isocalendar()
    return pd.factorize(iso.year.astype(int) * 100 + iso.week.astype(int))[0]


def _prior_group(df, codes):
    """Previous completed group's high/low/close/open mapped onto every bar."""
    h, l, c, o = df.high.to_numpy(float), df.low.to_numpy(float), df.close.to_numpy(float), df.open.to_numpy(float)
    g = pd.DataFrame(dict(code=codes, h=h, l=l, c=c, o=o)).groupby("code")
    agg = g.agg(h=("h", "max"), l=("l", "min"), c=("c", "last"), o=("o", "first"))
    prev = agg.shift(1)
    return (prev["h"].to_numpy()[codes], prev["l"].to_numpy()[codes],
            prev["c"].to_numpy()[codes], prev["o"].to_numpy()[codes])


def _running_group(df, codes):
    """Today's running high / low / open (inclusive of bar i)."""
    h, l, o = df.high.to_numpy(float), df.low.to_numpy(float), df.open.to_numpy(float)
    s = pd.DataFrame(dict(code=codes, h=h, l=l, o=o))
    g = s.groupby("code")
    return g["h"].cummax().to_numpy(), g["l"].cummin().to_numpy(), g["o"].transform("first").to_numpy()


def _window_range(df, codes, hours, a0, a1):
    """Running high/low of bars with open-hour in [a0, a1) within each day.
    Returned arrays are valid (finite) once the window has bars; use with
    `hours >= a1` so the window is complete."""
    h, l = df.high.to_numpy(float), df.low.to_numpy(float)
    m = (hours >= a0) & (hours < a1)
    hh = np.where(m, h, -np.inf)
    ll = np.where(m, l, np.inf)
    s = pd.DataFrame(dict(code=codes, hh=hh, ll=ll)).groupby("code")
    rh, rl = s["hh"].cummax().to_numpy().copy(), s["ll"].cummin().to_numpy().copy()
    rh[~np.isfinite(rh)] = np.nan
    rl[~np.isfinite(rl)] = np.nan
    return rh, rl


def _first_per_day(mask, codes):
    """Keep only the first True per day (causal: depends on earlier bars)."""
    out = np.zeros(len(mask), bool)
    seen = -1
    for i in np.flatnonzero(mask):
        if codes[i] != seen:
            out[i] = True
            seen = codes[i]
    return out


def _other(df, symbol):
    """Other symbol's close as-of each bar time (same tf, same server)."""
    tf = df.attrs.get("tf", "H1")
    split = df.attrs.get("split", "oos")
    key = (symbol.upper(), tf, split)
    if key not in _OTHER_CACHE:
        o = H.load(symbol, tf, split="all" if split != "is" else "is")
        _OTHER_CACHE[key] = o[["time", "close"]].rename(columns={"close": "oc"})
    o = _OTHER_CACHE[key]
    m = pd.merge_asof(df[["time"]].reset_index(drop=True), o, on="time", direction="backward")
    return m["oc"].to_numpy(float)


def _mk(side, c, sl, tp=None, **kw):
    if not np.isfinite(sl):
        return None
    if side == "long" and not (sl < c and (tp is None or tp > c)):
        return None
    if side == "short" and not (sl > c and (tp is None or tp < c)):
        return None
    return H.Entry(side, sl=float(sl), tp=None if tp is None else float(tp), **kw)


def _be_manager(be_r):
    """Move stop to entry once be_r x initial risk is reached."""
    def manage(df, i, pos):
        risk = abs(pos["entry"] - pos["sl0"])
        c = float(df["close"].iat[i])
        if pos["side"] == "long":
            if c - pos["entry"] >= be_r * risk and pos["sl"] < pos["entry"]:
                return pos["entry"]
        else:
            if pos["entry"] - c >= be_r * risk and pos["sl"] > pos["entry"]:
                return pos["entry"]
        return None
    return manage


def _trail_manager(atr_mult, atr):
    def manage(df, i, pos):
        c = float(df["close"].iat[i])
        a = atr[i]
        if not np.isfinite(a):
            return None
        if pos["side"] == "long":
            ns = c - atr_mult * a
            return ns if ns > pos["sl"] else None
        ns = c + atr_mult * a
        return ns if ns < pos["sl"] else None
    return manage


def _tp_price(mode, side, c, sl, struct_hi, struct_lo, rng, min_r=1.0, cap_r=5.0):
    """mode: 'r:2.5' R multiple | 'pdhl' structure level (fallback R) |
    'range' 1x range projection | 'mid' half range | 'other' far side."""
    risk = abs(c - sl)
    if risk <= 0:
        return None
    if mode.startswith("r:"):
        k = float(mode[2:])
        return c + k * risk if side == "long" else c - k * risk
    if mode == "range":
        return c + rng if side == "long" else c - rng
    if mode == "pdhl":
        lvl = struct_hi if side == "long" else struct_lo
        if not np.isfinite(lvl):
            return None
        dist = (lvl - c) if side == "long" else (c - lvl)
        if dist < min_r * risk:
            return c + min_r * 1.5 * risk if side == "long" else c - min_r * 1.5 * risk
        dist = min(dist, cap_r * risk)
        return c + dist if side == "long" else c - dist
    if mode in ("mid", "other"):
        lvl = (struct_hi + struct_lo) / 2 if mode == "mid" else (struct_lo if side == "short" else struct_hi)
        if not np.isfinite(lvl):
            return None
        dist = (lvl - c) if side == "long" else (c - lvl)
        if dist < min_r * risk:
            return None
        return lvl
    raise ValueError(mode)


# ----------------------------------------------------------------------- #
# 1. Asian / opening range breakout                                        #
# ----------------------------------------------------------------------- #
def build_asia_break(df, a0=3, a1=8, last_entry=14, buf_atr=0.0, cap_pct=0.6,
                     tp="r:2.5", be_r=1.5, min_rng=0.30, max_rng=1.60,
                     exit_hour=21, max_hold=None, one_per_day=True, side="both",
                     stop="range"):
    """Range = bars with open-hour in [a0, a1). From a1 to last_entry, first
    close beyond range (+ buf_atr*ATR) enters. stop='range': opposite side
    capped at cap_pct% of price; 'mid': range midpoint; 'atr:1.0': ATR mult.
    Range filter in % of price. BE at be_r (manage). Flat at exit_hour."""
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    hours = _hours(df)
    codes = _day_codes(df)
    atr = _atr(df)
    rh, rl = _window_range(df, codes, hours, a0, a1)
    pdh, pdl, pdc, _ = _prior_group(df, codes)
    rng = rh - rl
    pct = rng / c * 100
    ok = (hours >= a1) & (hours <= last_entry) & np.isfinite(rng) & (pct >= min_rng) & (pct <= max_rng)
    buf = buf_atr * np.nan_to_num(atr)
    up = ok & (c > rh + buf)
    dn = ok & (c < rl - buf)
    if side == "long":
        dn[:] = False
    elif side == "short":
        up[:] = False
    trig = up | dn
    if one_per_day:
        trig = _first_per_day(trig, codes)
    out = [None] * n
    mgr = _be_manager(be_r) if be_r else None
    for i in np.flatnonzero(trig):
        if up[i]:
            if stop == "range":
                sl = max(rl[i], c[i] * (1 - cap_pct / 100))
            elif stop == "mid":
                sl = (rh[i] + rl[i]) / 2
            else:
                sl = c[i] - float(stop.split(":")[1]) * atr[i]
            tpp = _tp_price(tp, "long", c[i], sl, pdh[i], pdl[i], rng[i])
            e = _mk("long", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold, manage=mgr)
        else:
            if stop == "range":
                sl = min(rh[i], c[i] * (1 + cap_pct / 100))
            elif stop == "mid":
                sl = (rh[i] + rl[i]) / 2
            else:
                sl = c[i] + float(stop.split(":")[1]) * atr[i]
            tpp = _tp_price(tp, "short", c[i], sl, pdh[i], pdl[i], rng[i])
            e = _mk("short", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold, manage=mgr)
        out[i] = e
    return out


# ----------------------------------------------------------------------- #
# 2. failed Asian-range poke                                               #
# ----------------------------------------------------------------------- #
def build_asia_fade(df, a0=1, a1=10, last_entry=16, buf_atr=0.1, tp="other",
                    exit_hour=22, max_hold=None, min_rng=0.0, max_rng=99.0):
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    hours = _hours(df)
    codes = _day_codes(df)
    atr = _atr(df)
    rh, rl = _window_range(df, codes, hours, a0, a1)
    rng = rh - rl
    pct = rng / c * 100
    ok = (hours >= a1) & (hours <= last_entry) & np.isfinite(rng) & (pct >= min_rng) & (pct <= max_rng)
    poke_up = ok & (h > rh) & (c < rh)
    poke_dn = ok & (l < rl) & (c > rl)
    trig = _first_per_day(poke_up | poke_dn, codes)
    out = [None] * n
    for i in np.flatnonzero(trig):
        b = buf_atr * atr[i]
        if poke_up[i]:
            sl = h[i] + b
            tpp = _tp_price(tp, "short", c[i], sl, rh[i], rl[i], rng[i])
            out[i] = _mk("short", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold)
        else:
            sl = l[i] - b
            tpp = _tp_price(tp, "long", c[i], sl, rh[i], rl[i], rng[i])
            out[i] = _mk("long", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold)
    return out


# ----------------------------------------------------------------------- #
# 3. prior-day / prior-week level sweep reversal                           #
# ----------------------------------------------------------------------- #
def build_pd_sweep(df, level="pd", h0=9, h1=20, buf_atr=0.1, tp="mid", exit_hour=22,
                   max_hold=24, min_r=1.0, side="both"):
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    hours = _hours(df)
    codes = _day_codes(df)
    atr = _atr(df)
    lh, ll, lc, _ = _prior_group(df, codes if level == "pd" else _week_codes(df))
    ok = (hours >= h0) & (hours <= h1) & np.isfinite(lh)
    sw_up = ok & (h > lh) & (c < lh) & (np.r_[np.nan, c[:-1]] < lh)
    sw_dn = ok & (l < ll) & (c > ll) & (np.r_[np.nan, c[:-1]] > ll)
    if side == "long":
        sw_up[:] = False
    elif side == "short":
        sw_dn[:] = False
    trig = _first_per_day(sw_up | sw_dn, codes)
    out = [None] * n
    for i in np.flatnonzero(trig):
        b = buf_atr * atr[i]
        if sw_up[i]:
            sl = h[i] + b
            tpp = _tp_price(tp, "short", c[i], sl, lh[i], ll[i], lh[i] - ll[i], min_r=min_r)
            out[i] = _mk("short", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold)
        else:
            sl = l[i] - b
            tpp = _tp_price(tp, "long", c[i], sl, lh[i], ll[i], lh[i] - ll[i], min_r=min_r)
            out[i] = _mk("long", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold)
    return out


# ----------------------------------------------------------------------- #
# 4. first close beyond PDH/PDL: continuation                              #
# ----------------------------------------------------------------------- #
def build_pd_break(df, h0=9, h1=18, stop="atr:1.0", tp="range", exit_hour=22,
                   max_hold=None, be_r=None, side="both", min_rng_atr=0.0):
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    hours = _hours(df)
    codes = _day_codes(df)
    atr = _atr(df)
    pdh, pdl, pdc, _ = _prior_group(df, codes)
    rng = pdh - pdl
    pc = np.r_[np.nan, c[:-1]]
    ok = (hours >= h0) & (hours <= h1) & np.isfinite(pdh) & (rng >= min_rng_atr * np.nan_to_num(atr))
    up = ok & (c > pdh) & (pc <= pdh)
    dn = ok & (c < pdl) & (pc >= pdl)
    if side == "long":
        dn[:] = False
    elif side == "short":
        up[:] = False
    trig = _first_per_day(up | dn, codes)
    mgr = _be_manager(be_r) if be_r else None
    out = [None] * n
    for i in np.flatnonzero(trig):
        if up[i]:
            sl = pdc[i] if stop == "pdc" else (pdl[i] + rng[i] / 2 if stop == "mid" else c[i] - float(stop.split(":")[1]) * atr[i])
            tpp = _tp_price(tp, "long", c[i], sl, pdh[i], pdl[i], rng[i])
            out[i] = _mk("long", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold, manage=mgr)
        else:
            sl = pdc[i] if stop == "pdc" else (pdl[i] + rng[i] / 2 if stop == "mid" else c[i] + float(stop.split(":")[1]) * atr[i])
            tpp = _tp_price(tp, "short", c[i], sl, pdh[i], pdl[i], rng[i])
            out[i] = _mk("short", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold, manage=mgr)
    return out


# ----------------------------------------------------------------------- #
# 5. clock drift: hold from h_in to h_out                                  #
# ----------------------------------------------------------------------- #
def build_session_hold(df, side="long", h_in=22, h_out=9, stop_atr=2.0, tp_atr=None,
                       dows=None, max_hold=30, trend_n=None, prev_day=None):
    """Enter at the close of the bar with open-hour h_in, exit at the close of
    the first later bar with open-hour h_out. dows: weekday list (0=Mon) of
    the ENTRY bar. trend_n: only when close > (long) / < (short) EMA(trend_n).
    prev_day: 'down' = prior completed day closed below the day before (Unger
    platinum filter), 'up' = the opposite."""
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    hours = _hours(df)
    atr = _atr(df)
    trig = hours == h_in
    if prev_day:
        codes = _day_codes(df)
        _, _, pdc, _ = _prior_group(df, codes)
        g = pd.DataFrame(dict(code=codes, c=c)).groupby("code")["c"].last()
        pdc2 = g.shift(2).to_numpy()[codes]
        ok = np.isfinite(pdc) & np.isfinite(pdc2)
        trig &= ok & ((pdc < pdc2) if prev_day == "down" else (pdc > pdc2))
    if dows is not None:
        wd = df["time"].dt.weekday.to_numpy()
        trig &= np.isin(wd, list(dows))
    if trend_n:
        e = _ema(c, trend_n)
        trig &= (c > e) if side == "long" else (c < e)
    out = [None] * n
    for i in np.flatnonzero(trig):
        a = atr[i]
        if not np.isfinite(a):
            continue
        if side == "long":
            sl = c[i] - stop_atr * a
            tp = c[i] + tp_atr * a if tp_atr else None
        else:
            sl = c[i] + stop_atr * a
            tp = c[i] - tp_atr * a if tp_atr else None
        out[i] = _mk(side, c[i], sl, tp, exit_hour=h_out, max_hold=max_hold)
    return out


# ----------------------------------------------------------------------- #
# 6. metal / metal ratio z-score                                           #
# ----------------------------------------------------------------------- #
def build_ratio_z(df, other="XAGUSD", z_n=200, z_in=2.5, stop_atr=2.0, tp_r=1.5,
                  max_hold=30, side="both", z_out=None):
    """ratio = close / other close. z > z_in: this metal rich -> short;
    z < -z_in: cheap -> long. Entry on threshold cross. ATR stop, R target,
    time backstop; z_out: also close when |z| < z_out (manage)."""
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    oc = _other(df, other)
    r = np.log(c / oc)
    s = pd.Series(r)
    z = ((s - s.rolling(z_n, min_periods=z_n).mean()) / s.rolling(z_n, min_periods=z_n).std()).to_numpy()
    atr = _atr(df)
    pz = np.r_[np.nan, z[:-1]]
    sh = (z > z_in) & (pz <= z_in)
    lo = (z < -z_in) & (pz >= -z_in)
    if side == "long":
        sh[:] = False
    elif side == "short":
        lo[:] = False
    out = [None] * n
    mgr = None
    if z_out is not None:
        def mgr(df_, i, pos, z=z, z_out=z_out):
            return "close" if abs(z[i]) < z_out else None
    for i in np.flatnonzero(sh | lo):
        a = atr[i]
        if not np.isfinite(a):
            continue
        if sh[i]:
            sl = c[i] + stop_atr * a
            out[i] = _mk("short", c[i], sl, c[i] - tp_r * stop_atr * a, max_hold=max_hold, manage=mgr)
        else:
            sl = c[i] - stop_atr * a
            out[i] = _mk("long", c[i], sl, c[i] + tp_r * stop_atr * a, max_hold=max_hold, manage=mgr)
    return out


# ----------------------------------------------------------------------- #
# 7. leader / laggard                                                      #
# ----------------------------------------------------------------------- #
def build_lag_catchup(df, leader="XAUUSD", n=24, z_n=500, z_in=1.5, own_max=0.5,
                      mode="follow", stop_atr=1.5, tp_r=1.5, max_hold=24):
    """Leader's n-bar log return z-scored over z_n bars. When |z_leader| > z_in
    and this metal's own z is < own_max in that direction: follow (trade own
    in the leader's direction) or fade (opposite)."""
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    nb = len(df)
    lc = _other(df, leader)
    def zret(x):
        r = pd.Series(np.log(x)).diff(n)
        return (r / r.rolling(z_n, min_periods=z_n).std()).to_numpy()
    zl, zo = zret(lc), zret(c)
    pzl = np.r_[np.nan, zl[:-1]]
    up = (zl > z_in) & (pzl <= z_in) & (zo < own_max)
    dn = (zl < -z_in) & (pzl >= -z_in) & (zo > -own_max)
    atr = _atr(df)
    out = [None] * nb
    for i in np.flatnonzero(up | dn):
        a = atr[i]
        if not np.isfinite(a):
            continue
        side = ("long" if up[i] else "short") if mode == "follow" else ("short" if up[i] else "long")
        if side == "long":
            out[i] = _mk("long", c[i], c[i] - stop_atr * a, c[i] + tp_r * stop_atr * a, max_hold=max_hold)
        else:
            out[i] = _mk("short", c[i], c[i] + stop_atr * a, c[i] - tp_r * stop_atr * a, max_hold=max_hold)
    return out


# ----------------------------------------------------------------------- #
# 8. round numbers                                                         #
# ----------------------------------------------------------------------- #
def build_round_level(df, step=50.0, mode="break", h0=2, h1=21, tol_atr=0.15,
                      stop_frac=0.5, tp="next", exit_hour=None, max_hold=24, side="both"):
    """Levels = multiples of `step`. break: close crosses a level -> continue to
    the next level (stop stop_frac*step back / or ATR). fade: first wick touch
    of a level from below/above with close back -> reverse, TP = half-step."""
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    hours = _hours(df)
    atr = _atr(df)
    pc = np.r_[np.nan, c[:-1]]
    ok = (hours >= h0) & (hours <= h1) & np.isfinite(pc)
    lvl_up = np.floor(c / step) * step            # highest level <= close
    lvl_dn = np.ceil(c / step) * step             # lowest level >= close
    out = [None] * n
    if mode == "break":
        up = ok & (pc < lvl_up) & (c >= lvl_up)   # crossed a level upward this bar
        dn = ok & (pc > lvl_dn) & (c <= lvl_dn)
        if side == "long":
            dn[:] = False
        elif side == "short":
            up[:] = False
        for i in np.flatnonzero(up | dn):
            if up[i]:
                L = lvl_up[i]
                sl = L - stop_frac * step
                tpp = L + step if tp == "next" else c[i] + float(tp[2:]) * (c[i] - sl)
                out[i] = _mk("long", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold)
            else:
                L = lvl_dn[i]
                sl = L + stop_frac * step
                tpp = L - step if tp == "next" else c[i] - float(tp[2:]) * (sl - c[i])
                out[i] = _mk("short", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold)
        return out
    # fade
    tol = tol_atr * np.nan_to_num(atr)
    touch_up = ok & (h >= lvl_dn - tol) & (c < lvl_dn) & (pc < lvl_dn) & (lvl_dn - c < step * 0.5)
    touch_dn = ok & (l <= lvl_up + tol) & (c > lvl_up) & (pc > lvl_up) & (c - lvl_up < step * 0.5)
    if side == "long":
        touch_up[:] = False
    elif side == "short":
        touch_dn[:] = False
    for i in np.flatnonzero(touch_up | touch_dn):
        if touch_up[i]:
            L = lvl_dn[i]
            sl = max(h[i], L) + tol[i]
            tpp = L - stop_frac * step if tp == "next" else c[i] - float(tp[2:]) * (sl - c[i])
            out[i] = _mk("short", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold)
        else:
            L = lvl_up[i]
            sl = min(l[i], L) - tol[i]
            tpp = L + stop_frac * step if tp == "next" else c[i] + float(tp[2:]) * (c[i] - sl)
            out[i] = _mk("long", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold)
    return out


# ----------------------------------------------------------------------- #
# 9. narrow-range / inside-day breakout                                    #
# ----------------------------------------------------------------------- #
def build_nr_break(df, nr=7, inside=False, h0=2, h1=18, stop="mid", tp="range",
                   exit_hour=22, max_hold=None, be_r=None):
    """Yesterday was the narrowest of the last `nr` days (or an inside day):
    first close of today beyond yesterday's range -> breakout."""
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    hours = _hours(df)
    codes = _day_codes(df)
    atr = _atr(df)
    g = pd.DataFrame(dict(code=codes, h=h, l=l)).groupby("code").agg(h=("h", "max"), l=("l", "min"))
    rng_d = (g.h - g.l)
    nr_flag = rng_d == rng_d.rolling(nr, min_periods=nr).min()
    ins_flag = (g.h < g.h.shift(1)) & (g.l > g.l.shift(1))
    flag_prev = (ins_flag if inside else nr_flag).shift(1).fillna(False).to_numpy()[codes]
    pdh, pdl, pdc, _ = _prior_group(df, codes)
    rng = pdh - pdl
    pc = np.r_[np.nan, c[:-1]]
    ok = (hours >= h0) & (hours <= h1) & flag_prev & np.isfinite(pdh)
    up = ok & (c > pdh) & (pc <= pdh)
    dn = ok & (c < pdl) & (pc >= pdl)
    trig = _first_per_day(up | dn, codes)
    mgr = _be_manager(be_r) if be_r else None
    out = [None] * n
    for i in np.flatnonzero(trig):
        if up[i]:
            sl = (pdh[i] + pdl[i]) / 2 if stop == "mid" else (pdl[i] if stop == "other" else c[i] - float(stop.split(":")[1]) * atr[i])
            tpp = _tp_price(tp, "long", c[i], sl, pdh[i], pdl[i], rng[i])
            out[i] = _mk("long", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold, manage=mgr)
        else:
            sl = (pdh[i] + pdl[i]) / 2 if stop == "mid" else (pdh[i] if stop == "other" else c[i] + float(stop.split(":")[1]) * atr[i])
            tpp = _tp_price(tp, "short", c[i], sl, pdh[i], pdl[i], rng[i])
            out[i] = _mk("short", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold, manage=mgr)
    return out


# ----------------------------------------------------------------------- #
# 10. London fix run-in                                                    #
# ----------------------------------------------------------------------- #
def build_fix_fade(df, fix="pm", lookback_h=2, k_atr=0.8, mode="fade", stop_atr=1.0,
                   tp_r=None, exit_hour=20, max_hold=8):
    """Signal at the bar that CLOSES at the fix (AM 12:30 / PM 17:00 server).
    Move = close now - close lookback_h hours earlier, in ATR(14 of this tf).
    |move| > k_atr: fade (opposite) or follow."""
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    step = _step(df)
    close_t = df["time"] + step
    fix_h, fix_m = (12, 30) if fix == "am" else (17, 0)
    at_fix = ((close_t.dt.hour == fix_h) & (close_t.dt.minute == fix_m)).to_numpy()
    if not at_fix.any():   # H1 cannot close at 12:30 -> use the bar closing at 13:00
        at_fix = ((close_t.dt.hour == fix_h + (1 if fix_m else 0)) & (close_t.dt.minute == 0)).to_numpy()
    lb = max(1, int(round(pd.Timedelta(hours=lookback_h) / step)))
    atr = _atr(df)
    mv = (c - np.r_[np.full(lb, np.nan), c[:-lb]]) / atr
    up = at_fix & (mv > k_atr)
    dn = at_fix & (mv < -k_atr)
    out = [None] * n
    for i in np.flatnonzero(up | dn):
        a = atr[i]
        side = ("short" if up[i] else "long") if mode == "fade" else ("long" if up[i] else "short")
        if side == "long":
            sl = c[i] - stop_atr * a
            tp = c[i] + tp_r * stop_atr * a if tp_r else None
        else:
            sl = c[i] + stop_atr * a
            tp = c[i] - tp_r * stop_atr * a if tp_r else None
        out[i] = _mk(side, c[i], sl, tp, exit_hour=exit_hour, max_hold=max_hold)
    return out


# ----------------------------------------------------------------------- #
# 11. late-day position in range                                           #
# ----------------------------------------------------------------------- #
def build_late_day(df, check_hour=16, q=0.8, need_pd=True, mode="follow", stop="mid",
                   exit_hour=22, max_hold=8, tp_r=None):
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    hours = _hours(df)
    codes = _day_codes(df)
    atr = _atr(df)
    dh, dl, do = _running_group(df, codes)
    pdh, pdl, pdc, _ = _prior_group(df, codes)
    rng = dh - dl
    pos = np.where(rng > 0, (c - dl) / np.where(rng > 0, rng, 1), 0.5)
    at = (hours == check_hour) & (rng > 0)
    up = at & (pos >= q) & ((c > pdh) if need_pd else True)
    dn = at & (pos <= 1 - q) & ((c < pdl) if need_pd else True)
    out = [None] * n
    for i in np.flatnonzero(up | dn):
        side = ("long" if up[i] else "short") if mode == "follow" else ("short" if up[i] else "long")
        mid = (dh[i] + dl[i]) / 2
        if side == "long":
            sl = mid if stop == "mid" else c[i] - float(stop.split(":")[1]) * atr[i]
            tp = c[i] + tp_r * (c[i] - sl) if tp_r else None
        else:
            sl = mid if stop == "mid" else c[i] + float(stop.split(":")[1]) * atr[i]
            tp = c[i] - tp_r * (sl - c[i]) if tp_r else None
        out[i] = _mk(side, c[i], sl, tp, exit_hour=exit_hour, max_hold=max_hold)
    return out


# ----------------------------------------------------------------------- #
# 12. day-open gap                                                         #
# ----------------------------------------------------------------------- #
def build_gap_fade(df, k_atr=0.5, mode="fade", monday_only=False, stop_mult=1.0,
                   tp="fill", max_hold=24, exit_hour=None, first_hours=(0, 1, 2)):
    """At the first bar of a day (open-hour in first_hours and new day): gap =
    close - prior-day close. |gap| > k_atr*ATR: fade to the prior close
    (TP = PDC, stop = stop_mult*gap beyond) or follow (TP = R)."""
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    hours = _hours(df)
    codes = _day_codes(df)
    atr = _atr(df)
    pdh, pdl, pdc, _ = _prior_group(df, codes)
    new_day = np.r_[True, codes[1:] != codes[:-1]]
    at = new_day & np.isin(hours, list(first_hours)) & np.isfinite(pdc)
    if monday_only:
        at &= df["time"].dt.weekday.to_numpy() == 0
    gap = c - pdc
    big = at & (np.abs(gap) > k_atr * np.nan_to_num(atr))
    out = [None] * n
    for i in np.flatnonzero(big):
        g = gap[i]
        if mode == "fade":
            side = "short" if g > 0 else "long"
            sl = c[i] + stop_mult * abs(g) if side == "short" else c[i] - stop_mult * abs(g)
            if tp == "fill":
                tpp = pdc[i]
            else:
                k = float(tp[2:])
                tpp = c[i] - k * abs(sl - c[i]) if side == "short" else c[i] + k * abs(sl - c[i])
        else:
            side = "long" if g > 0 else "short"
            sl = pdc[i]
            r = abs(c[i] - sl)
            k = float(tp[2:]) if tp.startswith("r:") else 1.5
            tpp = c[i] + k * r if side == "long" else c[i] - k * r
        out[i] = _mk(side, c[i], sl, tpp, max_hold=max_hold, exit_hour=exit_hour)
    return out


# ----------------------------------------------------------------------- #
# 13. buy the Asian dip in an uptrend                                      #
# ----------------------------------------------------------------------- #
def build_asia_dip(df, trend_n=20, dip_atr=0.5, h0=1, h1=9, stop_atr=1.0, tp="pdh",
                   exit_hour=22, max_hold=24, side="both"):
    """PDC is an n-day closing high (uptrend): during Asia, close <= PDC - dip
    -> long, TP = PDH (or PDC / R). Mirror for downtrend."""
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    hours = _hours(df)
    codes = _day_codes(df)
    atr = _atr(df)
    pdh, pdl, pdc, _ = _prior_group(df, codes)
    dc = pd.Series(c).groupby(codes).last()
    hi_n = (dc == dc.rolling(trend_n, min_periods=trend_n).max()).shift(1).fillna(False).to_numpy()[codes]
    lo_n = (dc == dc.rolling(trend_n, min_periods=trend_n).min()).shift(1).fillna(False).to_numpy()[codes]
    ok = (hours >= h0) & (hours <= h1) & np.isfinite(pdc)
    a = np.nan_to_num(atr)
    up = ok & hi_n & (c <= pdc - dip_atr * a)
    dn = ok & lo_n & (c >= pdc + dip_atr * a)
    if side == "long":
        dn[:] = False
    elif side == "short":
        up[:] = False
    trig = _first_per_day(up | dn, codes)
    out = [None] * n
    for i in np.flatnonzero(trig):
        if up[i]:
            sl = c[i] - stop_atr * atr[i]
            tpp = pdh[i] if tp == "pdh" else (pdc[i] if tp == "pdc" else c[i] + float(tp[2:]) * (c[i] - sl))
            out[i] = _mk("long", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold)
        else:
            sl = c[i] + stop_atr * atr[i]
            tpp = pdl[i] if tp == "pdh" else (pdc[i] if tp == "pdc" else c[i] - float(tp[2:]) * (sl - c[i]))
            out[i] = _mk("short", c[i], sl, tpp, exit_hour=exit_hour, max_hold=max_hold)
    return out


# ----------------------------------------------------------------------- #
# 14. D1 reversal (PGM daily anti-persistence)                             #
# ----------------------------------------------------------------------- #
def build_d1_reversal(df, k_atr=1.0, hold=1, stop_atr=1.5, tp_atr=None, side="both",
                      mode="fade", measure="co"):
    """For D1 (or any tf: 'bar' return). measure 'co': close-open; 'cc':
    close-prev close. |ret| > k_atr*ATR -> fade (or follow), hold `hold` bars."""
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    atr = _atr(df)
    ret = (c - o) if measure == "co" else (c - np.r_[np.nan, c[:-1]])
    big_dn = ret < -k_atr * atr
    big_up = ret > k_atr * atr
    out = [None] * n
    for i in np.flatnonzero(big_dn | big_up):
        a = atr[i]
        if not np.isfinite(a):
            continue
        s = ("long" if big_dn[i] else "short") if mode == "fade" else ("short" if big_dn[i] else "long")
        if side != "both" and s != side:
            continue
        if s == "long":
            out[i] = _mk("long", c[i], c[i] - stop_atr * a, c[i] + tp_atr * a if tp_atr else None, max_hold=hold)
        else:
            out[i] = _mk("short", c[i], c[i] + stop_atr * a, c[i] - tp_atr * a if tp_atr else None, max_hold=hold)
    return out


# ----------------------------------------------------------------------- #
# 15. weekly-open retest                                                   #
# ----------------------------------------------------------------------- #
def build_wopen_retest(df, min_dist_atr=1.0, tol_atr=0.2, stop_atr=1.0, tp="wext",
                       dows=(1, 2, 3), max_hold=48, exit_hour=None):
    """Week open = first bar open of the ISO week. Once price has been
    >= min_dist ATR above it this week, a close within tol of the open (from
    above) is a long with TP = the week's high so far ('wext') or R."""
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    atr = _atr(df)
    wc = _week_codes(df)
    wh, wl, wo = _running_group(df, wc)
    wd = df["time"].dt.weekday.to_numpy()
    a = np.nan_to_num(atr)
    ok = np.isin(wd, list(dows)) & (atr > 0)
    up = ok & (wh - wo >= min_dist_atr * a) & (c <= wo + tol_atr * a) & (c >= wo - tol_atr * a) & (wh - c >= 2 * tol_atr * a)
    dn = ok & (wo - wl >= min_dist_atr * a) & (c >= wo - tol_atr * a) & (c <= wo + tol_atr * a) & (c - wl >= 2 * tol_atr * a)
    # one per week per side
    up = _first_per_day(up, wc)
    dn = _first_per_day(dn, wc)
    out = [None] * n
    for i in np.flatnonzero(up | dn):
        if up[i] and not dn[i]:
            sl = c[i] - stop_atr * atr[i]
            tpp = wh[i] if tp == "wext" else c[i] + float(tp[2:]) * (c[i] - sl)
            out[i] = _mk("long", c[i], sl, tpp, max_hold=max_hold, exit_hour=exit_hour)
        elif dn[i] and not up[i]:
            sl = c[i] + stop_atr * atr[i]
            tpp = wl[i] if tp == "wext" else c[i] - float(tp[2:]) * (sl - c[i])
            out[i] = _mk("short", c[i], sl, tpp, max_hold=max_hold, exit_hour=exit_hour)
    return out


# ----------------------------------------------------------------------- #
# 16. Unger platinum channel                                               #
# ----------------------------------------------------------------------- #
def build_channel_pt(df, n_long=6, n_short=2, stop_atr=2.0, tp_r=2.0, max_hold=24,
                     h0=2, h1=21, side="both", trail_atr=None):
    """Close above the highest high of the prior n_long bars -> long; close
    below the lowest low of the prior n_short bars -> short. ATR stop, R target
    (or ATR trail), time exit."""
    df = df.reset_index(drop=True)
    o, h, l, c = _ohlc(df)
    n = len(df)
    hours = _hours(df)
    atr = _atr(df)
    hh = pd.Series(h).shift(1).rolling(n_long).max().to_numpy()
    ll = pd.Series(l).shift(1).rolling(n_short).min().to_numpy()
    ok = (hours >= h0) & (hours <= h1)
    up = ok & (c > hh)
    dn = ok & (c < ll)
    if side == "long":
        dn[:] = False
    elif side == "short":
        up[:] = False
    mgr = _trail_manager(trail_atr, atr) if trail_atr else None
    out = [None] * n
    for i in np.flatnonzero(up | dn):
        a = atr[i]
        if not np.isfinite(a):
            continue
        if up[i]:
            out[i] = _mk("long", c[i], c[i] - stop_atr * a, None if trail_atr else c[i] + tp_r * stop_atr * a,
                         max_hold=max_hold, manage=mgr)
        else:
            out[i] = _mk("short", c[i], c[i] + stop_atr * a, None if trail_atr else c[i] - tp_r * stop_atr * a,
                         max_hold=max_hold, manage=mgr)
    return out
