"""Breakout family for the 2026-10 prop-firm strategy search.

Every build_* function takes any df from research.prop.harness.load() and
returns a list (len(df)) of H.Entry | None. All signals are CAUSAL: the Entry
at bar i uses only rows <= i. Daily levels come from server-day (EET) bars of
COMPLETED previous days; session ranges use only bars already closed.

Bar time = bar OPEN time (MT5). A bar with hour h covers [h, h+1) on H1.
Server time is EET/EEST, so London cash open = 10:00 and the NY cash open is
16:30 server time all year (barring the 2-3 DST-mismatch weeks).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H


# ----------------------------------------------------------------- helpers
def _clock(df):
    t = pd.DatetimeIndex(df["time"])
    hr = (t.hour + t.minute / 60.0).to_numpy(float)
    day = t.normalize().to_numpy()
    dow = t.dayofweek.to_numpy()
    return hr, day, dow


def atr(df, n=14):
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def _daily(df, atr_n=14, ema_n=50):
    """Per-bar values of the PREVIOUS completed server day (causal)."""
    hr, day, _ = _clock(df)
    g = pd.DataFrame({"day": day, "h": df.high.to_numpy(float), "l": df.low.to_numpy(float),
                      "o": df.open.to_numpy(float), "c": df.close.to_numpy(float)})
    d = g.groupby("day").agg(h=("h", "max"), l=("l", "min"), o=("o", "first"), c=("c", "last"))
    pc = d.c.shift()
    tr = np.maximum(d.h - d.l, np.maximum((d.h - pc).abs(), (d.l - pc).abs()))
    d["atr"] = tr.ewm(alpha=1.0 / atr_n, adjust=False).mean()
    d["ema"] = d.c.ewm(span=ema_n, adjust=False).mean()
    d["rng"] = d.h - d.l
    prev = d.shift(1)                      # yesterday's completed values
    prev2 = d.shift(2)
    out = {k: prev[k].reindex(day).to_numpy() for k in ("h", "l", "o", "c", "atr", "ema", "rng")}
    out["h2"] = prev2["h"].reindex(day).to_numpy()
    out["l2"] = prev2["l"].reindex(day).to_numpy()
    # NR-n flags of yesterday: smallest range of last n days (incl. itself)
    for n in (4, 7):
        nr = (d.rng <= d.rng.rolling(n).min()).shift(1)
        out[f"nr{n}"] = nr.reindex(day).fillna(False).to_numpy(bool)
    ins = ((d.h <= d.h.shift(1)) & (d.l >= d.l.shift(1))).shift(1)
    out["inside"] = ins.reindex(day).fillna(False).to_numpy(bool)
    return out


def _trend_ok(side, dly, mode):
    """Daily trend filter using yesterday's close vs its EMA."""
    if mode is None:
        return np.ones_like(dly["c"], bool)
    up = dly["c"] > dly["ema"]
    return up if side == "long" else ~up


def make_manage(df, be_r=None, trail_atr=None, trail_after_r=1.0, atr_n=14):
    """Breakeven at be_r, then optional ATR chandelier trail once trade is
    trail_after_r in profit. Uses only rows <= i."""
    if be_r is None and trail_atr is None:
        return None
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    a = atr(df, atr_n)

    def manage(_df, i, pos):
        r = abs(pos["entry"] - pos["sl0"])
        if r <= 0:
            return None
        lo, hi = pos["bar"] + 1, i + 1
        long_ = pos["side"] == "long"
        if long_:
            best = h[lo:hi].max()
            gain = (best - pos["entry"]) / r
        else:
            best = l[lo:hi].min()
            gain = (pos["entry"] - best) / r
        new = pos["sl"]
        if be_r is not None and gain >= be_r:
            new = max(new, pos["entry"]) if long_ else min(new, pos["entry"])
        if trail_atr is not None and gain >= trail_after_r:
            t = best - trail_atr * a[i] if long_ else best + trail_atr * a[i]
            new = max(new, t) if long_ else min(new, t)
        if long_ and new >= c[i]:
            return "close"
        if (not long_) and new <= c[i]:
            return "close"
        return new if new != pos["sl"] else None
    return manage


def _entry(side, close, sl, tp_r, exit_h, max_hold, manage, meta):
    r = abs(close - sl)
    if not np.isfinite(sl) or r <= 0:
        return None
    tp = None
    if tp_r is not None:
        tp = close + tp_r * r if side == "long" else close - tp_r * r
    return H.Entry(side, sl=float(sl), tp=tp, max_hold=max_hold, exit_hour=exit_h,
                   manage=manage, meta=meta)


