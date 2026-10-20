"""Public EA rule sets, re-implemented in Python for research/prop/harness.py.

Every builder: build_<name>(df, **params) -> list[Entry|None] of len(df).
Signals at bar i use only rows <= i (indicators are trailing; exit arrays are
read inside manage() at index i only). Sources / versions are in NOTES.md.

Conventions
- Distances are ATR multiples (Wilder ATR) so a rule works on any symbol/TF.
  Where the EA had pip/point distances, the ATR default is the closest
  equivalent on its native chart (see NOTES.md).
- "ADDED STOP": the original EA had no stop loss; an ATR stop was added
  because the harness (and the prop firm) require one.
- Opposite signals flip the position (harness default allow_flip=True); most
  of these EAs close-and-reverse on opposite signals anyway.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop.harness import Entry


# --------------------------------------------------------------- indicators
def _arr(df, k):
    return df[k].to_numpy(float)


def sma(x, n):
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False).mean().to_numpy()


def smma(x, n):
    return pd.Series(x).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def atr(df, n=14):
    h, l, c = _arr(df, "high"), _arr(df, "low"), _arr(df, "close")
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return smma(tr, n)


def rsi(x, n=14):
    d = np.diff(x, prepend=x[0])
    up = smma(np.where(d > 0, d, 0.0), n)
    dn = smma(np.where(d < 0, -d, 0.0), n)
    with np.errstate(divide="ignore", invalid="ignore"):
        rs = up / dn
    out = 100 - 100 / (1 + rs)
    out[dn == 0] = 100.0
    out[:n] = np.nan
    return out


def rolling_max(x, n):
    return pd.Series(x).rolling(n, min_periods=n).max().to_numpy()


def rolling_min(x, n):
    return pd.Series(x).rolling(n, min_periods=n).min().to_numpy()


def cci(df, n=14):
    tp = (_arr(df, "high") + _arr(df, "low") + _arr(df, "close")) / 3
    m = sma(tp, n)
    out = np.full(len(tp), np.nan)
    if len(tp) >= n:
        w = np.lib.stride_tricks.sliding_window_view(tp, n)
        md = np.abs(w - w.mean(axis=1, keepdims=True)).mean(axis=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            out[n - 1:] = (tp[n - 1:] - m[n - 1:]) / (0.015 * md)
    return out


def mfi(df, n=14):
    tp = (_arr(df, "high") + _arr(df, "low") + _arr(df, "close")) / 3
    v = _arr(df, "tick_volume")
    mf = tp * v
    d = np.diff(tp, prepend=tp[0])
    pos = pd.Series(np.where(d > 0, mf, 0.0)).rolling(n).sum().to_numpy()
    neg = pd.Series(np.where(d < 0, mf, 0.0)).rolling(n).sum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        out = 100 * pos / (pos + neg)
    return out


def stoch_signal(df, k=47, d=9, slow=13):
    """MT5 iStochastic signal line (buffer 1), STO_LOWHIGH, SMA."""
    h, l, c = _arr(df, "high"), _arr(df, "low"), _arr(df, "close")
    hh, ll = rolling_max(h, k), rolling_min(l, k)
    num = pd.Series(c - ll).rolling(slow).sum().to_numpy()
    den = pd.Series(hh - ll).rolling(slow).sum().to_numpy()
    with np.errstate(divide="ignore", invalid="ignore"):
        main = 100 * num / den
    return sma(main, d)


def shift(x, k):
    """x shifted k bars into the past (value at i = x[i-k]); NaN padded."""
    out = np.full(len(x), np.nan)
    if k < len(x):
        out[k:] = x[:len(x) - k]
    return out


# --------------------------------------------------------------- helpers
def _finite(*xs):
    m = np.ones(len(xs[0]), bool)
    for x in xs:
        m &= np.isfinite(x)
    return m


def _assemble(n, long_m, short_m, sl_l, sl_s, tp_l=None, tp_s=None,
              max_hold=None, manage_l=None, manage_s=None, exit_hour=None,
              name=""):
    out = [None] * n
    for i in np.flatnonzero(long_m):
        out[i] = Entry("long", float(sl_l[i]),
                       tp=None if tp_l is None or not np.isfinite(tp_l[i]) else float(tp_l[i]),
                       max_hold=max_hold, exit_hour=exit_hour, manage=manage_l,
                       meta={"ea": name})
    for i in np.flatnonzero(short_m):
        if out[i] is not None:      # both fire: skip (ambiguous)
            out[i] = None
            continue
        out[i] = Entry("short", float(sl_s[i]),
                       tp=None if tp_s is None or not np.isfinite(tp_s[i]) else float(tp_s[i]),
                       max_hold=max_hold, exit_hour=exit_hour, manage=manage_s,
                       meta={"ea": name})
    return out


def _exit_manager(close_long=None, close_short=None, trail=None, c=None):
    """manage() that closes on precomputed exit arrays (read at index i
    only) and optionally trails the stop by `trail[i]` price distance once
    the close is that far in profit (MetaQuotes MACD Sample style)."""
    def m(df, i, pos):
        long_ = pos["side"] == "long"
        if long_ and close_long is not None and close_long[i]:
            return "close"
        if (not long_) and close_short is not None and close_short[i]:
            return "close"
        if trail is not None and np.isfinite(trail[i]):
            t = trail[i]
            if long_ and c[i] - pos["entry"] > t:
                ns = c[i] - t
                if ns > pos["sl"]:
                    return ns
            if (not long_) and pos["entry"] - c[i] > t:
                ns = c[i] + t
                if ns < pos["sl"]:
                    return ns
        return None
    return m


# ===================================================================
# 1. MetaQuotes "MACD Sample" 5.50 (ships with MT5)
# ===================================================================
def build_macd_sample(df, fast=12, slow=26, signal=9, trend=26,
                      open_lvl=0.12, close_lvl=0.08, tp=2.0, trail=1.2,
                      sl=2.0, atr_n=14, use_tp=True, use_trail=True):
    """Buy: MACD<0, MACD crosses above signal, |MACD|>open_lvl*ATR, EMA(trend) rising.
    Close long: MACD>0, crosses below signal, MACD>close_lvl*ATR. Mirror for shorts.
    TP + trailing stop as in source (pips -> ATR). ADDED STOP: sl*ATR."""
    c = _arr(df, "close")
    a = atr(df, atr_n)
    macd = ema(c, fast) - ema(c, slow)
    sig = sma(macd, signal)
    e = ema(c, trend)
    pm, ps, pe = shift(macd, 1), shift(sig, 1), shift(e, 1)
    up = (macd > sig) & (pm < ps)
    dn = (macd < sig) & (pm > ps)
    ok = _finite(macd, sig, pm, ps, a, pe)
    long_m = ok & (macd < 0) & up & (np.abs(macd) > open_lvl * a) & (e > pe)
    short_m = ok & (macd > 0) & dn & (macd > open_lvl * a) & (e < pe)
    close_l = ok & (macd > 0) & dn & (macd > close_lvl * a)
    close_s = ok & (macd < 0) & up & (np.abs(macd) > close_lvl * a)
    mg = _exit_manager(close_l, close_s, trail * a if use_trail else None, c)
    return _assemble(len(df), long_m, short_m, c - sl * a, c + sl * a,
                     c + tp * a if use_tp else None, c - tp * a if use_tp else None,
                     manage_l=mg, manage_s=mg, name="macd_sample")


# ===================================================================
# 2. MetaQuotes "Moving Average" EA (ships with MT5)
# ===================================================================
def build_moving_average(df, period=12, ma_shift=6, sl=2.0, atr_n=14, tp=None):
    """Last closed candle crosses the SMA(period) displaced ma_shift bars:
    open<ma & close>ma -> buy, open>ma & close<ma -> sell; opposite cross
    closes and (next tick) reverses. ADDED STOP: sl*ATR."""
    o, c = _arr(df, "open"), _arr(df, "close")
    a = atr(df, atr_n)
    ma = shift(sma(c, period), ma_shift)
    ok = _finite(ma, a)
    long_m = ok & (o < ma) & (c > ma)
    short_m = ok & (o > ma) & (c < ma)
    return _assemble(len(df), long_m, short_m, c - sl * a, c + sl * a,
                     None if tp is None else c + tp * a,
                     None if tp is None else c - tp * a, name="moving_average")


# ===================================================================
# 3. MetaQuotes "Free Robots" candlestick pattern + oscillator family
# ===================================================================
def _patterns(df, body_n=12, ma_n=5):
    o, h, l, c = (_arr(df, k) for k in ("open", "high", "low", "close"))
    avgb = sma(np.abs(o - c), body_n)         # AvgBody(1): bars 1..12
    ma = sma(c, ma_n)
    O1, C1, H1, L1 = o, c, h, l
    O2, C2, H2, L2 = shift(o, 1), shift(c, 1), shift(h, 1), shift(l, 1)
    O3, C3 = shift(o, 2), shift(c, 2)
    MA2 = shift(ma, 1)
    mid = (h + l) / 2
    mid2, mid3 = shift(mid, 1), shift(mid, 2)
    moc2 = (O2 + C2) / 2
    moc3 = (O3 + C3) / 2
    p = {}
    p["engulfing"] = (
        (O2 > C2) & (C1 - O1 > avgb) & (C1 > O2) & (moc2 < MA2) & (O1 < C2),
        (O2 < C2) & (O1 - C1 > avgb) & (C1 < O2) & (moc2 > MA2) & (O1 > C2))
    p["harami"] = (
        (C1 > O1) & (O2 - C2 > avgb) & (C1 < O2) & (O1 > C2) & (mid2 < MA2),
        (C1 < O1) & (C2 - O2 > avgb) & (C1 > O2) & (O1 < C2) & (mid2 > MA2))
    body_top = (H1 - (H1 - L1) / 3.0)
    p["hammer"] = (
        (mid < MA2) & (np.minimum(O1, C1) > body_top) & (C1 < C2) & (O1 < O2),
        (mid > MA2) & (np.minimum(O1, C1) > body_top) & (C1 > C2) & (O1 > O2))
    star_buy = (((O3 - C3 > avgb) & (np.abs(C2 - O2) < avgb * 0.1) & (C2 < C3) & (O2 < O3)
                 & (O1 > C2) & (C1 > C2))
                | ((O3 - C3 > avgb) & (np.abs(C2 - O2) < avgb * 0.5) & (C2 < C3) & (O2 < O3)
                   & (C1 > moc3)))
    star_sell = (((C3 - O3 > avgb) & (np.abs(C2 - O2) < avgb * 0.1) & (C2 > C3) & (O2 > O3)
                  & (O1 < C2) & (C1 < C2))
                 | ((C3 - O3 > avgb) & (np.abs(C2 - O2) < avgb * 0.5) & (C2 > C3) & (O2 > O3)
                    & (C1 < moc3)))
    p["star"] = (star_buy, star_sell)
    p["soldiers"] = (
        (C3 - O3 > avgb) & (C2 - O2 > avgb) & (C1 - O1 > avgb) & (mid2 > mid3) & (mid > mid2),
        (O3 - C3 > avgb) & (O2 - C2 > avgb) & (O1 - C1 > avgb) & (mid2 < mid3) & (mid < mid2))
    # NOTE: shipped source has a stray `return(true);` so Piercing Line never buys.
    # We implement the intended piercing rule (documented deviation).
    p["darkcloud"] = (
        (C1 - O1 > avgb) & (O2 - C2 > avgb) & (C1 > C2) & (C1 < O2) & (moc2 < MA2) & (O1 < L2),
        (C2 - O2 > avgb) & (C1 < C2) & (C1 > O2) & (moc2 > MA2) & (O1 > H2))
    p["meetinglines"] = (
        (O2 - C2 > avgb) & (C1 - O1 > avgb) & (np.abs(C1 - C2) < 0.1 * avgb),
        (C2 - O2 > avgb) & (O1 - C1 > avgb) & (np.abs(C1 - C2) < 0.1 * avgb))
    return p


def _osc(df, osc):
    """(values, buy_confirm_level, sell_confirm_level, (lo, hi) close levels)"""
    if osc == "rsi":
        return rsi(_arr(df, "close"), 37), 40, 60, (30, 70)
    if osc == "cci":
        return cci(df, 37), -50, 50, (-80, 80)
    if osc == "mfi":
        return mfi(df, 37), 40, 60, (30, 70)
    if osc == "stoch":
        return stoch_signal(df, 47, 9, 13), 30, 70, (20, 80)
    raise ValueError(osc)


def build_free_robot(df, pattern="engulfing", osc="rsi", sl=1.5, tp=1.5,
                     hold=10, atr_n=14, use_osc_exit=True):
    """Pattern on last closed bars + oscillator confirmation (RSI<40 buy /
    >60 sell etc.). Exit: SL/TP (source: 200 points each), close after
    `hold` bars, or oscillator crossing back through its 30/70-type levels."""
    c = _arr(df, "close")
    a = atr(df, atr_n)
    buy_p, sell_p = _patterns(df)[pattern]
    v, bl, sl_lvl, (lo, hi) = _osc(df, osc)
    v2 = shift(v, 1)
    ok = _finite(v, v2, a)
    buy_p = np.nan_to_num(buy_p).astype(bool) if buy_p.dtype != bool else buy_p
    long_m = ok & buy_p & (v < bl)
    short_m = ok & sell_p & (v > sl_lvl)
    if use_osc_exit:
        close_l = ok & (((v < hi) & (v2 > hi)) | ((v < lo) & (v2 > lo))) & ~long_m & ~short_m
        close_s = ok & (((v > lo) & (v2 < lo)) | ((v > hi) & (v2 < hi))) & ~long_m & ~short_m
        mg = _exit_manager(close_l, close_s)
    else:
        mg = None
    return _assemble(len(df), long_m, short_m, c - sl * a, c + sl * a,
                     c + tp * a, c - tp * a, max_hold=hold, manage_l=mg,
                     manage_s=mg, name=f"free_robot_{pattern}_{osc}")


# ===================================================================
# 4. EarnForex "Spike Trader" (fade a spike bar)
# ===================================================================
def build_spike_trader(df, bars=3, pct=0.003, third=0.5, hold=11,
                       sl=1.0, sl_mode="extreme", atr_n=14, tp=None):
    """Sell: high > previous `bars` highs, (H0-H1)/H1 >= pct, close in the lower
    `third` of the bar. Buy mirror. Hold `hold` bars (timer re-armed by a
    same-direction signal). ADDED STOP: spike extreme + sl*ATR (sl_mode
    'extreme') or entry +/- sl*ATR ('atr')."""
    o, h, l, c = (_arr(df, k) for k in ("open", "high", "low", "close"))
    a = atr(df, atr_n)
    n = len(df)
    hh = np.ones(n, bool)
    ll = np.ones(n, bool)
    for k in range(1, bars + 1):
        hh &= h > shift(h, k)
        ll &= l < shift(l, k)
    h1, l1 = shift(h, 1), shift(l, 1)
    rng = h - l
    with np.errstate(divide="ignore", invalid="ignore"):
        sell = hh & ((h - h1) / h1 >= pct) & ((c - l) / rng <= third)
        buy = ll & ((l1 - l) / l1 >= pct) & ((h - c) / rng <= third)
    ok = _finite(h1, l1, a) & (rng > 0)
    sell &= ok
    buy &= ok & ~sell        # source checks sell first
    # timer re-arm: close when `hold` bars passed since last same-side signal
    idx = np.arange(n)
    last_b = pd.Series(np.where(buy, idx, np.nan)).ffill().to_numpy()
    last_s = pd.Series(np.where(sell, idx, np.nan)).ffill().to_numpy()

    def mg(df_, i, pos):
        last = last_b[i] if pos["side"] == "long" else last_s[i]
        if np.isfinite(last) and i - last >= hold - 1:
            return "close"
        return None
    if sl_mode == "extreme":
        sl_l, sl_s = l - sl * a, h + sl * a
    else:
        sl_l, sl_s = c - sl * a, c + sl * a
    return _assemble(n, buy, sell, sl_l, sl_s,
                     None if tp is None else c + tp * a,
                     None if tp is None else c - tp * a,
                     manage_l=mg, manage_s=mg, name="spike_trader")


# ===================================================================
# 5. EarnForex "Ichimoku Chikou Cross" 1.01
# ===================================================================
def build_ichimoku_chikou(df, tenkan=9, kijun=26, senkou=52, sl=2.0, atr_n=20):
    """Chikou/price cross = close[t] vs close[t-kijun] crossing. Armed cross
    waits for confirmation: close above both spans (buffer value at t) and
    chikou above both spans at t-kijun. Opposite cross closes. ADDED STOP:
    sl*ATR(20) (the EA uses ATR(20)*1 only for position sizing)."""
    h, l, c = _arr(df, "high"), _arr(df, "low"), _arr(df, "close")
    a = atr(df, atr_n)
    tk = (rolling_max(h, tenkan) + rolling_min(l, tenkan)) / 2
    kj = (rolling_max(h, kijun) + rolling_min(l, kijun)) / 2
    A = (tk + kj) / 2
    B = (rolling_max(h, senkou) + rolling_min(l, senkou)) / 2
    ck0, ck1 = c, shift(c, 1)                       # chikou at shifts 27, 28
    p0, p1 = shift(c, kijun), shift(c, kijun + 1)   # price at shifts 27, 28
    bull_x = (ck0 > p0) & (ck1 <= p1)
    bear_x = (ck0 < p0) & (ck1 >= p1)
    eq = ck0 == p0
    kb = (c > A) & (c > B)
    ks = (c < A) & (c < B)
    Ak, Bk = shift(A, kijun), shift(B, kijun)
    kcb = (ck0 > Ak) & (ck0 > Bk)
    kcs = (ck0 < Ak) & (ck0 < Bk)
    n = len(df)
    ok = _finite(A, B, Ak, Bk, p1, a)
    long_m = np.zeros(n, bool)
    short_m = np.zeros(n, bool)
    close_l = np.zeros(n, bool)
    close_s = np.zeros(n, bool)
    bull = bear = False
    for i in range(n):
        if not ok[i]:
            continue
        if bull_x[i]:
            bull, bear = True, False
        elif bear_x[i]:
            bull, bear = False, True
        elif eq[i]:
            bull = bear = False
        if bull:
            close_s[i] = True
            if kb[i] and kcb[i]:
                long_m[i] = True
                bull = False
        elif bear:
            close_l[i] = True
            if ks[i] and kcs[i]:
                short_m[i] = True
                bear = False
    mg = _exit_manager(close_l, close_s)
    return _assemble(n, long_m, short_m, c - sl * a, c + sl * a,
                     manage_l=mg, manage_s=mg, name="ichimoku_chikou")


# ===================================================================
# 6. EarnForex "Weekly Breakout" (prev-week range break, out by week end)
# ===================================================================
def build_weekly_breakout(df, period="W", sl_mode="range", sl=2.0,
                          fri_hour=20, day_exit_hour=22, atr_n=14,
                          side="both"):
    """Run on an intraday df. First close above previous week's (or day's,
    period='D') high -> long, stop = previous period low (source) or
    sl*ATR. Mirror for shorts. Exit at end of the period (week: first bar
    on Friday with hour >= fri_hour; day: hour >= day_exit_hour).
    Deviation: source uses buy/sell STOP orders; we enter at the close of
    the first bar that closed beyond the level (later, worse fill)."""
    t = pd.DatetimeIndex(df["time"])
    h, l, c = _arr(df, "high"), _arr(df, "low"), _arr(df, "close")
    a = atr(df, atr_n)
    if period == "W":
        key = (t.normalize() - pd.to_timedelta(t.weekday, unit="D")).to_numpy()
    else:
        key = t.normalize().to_numpy()
    s = pd.DataFrame({"k": key, "h": h, "l": l})
    g = s.groupby("k")
    ph = g["h"].max().shift(1)
    pl = g["l"].min().shift(1)
    PH = s["k"].map(ph).to_numpy(float)
    PL = s["k"].map(pl).to_numpy(float)
    above = (c > PH)
    below = (c < PL)
    first_up = above & (pd.Series(above).groupby(key).cumsum().to_numpy() == 1)
    first_dn = below & (pd.Series(below).groupby(key).cumsum().to_numpy() == 1)
    wd, hr = t.weekday.to_numpy(), t.hour.to_numpy()
    if period == "W":
        end = (wd == 4) & (hr >= fri_hour)
    else:
        end = hr >= day_exit_hour
    ok = _finite(PH, PL, a) & ~end
    long_m = ok & first_up
    short_m = ok & first_dn
    if side == "long":
        short_m[:] = False
    elif side == "short":
        long_m[:] = False
    if sl_mode == "range":
        sl_l, sl_s = PL.copy(), PH.copy()
    else:
        sl_l, sl_s = c - sl * a, c + sl * a
    mg = _exit_manager(end, end)
    return _assemble(len(df), long_m, short_m, sl_l, sl_s,
                     manage_l=mg, manage_s=mg, name=f"breakout_{period}")


# ===================================================================
# 7. EarnForex "Bollinger Bands Breakout" 1.00
# ===================================================================
def build_bb_breakout(df, period=200, dev=2.0, sl=1.5, tp=3.75, atr_n=14):
    """Close crosses above upper band -> buy, below lower -> sell. Fixed SL/TP
    (source 20/50 pips; here ATR multiples, same 1:2.5 ratio). No other exit."""
    c = _arr(df, "close")
    a = atr(df, atr_n)
    m = sma(c, period)
    sd = pd.Series(c).rolling(period).std(ddof=0).to_numpy()
    up, lo = m + dev * sd, m - dev * sd
    ok = _finite(up, lo, a) & np.isfinite(shift(up, 1))
    long_m = ok & (shift(c, 1) < shift(up, 1)) & (c > up)
    short_m = ok & (shift(c, 1) > shift(lo, 1)) & (c < lo)
    return _assemble(len(df), long_m, short_m, c - sl * a, c + sl * a,
                     c + tp * a, c - tp * a, name="bb_breakout")


# ===================================================================
# 8. EarnForex "myPickyBreakout" (2009)
# ===================================================================
def build_picky_breakout(df, lookup=8, mindiff=0.0, hold=5, sl=2.0,
                         atr_n=14, days=(1, 2, 3)):
    """Last closed bar's high exceeds each of the previous `lookup` highs
    (by > mindiff*ATR; source 3 points ~ 0) -> buy; low below all -> sell.
    Signals only when the NEXT bar opens on Tue/Wed/Thu (source DayOfWeek()
    filter; days given as weekday numbers of the next session, Mon=0).
    Exit after `hold` bars or on reverse. ADDED STOP: sl*ATR."""
    o, h, l, c = (_arr(df, k) for k in ("open", "high", "low", "close"))
    a = atr(df, atr_n)
    n = len(df)
    H = np.ones(n, bool)
    L = np.ones(n, bool)
    for k in range(1, lookup + 1):
        H &= (h - shift(h, k)) > mindiff * a
        L &= (shift(l, k) - l) > mindiff * a
    t = pd.DatetimeIndex(df["time"])
    tf = df.attrs.get("tf", "D1").upper()
    if tf == "D1":
        nxt = (t.weekday.to_numpy() + 1) % 7
        nxt[nxt == 5] = 0          # Fri -> next session Mon
        dayok = np.isin(nxt, days)
    elif days is None:
        dayok = np.ones(n, bool)
    else:
        dayok = np.isin(t.weekday.to_numpy(), days)
    ok = np.isfinite(shift(h, lookup)) & np.isfinite(a) & dayok
    both = H & L
    long_m = ok & ((H & ~L) | (both & (c >= o)))
    short_m = ok & ((L & ~H) | (both & (c < o)))
    return _assemble(n, long_m, short_m, c - sl * a, c + sl * a,
                     max_hold=hold, name="picky_breakout")


# ===================================================================
# 9. EarnForex "PersistentAnti" 1.01
# ===================================================================
def build_persistent_anti(df, N=10, ratio=0.66, reverse=True, sl=2.0, atr_n=14):
    """Count same-direction vs opposite-direction consecutive candle pairs
    over the last N pairs. reverse=True: persistence dominant -> fade the
    last candle; anti-persistence dominant -> follow it. Position held one
    bar, kept while the same signal repeats, closed when no mode dominates.
    ADDED STOP: sl*ATR."""
    o, c = _arr(df, "open"), _arr(df, "close")
    a = atr(df, atr_n)
    d = np.sign(c - o)
    dp = shift(d, 1)
    pers = ((d == dp) & (d != 0)).astype(float)
    anti = ((d == -dp) & (d != 0)).astype(float)
    P = pd.Series(pers).rolling(N).sum().to_numpy()
    A = pd.Series(anti).rolling(N).sum().to_numpy()
    bull = d > 0
    bear = d < 0
    sell_mode = ((P > ratio * N) & reverse) | ((A > ratio * N) & (not reverse))
    buy_mode = ~sell_mode & (((P > ratio * N) & (not reverse)) | ((A > ratio * N) & reverse))
    ok = _finite(P, A, a, dp)
    short_m = ok & ((sell_mode & bull) | (buy_mode & bear))
    long_m = ok & ((sell_mode & bear) | (buy_mode & bull))
    no_l = ~long_m
    no_s = ~short_m
    mg = _exit_manager(no_l, no_s)
    return _assemble(len(df), long_m, short_m, c - sl * a, c + sl * a,
                     manage_l=mg, manage_s=mg, name="persistent_anti")


# ===================================================================
# 10. Original Turtle Trading Rules (Curtis Faith, 2003) - no pyramiding
# ===================================================================
def build_turtle(df, entry_n=20, exit_n=10, stop_n=2.0, atr_n=20,
                 skip_after_win=False, side="both"):
    """Close breaks above prior entry_n-bar high -> long; exit when close
    breaks the prior exit_n-bar low; stop 2N (N = ATR(20)). Mirror shorts.
    Deviations: close-based breakout (rules use intraday touch), one unit,
    no pyramiding; skip_after_win approximated off (System 1 filter)."""
    h, l, c = _arr(df, "high"), _arr(df, "low"), _arr(df, "close")
    N = atr(df, atr_n)
    hi = shift(rolling_max(h, entry_n), 1)
    lo = shift(rolling_min(l, entry_n), 1)
    xhi = shift(rolling_max(h, exit_n), 1)
    xlo = shift(rolling_min(l, exit_n), 1)
    ok = _finite(hi, lo, xhi, xlo, N)
    long_m = ok & (c > hi)
    short_m = ok & (c < lo)
    if side == "long":
        short_m[:] = False
    elif side == "short":
        long_m[:] = False
    mg = _exit_manager(ok & (c < xlo), ok & (c > xhi))
    return _assemble(len(df), long_m, short_m, c - stop_n * N, c + stop_n * N,
                     manage_l=mg, manage_s=mg, name="turtle")


# ===================================================================
# 11. Connors RSI(2) (Connors & Alvarez, Short Term Trading Strategies That Work)
# ===================================================================
def build_connors_rsi2(df, rsi_n=2, buy_lvl=5, sell_lvl=95, trend_n=200,
                       exit_n=5, sl=2.0, atr_n=14, side="both", max_hold=None):
    """Long: close > SMA(trend_n) and RSI(2) < buy_lvl; exit close > SMA(exit_n).
    Short mirror. ADDED STOP: sl*ATR (Connors trades it without stops)."""
    c = _arr(df, "close")
    a = atr(df, atr_n)
    r = rsi(c, rsi_n)
    tr = sma(c, trend_n)
    ex = sma(c, exit_n)
    ok = _finite(r, tr, ex, a)
    long_m = ok & (c > tr) & (r < buy_lvl)
    short_m = ok & (c < tr) & (r > sell_lvl)
    if side == "long":
        short_m[:] = False
    elif side == "short":
        long_m[:] = False
    mg = _exit_manager(ok & (c > ex), ok & (c < ex))
    return _assemble(len(df), long_m, short_m, c - sl * a, c + sl * a,
                     max_hold=max_hold, manage_l=mg, manage_s=mg, name="connors_rsi2")


# ===================================================================
# 12. EarnForex "Bill Williams Alligator" 1.0
# ===================================================================
def build_alligator(df, jaw=13, jaw_s=8, teeth=8, teeth_s=5, lips=5, lips_s=3,
                    sl=2.0, tp=None, atr_n=14):
    """All three (displaced SMMA of median price) lines rising and
    lips > teeth > jaw -> buy; falling and lips < teeth < jaw -> sell.
    Exit on opposite entry (source option) or SL/TP. Signal on first bar the
    condition becomes true. Source SL/TP in pips -> ATR."""
    h, l, c = _arr(df, "high"), _arr(df, "low"), _arr(df, "close")
    a = atr(df, atr_n)
    med = (h + l) / 2
    J = shift(smma(med, jaw), jaw_s)
    T = shift(smma(med, teeth), teeth_s)
    Lp = shift(smma(med, lips), lips_s)
    rising = (J > shift(J, 1)) & (T > shift(T, 1)) & (Lp > shift(Lp, 1))
    falling = (J < shift(J, 1)) & (T < shift(T, 1)) & (Lp < shift(Lp, 1))
    bull = rising & (Lp > T) & (T > J)
    bear = falling & (Lp < T) & (T < J)
    ok = _finite(J, shift(J, 1), a)
    long_m = ok & bull & ~shift(bull.astype(float), 1).astype(bool)
    short_m = ok & bear & ~shift(bear.astype(float), 1).astype(bool)
    return _assemble(len(df), long_m, short_m, c - sl * a, c + sl * a,
                     None if tp is None else c + tp * a,
                     None if tp is None else c - tp * a, name="alligator")


# ===================================================================
# Generic "fix" wrapper: side restriction and/or trend filter on any EA
# ===================================================================
def build_filtered(df, base="bb_breakout", trend_n=0, side="both", hours=None,
                   **params):
    """Run EA `base`, then drop entries against a trend filter (long only if
    close > SMA(trend_n), short only if below; trend_n=0 disables) and/or keep
    only one side; `hours`=(start, end) keeps entries whose bar-open hour h
    satisfies start <= h <= end (broker time). Closed bars only."""
    sigs = BUILDERS[base](df, **params)
    hr = pd.DatetimeIndex(df["time"]).hour.to_numpy()
    c = _arr(df, "close")
    tr = sma(c, trend_n) if trend_n else None
    out = []
    for i, e in enumerate(sigs):
        if e is not None:
            if side != "both" and e.side != side:
                e = None
            elif hours is not None and not (hours[0] <= hr[i] <= hours[1]):
                e = None
            elif tr is not None and (not np.isfinite(tr[i]) or
                                     (e.side == "long" and c[i] <= tr[i]) or
                                     (e.side == "short" and c[i] >= tr[i])):
                e = None
        out.append(e)
    return out


BUILDERS = {k[6:]: v for k, v in globals().items() if k.startswith("build_")}
