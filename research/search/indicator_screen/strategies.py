"""Indicator screen: ~15 classic indicators, simple causal entry rules, ONE exit.

Standard exit for every rule: stop = 2 x ATR(14), target = 3 x ATR(14),
time exit after 48 bars. Optional trend filter: long only above SMA(200),
short only below it. Every indicator is trailing (rolling / ewm on rows <= i),
entries fire on the bar where the event happens (cross on close of bar i).

Public API
    rule_events(df, rule) -> (long_bool, short_bool) numpy arrays
    build_rule(df, rule, trend=False, sides="both", sl_atr=2, tp_atr=3, hold=48)
    build_<candidate>(df, **params)  - named wrappers for the shortlisted rules
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H


# ---------------------------------------------------------------- indicators
def _wilder(s, n):
    return s.ewm(alpha=1.0 / n, adjust=False).mean()


def atr(df, n=14):
    h, l, c = df.high, df.low, df.close
    pc = c.shift()
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return _wilder(tr, n)


def rsi(c, n=14):
    d = c.diff()
    up = _wilder(d.clip(lower=0), n)
    dn = _wilder((-d).clip(lower=0), n)
    return 100 - 100 / (1 + up / dn.replace(0, np.nan))


def macd(c, f=12, s=26, sig=9):
    m = c.ewm(span=f, adjust=False).mean() - c.ewm(span=s, adjust=False).mean()
    return m, m.ewm(span=sig, adjust=False).mean()


def stoch(df, n=14, k=3, d=3):
    ll = df.low.rolling(n).min()
    hh = df.high.rolling(n).max()
    raw = 100 * (df.close - ll) / (hh - ll).replace(0, np.nan)
    K = raw.rolling(k).mean()
    return K, K.rolling(d).mean()


def cci(df, n=20):
    tp = (df.high + df.low + df.close) / 3
    ma = tp.rolling(n).mean()
    md = tp.rolling(n).apply(lambda x: np.abs(x - x.mean()).mean(), raw=True)
    return (tp - ma) / (0.015 * md)


def dmi(df, n=14):
    up = df.high.diff()
    dn = -df.low.diff()
    pdm = pd.Series(np.where((up > dn) & (up > 0), up, 0.0), index=df.index)
    ndm = pd.Series(np.where((dn > up) & (dn > 0), dn, 0.0), index=df.index)
    a = atr(df, n)
    pdi = 100 * _wilder(pdm, n) / a
    ndi = 100 * _wilder(ndm, n) / a
    dx = 100 * (pdi - ndi).abs() / (pdi + ndi).replace(0, np.nan)
    return pdi, ndi, _wilder(dx, n)


def bollinger_pb(c, n=20, k=2.0):
    ma = c.rolling(n).mean()
    sd = c.rolling(n).std(ddof=0)
    return (c - (ma - k * sd)) / (2 * k * sd)


def keltner(df, n=20, k=2.0):
    mid = df.close.ewm(span=n, adjust=False).mean()
    a = atr(df, n)
    return mid + k * a, mid - k * a


def atr_pct(df, n=14, look=500):
    a = atr(df, n) / df.close
    return a.rolling(look).rank(pct=True)


def aroon(df, n=25):
    up = df.high.rolling(n + 1).apply(lambda x: np.argmax(x), raw=True) / n * 100
    dn = df.low.rolling(n + 1).apply(lambda x: np.argmin(x), raw=True) / n * 100
    return up, dn


def williams_r(df, n=14):
    hh = df.high.rolling(n).max()
    ll = df.low.rolling(n).min()
    return -100 * (hh - df.close) / (hh - ll).replace(0, np.nan)


def mfi(df, n=14):
    tp = (df.high + df.low + df.close) / 3
    mf = tp * df.tick_volume
    pos = mf.where(tp > tp.shift(), 0.0).rolling(n).sum()
    neg = mf.where(tp < tp.shift(), 0.0).rolling(n).sum()
    return 100 - 100 / (1 + pos / neg.replace(0, np.nan))


def cmf(df, n=20):
    rng = (df.high - df.low).replace(0, np.nan)
    mfm = ((df.close - df.low) - (df.high - df.close)) / rng
    return (mfm.fillna(0) * df.tick_volume).rolling(n).sum() / df.tick_volume.rolling(n).sum()


def obv(df):
    return (np.sign(df.close.diff()).fillna(0) * df.tick_volume).cumsum()


def heikin_ashi(df):
    hc = (df.open + df.high + df.low + df.close) / 4
    ho = np.empty(len(df))
    o, cv = df.open.to_numpy(float), hc.to_numpy(float)
    ho[0] = (o[0] + df.close.iloc[0]) / 2
    for i in range(1, len(df)):
        ho[i] = (ho[i - 1] + cv[i - 1]) / 2
    return pd.Series(ho, index=df.index), hc


def donchian_pos(df, n=20):
    hh = df.high.rolling(n).max()
    ll = df.low.rolling(n).min()
    return (df.close - ll) / (hh - ll).replace(0, np.nan)


# ---------------------------------------------------------------- rules
def _xup(a, b):
    """a crosses above b on this bar (both may be series or scalars)."""
    a = pd.Series(a)
    b = b if np.isscalar(b) else pd.Series(b)
    pa, pb = a.shift(), (b if np.isscalar(b) else b.shift())
    return ((a > b) & (pa <= pb)).fillna(False).to_numpy()


def _xdn(a, b):
    a = pd.Series(a)
    pa, pb = a.shift(), (b if np.isscalar(b) else b.shift())
    return ((a < b) & (pa >= pb)).fillna(False).to_numpy()


def rule_events(df: pd.DataFrame, rule: str, p: dict | None = None):
    """Return (long_events, short_events) boolean arrays. `p` overrides the
    rule's main period / threshold for neighbour tests."""
    p = p or {}
    c = df.close
    n = p.get("n")
    if rule == "rsi_rev":            # RSI back out of 30/70
        r = rsi(c, n or 14); lo = p.get("lo", 30)
        return _xup(r, lo), _xdn(r, 100 - lo)
    if rule == "rsi_mom":            # RSI crosses 50
        r = rsi(c, n or 14)
        return _xup(r, 50), _xdn(r, 50)
    if rule == "macd_x":
        m, s = macd(c, p.get("f", 12), p.get("s", 26), p.get("sig", 9))
        return _xup(m, s), _xdn(m, s)
    if rule == "macd_zero":
        m, _ = macd(c, p.get("f", 12), p.get("s", 26))
        return _xup(m, 0), _xdn(m, 0)
    if rule == "stoch_rev":          # %K x %D inside OB/OS zone
        K, D = stoch(df, n or 14); z = p.get("lo", 20)
        return _xup(K, D) & (D.to_numpy() < z), _xdn(K, D) & (D.to_numpy() > 100 - z)
    if rule == "cci_rev":            # CCI back above -100 / below +100
        x = cci(df, n or 20); t = p.get("t", 100)
        return _xup(x, -t), _xdn(x, t)
    if rule == "cci_mom":            # CCI breaks +100 / -100
        x = cci(df, n or 20); t = p.get("t", 100)
        return _xup(x, t), _xdn(x, -t)
    if rule == "dmi_x":              # +DI x -DI with ADX > 20
        pdi, ndi, adx = dmi(df, n or 14); a = (adx > p.get("adx", 20)).to_numpy()
        return _xup(pdi, ndi) & a, _xdn(pdi, ndi) & a
    if rule == "bb_rev":             # back inside the band
        b = bollinger_pb(c, n or 20, p.get("k", 2.0))
        return _xup(b, 0), _xdn(b, 1)
    if rule == "bb_brk":             # close breaks out of the band
        b = bollinger_pb(c, n or 20, p.get("k", 2.0))
        return _xup(b, 1), _xdn(b, 0)
    if rule == "kelt_brk":
        up, lo = keltner(df, n or 20, p.get("k", 2.0))
        return _xup(c, up), _xdn(c, lo)
    if rule == "kelt_rev":
        up, lo = keltner(df, n or 20, p.get("k", 2.0))
        return _xup(c, lo), _xdn(c, up)
    if rule == "squeeze_brk":        # low-ATR regime then 20-bar breakout
        q = (atr_pct(df, 14, p.get("look", 500)).shift() < p.get("q", 0.25)).to_numpy()
        hh = df.high.rolling(n or 20).max().shift(); ll = df.low.rolling(n or 20).min().shift()
        return _xup(c, hh) & q, _xdn(c, ll) & q
    if rule == "aroon_x":
        u, d = aroon(df, n or 25)
        return _xup(u, d), _xdn(u, d)
    if rule == "willr_rev":
        w = williams_r(df, n or 14); t = p.get("lo", 80)
        return _xup(w, -t), _xdn(w, -(100 - t))
    if rule == "mfi_rev":
        m = mfi(df, n or 14); lo = p.get("lo", 20)
        return _xup(m, lo), _xdn(m, 100 - lo)
    if rule == "cmf_zero":
        m = cmf(df, n or 20); t = p.get("t", 0.05)
        return _xup(m, t), _xdn(m, -t)
    if rule == "obv_slope":          # OBV crosses its own EMA
        o = obv(df); e = o.ewm(span=n or 20, adjust=False).mean()
        return _xup(o, e), _xdn(o, e)
    if rule == "ema_slope":          # EMA slope turns up / down
        e = c.ewm(span=n or 50, adjust=False).mean(); s = e.diff(p.get("k", 3))
        return _xup(s, 0), _xdn(s, 0)
    if rule == "ema_x":              # EMA20 x EMA50
        f = c.ewm(span=p.get("f", 20), adjust=False).mean()
        s = c.ewm(span=p.get("s", 50), adjust=False).mean()
        return _xup(f, s), _xdn(f, s)
    if rule == "ha_flip":            # 2 same-colour HA candles after opposite
        ho, hc = heikin_ashi(df); g = (hc > ho).to_numpy(); r = ~g
        g1, g2 = np.r_[False, g[:-1]], np.r_[False, False, g[:-2]]
        r1, r2 = np.r_[False, r[:-1]], np.r_[False, False, r[:-2]]
        return g & g1 & r2, r & r1 & g2
    if rule == "don_brk":            # close breaks prior N-bar high/low
        hh = df.high.rolling(n or 20).max().shift(); ll = df.low.rolling(n or 20).min().shift()
        return _xup(c, hh), _xdn(c, ll)
    if rule == "trend_vote":         # consensus of 6 trend indicators crosses `v` of 6
        m, _ = macd(c)
        pdi, ndi, _a = dmi(df, 14)
        au, ad = aroon(df, 25)
        e20, e50 = c.ewm(span=20, adjust=False).mean(), c.ewm(span=50, adjust=False).mean()
        votes = ((m > 0).astype(int) + (pdi > ndi) + (au > ad) + (e20 > e50)
                 + (cmf(df, 20) > 0) + (rsi(c, 14) > 50))
        v = p.get("v", 5)
        return _xup(votes, v - 0.5), _xdn(votes, 6 - v + 0.5)
    if rule == "don_rev":            # Donchian position back above 0.1 / below 0.9
        d = donchian_pos(df, n or 20); t = p.get("t", 0.1)
        return _xup(d, t), _xdn(d, 1 - t)
    raise KeyError(rule)


