"""search3 / exotics: from-scratch strategy builders for the exotic FX group
(USDZAR USDMXN USDNOK USDSEK EURNOK EURSEK USDSGD USDCNH USDPLN) scored by
research.prop.harness on H1 / H4 / D1.

Every builder: build_<name>(df, **params) -> list[Entry|None] of len(df),
causal (bar i only uses rows <= i). Every Entry has a stop and a defined
exit: R-multiple target, ATR trailing stop (manage), time stop (max_hold /
exit_hour) or the opposite signal (flip).

HARNESS PATCH (call patch_harness() before H.load on these symbols):
  * the stock harness only converts JPY/CHF/CAD/GBP/EUR profit currencies;
    USDZAR profit is ZAR etc.  patch_harness() teaches _attach_conv the
    quote currency of every exotic (USDXXX -> conv = 1/close of the pair
    itself; EURNOK/EURSEK -> 1/close of USDNOK/USDSEK) WITHOUT relying on
    symbol_specs.json (if the spec is missing the stock code would treat
    ZAR P&L as USD and overstate by ~18x).
  * spread floors (price units) from IC Markets raw-spread averages
    (icmarkets.com spreads page, Oct 2026) scaled x1.3 for a FundedNext
    feed, plus the bar's own spread column (harness takes the larger):
      USDZAR 0.0100  USDMXN 0.0040  USDNOK 0.0050  USDSEK 0.0040
      EURNOK 0.0055  EURSEK 0.0045  USDSGD 0.00012 USDCNH 0.00040
      USDPLN 0.0022
  * slippage: harness uses 0.1 pip; exotics gap more, so the floors above
    already carry the extra.

Clock: broker server = EET-like (New York + 7h). Oslo/Stockholm/Warsaw
(CET) = server - 1h, Johannesburg (SAST, no DST) ~ server (-1h in US
summer), Mexico City (CST, no DST) = server - 8h / -9h.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H
from research.prop.harness import Entry

SYMBOLS = ["USDZAR", "USDMXN", "USDNOK", "USDSEK", "EURNOK", "EURSEK",
           "USDSGD", "USDCNH", "USDPLN"]

SPREAD_FLOOR = {
    "USDZAR": 0.0100, "USDMXN": 0.0040, "USDNOK": 0.0050, "USDSEK": 0.0040,
    "EURNOK": 0.0055, "EURSEK": 0.0045, "USDSGD": 0.00012, "USDCNH": 0.00040,
    "USDPLN": 0.0022,
}

# quote currency -> USD conversion source (pair, invert)
_QUOTE_SRC = {"ZAR": ("USDZAR", True), "MXN": ("USDMXN", True), "NOK": ("USDNOK", True),
              "SEK": ("USDSEK", True), "SGD": ("USDSGD", True), "CNH": ("USDCNH", True),
              "PLN": ("USDPLN", True), "NZD": ("NZDUSD", False), "AUD": ("AUDUSD", False)}

_patched = False


def patch_harness():
    """Monkeypatch research.prop.harness for the exotic group (idempotent)."""
    global _patched
    if _patched:
        return
    H.SPREAD_FLOOR.update(SPREAD_FLOOR)
    orig = H._attach_conv

    def _attach_conv(df, symbol, tf):
        q = symbol[3:6]
        if q in _QUOTE_SRC:
            pair, invert = _QUOTE_SRC[q]
            src = None
            for t in (tf, "H1"):
                p = H.DATA / f"{pair.lower()}-{t.lower()}.csv"
                if p.exists():
                    src = pd.read_csv(p, usecols=["time", "close"], parse_dates=["time"])
                    break
            if src is None:
                raise FileNotFoundError(f"conversion series {pair} missing")
            src = src.drop_duplicates("time").sort_values("time")
            src["conv"] = 1.0 / src["close"] if invert else src["close"]
            out = pd.merge_asof(df, src[["time", "conv"]], on="time", direction="backward")
            out["conv"] = out["conv"].bfill()
            return out
        return orig(df, symbol, tf)

    H._attach_conv = _attach_conv

    # symbol specs: 5-digit FX defaults for the exotics if the fetch has not
    # written them yet (stock default point=0.01 would scale the bar spread
    # column 1000x for a 5-digit pair).
    orig_spec = H._spec

    def _spec():
        d = dict(orig_spec())
        for s in SYMBOLS:
            d.setdefault(s, dict(digits=5, point=1e-5, contract=100000.0, profit_ccy=s[3:6],
                                 vol_min=0.01, vol_step=0.01, vol_max=500.0))
        return d

    H._spec = _spec
    _patched = True


# ----------------------------------------------------------------- helpers
def _arr(df):
    return (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))


def atr(df, n=14):
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).rolling(n, min_periods=n).mean().to_numpy()


def ema(x, n):
    return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()


def sma(x, n):
    return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.where(d > 0, d, 0.0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = pd.Series(np.where(d < 0, -d, 0.0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).to_numpy()


def _clock(df):
    t = pd.DatetimeIndex(df.time)
    return t.hour.to_numpy(), t.weekday.to_numpy(), t.normalize().to_numpy()


def _bars_per_day(df):
    t = pd.DatetimeIndex(df.time)
    step = int((t[1:] - t[:-1]).median() / pd.Timedelta(minutes=1)) if len(t) > 2 else 60
    return max(1, 1440 // step), step


def prev_day_levels(df):
    """Yesterday's (completed day) high / low / close on every bar of today."""
    t = pd.DatetimeIndex(df.time)
    d = pd.DataFrame({"day": t.normalize(), "h": df.high.values, "l": df.low.values,
                      "c": df.close.values, "o": df.open.values})
    g = d.groupby("day").agg(h=("h", "max"), l=("l", "min"), c=("c", "last"), o=("o", "first"))
    g = g.shift(1)
    r = g.reindex(t.normalize())
    return r.h.to_numpy(), r.l.to_numpy(), r.c.to_numpy()


