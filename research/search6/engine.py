"""Round 6 rule engine: one builder for every YouTube-described strategy.

build_spec(df, spec=...) turns a JSON spec into harness entries (H.Entry | None per bar). The spec
is produced from a video transcript (see extract_prompt.md) and holds only building blocks a retail
video can describe: trend filter, entry trigger(s), session window, stop rule, target rule.

Spec keys (all optional except entry):
  side          "both" | "long" | "short"
  trend         {"type": "ema"|"sma", "n": 200}              price above -> longs only, below -> shorts only
                {"type": "ema_stack", "fast": 50, "slow": 200} fast above slow -> longs only
                {"type": "adx", "n": 14, "min": 25}           only when ADX >= min
                {"type": "supertrend", "n": 10, "mult": 3}    direction of supertrend
                {"type": "ichimoku"}                          price above/below the cloud
                {"type": "htf_ema", "n": 50, "tf_mult": 4}    EMA on a higher timeframe (bars aggregated x tf_mult)
                {"type": "rsi_state", "n": 14, "level": 50}   RSI above level -> longs only, below -> shorts only
                {"type": "prev_day"}                          yesterday closed up -> longs only, down -> shorts only
                {"type": "fib_zone", "k": 5, "lo": 0.5, "hi": 0.79}  price in the discount/premium zone of the last swing
  entry         one trigger or a list of triggers that must ALL fire on the same bar:
                {"type": "ema_cross", "fast": 9, "slow": 21}
                {"type": "ema_pullback", "n": 20, "tol_atr": 0.3}        pull back to the EMA, close back in trend direction
                {"type": "rsi", "n": 14, "lo": 30, "hi": 70, "mode": "cross_back"|"level"|"cross_50"}
                {"type": "stoch", "k": 14, "d": 3, "lo": 20, "hi": 80}
                {"type": "macd", "fast": 12, "slow": 26, "signal": 9, "zero": false}
                {"type": "bb", "n": 20, "k": 2, "mode": "fade"|"break"}
                {"type": "donchian", "n": 20}                             close beyond the N-bar high/low
                {"type": "session_break", "h0": 2, "h1": 9}               break of the h0..h1 range (server hours)
                {"type": "prev_day_break"}                                close beyond yesterday's high/low
                {"type": "orb", "h0": 16, "m0": 30, "bars": 1}             opening range of the first N bars from h0:m0, break of it
                {"type": "engulfing"} | {"type": "pinbar", "n": 10} | {"type": "inside_bar"} | {"type": "doji_reversal"}
                {"type": "sr_bounce", "k": 5, "tol_atr": 0.3}            touch of a confirmed pivot level and close back
                {"type": "sweep", "n": 20}                                 wick through N-bar high/low, close back inside (fade)
                {"type": "fvg"}                                            3-bar gap, price returns into it, continue
                {"type": "order_block", "k": 3}                            retest of the last opposite candle before a break
                {"type": "supertrend_flip", "n": 10, "mult": 3}
                {"type": "psar_flip", "step": 0.02, "max": 0.2}
                {"type": "heikin_ashi"}                                    HA colour change
                {"type": "ichimoku_tk"}                                    tenkan/kijun cross with cloud
                {"type": "vwap_bounce", "tol_atr": 0.3}                    touch of day VWAP, close back
                {"type": "vwap_cross"}                                     close crosses the day VWAP
                {"type": "three_bar"}                                      3 same-colour bars then entry
  session       {"h0": 10, "h1": 18}  entries only when bar hour in [h0, h1) (server time, UTC+2/3)
  days          [0,1,2,3,4]  weekdays allowed
  stop          {"type": "atr", "mult": 1.5} | {"type": "swing", "n": 10, "buf_atr": 0.1} | {"type": "candle", "buf_atr": 0.1}
                {"type": "pips", "pips": 20} | {"type": "pct", "pct": 1.0} | {"type": "bb_mid"}
                {"type": "range_opposite", "n": 12, "buf_atr": 0.0}   other side of the last n bars' range (session/opening-range stops)   (default atr 1.5)
  target        {"type": "rr", "r": 2} | {"type": "atr", "mult": 3} | {"type": "trail_atr", "mult": 2} | {"type": "opposite"}
                {"type": "ema_cross_back", "fast": 9, "slow": 21} | {"type": "time", "bars": 24} | {"type": "bb_mid"} | {"type": "pips", "pips": 40}
                {"type": "close_hour", "hour": 18}   flat at the close of the first bar with that server hour (no target)
                (default rr 2)
  max_hold      bars (default 200)
  min_stop_atr  smallest stop allowed in ATRs (default 0.3; narrower stops are widened)
"""
from __future__ import annotations
import numpy as np, pandas as pd
from research.prop import harness as H