# ----------------------------------------------------- 1. session range ORB
def build_session_orb(df, rs=0.0, re=9.0, te=14.0, exit_h=22, max_hold=None,
                      sl="far", sl_atr=1.0, sl_frac=1.0, tp_r=1.5,
                      min_rng=0.0, max_rng=99.0, sides="both", trend=None,
                      body=False, dow_skip=(), be_r=None, trail_atr=None,
                      trail_after_r=1.0):
    """Range = high/low of bars with clock hour in [rs, re) (server time).
    First bar closing beyond the range with clock hour in [re, te) enters
    (one trade per day). Stop: 'far' side of range (sl_frac of range from
    the breakout edge), 'mid' or 'atr' (sl_atr x daily ATR). min/max_rng =
    range size in units of yesterday's daily ATR."""
    hr, day, dow = _clock(df)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    dly = _daily(df)
    up_ok = _trend_ok("long", dly, trend)
    dn_ok = _trend_ok("short", dly, trend)
    manage = make_manage(df, be_r, trail_atr, trail_after_r)
    n = len(df)
    sig = [None] * n
    cur, rh, rl, done = None, -np.inf, np.inf, False
    for i in range(n):
        if day[i] != cur:
            cur, rh, rl, done = day[i], -np.inf, np.inf, False
        x = hr[i]
        in_rng = (rs <= x < re) if rs < re else (x >= rs or x < re)
        if in_rng:
            rh, rl = max(rh, h[i]), min(rl, l[i])
            continue
        if done or not (re <= x < te) or not np.isfinite(rh) or dow[i] in dow_skip:
            continue
        rng = rh - rl
        da = dly["atr"][i]
        if not np.isfinite(da) or rng <= 0 or not (min_rng * da <= rng <= max_rng * da):
            continue
        side = None
        if c[i] > rh and sides in ("both", "long") and up_ok[i] and (not body or c[i] > o[i]):
            side = "long"
        elif c[i] < rl and sides in ("both", "short") and dn_ok[i] and (not body or c[i] < o[i]):
            side = "short"
        if side is None:
            continue
        done = True
        if sl == "far":
            s = rh - sl_frac * rng if side == "long" else rl + sl_frac * rng
        elif sl == "mid":
            s = (rh + rl) / 2
        else:
            s = c[i] - sl_atr * da if side == "long" else c[i] + sl_atr * da
        sig[i] = _entry(side, c[i], s, tp_r, exit_h, max_hold, manage,
                        {"rng_atr": rng / da})
    return sig


# ------------------------------------------ 2. previous-day high/low break
def build_pdhl(df, ts=9.0, te=16.0, exit_h=22, max_hold=None, sl="atr",
               sl_atr=0.5, tp_r=1.5, trend=None, fade=False, buf=0.0,
               be_r=None, trail_atr=None, trail_after_r=1.0):
    """Breakout: first close beyond yesterday's high/low in [ts, te).
    fade=True: false-breakout reversal - after price has traded beyond the
    level today, the first close back inside fades it (stop beyond today's
    extreme + buf x daily ATR)."""
    hr, day, _ = _clock(df)
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    dly = _daily(df)
    up_ok, dn_ok = _trend_ok("long", dly, trend), _trend_ok("short", dly, trend)
    manage = make_manage(df, be_r, trail_atr, trail_after_r)
    n = len(df)
    sig = [None] * n
    cur, done, dh, dl = None, False, -np.inf, np.inf
    for i in range(n):
        if day[i] != cur:
            cur, done, dh, dl = day[i], False, -np.inf, np.inf
        dh, dl = max(dh, h[i]), min(dl, l[i])
        if done or not (ts <= hr[i] < te):
            continue
        ph, pl, da = dly["h"][i], dly["l"][i], dly["atr"][i]
        if not np.isfinite(ph) or not np.isfinite(da):
            continue
        side = None
        if not fade:
            if c[i] > ph and up_ok[i]:
                side, s = "long", (c[i] - sl_atr * da if sl == "atr" else pl)
            elif c[i] < pl and dn_ok[i]:
                side, s = "short", (c[i] + sl_atr * da if sl == "atr" else ph)
        else:
            if dh > ph and c[i] < ph and dn_ok[i]:
                side, s = "short", dh + buf * da
            elif dl < pl and c[i] > pl and up_ok[i]:
                side, s = "long", dl - buf * da
        if side is None:
            continue
        done = True
        sig[i] = _entry(side, c[i], s, tp_r, exit_h, max_hold, manage, {})
    return sig