def prev_week_levels(df):
    t = pd.DatetimeIndex(df.time)
    wk = (t - pd.to_timedelta(t.weekday, unit="D")).normalize()
    d = pd.DataFrame({"wk": wk, "h": df.high.values, "l": df.low.values, "c": df.close.values})
    g = d.groupby("wk").agg(h=("h", "max"), l=("l", "min"), c=("c", "last")).shift(1)
    r = g.reindex(wk)
    return r.h.to_numpy(), r.l.to_numpy(), r.c.to_numpy()


def daily_series(df):
    """Completed-day OHLC aligned to every bar (yesterday = last completed)."""
    t = pd.DatetimeIndex(df.time)
    d = pd.DataFrame({"day": t.normalize(), "h": df.high.values, "l": df.low.values,
                      "c": df.close.values, "o": df.open.values})
    g = d.groupby("day").agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"))
    return g, t.normalize()


def daily_atr(df, n=14):
    g, days = daily_series(df)
    pc = g.c.shift()
    tr = np.maximum(g.h - g.l, np.maximum((g.h - pc).abs(), (g.l - pc).abs()))
    a = tr.rolling(n, min_periods=n).mean().shift(1)
    return a.reindex(days).to_numpy()


def _entry(side, c, dist, tp_r=None, max_hold=None, exit_hour=None, manage=None, meta=None):
    if not np.isfinite(dist) or dist <= 0:
        return None
    if side == "long":
        sl, tp = c - dist, (c + tp_r * dist if tp_r else None)
    else:
        sl, tp = c + dist, (c - tp_r * dist if tp_r else None)
    return Entry(side, float(sl), tp=None if tp is None else float(tp),
                 max_hold=max_hold, exit_hour=exit_hour, manage=manage, meta=meta or {})


def trail_manager(a, k, be_r=None):
    """Chandelier trail: stop = extreme since entry -/+ k*ATR[i]; only tightens.
    be_r: move stop to entry once price is be_r*initial-risk in profit."""
    def manage(df, i, pos):
        hi = df.high.values[pos["bar"] + 1:i + 1]
        lo = df.low.values[pos["bar"] + 1:i + 1]
        if len(hi) == 0 or not np.isfinite(a[i]):
            return None
        risk0 = abs(pos["entry"] - pos["sl0"])
        if pos["side"] == "long":
            ns = hi.max() - k * a[i]
            if be_r and df.close.values[i] - pos["entry"] >= be_r * risk0:
                ns = max(ns, pos["entry"])
            return float(ns) if ns > pos["sl"] else None
        ns = lo.min() + k * a[i]
        if be_r and pos["entry"] - df.close.values[i] >= be_r * risk0:
            ns = min(ns, pos["entry"])
        return float(ns) if ns < pos["sl"] else None
    manage.__name__ = f"trail_{k}_{be_r}"
    return manage


def _warm(n, i):
    return i >= n


# ===================================================================
# 1. Donchian channel breakout with ATR trail (classic trend following)
# ===================================================================
def build_donchian_trail(df, n=20, atr_n=14, sl_atr=2.0, trail_k=3.0, be_r=None,
                         long_only=False, short_only=False, exit_n=None):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    hh = pd.Series(h).rolling(n, min_periods=n).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n, min_periods=n).min().shift(1).to_numpy()
    mg = trail_manager(a, trail_k, be_r)
    out = [None] * len(df)
    for i in range(n + atr_n + 1, len(df)):
        if not np.isfinite(a[i]) or not np.isfinite(hh[i]):
            continue
        if c[i] > hh[i] and not short_only:
            out[i] = _entry("long", c[i], sl_atr * a[i], manage=mg, meta=dict(k="don"))
        elif c[i] < ll[i] and not long_only:
            out[i] = _entry("short", c[i], sl_atr * a[i], manage=mg, meta=dict(k="don"))
    return out


# ===================================================================
# 2. EMA trend + pullback to fast EMA (swing trading per IG/tastyfx USDZAR
#    guide: MA for trend, momentum for timing)
# ===================================================================
def build_ema_pullback(df, fast=20, slow=100, atr_n=14, sl_atr=1.5, tp_r=2.0,
                       rsi_n=5, rsi_lo=35, rsi_hi=65, trail_k=None, max_hold=None):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    ef, es = ema(c, fast), ema(c, slow)
    r = rsi(c, rsi_n)
    mg = trail_manager(a, trail_k) if trail_k else None
    out = [None] * len(df)
    for i in range(slow + 2, len(df)):
        if not (np.isfinite(a[i]) and np.isfinite(es[i]) and np.isfinite(r[i])):
            continue
        up = ef[i] > es[i] and c[i] > es[i]
        dn = ef[i] < es[i] and c[i] < es[i]
        # pullback: previous bar touched fast EMA, this bar closes back in trend direction
        if up and l[i - 1] <= ef[i - 1] and c[i] > ef[i] and r[i] > rsi_lo and c[i] > o[i]:
            out[i] = _entry("long", c[i], sl_atr * a[i], tp_r if not mg else None,
                            max_hold=max_hold, manage=mg)
        elif dn and h[i - 1] >= ef[i - 1] and c[i] < ef[i] and r[i] < rsi_hi and c[i] < o[i]:
            out[i] = _entry("short", c[i], sl_atr * a[i], tp_r if not mg else None,
                            max_hold=max_hold, manage=mg)
    return out