RULES = ["rsi_rev", "rsi_mom", "macd_x", "macd_zero", "stoch_rev", "cci_rev", "cci_mom",
         "dmi_x", "bb_rev", "bb_brk", "kelt_brk", "kelt_rev", "squeeze_brk", "aroon_x",
         "willr_rev", "mfi_rev", "cmf_zero", "obv_slope", "ema_slope", "ema_x", "ha_flip",
         "don_brk", "don_rev"]


def events_to_entries(df, longs, shorts, *, trend=False, sides="both",
                      sl_atr=2.0, tp_atr=3.0, hold=48, trend_n=200, meta=None):
    c = df.close.to_numpy(float)
    a = atr(df, 14).to_numpy(float)
    longs = np.asarray(longs, bool).copy()
    shorts = np.asarray(shorts, bool).copy()
    if trend:
        ma = df.close.rolling(trend_n).mean().to_numpy(float)
        longs &= c > ma
        shorts &= c < ma
    if sides == "long":
        shorts[:] = False
    elif sides == "short":
        longs[:] = False
    ok = np.isfinite(a) & (a > 0)
    longs &= ok; shorts &= ok
    out = [None] * len(df)
    meta = meta or {}
    for i in np.flatnonzero(longs | shorts):
        if longs[i] and shorts[i]:
            continue
        if longs[i]:
            out[i] = H.Entry("long", c[i] - sl_atr * a[i], c[i] + tp_atr * a[i], max_hold=hold, meta=meta)
        else:
            out[i] = H.Entry("short", c[i] + sl_atr * a[i], c[i] - tp_atr * a[i], max_hold=hold, meta=meta)
    return out