PIP = {"XAUUSD": 0.1, "XAGUSD": 0.01}


def _pip(sym):
    if sym in PIP:
        return PIP[sym]
    if sym in ("US500", "US30", "USTEC", "DE40", "UK100", "FRA40", "JPN225", "AUS200", "US2000"):
        return 1.0
    if sym in ("BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD", "SOLUSD"):
        return 1.0
    if sym in ("XTIUSD", "XBRUSD"):
        return 0.01
    return 0.01 if sym.endswith("JPY") else 0.0001


# ----------------------------------------------------------------- indicators
def ema(x, n): return pd.Series(x).ewm(span=n, adjust=False, min_periods=n).mean().to_numpy()
def sma(x, n): return pd.Series(x).rolling(n, min_periods=n).mean().to_numpy()


def atr(h, l, c, n=14):
    pc = np.r_[np.nan, c[:-1]]
    tr = np.nanmax(np.c_[h - l, np.abs(h - pc), np.abs(l - pc)], axis=1)
    return pd.Series(tr).ewm(alpha=1 / n, adjust=False, min_periods=n).mean().to_numpy()


def rsi(c, n=14):
    d = np.diff(c, prepend=c[0]); up = np.where(d > 0, d, 0.0); dn = np.where(d < 0, -d, 0.0)
    au = pd.Series(up).ewm(alpha=1 / n, adjust=False, min_periods=n).mean(); ad = pd.Series(dn).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return (100 - 100 / (1 + au / ad.replace(0, np.nan))).to_numpy()


def stoch(h, l, c, k=14, d=3):
    hh = pd.Series(h).rolling(k).max(); ll = pd.Series(l).rolling(k).min()
    kk = 100 * (pd.Series(c) - ll) / (hh - ll).replace(0, np.nan)
    kk = kk.rolling(3).mean()
    return kk.to_numpy(), kk.rolling(d).mean().to_numpy()


def macd(c, f=12, s=26, sig=9):
    m = ema(c, f) - ema(c, s); return m, pd.Series(m).ewm(span=sig, adjust=False).mean().to_numpy()


def adx(h, l, c, n=14):
    up = np.diff(h, prepend=h[0]); dn = -np.diff(l, prepend=l[0])
    pdm = np.where((up > dn) & (up > 0), up, 0.0); ndm = np.where((dn > up) & (dn > 0), dn, 0.0)
    a = atr(h, l, c, n)
    pdi = 100 * pd.Series(pdm).ewm(alpha=1 / n, adjust=False).mean().to_numpy() / a
    ndi = 100 * pd.Series(ndm).ewm(alpha=1 / n, adjust=False).mean().to_numpy() / a
    dx = 100 * np.abs(pdi - ndi) / np.where(pdi + ndi == 0, np.nan, pdi + ndi)
    return pd.Series(dx).ewm(alpha=1 / n, adjust=False, min_periods=n).mean().to_numpy()