# ------------------------------------------- 3. NR4 / NR7 / inside-day break
def build_nr_break(df, kind="nr7", ts=0.0, te=20.0, exit_h=22, max_hold=None,
                   sl="far", sl_atr=1.0, tp_r=2.0, trend=None,
                   be_r=None, trail_atr=None, trail_after_r=1.0):
    """Yesterday was a narrow-range (NR4/NR7) or inside day (or 'nr4in'
    = both). Today: first close beyond yesterday's high/low enters. Stop
    = yesterday's far side ('far'), midpoint ('mid') or ATR."""
    hr, day, _ = _clock(df)
    c = df.close.to_numpy(float)
    dly = _daily(df)
    flag = {"nr4": dly["nr4"], "nr7": dly["nr7"], "inside": dly["inside"],
            "nr4in": dly["nr4"] & dly["inside"], "any": dly["nr4"] | dly["inside"]}[kind]
    up_ok, dn_ok = _trend_ok("long", dly, trend), _trend_ok("short", dly, trend)
    manage = make_manage(df, be_r, trail_atr, trail_after_r)
    n = len(df)
    sig = [None] * n
    cur, done = None, False
    for i in range(n):
        if day[i] != cur:
            cur, done = day[i], False
        if done or not flag[i] or not (ts <= hr[i] < te):
            continue
        ph, pl, da = dly["h"][i], dly["l"][i], dly["atr"][i]
        if not np.isfinite(ph):
            continue
        side = None
        if c[i] > ph and up_ok[i]:
            side = "long"
        elif c[i] < pl and dn_ok[i]:
            side = "short"
        if side is None:
            continue
        done = True
        if sl == "far":
            s = pl if side == "long" else ph
        elif sl == "mid":
            s = (ph + pl) / 2
        else:
            s = c[i] - sl_atr * da if side == "long" else c[i] + sl_atr * da
        sig[i] = _entry(side, c[i], s, tp_r, exit_h, max_hold, manage, {})
    return sig


# ---------------------------------------- 4. Bollinger squeeze / Donchian
def build_squeeze(df, bb_n=20, bb_k=2.0, look=200, pct=0.15, recent=5,
                  sl_atr=1.5, tp_r=2.0, max_hold=48, exit_h=None, hours=None,
                  trend=None, be_r=None, trail_atr=None, trail_after_r=1.0):
    """Volatility contraction: Bollinger bandwidth was in its lowest `pct`
    quantile of the last `look` bars within the last `recent` bars; first
    close outside the band enters in that direction. Stop = sl_atr x ATR(14)
    of this timeframe. `hours` = (start, end) clock window for entries."""
    c = df.close.to_numpy(float)
    s = pd.Series(c)
    ma, sd = s.rolling(bb_n).mean(), s.rolling(bb_n).std(ddof=0)
    up, lo = (ma + bb_k * sd).to_numpy(), (ma - bb_k * sd).to_numpy()
    bw = (2 * bb_k * sd / ma)
    q = bw.rolling(look).quantile(pct)
    sq = (bw <= q).astype(float).rolling(recent).max().shift(1).fillna(0).to_numpy() > 0
    a = atr(df)
    hr, _, _ = _clock(df)
    dly = _daily(df)
    up_ok, dn_ok = _trend_ok("long", dly, trend), _trend_ok("short", dly, trend)
    manage = make_manage(df, be_r, trail_atr, trail_after_r)
    pc = np.r_[np.nan, c[:-1]]
    pup, plo = np.r_[np.nan, up[:-1]], np.r_[np.nan, lo[:-1]]
    n = len(df)
    sig = [None] * n
    for i in range(look + bb_n, n):
        if not sq[i]:
            continue
        if hours is not None and not (hours[0] <= hr[i] < hours[1]):
            continue
        side = None
        if c[i] > up[i] and pc[i] <= pup[i] and up_ok[i]:
            side, st = "long", c[i] - sl_atr * a[i]
        elif c[i] < lo[i] and pc[i] >= plo[i] and dn_ok[i]:
            side, st = "short", c[i] + sl_atr * a[i]
        if side is None:
            continue
        sig[i] = _entry(side, c[i], st, tp_r, exit_h, max_hold, manage, {})
    return sig


