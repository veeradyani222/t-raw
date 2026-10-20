"""gold_fix family: diagnosis-driven fixes of the gold BOS+CMF strategy and
other gold ideas. Every build_* returns a list (len(df)) of H.Entry | None and
is causal (Entry at bar i uses rows <= i only). Works on any df from H.load.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H
from research.search.gold_fix import lib as L
from research.search.gold_fix.ideas import (  # noqa: F401  (re-exported builders)
    build_donchian, build_session_break, build_pullback, build_hour_hold, build_regime,
    build_squeeze, build_mtf, build_combo)


# --------------------------------------------------------------------------- #
# Break of structure + CMF (re-implementation of bos_backtest.make_bos_signal) #
# with optional, diagnosis-driven filters.                                      #
# --------------------------------------------------------------------------- #
def bos_features(df, swing_window=2, cmf_n=20, lookback=2000, trend_ma=200):
    o, h, l, c = L.arr(df)
    n = len(df)
    w = swing_window
    sh, sl = L.swings(h, l, w)
    lh = L.confirmed_last(sh, w, n)
    ll = L.confirmed_last(sl, w, n)
    floor = np.arange(n) - lookback + 1 + w
    lh = np.where(lh >= floor, lh, -1)
    ll = np.where(ll >= floor, ll, -1)
    f = dict(o=o, h=h, l=l, c=c, n=n, w=w, sh=sh, sl=sl, lh=lh, ll=ll, L=lookback)
    f["cmf"] = L.cmf(df, cmf_n)
    f["ma"] = L.sma(c, trend_ma) if trend_ma else None
    f["atr"] = L.atr(df, 14)
    f["adx"], f["pdi"], f["ndi"] = L.adx(df, 14)
    f["atr_pct"] = L.rolling_pct_rank(f["atr"], 2000)
    ema50 = L.ema(c, 50)
    f["slope"] = (ema50 - np.r_[np.full(10, np.nan), ema50[:-10]]) / f["atr"]
    t = pd.DatetimeIndex(df["time"])
    f["hour"], f["wd"], f["day"] = t.hour.to_numpy(), t.weekday.to_numpy(), t.day.to_numpy()
    f["nfp"] = L.first_friday_mask(t)
    return f


def build_bos(df, swing_window=2, cmf_n=20, cmf_min=0.0, use_cmf=True, trend_ma=200,
              lookback=2000, tp_mode="structure", tp_r=3.0, tp_min_r=1.0,
              hours=None, sides=("long", "short"), adx_min=None, adx_max=None,
              atrp_min=None, atrp_max=None, stop_atr_min=None, stop_atr_max=None,
              skip_nfp=False, max_hold=None, slope_align=None, be_r=None,
              tgt_r_max=None, htf=None, trail_atr=None, _f=None):
    """htf=(rule, n): trade only in the direction of the last CLOSED higher-
    timeframe bar's close vs its EMA(n), e.g. ("1D", 50).
    trail_atr: chandelier trailing stop (x ATR14) in addition to the target."""
    f = _f or bos_features(df, swing_window, cmf_n, lookback, trend_ma)
    o, h, l, c, n, w = f["o"], f["h"], f["l"], f["c"], f["n"], f["w"]
    lh, ll, sh, slw, Lb = f["lh"], f["ll"], f["sh"], f["sl"], f["L"]
    cm = f["cmf"]
    ma = f["ma"]
    cmin = -1.0 if not use_cmf else cmf_min
    a = f["atr"]
    out = [None] * n
    prev_c = np.r_[np.nan, c[:-1]]
    lvl_h = np.where(lh >= 0, h[np.maximum(lh, 0)], np.nan)
    lvl_l = np.where(ll >= 0, l[np.maximum(ll, 0)], np.nan)
    ma_ok_l = np.ones(n, bool) if ma is None else (c > ma)
    ma_ok_s = np.ones(n, bool) if ma is None else (c < ma)
    with np.errstate(invalid="ignore"):
        long_c = (c > lvl_h) & (prev_c <= lvl_h) & (c > o) & (cm > cmin) & ma_ok_l
        short_c = (c < lvl_l) & (prev_c >= lvl_l) & (c < o) & (cm < -cmin) & ma_ok_s
    if htf is not None:
        rule, hn = htf
        hc = L.htf_close_aligned(df, rule, lambda g: g["close"].to_numpy(float))
        he = L.htf_close_aligned(df, rule, lambda g: L.ema(g["close"].to_numpy(float), hn))
        with np.errstate(invalid="ignore"):
            long_c &= hc > he
            short_c &= hc < he
    min_bars = max(cmf_n, w * 2) + 2
    manage = _be_manager(be_r) if be_r else None
    if trail_atr:
        manage = _trail_manager(h, l, a, trail_atr)
    for i in np.where(long_c | short_c)[0]:
        if i < min_bars:
            continue
        side = None
        if long_c[i] and ll[i] >= 0 and l[ll[i]] < c[i]:
            side = "long"; stop = l[ll[i]]; risk = c[i] - stop
        elif short_c[i] and (not long_c[i]) and lh[i] >= 0 and h[lh[i]] > c[i]:
            side = "short"; stop = h[lh[i]]; risk = stop - c[i]
        elif long_c[i]:
            continue
        if side is None or risk <= 0:
            continue
        if side == "long":
            tp = c[i] + tp_r * risk
            if tp_mode == "structure":
                cand = sh[(sh + w <= i) & (sh - w >= i - Lb + 1) & (h[sh] >= c[i] + tp_min_r * risk)]
                if cand.size:
                    tp = float(h[cand].min())
        else:
            tp = c[i] - tp_r * risk
            if tp_mode == "structure":
                cand = slw[(slw + w <= i) & (slw - w >= i - Lb + 1) & (l[slw] <= c[i] - tp_min_r * risk)]
                if cand.size:
                    tp = float(l[cand].max())
        if tp_mode == "none":
            tp = None
        stop_atr = risk / a[i] if a[i] > 0 else np.nan
        tgt_r = abs(tp - c[i]) / risk if tp is not None else np.nan
        meta = dict(hour=int(f["hour"][i]), wd=int(f["wd"][i]), atr_pct=float(f["atr_pct"][i]),
                    adx=float(f["adx"][i]), stop_atr=float(stop_atr), tgt_r=float(tgt_r),
                    slope=float(f["slope"][i]), nfp=bool(f["nfp"][i]), dom=int(f["day"][i]),
                    cmf=float(cm[i]))
        # ---- filters ----
        if side not in sides:
            continue
        if hours is not None and meta["hour"] not in hours:
            continue
        if adx_min is not None and not meta["adx"] >= adx_min:
            continue
        if adx_max is not None and not meta["adx"] <= adx_max:
            continue
        if atrp_min is not None and not meta["atr_pct"] >= atrp_min:
            continue
        if atrp_max is not None and not meta["atr_pct"] <= atrp_max:
            continue
        if stop_atr_min is not None and not stop_atr >= stop_atr_min:
            continue
        if stop_atr_max is not None and not stop_atr <= stop_atr_max:
            continue
        if tgt_r_max is not None and not tgt_r <= tgt_r_max:
            continue
        if skip_nfp and meta["nfp"]:
            continue
        if slope_align is not None:
            s = meta["slope"]
            if side == "long" and not s > slope_align:
                continue
            if side == "short" and not s < -slope_align:
                continue
        out[i] = H.Entry(side, sl=float(stop), tp=tp, max_hold=max_hold, manage=manage, meta=meta)
    return out


def _be_manager(be_r):
    """Move the stop to entry once price has gone be_r x initial risk in favour."""
    def m(df, i, pos):
        r0 = abs(pos["entry"] - pos["sl0"])
        if pos["side"] == "long":
            if pos["sl"] < pos["entry"] and df["high"].iat[i] >= pos["entry"] + be_r * r0:
                return pos["entry"]
        else:
            if pos["sl"] > pos["entry"] and df["low"].iat[i] <= pos["entry"] - be_r * r0:
                return pos["entry"]
        return None
    return m


def _trail_manager(h, l, a, k):
    """Chandelier trail: stop = extreme since entry -/+ k x ATR (never loosens)."""
    def m(_df, i, pos):
        if pos["side"] == "long":
            st = h[pos["bar"]:i + 1].max() - k * a[i]
            return st if st > pos["sl"] else None
        st = l[pos["bar"]:i + 1].min() + k * a[i]
        return st if st < pos["sl"] else None
    return m


# =========================================================================== #
# CANDIDATES (defaults = the in-sample settings reported in NOTES.md)          #
# =========================================================================== #
def build_gold_lowvol_donchian(df, n_entry=15, n_exit=7, atr_stop=2.0, trail_atr=5.0,
                               atrp_max=0.5, atrp_window=500, adx_min=20):
    """XAUUSD H4. Donchian breakout taken only when ATR14 is in the lower half of
    its trailing 500-bar range (calm -> expansion) and ADX14 >= 20. Stop 2xATR20,
    exit on close beyond the 7-bar opposite extreme or a 5xATR chandelier trail."""
    return build_regime(df, base="build_donchian",
                        base_params=dict(n_entry=n_entry, n_exit=n_exit, atr_stop=atr_stop,
                                         trail_atr=trail_atr),
                        atrp_max=atrp_max, atrp_window=atrp_window, adx_min=adx_min)


def build_gold_lowvol_donchian_fast(df, n_entry=15, n_exit=5, atr_stop=2.0, trail_atr=4.0,
                                    atrp_max=0.5, atrp_window=500, adx_min=20):
    """Same idea, faster exit (5-bar) + 4xATR trail; safe up to 0.75% risk in-sample."""
    return build_gold_lowvol_donchian(df, n_entry, n_exit, atr_stop, trail_atr, atrp_max,
                                      atrp_window, adx_min)


def build_bos_fixed(df, sides=("long", "short"), atrp_min=0.6, tp_min_r=2.0, htf=("1D", 100),
                    stop_atr_min=None):
    """XAUUSD M30. Live BOS+CMF (MA200, swing 2, structure stop) with the
    diagnosis fixes: only in the top-40% ATR regime, structure target must be
    >= 2R (else the 3R fallback), and trade only with the daily EMA100 trend."""
    return build_bos(df, atrp_min=atrp_min, tp_min_r=tp_min_r, htf=tuple(htf) if htf else None,
                     sides=tuple(sides), stop_atr_min=stop_atr_min)


def build_bos_fixed_long(df, atrp_min=0.6, tp_min_r=2.0, htf=("1D", 100)):
    """build_bos_fixed, long side only (shorts were the bigger loser in the diagnosis)."""
    return build_bos_fixed(df, sides=("long",), atrp_min=atrp_min, tp_min_r=tp_min_r, htf=htf)


def build_gold_squeeze_adx(df, n_exit=7, trail_atr=5.0, adx_min=20):
    """XAUUSD H4. Bollinger(20,2) width in bottom 20% of 500 bars within the last 5
    bars, then a close outside the band with ADX14 >= 20. Stop 2xATR, exit 7-bar
    opposite extreme or 5xATR trail."""
    return build_regime(df, base="build_squeeze",
                        base_params=dict(n_exit=n_exit, trail_atr=trail_atr), adx_min=adx_min)