def supertrend(h, l, c, n=10, mult=3.0):
    a = atr(h, l, c, n); mid = (h + l) / 2
    ub, lb = mid + mult * a, mid - mult * a
    n_ = len(c); fu = ub.copy(); fl = lb.copy(); d = np.ones(n_, int)
    first = int(np.argmax(np.isfinite(a))) + 1
    for i in range(first, n_):
        fu[i] = ub[i] if (ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        if d[i - 1] == 1:
            d[i] = -1 if c[i] < fl[i] else 1
        else:
            d[i] = 1 if c[i] > fu[i] else -1
    return d


def psar(h, l, step=0.02, mx=0.2):
    n = len(h); d = np.ones(n, int); sar = np.empty(n); sar[0] = l[0]; ep = h[0]; af = step
    for i in range(1, n):
        sar[i] = sar[i - 1] + af * (ep - sar[i - 1])
        if d[i - 1] == 1:
            sar[i] = min(sar[i], l[i - 1], l[max(i - 2, 0)])
            if l[i] < sar[i]:
                d[i] = -1; sar[i] = ep; ep = l[i]; af = step
            else:
                d[i] = 1
                if h[i] > ep: ep = h[i]; af = min(af + step, mx)
        else:
            sar[i] = max(sar[i], h[i - 1], h[max(i - 2, 0)])
            if h[i] > sar[i]:
                d[i] = 1; sar[i] = ep; ep = h[i]; af = step
            else:
                d[i] = -1
                if l[i] < ep: ep = l[i]; af = min(af + step, mx)
    return d


def heikin(o, h, l, c):
    hc = (o + h + l + c) / 4; ho = np.empty_like(o); ho[0] = o[0]
    for i in range(1, len(o)):
        ho[i] = (ho[i - 1] + hc[i - 1]) / 2
    return ho, hc


def ichimoku(h, l, c):
    hh = lambda n: pd.Series(h).rolling(n).max().to_numpy(); ll = lambda n: pd.Series(l).rolling(n).min().to_numpy()
    tenkan = (hh(9) + ll(9)) / 2; kijun = (hh(26) + ll(26)) / 2
    spa = pd.Series((tenkan + kijun) / 2).shift(26).to_numpy(); spb = pd.Series((hh(52) + ll(52)) / 2).shift(26).to_numpy()
    return tenkan, kijun, np.fmax(spa, spb), np.fmin(spa, spb)


def pivots(h, l, k):
    n = len(h); win = 2 * k + 1
    hmax = pd.Series(h).rolling(win, center=True, min_periods=win).max().to_numpy()
    lmin = pd.Series(l).rolling(win, center=True, min_periods=win).min().to_numpy()
    ph = np.full(n, np.nan); pl = np.full(n, np.nan)
    for j in np.flatnonzero(h == hmax):
        if j + k < n: ph[j + k] = h[j]
    for j in np.flatnonzero(l == lmin):
        if j + k < n: pl[j + k] = l[j]
    return pd.Series(ph).ffill().to_numpy(), pd.Series(pl).ffill().to_numpy()


def day_vwap(df):
    tp = (df.high + df.low + df.close) / 3; v = df.tick_volume.astype(float).clip(lower=1)
    day = df.time.dt.normalize()
    return ((tp * v).groupby(day).cumsum() / v.groupby(day).cumsum()).to_numpy()


def prev_day_hl(df):
    day = df.time.dt.normalize()
    g = df.groupby(day).agg(h=("high", "max"), l=("low", "min")).shift(1)
    codes = pd.factorize(day)[0]
    return g.h.to_numpy()[codes], g.l.to_numpy()[codes]


def session_range(df, h0, h1):
    hours = df.time.dt.hour.to_numpy(); day = pd.factorize(df.time.dt.normalize())[0]
    m = (hours >= h0) & (hours < h1)
    hh = np.where(m, df.high.to_numpy(), -np.inf); ll = np.where(m, df.low.to_numpy(), np.inf)
    s = pd.DataFrame(dict(d=day, hh=hh, ll=ll)).groupby("d")
    rh = s.hh.cummax().to_numpy().copy(); rl = s.ll.cummin().to_numpy().copy()
    rh[~np.isfinite(rh)] = np.nan; rl[~np.isfinite(rl)] = np.nan
    done = hours >= h1
    return np.where(done, rh, np.nan), np.where(done, rl, np.nan)


# ----------------------------------------------------------------- triggers: +1 long, -1 short, 0 none
def trigger(t, o, h, l, c, a, df):
    typ = t["type"]; n_ = len(c); sig = np.zeros(n_, int)
    prev = lambda x: np.r_[np.nan, x[:-1]]
    if typ == "ema_cross":
        f, s = ema(c, t.get("fast", 9)), ema(c, t.get("slow", 21))
        sig[(f > s) & (prev(f) <= prev(s))] = 1; sig[(f < s) & (prev(f) >= prev(s))] = -1
    elif typ == "ema_pullback":
        e = ema(c, t.get("n", 20)); tol = t.get("tol_atr", 0.3) * a
        sig[(l <= e + tol) & (c > e) & (prev(c) > prev(e)) & (c > o)] = 1
        sig[(h >= e - tol) & (c < e) & (prev(c) < prev(e)) & (c < o)] = -1
    elif typ == "rsi":
        r = rsi(c, t.get("n", 14)); lo, hi = t.get("lo", 30), t.get("hi", 70); mode = t.get("mode", "cross_back")
        if mode == "level":
            sig[r < lo] = 1; sig[r > hi] = -1
        elif mode == "cross_50":
            sig[(r > 50) & (prev(r) <= 50)] = 1; sig[(r < 50) & (prev(r) >= 50)] = -1
        else:
            sig[(r > lo) & (prev(r) <= lo)] = 1; sig[(r < hi) & (prev(r) >= hi)] = -1
    elif typ == "stoch":
        k, d = stoch(h, l, c, t.get("k", 14), t.get("d", 3)); lo, hi = t.get("lo", 20), t.get("hi", 80)
        sig[(k > d) & (prev(k) <= prev(d)) & (k < lo + 10)] = 1; sig[(k < d) & (prev(k) >= prev(d)) & (k > hi - 10)] = -1
    elif typ == "macd":
        m, s = macd(c, t.get("fast", 12), t.get("slow", 26), t.get("signal", 9))
        up = (m > s) & (prev(m) <= prev(s)); dn = (m < s) & (prev(m) >= prev(s))
        if t.get("zero"):
            up &= m < 0; dn &= m > 0
        sig[up] = 1; sig[dn] = -1
    elif typ == "bb":
        n, k = t.get("n", 20), t.get("k", 2.0); mid = sma(c, n); sd = pd.Series(c).rolling(n).std().to_numpy()
        up, lo_ = mid + k * sd, mid - k * sd
        if t.get("mode", "fade") == "fade":
            sig[(prev(c) < prev(lo_)) & (c > lo_)] = 1; sig[(prev(c) > prev(up)) & (c < up)] = -1
        else:
            sig[(c > up) & (prev(c) <= prev(up))] = 1; sig[(c < lo_) & (prev(c) >= prev(lo_))] = -1
    elif typ == "donchian":
        n = t.get("n", 20); hh = pd.Series(h).rolling(n).max().shift(1).to_numpy(); ll = pd.Series(l).rolling(n).min().shift(1).to_numpy()
        sig[c > hh] = 1; sig[c < ll] = -1
    elif typ == "session_break":
        rh, rl = session_range(df, t.get("h0", 2), t.get("h1", 9))
        sig[(c > rh) & ~(prev(c) > prev(rh))] = 1; sig[(c < rl) & ~(prev(c) < prev(rl))] = -1
    elif typ == "orb":
        # opening range = the first `bars` bars at/after h0:m0 each day; entry on a close beyond it (same day)
        tm = df.time; mins = (tm.dt.hour * 60 + tm.dt.minute).to_numpy(); day = pd.factorize(tm.dt.normalize())[0]
        start = t.get("h0", 16) * 60 + t.get("m0", 30); nb = int(t.get("bars", 1))
        after = mins >= start
        rank = pd.Series(after.astype(int)).groupby(day).cumsum().to_numpy()          # 1 for the first bar at/after start
        inrng = after & (rank >= 1) & (rank <= nb)
        hh = np.where(inrng, h, -np.inf); ll = np.where(inrng, l, np.inf)
        g = pd.DataFrame(dict(d=day, hh=hh, ll=ll)).groupby("d")
        rh = g.hh.cummax().to_numpy().copy(); rl = g.ll.cummin().to_numpy().copy()
        rh[~np.isfinite(rh)] = np.nan; rl[~np.isfinite(rl)] = np.nan
        done = after & (rank > nb)
        rh = np.where(done, rh, np.nan); rl = np.where(done, rl, np.nan)
        sig[(c > rh) & ~(prev(c) > prev(rh))] = 1; sig[(c < rl) & ~(prev(c) < prev(rl))] = -1
    elif typ == "prev_day_break":
        ph, pl = prev_day_hl(df)
        sig[(c > ph) & ~(prev(c) > prev(ph))] = 1; sig[(c < pl) & ~(prev(c) < prev(pl))] = -1
    elif typ == "engulfing":
        po, pc = prev(o), prev(c)
        sig[(pc < po) & (c > o) & (c >= po) & (o <= pc) & (c - o > 0.5 * a)] = 1
        sig[(pc > po) & (c < o) & (c <= po) & (o >= pc) & (o - c > 0.5 * a)] = -1
    elif typ == "pinbar":
        n = t.get("n", 10); rng = h - l; body = np.abs(c - o); lw = np.minimum(o, c) - l; uw = h - np.maximum(o, c)
        hh = pd.Series(h).rolling(n).max().shift(1).to_numpy(); ll = pd.Series(l).rolling(n).min().shift(1).to_numpy()
        ok = (rng > 0.5 * a) & (body < 0.35 * rng)
        sig[ok & (lw > 0.6 * rng) & (l <= ll)] = 1; sig[ok & (uw > 0.6 * rng) & (h >= hh)] = -1
    elif typ == "inside_bar":
        ph, pl = prev(h), prev(l); pph, ppl = prev(ph), prev(pl)
        inside_prev = (ph <= pph) & (pl >= ppl)
        sig[inside_prev & (c > pph)] = 1; sig[inside_prev & (c < ppl)] = -1
    elif typ == "doji_reversal":
        rng = h - l; body = np.abs(c - o); pd_ = prev(body) < 0.1 * prev(rng)
        sig[pd_ & (c > prev(h)) & (prev(prev(c)) < prev(prev(o)))] = 1; sig[pd_ & (c < prev(l)) & (prev(prev(c)) > prev(prev(o)))] = -1
    elif typ == "sr_bounce":
        ph, pl = pivots(h, l, t.get("k", 5)); tol = t.get("tol_atr", 0.3) * a
        sig[(l <= pl + tol) & (c > pl) & (c > o)] = 1; sig[(h >= ph - tol) & (c < ph) & (c < o)] = -1
    elif typ == "sweep":
        n = t.get("n", 20); hh = pd.Series(h).rolling(n).max().shift(1).to_numpy(); ll = pd.Series(l).rolling(n).min().shift(1).to_numpy()
        sig[(l < ll) & (c > ll)] = 1; sig[(h > hh) & (c < hh)] = -1
    elif typ == "fvg":
        # bullish gap: low[i-1] > high[i-3]; entry when price later trades back into the gap and closes above it (within 20 bars)
        gl_up = prev(l) > np.r_[np.nan, np.nan, np.nan, h[:-3]]; gl_dn = prev(h) < np.r_[np.nan, np.nan, np.nan, l[:-3]]
        up_lo = np.where(gl_up, np.r_[np.nan, np.nan, np.nan, h[:-3]], np.nan); up_hi = np.where(gl_up, prev(l), np.nan)
        dn_hi = np.where(gl_dn, np.r_[np.nan, np.nan, np.nan, l[:-3]], np.nan); dn_lo = np.where(gl_dn, prev(h), np.nan)
        for arr in (up_lo, up_hi, dn_hi, dn_lo):
            s = pd.Series(arr).ffill(limit=20); arr[:] = s.to_numpy()
        sig[(l <= up_hi) & (l >= up_lo - a) & (c > up_hi)] = 1; sig[(h >= dn_lo) & (h <= dn_hi + a) & (c < dn_lo)] = -1
    elif typ == "order_block":
        k = t.get("k", 3); hh = pd.Series(h).rolling(k * 4).max().shift(1).to_numpy(); ll = pd.Series(l).rolling(k * 4).min().shift(1).to_numpy()
        brk_up = c > hh; brk_dn = c < ll
        ob_hi = np.full(len(c), np.nan); ob_lo = np.full(len(c), np.nan); ob_side = np.zeros(len(c), int)
        last = None
        for i in range(k, len(c)):
            if brk_up[i]:
                j = next((m for m in range(i - 1, max(i - k * 4, 0), -1) if c[m] < o[m]), None)
                if j is not None: last = (1, l[j], h[j], i)
            elif brk_dn[i]:
                j = next((m for m in range(i - 1, max(i - k * 4, 0), -1) if c[m] > o[m]), None)
                if j is not None: last = (-1, l[j], h[j], i)
            if last and i - last[3] <= 50 and i > last[3]:
                ob_side[i], ob_lo[i], ob_hi[i] = last[0], last[1], last[2]
        sig[(ob_side == 1) & (l <= ob_hi) & (c > ob_hi) & (c > o)] = 1; sig[(ob_side == -1) & (h >= ob_lo) & (c < ob_lo) & (c < o)] = -1
    elif typ == "supertrend_flip":
        d = supertrend(h, l, c, t.get("n", 10), t.get("mult", 3.0)); pdd = np.r_[0, d[:-1]]
        sig[(d == 1) & (pdd == -1)] = 1; sig[(d == -1) & (pdd == 1)] = -1
    elif typ == "psar_flip":
        d = psar(h, l, t.get("step", 0.02), t.get("max", 0.2)); pdd = np.r_[0, d[:-1]]
        sig[(d == 1) & (pdd == -1)] = 1; sig[(d == -1) & (pdd == 1)] = -1
    elif typ == "heikin_ashi":
        ho, hc = heikin(o, h, l, c); g = hc > ho; pg = np.r_[False, g[:-1]]
        sig[g & ~pg] = 1; sig[~g & pg] = -1
    elif typ == "ichimoku_tk":
        tk, kj, top, bot = ichimoku(h, l, c)
        sig[(tk > kj) & (prev(tk) <= prev(kj)) & (c > top)] = 1; sig[(tk < kj) & (prev(tk) >= prev(kj)) & (c < bot)] = -1
    elif typ == "vwap_bounce":
        v = day_vwap(df); tol = t.get("tol_atr", 0.3) * a
        sig[(l <= v + tol) & (c > v) & (c > o) & (prev(c) > prev(v))] = 1; sig[(h >= v - tol) & (c < v) & (c < o) & (prev(c) < prev(v))] = -1
    elif typ == "vwap_cross":
        v = day_vwap(df)
        sig[(c > v) & (prev(c) <= prev(v))] = 1; sig[(c < v) & (prev(c) >= prev(v))] = -1
    elif typ == "three_bar":
        g = c > o; r = c < o
        sig[g & np.r_[False, g[:-1]] & np.r_[False, False, g[:-2]]] = 1; sig[r & np.r_[False, r[:-1]] & np.r_[False, False, r[:-2]]] = -1
    else:
        raise ValueError(f"unknown trigger {typ}")
    return sig


def trend_mask(tr, o, h, l, c, df):
    """-> allowed direction per bar: +1 longs only, -1 shorts only, 2 both, 0 none."""
    n_ = len(c); typ = tr["type"]
    if typ in ("ema", "sma"):
        m = (ema if typ == "ema" else sma)(c, tr.get("n", 200)); return np.where(c > m, 1, np.where(c < m, -1, 0))
    if typ == "ema_stack":
        f, s = ema(c, tr.get("fast", 50)), ema(c, tr.get("slow", 200)); return np.where(f > s, 1, np.where(f < s, -1, 0))
    if typ == "adx":
        return np.where(adx(h, l, c, tr.get("n", 14)) >= tr.get("min", 25), 2, 0)
    if typ == "supertrend":
        return supertrend(h, l, c, tr.get("n", 10), tr.get("mult", 3.0))
    if typ == "ichimoku":
        _, _, top, bot = ichimoku(h, l, c); return np.where(c > top, 1, np.where(c < bot, -1, 0))
    if typ == "rsi_state":
        r = rsi(c, tr.get("n", 14)); lv = tr.get("level", 50); return np.where(r > lv, 1, np.where(r < lv, -1, 0))
    if typ == "prev_day":
        day = pd.factorize(df.time.dt.normalize())[0]
        g = pd.DataFrame(dict(d=day, o=o, c=c)).groupby("d").agg(o=("o", "first"), c=("c", "last"))
        up = (g.c > g.o).shift(1).to_numpy()[day]; dn = (g.c < g.o).shift(1).to_numpy()[day]
        return np.where(up == True, 1, np.where(dn == True, -1, 0))  # noqa: E712
    if typ == "fib_zone":
        # price inside the discount (long) / premium (short) zone of the last confirmed swing: between lo and hi of the leg
        ph, pl = pivots(h, l, tr.get("k", 5)); lo_f, hi_f = tr.get("lo", 0.5), tr.get("hi", 0.79)
        rng = ph - pl
        long_ok = (c <= ph - lo_f * rng) & (c >= ph - hi_f * rng); short_ok = (c >= pl + lo_f * rng) & (c <= pl + hi_f * rng)
        return np.where(long_ok & ~short_ok, 1, np.where(short_ok & ~long_ok, -1, np.where(long_ok & short_ok, 2, 0)))
    if typ == "htf_ema":
        k = int(tr.get("tf_mult", 4)); n = tr.get("n", 50)
        # EMA on k-bar aggregated closes (completed groups only), mapped back: causal
        grp = np.arange(n_) // k
        gc = pd.Series(c).groupby(grp).last().to_numpy(); e = ema(gc, n)
        e_prev = np.r_[np.nan, e[:-1]][grp]            # the last COMPLETED group's EMA
        return np.where(c > e_prev, 1, np.where(c < e_prev, -1, 0))
    raise ValueError(f"unknown trend {typ}")


def build_spec(df, spec):
    df = df.reset_index(drop=True)
    o, h, l, c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    n_ = len(c); a = atr(h, l, c, 14); sym = df.attrs.get("symbol", ""); pip = _pip(sym)
    ents = spec["entry"] if isinstance(spec["entry"], list) else [spec["entry"]]
    sig = trigger(ents[0], o, h, l, c, a, df)
    for t in ents[1:]:
        s2 = trigger(t, o, h, l, c, a, df); sig = np.where(sig == s2, sig, 0)
    if spec.get("trend"):
        tm = trend_mask(spec["trend"], o, h, l, c, df)
        sig = np.where((tm == 2) | (tm == sig), sig, 0)
    side = spec.get("side", "both")
    if side == "long": sig[sig < 0] = 0
    if side == "short": sig[sig > 0] = 0
    if spec.get("session"):
        hr = df.time.dt.hour.to_numpy(); h0, h1 = spec["session"]["h0"], spec["session"]["h1"]
        ok = (hr >= h0) & (hr < h1) if h0 <= h1 else (hr >= h0) | (hr < h1)
        sig[~ok] = 0
    if spec.get("days"):
        sig[~np.isin(df.time.dt.weekday.to_numpy(), spec["days"])] = 0
    st = spec.get("stop", {"type": "atr", "mult": 1.5}); tg = spec.get("target", {"type": "rr", "r": 2})
    min_stop = spec.get("min_stop_atr", 0.3); max_hold = spec.get("max_hold", 200)
    sw_lo = pd.Series(l).rolling(st.get("n", 10)).min().to_numpy() if st["type"] == "swing" else None
    sw_hi = pd.Series(h).rolling(st.get("n", 10)).max().to_numpy() if st["type"] == "swing" else None
    bbmid = sma(c, 20) if (st["type"] == "bb_mid" or tg["type"] == "bb_mid") else None
    xf = xs = None
    if tg["type"] == "ema_cross_back":
        xf, xs = ema(c, tg.get("fast", 9)), ema(c, tg.get("slow", 21))
    out = [None] * n_
    for i in np.flatnonzero(sig):
        if not np.isfinite(a[i]) or a[i] <= 0:
            continue
        long_ = sig[i] == 1; px = c[i]
        if st["type"] == "atr": dist = st.get("mult", 1.5) * a[i]
        elif st["type"] == "swing": dist = (px - sw_lo[i]) if long_ else (sw_hi[i] - px); dist += st.get("buf_atr", 0.1) * a[i]
        elif st["type"] == "candle": dist = (px - l[i]) if long_ else (h[i] - px); dist += st.get("buf_atr", 0.1) * a[i]
        elif st["type"] == "pips": dist = st.get("pips", 20) * pip
        elif st["type"] == "pct": dist = st.get("pct", 1.0) / 100 * px
        elif st["type"] == "bb_mid": dist = abs(px - bbmid[i]) if np.isfinite(bbmid[i]) else np.nan
        elif st["type"] == "range_opposite":
            n_r = int(st.get("n", 12)); lo_r = l[max(0, i - n_r):i + 1].min(); hi_r = h[max(0, i - n_r):i + 1].max()
            dist = (px - lo_r) if long_ else (hi_r - px); dist += st.get("buf_atr", 0.0) * a[i]
        else: raise ValueError(st["type"])
        if not np.isfinite(dist): continue
        dist = max(dist, min_stop * a[i])
        sl = px - dist if long_ else px + dist
        tp = None; manage = None; hold = max_hold
        if tg["type"] == "rr": tp = px + tg.get("r", 2) * dist if long_ else px - tg.get("r", 2) * dist
        elif tg["type"] == "atr": tp = px + tg.get("mult", 3) * a[i] if long_ else px - tg.get("mult", 3) * a[i]
        elif tg["type"] == "pips": tp = px + tg.get("pips", 40) * pip if long_ else px - tg.get("pips", 40) * pip
        elif tg["type"] == "bb_mid":
            tp = bbmid[i] if np.isfinite(bbmid[i]) and ((bbmid[i] > px) == long_) else None
        elif tg["type"] == "time": hold = tg.get("bars", 24)
        elif tg["type"] == "close_hour": pass
        elif tg["type"] == "trail_atr":
            m = tg.get("mult", 2.0)
            def manage(df_, j, pos, _m=m, _l=long_):
                new = c[j] - _m * a[j] if _l else c[j] + _m * a[j]
                return new if ((new > pos["sl"]) if _l else (new < pos["sl"])) else None
        elif tg["type"] == "opposite":
            def manage(df_, j, pos, _l=long_):
                return "close" if (sig[j] == -1 if _l else sig[j] == 1) else None
        elif tg["type"] == "ema_cross_back":
            def manage(df_, j, pos, _l=long_):
                return "close" if ((xf[j] < xs[j]) if _l else (xf[j] > xs[j])) else None
        else: raise ValueError(tg["type"])
        if tp is not None and ((tp <= px) if long_ else (tp >= px)):
            tp = None
        out[i] = H.Entry("long" if long_ else "short", sl=float(sl), tp=None if tp is None else float(tp), max_hold=hold, manage=manage,
                         exit_hour=(int(tg.get("hour", 18)) if tg["type"] == "close_hour" else None))
    return out