def build_donchian(df, n_ch=20, sl_atr=2.0, tp_r=None, max_hold=None,
                   exit_h=None, hours=None, trend=None, be_r=None,
                   trail_atr=3.0, trail_after_r=0.0):
    """Classic N-bar channel breakout: close above the prior N-bar high
    (rows < i) enters long; ATR stop; ATR chandelier trail."""
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    hh = pd.Series(h).rolling(n_ch).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n_ch).min().shift(1).to_numpy()
    a = atr(df)
    hr, _, _ = _clock(df)
    dly = _daily(df)
    up_ok, dn_ok = _trend_ok("long", dly, trend), _trend_ok("short", dly, trend)
    manage = make_manage(df, be_r, trail_atr, trail_after_r)
    pc = np.r_[np.nan, c[:-1]]
    phh, pll = np.r_[np.nan, hh[:-1]], np.r_[np.nan, ll[:-1]]
    n = len(df)
    sig = [None] * n
    for i in range(n_ch + 2, n):
        if hours is not None and not (hours[0] <= hr[i] < hours[1]):
            continue
        side = None
        if c[i] > hh[i] and not (pc[i] > phh[i]) and up_ok[i]:
            side, st = "long", c[i] - sl_atr * a[i]
        elif c[i] < ll[i] and not (pc[i] < pll[i]) and dn_ok[i]:
            side, st = "short", c[i] + sl_atr * a[i]
        if side is None:
            continue
        sig[i] = _entry(side, c[i], st, tp_r, exit_h, max_hold, manage, {})
    return sig


# ------------------------------------- 5. Crabel stretch ORB (+NR filter)
def build_crabel(df, ss=10.0, te=16.0, exit_h=23, k=1.0, look=10, filt=None,
                 tp_r=None, sl_mode="opp", sl_atr=0.5, trend=None, dow_skip=(),
                 be_r=None, trail_atr=None, trail_after_r=1.0):
    """Toby Crabel opening-range breakout, close-confirmed version.
    Session open = open of the first bar at/after clock hour `ss`.
    stretch = mean over the previous `look` days of min(high-open, open-low)
    measured from that day's session open to its end. Long when a bar in
    [ss, te) closes above open + k*stretch (short mirrored). Stop = the
    opposite level ('opp') or sl_atr x daily ATR. Day filter on yesterday:
    None / 'nr4' / 'nr7' / 'inside' / 'any'. Flat at exit_h."""
    hr, day, dow = _clock(df)
    o, h, l, c = (df[k_].to_numpy(float) for k_ in ("open", "high", "low", "close"))
    dly = _daily(df)
    flag = {None: np.ones(len(df), bool), "nr4": dly["nr4"], "nr7": dly["nr7"],
            "inside": dly["inside"], "any": dly["nr4"] | dly["inside"] | dly["nr7"]}[filt]
    up_ok, dn_ok = _trend_ok("long", dly, trend), _trend_ok("short", dly, trend)
    manage = make_manage(df, be_r, trail_atr, trail_after_r)
    # per-day session stretch (uses whole session -> only usable for LATER days)
    sess = hr >= ss
    g = pd.DataFrame({"day": day[sess], "o": o[sess], "h": h[sess], "l": l[sess]})
    d = g.groupby("day").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"))
    st = np.minimum(d.h - d.o, d.o - d.l).rolling(look).mean().shift(1)  # prior days only
    stretch = st.reindex(day).to_numpy()
    n = len(df)
    sig = [None] * n
    cur, so, done = None, np.nan, False
    for i in range(n):
        if day[i] != cur:
            cur, so, done = day[i], np.nan, False
        if hr[i] >= ss and not np.isfinite(so):
            so = o[i]
        if done or not np.isfinite(so) or not (ss <= hr[i] < te) or not flag[i] or dow[i] in dow_skip:
            continue
        s_ = stretch[i]
        if not np.isfinite(s_) or s_ <= 0:
            continue
        up_lv, dn_lv = so + k * s_, so - k * s_
        side = None
        if c[i] > up_lv and up_ok[i]:
            side = "long"
        elif c[i] < dn_lv and dn_ok[i]:
            side = "short"
        if side is None:
            continue
        done = True
        if sl_mode == "opp":
            stp = dn_lv if side == "long" else up_lv
        else:
            da = dly["atr"][i]
            stp = c[i] - sl_atr * da if side == "long" else c[i] + sl_atr * da
        sig[i] = _entry(side, c[i], stp, tp_r, exit_h, None, manage, {})
    return sig