# ===================================================================
# 3. Time-series momentum (sign of N-bar return) with ATR trail / flip
# ===================================================================
def build_tsmom(df, n=60, atr_n=14, sl_atr=2.5, trail_k=None, max_hold=None,
                thresh_atr=0.0, long_only=False, short_only=False, cooldown=5):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    mg = trail_manager(a, trail_k) if trail_k else None
    out = [None] * len(df)
    last = -10**9
    for i in range(n + atr_n + 1, len(df)):
        if not np.isfinite(a[i]) or i - last < cooldown:
            continue
        mom = c[i] - c[i - n]
        if mom > thresh_atr * a[i] and not short_only:
            out[i] = _entry("long", c[i], sl_atr * a[i], max_hold=max_hold, manage=mg)
            last = i
        elif mom < -thresh_atr * a[i] and not long_only:
            out[i] = _entry("short", c[i], sl_atr * a[i], max_hold=max_hold, manage=mg)
            last = i
    return out


# ===================================================================
# 4. Multi-week range breakout with compression filter (Saxo FX breakout
#    monitor: break of 19/49-day closing high/low), D1/H4
# ===================================================================
def build_range_compression_break(df, n=20, lookback_vol=100, vol_pct=0.5, atr_n=14,
                                  sl_atr=2.0, trail_k=3.0, tp_r=None, use_close=True):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    src_h = c if use_close else h
    src_l = c if use_close else l
    hh = pd.Series(src_h).rolling(n, min_periods=n).max().shift(1).to_numpy()
    ll = pd.Series(src_l).rolling(n, min_periods=n).min().shift(1).to_numpy()
    width = (hh - ll) / a
    # range width percentile over the lookback (causal): compressed if below vol_pct quantile
    wq = pd.Series(width).rolling(lookback_vol, min_periods=lookback_vol // 2).quantile(vol_pct).to_numpy()
    mg = trail_manager(a, trail_k) if trail_k else None
    out = [None] * len(df)
    for i in range(n + lookback_vol // 2 + 2, len(df)):
        if not (np.isfinite(a[i]) and np.isfinite(hh[i]) and np.isfinite(wq[i])):
            continue
        if width[i] > wq[i]:
            continue
        if c[i] > hh[i]:
            out[i] = _entry("long", c[i], sl_atr * a[i], tp_r, manage=mg)
        elif c[i] < ll[i]:
            out[i] = _entry("short", c[i], sl_atr * a[i], tp_r, manage=mg)
    return out


# ===================================================================
# 5. European-session breakout of the Asian range (NOK/SEK/PLN desks open
#    08:00 CET = server 09:00); H1 only. Exit at end of session.
# ===================================================================
def build_session_range_break(df, asia_start=1, asia_end=8, trade_start=9, trade_end=15,
                              exit_hour=20, atr_n=14, sl_atr=1.0, tp_r=1.5,
                              min_range_atr=0.3, max_range_atr=1.5, sl_mode="atr"):
    o, h, l, c = _arr(df)
    hrs, wd, days = _clock(df)
    a = daily_atr(df, atr_n)
    out = [None] * len(df)
    rh = rl = np.nan
    day = None
    traded = False
    for i in range(len(df)):
        if days[i] != day:
            day, rh, rl, traded = days[i], np.nan, np.nan, False
        if asia_start <= hrs[i] <= asia_end:
            rh = h[i] if not np.isfinite(rh) else max(rh, h[i])
            rl = l[i] if not np.isfinite(rl) else min(rl, l[i])
            continue
        if traded or not (trade_start <= hrs[i] <= trade_end) or not np.isfinite(rh) or not np.isfinite(a[i]):
            continue
        rng = rh - rl
        if rng < min_range_atr * a[i] or rng > max_range_atr * a[i]:
            continue
        if c[i] > rh:
            dist = sl_atr * a[i] if sl_mode == "atr" else max(c[i] - rl, 0.2 * a[i])
            out[i] = _entry("long", c[i], dist, tp_r, exit_hour=exit_hour)
            traded = True
        elif c[i] < rl:
            dist = sl_atr * a[i] if sl_mode == "atr" else max(rh - c[i], 0.2 * a[i])
            out[i] = _entry("short", c[i], dist, tp_r, exit_hour=exit_hour)
            traded = True
    return out


# ===================================================================
# 6. Prior-day high/low break (market structure) on H1, intraday exit
# ===================================================================
def build_pdh_pdl_break(df, trade_start=8, trade_end=16, exit_hour=22, atr_n=14, sl_atr=0.8,
                        tp_r=2.0, trend_n=None, one_per_day=True, confirm_atr=0.0):
    o, h, l, c = _arr(df)
    hrs, wd, days = _clock(df)
    a = daily_atr(df, atr_n)
    ph, pl, pc = prev_day_levels(df)
    tr = sma(c, trend_n) if trend_n else None
    out = [None] * len(df)
    day, traded = None, False
    for i in range(1, len(df)):
        if days[i] != day:
            day, traded = days[i], False
        if (one_per_day and traded) or not (trade_start <= hrs[i] <= trade_end):
            continue
        if not (np.isfinite(ph[i]) and np.isfinite(a[i])):
            continue
        if c[i] > ph[i] + confirm_atr * a[i] and c[i - 1] <= ph[i] and (tr is None or c[i] > tr[i]):
            out[i] = _entry("long", c[i], sl_atr * a[i], tp_r, exit_hour=exit_hour)
            traded = True
        elif c[i] < pl[i] - confirm_atr * a[i] and c[i - 1] >= pl[i] and (tr is None or c[i] < tr[i]):
            out[i] = _entry("short", c[i], sl_atr * a[i], tp_r, exit_hour=exit_hour)
            traded = True
    return out


# ===================================================================
# 7. Prior-day high/low FADE (sweep and reject) for the managed pairs
# ===================================================================
def build_pdh_pdl_fade(df, trade_start=3, trade_end=18, atr_n=14, sl_atr=0.6, tp_r=1.5,
                       max_hold=12, wick_frac=0.4):
    o, h, l, c = _arr(df)
    hrs, wd, days = _clock(df)
    a = daily_atr(df, atr_n)
    ph, pl, pc = prev_day_levels(df)
    out = [None] * len(df)
    for i in range(1, len(df)):
        if not (trade_start <= hrs[i] <= trade_end) or not (np.isfinite(ph[i]) and np.isfinite(a[i])):
            continue
        rng = max(h[i] - l[i], 1e-12)
        if h[i] > ph[i] and c[i] < ph[i] and (h[i] - c[i]) / rng >= wick_frac:
            out[i] = _entry("short", c[i], sl_atr * a[i], tp_r, max_hold=max_hold)
        elif l[i] < pl[i] and c[i] > pl[i] and (c[i] - l[i]) / rng >= wick_frac:
            out[i] = _entry("long", c[i], sl_atr * a[i], tp_r, max_hold=max_hold)
    return out


# ===================================================================
# 8. Bollinger band mean reversion (USDSGD / USDCNH managed-range idea)
# ===================================================================
def build_bb_revert(df, n=20, k=2.0, atr_n=14, sl_atr=1.5, exit="mid", tp_r=1.0,
                    max_hold=24, trend_n=None, trend_mode="with"):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    m = sma(c, n)
    sd = pd.Series(c).rolling(n, min_periods=n).std(ddof=0).to_numpy()
    up, lo = m + k * sd, m - k * sd
    tr = sma(c, trend_n) if trend_n else None

    def mid_exit(df_, i, pos):
        mm = m[i]
        if not np.isfinite(mm):
            return None
        if pos["side"] == "long" and df_.close.values[i] >= mm:
            return "close"
        if pos["side"] == "short" and df_.close.values[i] <= mm:
            return "close"
        return None
    mid_exit.__name__ = "mid_exit"
    mg = mid_exit if exit == "mid" else None
    out = [None] * len(df)
    for i in range(max(n, atr_n, trend_n or 0) + 1, len(df)):
        if not (np.isfinite(a[i]) and np.isfinite(up[i])):
            continue
        if tr is not None:
            ok_long = (c[i] > tr[i]) if trend_mode == "with" else (c[i] < tr[i])
            ok_short = (c[i] < tr[i]) if trend_mode == "with" else (c[i] > tr[i])
        else:
            ok_long = ok_short = True
        if c[i] < lo[i] and c[i - 1] >= lo[i - 1] and ok_long:
            out[i] = _entry("long", c[i], sl_atr * a[i], None if mg else tp_r, max_hold=max_hold, manage=mg)
        elif c[i] > up[i] and c[i - 1] <= up[i - 1] and ok_short:
            out[i] = _entry("short", c[i], sl_atr * a[i], None if mg else tp_r, max_hold=max_hold, manage=mg)
    return out


# ===================================================================
# 9. RSI(2) pullback in the direction of the long trend (Connors style)
# ===================================================================
def build_rsi2_trend(df, rsi_n=2, lo=10, hi=90, trend_n=200, atr_n=14, sl_atr=2.0,
                     max_hold=10, exit_rsi=50, tp_r=None):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    r = rsi(c, rsi_n)
    tr = sma(c, trend_n)

    def rsi_exit(df_, i, pos):
        if not np.isfinite(r[i]):
            return None
        if pos["side"] == "long" and r[i] >= exit_rsi:
            return "close"
        if pos["side"] == "short" and r[i] <= 100 - exit_rsi:
            return "close"
        return None
    rsi_exit.__name__ = "rsi_exit"
    mg = rsi_exit if tp_r is None else None
    out = [None] * len(df)
    for i in range(trend_n + 1, len(df)):
        if not (np.isfinite(a[i]) and np.isfinite(r[i]) and np.isfinite(tr[i])):
            continue
        if c[i] > tr[i] and r[i] < lo:
            out[i] = _entry("long", c[i], sl_atr * a[i], tp_r, max_hold=max_hold, manage=mg)
        elif c[i] < tr[i] and r[i] > hi:
            out[i] = _entry("short", c[i], sl_atr * a[i], tp_r, max_hold=max_hold, manage=mg)
    return out


# ===================================================================
# 10. Round-number (big figure) break / fade
# ===================================================================
def _figure_step(price):
    """Big-figure step scaled to price: ZAR ~18 -> 0.10, MXN ~20 -> 0.10,
    NOK ~10 -> 0.05, SGD ~1.3 -> 0.005, CNH ~7 -> 0.05, PLN ~4 -> 0.01."""
    if price >= 15:
        return 0.10
    if price >= 5:
        return 0.05
    if price >= 2:
        return 0.01
    return 0.005


def build_round_number(df, mode="break", atr_n=14, sl_atr=1.0, tp_r=1.5, max_hold=24,
                       trade_start=3, trade_end=20, step_mult=1.0):
    o, h, l, c = _arr(df)
    hrs, wd, days = _clock(df)
    a = atr(df, atr_n)
    out = [None] * len(df)
    for i in range(atr_n + 2, len(df)):
        if not np.isfinite(a[i]) or not (trade_start <= hrs[i] <= trade_end):
            continue
        st = _figure_step(c[i]) * step_mult
        lvl_up = np.floor(c[i] / st) * st       # level just below close
        lvl_dn = np.ceil(c[i] / st) * st        # level just above close
        if mode == "break":
            # close crossed a figure this bar (prev close on the other side)
            if c[i - 1] < lvl_up <= c[i] and (c[i] - lvl_up) < 0.5 * a[i]:
                out[i] = _entry("long", c[i], sl_atr * a[i], tp_r, max_hold=max_hold)
            elif c[i - 1] > lvl_dn >= c[i] and (lvl_dn - c[i]) < 0.5 * a[i]:
                out[i] = _entry("short", c[i], sl_atr * a[i], tp_r, max_hold=max_hold)
        else:  # fade: wick through the figure, close back on the original side
            if h[i] > lvl_dn and c[i] < lvl_dn and o[i] < lvl_dn and (lvl_dn - c[i]) < 0.5 * a[i]:
                out[i] = _entry("short", c[i], sl_atr * a[i], tp_r, max_hold=max_hold)
            elif l[i] < lvl_up and c[i] > lvl_up and o[i] > lvl_up and (c[i] - lvl_up) < 0.5 * a[i]:
                out[i] = _entry("long", c[i], sl_atr * a[i], tp_r, max_hold=max_hold)
    return out


# ===================================================================
# 11. Volatility squeeze (ATR percentile low) then N-bar breakout
# ===================================================================
def build_squeeze_break(df, atr_n=14, atr_long=100, pct=0.25, n=10, sl_atr=1.5, tp_r=3.0,
                        trail_k=None, max_hold=None):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    aq = pd.Series(a).rolling(atr_long, min_periods=atr_long // 2).quantile(pct).to_numpy()
    hh = pd.Series(h).rolling(n, min_periods=n).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n, min_periods=n).min().shift(1).to_numpy()
    mg = trail_manager(a, trail_k) if trail_k else None
    out = [None] * len(df)
    for i in range(atr_long // 2 + n + 2, len(df)):
        if not (np.isfinite(a[i]) and np.isfinite(aq[i]) and np.isfinite(hh[i])):
            continue
        if a[i - 1] > aq[i - 1]:
            continue
        if c[i] > hh[i]:
            out[i] = _entry("long", c[i], sl_atr * a[i], None if mg else tp_r, max_hold=max_hold, manage=mg)
        elif c[i] < ll[i]:
            out[i] = _entry("short", c[i], sl_atr * a[i], None if mg else tp_r, max_hold=max_hold, manage=mg)
    return out


# ===================================================================
# 12. Weekend gap fade (Monday open vs Friday close), H1
# ===================================================================
def build_gap_fade(df, min_gap_atr=0.15, max_gap_atr=2.0, atr_n=14, sl_atr=1.0, tp="fill",
                   tp_r=1.0, max_hold=24, direction="fade"):
    o, h, l, c = _arr(df)
    hrs, wd, days = _clock(df)
    a = daily_atr(df, atr_n)
    out = [None] * len(df)
    for i in range(1, len(df)):
        if days[i] == days[i - 1]:
            continue
        gap_days = (days[i] - days[i - 1]) / np.timedelta64(1, "D")
        if gap_days < 2 or not np.isfinite(a[i]):
            continue  # weekend gap only (Fri -> Mon)
        gap = o[i] - c[i - 1]
        if abs(gap) < min_gap_atr * a[i] or abs(gap) > max_gap_atr * a[i]:
            continue
        side = ("short" if gap > 0 else "long") if direction == "fade" else ("long" if gap > 0 else "short")
        if tp == "fill" and direction == "fade":
            tgt = c[i - 1]
            dist = sl_atr * a[i]
            e = _entry(side, c[i], dist, None, max_hold=max_hold)
            if e is None:
                continue
            if (side == "short" and tgt < c[i]) or (side == "long" and tgt > c[i]):
                e.tp = float(tgt)
            else:
                continue
            out[i] = e
        else:
            out[i] = _entry(side, c[i], sl_atr * a[i], tp_r, max_hold=max_hold)
    return out


# ===================================================================
# 13. Inside-day / NR-k breakout on D1 (contraction -> expansion)
# ===================================================================
def build_inside_day_break(df, k_nr=7, atr_n=14, sl_mode="range", sl_atr=1.0, tp_r=2.0,
                           max_hold=5, require_inside=False):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    rng = h - l
    nr = pd.Series(rng).rolling(k_nr, min_periods=k_nr).min().to_numpy()
    out = [None] * len(df)
    for i in range(k_nr + atr_n + 2, len(df)):
        if not np.isfinite(a[i]):
            continue
        j = i - 1   # setup bar is yesterday; today's close breaks it
        setup = rng[j] <= nr[j]
        if require_inside:
            setup = setup and h[j] <= h[j - 1] and l[j] >= l[j - 1]
        if not setup:
            continue
        if c[i] > h[j]:
            dist = (c[i] - l[j]) if sl_mode == "range" else sl_atr * a[i]
            out[i] = _entry("long", c[i], dist, tp_r, max_hold=max_hold)
        elif c[i] < l[j]:
            dist = (h[j] - c[i]) if sl_mode == "range" else sl_atr * a[i]
            out[i] = _entry("short", c[i], dist, tp_r, max_hold=max_hold)
    return out


# ===================================================================
# 14. Risk-off spike: big up-day in USD-EM pair -> continuation (carry
#     unwinds cluster) or fade (overshoot). D1 / H4.
# ===================================================================
def build_spike_follow(df, n_ret=1, spike_atr=1.5, atr_n=14, mode="follow", sl_atr=1.5,
                       tp_r=2.0, max_hold=5, side_filter=None):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    out = [None] * len(df)
    for i in range(n_ret + atr_n + 1, len(df)):
        if not np.isfinite(a[i]):
            continue
        mv = c[i] - c[i - n_ret]
        if abs(mv) < spike_atr * a[i]:
            continue
        up = mv > 0
        side = ("long" if up else "short") if mode == "follow" else ("short" if up else "long")
        if side_filter and side != side_filter:
            continue
        out[i] = _entry(side, c[i], sl_atr * a[i], tp_r, max_hold=max_hold)
    return out


# ===================================================================
# 15. Hour-of-day drift (from the market study): enter at hour h, exit at
#     hour h2, optional direction from D1 trend. Explicit time exit.
# ===================================================================
def build_hour_drift(df, enter_hour=9, exit_hour=16, side="long", atr_n=14, sl_atr=1.0,
                     weekdays=None, trend_n=None):
    o, h, l, c = _arr(df)
    hrs, wd, days = _clock(df)
    a = daily_atr(df, atr_n)
    tr = sma(c, trend_n) if trend_n else None
    out = [None] * len(df)
    for i in range(1, len(df)):
        if hrs[i] != enter_hour or not np.isfinite(a[i]):
            continue
        if weekdays is not None and wd[i] not in weekdays:
            continue
        s = side
        if tr is not None and np.isfinite(tr[i]):
            s = "long" if c[i] > tr[i] else "short"
            if side in ("long", "short") and s != side:
                continue
        out[i] = _entry(s, c[i], sl_atr * a[i], None, exit_hour=exit_hour)
    return out


# ===================================================================
# 16. Prior-week high/low break on H4 (multi-day structure), ATR trail
# ===================================================================
def build_pwh_pwl_break(df, atr_n=14, sl_atr=1.5, trail_k=2.5, tp_r=None, max_hold=None,
                        trend_n=None):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    wh, wl, wc = prev_week_levels(df)
    tr = sma(c, trend_n) if trend_n else None
    mg = trail_manager(a, trail_k) if trail_k else None
    out = [None] * len(df)
    for i in range(atr_n + 2, len(df)):
        if not (np.isfinite(a[i]) and np.isfinite(wh[i])):
            continue
        if c[i] > wh[i] and c[i - 1] <= wh[i] and (tr is None or c[i] > tr[i]):
            out[i] = _entry("long", c[i], sl_atr * a[i], tp_r, max_hold=max_hold, manage=mg)
        elif c[i] < wl[i] and c[i - 1] >= wl[i] and (tr is None or c[i] < tr[i]):
            out[i] = _entry("short", c[i], sl_atr * a[i], tp_r, max_hold=max_hold, manage=mg)
    return out


# ===================================================================
# 17. Keltner channel trend ride: close outside channel in trend direction,
#     exit on close back through the midline (opposite-side / manage exit)
# ===================================================================
def build_keltner_ride(df, n=20, k=1.5, atr_n=14, sl_atr=2.0, trend_n=100, max_hold=None):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    m = ema(c, n)
    tr = ema(c, trend_n)
    up, lo = m + k * a, m - k * a

    def mid_exit(df_, i, pos):
        if not np.isfinite(m[i]):
            return None
        cc = df_.close.values[i]
        if pos["side"] == "long" and cc < m[i]:
            return "close"
        if pos["side"] == "short" and cc > m[i]:
            return "close"
        return None
    mid_exit.__name__ = "kelt_mid"
    out = [None] * len(df)
    for i in range(max(n, trend_n, atr_n) + 2, len(df)):
        if not (np.isfinite(a[i]) and np.isfinite(tr[i]) and np.isfinite(up[i])):
            continue
        if c[i] > up[i] and c[i - 1] <= up[i - 1] and m[i] > tr[i]:
            out[i] = _entry("long", c[i], sl_atr * a[i], None, max_hold=max_hold, manage=mid_exit)
        elif c[i] < lo[i] and c[i - 1] >= lo[i - 1] and m[i] < tr[i]:
            out[i] = _entry("short", c[i], sl_atr * a[i], None, max_hold=max_hold, manage=mid_exit)
    return out


# ===================================================================
# 18. Day-of-week / session drift: enter at day open (first bar of the day)
#     in the direction of yesterday's close-to-close move (daily momentum)
#     or against it (daily reversal). Exit at end of day.
# ===================================================================
def build_daily_follow(df, mode="follow", min_move_atr=0.3, atr_n=14, sl_atr=0.8,
                       tp_r=None, exit_hour=23, enter_hour=None, weekdays=None):
    o, h, l, c = _arr(df)
    hrs, wd, days = _clock(df)
    a = daily_atr(df, atr_n)
    ph, pl, pc = prev_day_levels(df)
    # prior day's close-to-close move: pc[i] - close of the day before
    g, dd = daily_series(df)
    mv = (g.c - g.c.shift(1)).shift(1).reindex(dd).to_numpy()
    out = [None] * len(df)
    for i in range(1, len(df)):
        first = days[i] != days[i - 1] if enter_hour is None else hrs[i] == enter_hour
        if not first or not (np.isfinite(a[i]) and np.isfinite(mv[i])):
            continue
        if weekdays is not None and wd[i] not in weekdays:
            continue
        if abs(mv[i]) < min_move_atr * a[i]:
            continue
        up = mv[i] > 0
        side = ("long" if up else "short") if mode == "follow" else ("short" if up else "long")
        out[i] = _entry(side, c[i], sl_atr * a[i], tp_r, exit_hour=exit_hour)
    return out


# ===================================================================
# 19. Double EMA crossover with flip (always-in trend following), D1/H4
# ===================================================================
def build_ema_cross_flip(df, fast=10, slow=40, atr_n=14, sl_atr=3.0, trail_k=None,
                         min_sep_atr=0.0):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    ef, es = ema(c, fast), ema(c, slow)
    mg = trail_manager(a, trail_k) if trail_k else None
    out = [None] * len(df)
    for i in range(slow + 2, len(df)):
        if not (np.isfinite(a[i]) and np.isfinite(es[i - 1])):
            continue
        if ef[i] > es[i] + min_sep_atr * a[i] and ef[i - 1] <= es[i - 1]:
            out[i] = _entry("long", c[i], sl_atr * a[i], manage=mg)
        elif ef[i] < es[i] - min_sep_atr * a[i] and ef[i - 1] >= es[i - 1]:
            out[i] = _entry("short", c[i], sl_atr * a[i], manage=mg)
    return out


# ===================================================================
# 20. Carry-direction trend (USD-EM drift): trade only the long-USD side
#     of a breakout when price is above the long MA (depreciation drift of
#     ZAR/MXN/PLN), or only the short side for the managed pairs.
# ===================================================================
def build_carry_trend(df, n=20, trend_n=200, atr_n=14, sl_atr=2.0, trail_k=3.0, side="long"):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    tr = sma(c, trend_n)
    hh = pd.Series(h).rolling(n, min_periods=n).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n, min_periods=n).min().shift(1).to_numpy()
    mg = trail_manager(a, trail_k)
    out = [None] * len(df)
    for i in range(max(n, trend_n) + 2, len(df)):
        if not (np.isfinite(a[i]) and np.isfinite(tr[i]) and np.isfinite(hh[i])):
            continue
        if side == "long" and c[i] > hh[i] and c[i] > tr[i]:
            out[i] = _entry("long", c[i], sl_atr * a[i], manage=mg)
        elif side == "short" and c[i] < ll[i] and c[i] < tr[i]:
            out[i] = _entry("short", c[i], sl_atr * a[i], manage=mg)
    return out


BUILDERS = {k[6:]: v for k, v in globals().items() if k.startswith("build_")}


# ----------------------------------------------------------------- data quality
def clean(df):
    """Drop stale/flat days (daily range < 5% of the median daily range) and
    zero-volume bars; keeps df.attrs. Counts stored in df.attrs['dq']."""
    t = pd.DatetimeIndex(df.time)
    day = t.normalize()
    rng = (df.high - df.low).groupby(day).transform("max") - (df.high - df.low).groupby(day).transform("min")
    drng = df.groupby(day).high.transform("max") - df.groupby(day).low.transform("min")
    med = drng.groupby(day).first().median()
    flat = drng < 0.05 * med
    zero = (df.tick_volume == 0) if "tick_volume" in df else pd.Series(False, index=df.index)
    keep = ~(flat | zero)
    attrs = dict(df.attrs)
    out = df[keep.to_numpy()].reset_index(drop=True)
    attrs["dq"] = dict(flat_bars=int(flat.sum()), zero_vol_bars=int(zero.sum()),
                       flat_days=int(flat.groupby(day).first().sum()))
    out.attrs.update(attrs)
    return out


# ===================================================================
# 21. Swing break-of-structure: fractal swing highs/lows (k bars each side);
#     break of the last swing high in an up-trend (close > SMA) -> long,
#     stop under the last swing low (min sl_atr*ATR); mirror for shorts.
# ===================================================================
def build_swing_bos(df, k=3, atr_n=14, sl_atr=1.0, trend_n=100, tp_r=None, trail_k=3.0,
                    max_hold=None, max_sl_atr=4.0):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    tr = sma(c, trend_n) if trend_n else None
    mg = trail_manager(a, trail_k) if trail_k else None
    out = [None] * len(df)
    last_sh = last_sl = np.nan
    for i in range(max(atr_n, trend_n or 0) + 2 * k + 1, len(df)):
        j = i - k                      # bar j is a confirmed swing once k later bars are closed
        if h[j] == h[j - k:j + k + 1].max():
            last_sh = h[j]
        if l[j] == l[j - k:j + k + 1].min():
            last_sl = l[j]
        if not np.isfinite(a[i]):
            continue
        if np.isfinite(last_sh) and c[i] > last_sh and c[i - 1] <= last_sh and (tr is None or c[i] > tr[i]):
            dist = c[i] - last_sl if np.isfinite(last_sl) else sl_atr * a[i]
            dist = min(max(dist, sl_atr * a[i]), max_sl_atr * a[i])
            out[i] = _entry("long", c[i], dist, tp_r, max_hold=max_hold, manage=mg)
            last_sh = np.nan
        elif np.isfinite(last_sl) and c[i] < last_sl and c[i - 1] >= last_sl and (tr is None or c[i] < tr[i]):
            dist = last_sh - c[i] if np.isfinite(last_sh) else sl_atr * a[i]
            dist = min(max(dist, sl_atr * a[i]), max_sl_atr * a[i])
            out[i] = _entry("short", c[i], dist, tp_r, max_hold=max_hold, manage=mg)
            last_sl = np.nan
    return out


# ===================================================================
# 22. Multi-week range box fade (managed / range pairs): when the N-bar range
#     is tight (< box_atr * ATR), buy the bottom q of the box, sell the top q,
#     target the box middle, stop outside the box.
# ===================================================================
def build_range_box_fade(df, n=20, atr_n=14, box_atr=4.0, q=0.15, sl_atr=1.0, max_hold=10,
                         exit="mid", tp_r=1.0):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    hh = pd.Series(h).rolling(n).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n).min().shift(1).to_numpy()
    out = [None] * len(df)
    for i in range(n + atr_n + 1, len(df)):
        if not (np.isfinite(a[i]) and np.isfinite(hh[i])):
            continue
        box = hh[i] - ll[i]
        if box <= 0 or box > box_atr * a[i]:
            continue
        mid = (hh[i] + ll[i]) / 2
        if c[i] <= ll[i] + q * box and c[i] > ll[i] - 0.5 * a[i]:
            dist = max(c[i] - (ll[i] - sl_atr * a[i]), 0.3 * a[i])
            tp = mid if exit == "mid" else c[i] + tp_r * dist
            out[i] = Entry("long", float(c[i] - dist), tp=float(tp), max_hold=max_hold)
        elif c[i] >= hh[i] - q * box and c[i] < hh[i] + 0.5 * a[i]:
            dist = max((hh[i] + sl_atr * a[i]) - c[i], 0.3 * a[i])
            tp = mid if exit == "mid" else c[i] - tp_r * dist
            out[i] = Entry("short", float(c[i] + dist), tp=float(tp), max_hold=max_hold)
    return out


# ===================================================================
# 23. Three-bar pullback in a trend: m consecutive counter-trend closes while
#     price stays on the trend side of the SMA, enter when a bar closes back
#     in the trend direction.
# ===================================================================
def build_three_bar_pullback(df, m=3, trend_n=50, atr_n=14, sl_atr=1.5, tp_r=2.0, max_hold=15,
                             trail_k=None):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    tr = sma(c, trend_n)
    mg = trail_manager(a, trail_k) if trail_k else None
    out = [None] * len(df)
    for i in range(trend_n + m + 2, len(df)):
        if not np.isfinite(a[i]):
            continue
        dn = all(c[i - j] < c[i - j - 1] for j in range(1, m + 1))
        up = all(c[i - j] > c[i - j - 1] for j in range(1, m + 1))
        if c[i] > tr[i] and dn and c[i] > c[i - 1]:
            out[i] = _entry("long", c[i], sl_atr * a[i], None if trail_k else tp_r, max_hold=max_hold, manage=mg)
        elif c[i] < tr[i] and up and c[i] < c[i - 1]:
            out[i] = _entry("short", c[i], sl_atr * a[i], None if trail_k else tp_r, max_hold=max_hold, manage=mg)
    return out


# ===================================================================
# 24. Prior-week high/low sweep-and-reject (H4/H1): bar trades through the
#     previous week's extreme and closes back inside -> fade.
# ===================================================================
def build_pwh_pwl_fade(df, atr_n=14, sl_atr=1.0, tp_r=1.5, max_hold=18, min_pen_atr=0.1):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    wh, wl, wc = prev_week_levels(df)
    out = [None] * len(df)
    for i in range(atr_n + 2, len(df)):
        if not (np.isfinite(a[i]) and np.isfinite(wh[i])):
            continue
        if h[i] > wh[i] + min_pen_atr * a[i] and c[i] < wh[i]:
            out[i] = _entry("short", c[i], max(h[i] - c[i], sl_atr * a[i]), tp_r, max_hold=max_hold)
        elif l[i] < wl[i] - min_pen_atr * a[i] and c[i] > wl[i]:
            out[i] = _entry("long", c[i], max(c[i] - l[i], sl_atr * a[i]), tp_r, max_hold=max_hold)
    return out


# ===================================================================
# 25. Weekly open follow (D1/H4): on the first bar of the week, if last week
#     closed above/below the close `weeks` weeks earlier, hold that side
#     (or fade it) for the week.
# ===================================================================
def build_weekly_open_follow(df, weeks=4, atr_n=14, sl_atr=1.5, mode="follow", tp_r=None):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    t = pd.DatetimeIndex(df.time)
    wk = (t - pd.to_timedelta(t.weekday, unit="D")).normalize().to_numpy()
    wh, wl, wc = prev_week_levels(df)
    d = pd.DataFrame({"wk": wk, "c": c})
    g = d.groupby("wk").c.last()
    ref = g.shift(weeks).reindex(wk).to_numpy()
    bpd, _ = _bars_per_day(df)
    hold = 5 * bpd - 1
    out = [None] * len(df)
    for i in range(1, len(df)):
        if wk[i] == wk[i - 1] or not (np.isfinite(a[i]) and np.isfinite(wc[i]) and np.isfinite(ref[i])):
            continue
        up = wc[i] > ref[i]
        side = ("long" if up else "short") if mode == "follow" else ("short" if up else "long")
        out[i] = _entry(side, c[i], sl_atr * a[i], tp_r, max_hold=hold)
    return out


# ===================================================================
# 26. Volatility-regime momentum (risk-off trends): tsmom entries only while
#     ATR is above (rising) or below (falling) its own SMA.
# ===================================================================
def build_vol_regime_tsmom(df, n=20, atr_n=14, vol_n=50, sl_atr=2.0, trail_k=3.0, max_hold=None,
                           regime="rising", cooldown=5):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    av = sma(a, vol_n)
    mg = trail_manager(a, trail_k) if trail_k else None
    out = [None] * len(df)
    last = -10**9
    for i in range(n + atr_n + vol_n + 1, len(df)):
        if not (np.isfinite(a[i]) and np.isfinite(av[i])) or i - last < cooldown:
            continue
        ok = a[i] > av[i] if regime == "rising" else a[i] < av[i]
        if not ok:
            continue
        mom = c[i] - c[i - n]
        if mom > 0:
            out[i] = _entry("long", c[i], sl_atr * a[i], max_hold=max_hold, manage=mg)
            last = i
        elif mom < 0:
            out[i] = _entry("short", c[i], sl_atr * a[i], max_hold=max_hold, manage=mg)
            last = i
    return out


# ===================================================================
# 27. London-fix fade (H1): the move over the `lookback` hours into the
#     16:00 London fix (server 18:00 winter / 17:00 summer) faded (or
#     followed) at the fix bar close.
# ===================================================================
def build_london_fix_fade(df, fix_hour=18, lookback=3, min_move_atr=0.6, atr_n=14, sl_atr=1.0,
                          tp_r=1.0, max_hold=6, mode="fade"):
    o, h, l, c = _arr(df)
    a = atr(df, atr_n)
    hr, wd, _ = _clock(df)
    out = [None] * len(df)
    for i in range(atr_n + lookback + 1, len(df)):
        if hr[i] != fix_hour or not np.isfinite(a[i]):
            continue
        mv = c[i] - c[i - lookback]
        if abs(mv) < min_move_atr * a[i]:
            continue
        up = mv > 0
        side = ("short" if up else "long") if mode == "fade" else ("long" if up else "short")
        out[i] = _entry(side, c[i], sl_atr * a[i], tp_r, max_hold=max_hold)
    return out