def build_rule(df, rule="rsi_rev", trend=False, sides="both", sl_atr=2.0, tp_atr=3.0,
               hold=48, trend_n=200, **p):
    lg, sh = rule_events(df, rule, p)
    return events_to_entries(df, lg, sh, trend=trend, sides=sides, sl_atr=sl_atr,
                             tp_atr=tp_atr, hold=hold, trend_n=trend_n)


# ---------------------------------------------------------------- shortlisted candidates
# All use the screen's standard exit (2xATR stop, 3xATR target, 48-bar time exit).
def build_us30_aroon_trend(df, n=25, trend=True, **kw):
    """Aroon(25) up/down cross, SMA200 trend filter. Best on US30 H4."""
    return build_rule(df, "aroon_x", trend=trend, n=n, **kw)


def build_us500_emax_trend(df, f=20, s=50, trend=True, **kw):
    """EMA20 x EMA50 with SMA200 filter. Best on US500 H4."""
    return build_rule(df, "ema_x", trend=trend, f=f, s=s, **kw)


def build_gbpjpy_keltner_breakout(df, n=20, k=2.0, trend=False, **kw):
    """Close crosses outside Keltner(EMA20 +/- 2 ATR20). Best on GBPJPY H4 (peaky)."""
    return build_rule(df, "kelt_brk", trend=trend, n=n, k=k, **kw)


def build_index_d1_squeeze(df, n=20, q=0.25, trend=True, **kw):
    """Low ATR-percentile regime (<25% of last 500 bars) then 20-bar breakout,
    SMA200 filter. D1 on US500/US30 (very few trades)."""
    return build_rule(df, "squeeze_brk", trend=trend, n=n, q=q, **kw)


def build_gbpjpy_d1_donchian(df, n=20, trend=False, **kw):
    """Close breaks prior 20-day high/low (turtle-style entry). GBPJPY D1."""
    return build_rule(df, "don_brk", trend=trend, n=n, **kw)