# ------------------------------------------ 6. previous-week range break
def build_prev_week(df, sl_atr=1.0, tp_r=None, max_hold=None, trend=None,
                    be_r=None, trail_atr=None, trail_after_r=1.0, trail_n=14,
                    exit_friday=True):
    """First close beyond LAST week's high/low (completed week, Mon-Fri by
    server date) enters; stop sl_atr x daily ATR; optional TP / trail.
    exit_friday: flat at the Friday 22:00 bar (no weekend gap risk)."""
    t = pd.DatetimeIndex(df["time"])
    wk = (t.normalize() - pd.to_timedelta(t.dayofweek, unit="D")).to_numpy()
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    g = pd.DataFrame({"wk": wk, "h": h, "l": l}).groupby("wk").agg(h=("h", "max"), l=("l", "min"))
    ph = g.h.shift(1).reindex(wk).to_numpy()
    pl = g.l.shift(1).reindex(wk).to_numpy()
    dly = _daily(df)
    up_ok, dn_ok = _trend_ok("long", dly, trend), _trend_ok("short", dly, trend)
    manage = make_manage(df, be_r, trail_atr, trail_after_r, atr_n=trail_n)
    dow = t.dayofweek.to_numpy()
    hr = t.hour.to_numpy()

    def manage2(_df, i, pos):          # Friday flat uses only bar i's own clock
        if exit_friday and dow[i] == 4 and hr[i] >= 21:
            return "close"
        return manage(_df, i, pos) if manage is not None else None
    n = len(df)
    sig = [None] * n
    cur, done_l, done_s = None, False, False
    for i in range(n):
        if wk[i] != cur:
            cur, done_l, done_s = wk[i], False, False
        if not np.isfinite(ph[i]) or (exit_friday and dow[i] == 4 and hr[i] >= 20):
            continue
        da = dly["atr"][i]
        if not np.isfinite(da):
            continue
        side = None
        if not done_l and c[i] > ph[i] and up_ok[i]:
            side, done_l = "long", True
        elif not done_s and c[i] < pl[i] and dn_ok[i]:
            side, done_s = "short", True
        if side is None:
            continue
        stp = c[i] - sl_atr * da if side == "long" else c[i] + sl_atr * da
        sig[i] = _entry(side, c[i], stp, tp_r, None, max_hold, manage2, {})
    return sig


# ------------------------------------------------ 7. signal combinations
def build_combo(df, parts=()):
    """Merge several breakout signal lists on ONE symbol into one strategy
    (still one position at a time). parts = [(build_fn_name, params), ...];
    earlier parts win when two fire on the same bar."""
    out = [None] * len(df)
    g = globals()
    for fn, p in parts:
        sig = g[fn](df, **p)
        for i, s in enumerate(sig):
            if out[i] is None and s is not None:
                out[i] = s
    return out


# ======================================================= named candidates
def build_de40_xetra_orb(df, rs=10.0, re=10.5, te=12.5, exit_h=18, sl_frac=1.0,
                         trend="d", min_rng=0.1, tp_r=None):
    """DE40 (DAX) Xetra-open range breakout. Range = 10:00-10:30 server
    (09:00-09:30 CET) M30 bar; first close beyond it before 12:30 enters in
    the direction of yesterday's daily close vs EMA50; stop = far side of the
    range (sl_frac=1) ; no target; flat at the 18:00 bar. Range must be at
    least 0.1 x daily ATR (filters the tiny-range days that produced 5R gap
    losses). Designed for M30; also positive on H1 (re=11) and M15."""
    return build_session_orb(df, rs=rs, re=re, te=te, exit_h=exit_h, sl="far",
                             sl_frac=sl_frac, tp_r=tp_r, trend=trend, min_rng=min_rng)


def build_jpy_inside_day(df, tp_r=3.0, max_hold=48, sl="far"):
    """Yesterday was an inside day -> first H1 close beyond yesterday's
    high/low enters; stop = yesterday's far side; 3R target or 48 bars.
    Works on USDJPY and GBPJPY (not on other JPY crosses / majors)."""
    return build_nr_break(df, kind="inside", ts=0, te=20, exit_h=None,
                          max_hold=max_hold, sl=sl, tp_r=tp_r)


def build_gold_h4_donchian(df, n_ch=55, sl_atr=3.0, trail_atr=3.0, trend="d"):
    """55-bar H4 channel breakout with daily-EMA50 trend filter, ATR stop and
    3xATR chandelier trail. NOTE: profit is almost entirely gold LONGS in
    2019-2020 (gold bull beta), shorts ~0R."""
    return build_donchian(df, n_ch=n_ch, sl_atr=sl_atr, trail_atr=trail_atr,
                          trail_after_r=0.0, trend=trend)


def build_gbpjpy_prev_week(df, sl_atr=1.0, trail_atr=8.0):
    """First H1 close beyond last week's high/low; stop 1x daily ATR; BE at
    1R then 8xH1-ATR trail; flat Friday 21:00 server."""
    return build_prev_week(df, sl_atr=sl_atr, trail_atr=trail_atr, trail_after_r=1.0, be_r=1.0)
