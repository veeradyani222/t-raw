"""Round-3 oil & gas candidates (XTIUSD, XBRUSD, XNGUSD). Every build_* takes a df
from research.prop.harness.load (server time = EET) and returns list[Entry|None]
of len(df), using only rows <= i for the signal at i (entries fill at bar i close).

Server-time map used throughout (EET): NY pit open 16:00, EIA crude report
Wed 17:30, EIA gas storage Thu 17:30, NYMEX settlement 21:30, CFD close 24:00,
London open 10:00, Asia 01:00-10:00."""
from __future__ import annotations
import numpy as np, pandas as pd
from research.prop.harness import Entry, load as _hload

# ----------------------------------------------------------------- helpers
def _atr(df, n):
    h, l, c = df.high, df.low, df.close
    pc = c.shift()
    tr = pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
    return tr.rolling(n, min_periods=max(2, n // 2)).mean().to_numpy()

def _rsi(c, n):
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).fillna(50).to_numpy()

def _bar_minutes(df):
    tf = str(df.attrs.get("tf", "H1")).upper()
    return {"M30": 30, "H1": 60, "H4": 240, "D1": 1440}.get(tf, 60)

def _day_levels(df):
    """Prior completed day's high/low/close and today's open, per bar (causal)."""
    day = df.time.dt.normalize()
    g = df.groupby(day)
    dh, dl, dc, do = g.high.max(), g.low.min(), g.close.last(), g.open.first()
    prev = pd.DataFrame(dict(ph=dh.shift(), pl=dl.shift(), pc=dc.shift(), dopen=do))
    m = prev.reindex(day.values)
    return (m.ph.to_numpy(), m.pl.to_numpy(), m.pc.to_numpy(), m.dopen.to_numpy())

def _week_levels(df):
    wk = df.time.dt.to_period("W").astype(str)
    g = df.groupby(wk)
    wh, wl = g.high.max().shift(), g.low.min().shift()
    return wh.reindex(wk.values).to_numpy(), wl.reindex(wk.values).to_numpy()

def _trail_manage(atr_mult, atr_arr):
    def manage(df, i, pos):
        a = atr_arr[i]
        if not np.isfinite(a):
            return None
        if pos["side"] == "long":
            new = df.close.iat[i] - atr_mult * a
            return new if new > pos["sl"] else None
        new = df.close.iat[i] + atr_mult * a
        return new if new < pos["sl"] else None
    return manage

def _entry(side, px, sl_dist, tp_r=None, **kw):
    if side == "long":
        return Entry("long", px - sl_dist, None if tp_r is None else px + tp_r * sl_dist, **kw)
    return Entry("short", px + sl_dist, None if tp_r is None else px - tp_r * sl_dist, **kw)

def _hm(df):
    t = df.time
    return t.dt.hour.to_numpy(), t.dt.minute.to_numpy(), t.dt.weekday.to_numpy()


# ------------------------------------------------- 1. weekday / calendar holds
def build_weekday_hold(df, enter_wd=2, enter_hour=None, hold_bars=1, side="long",
                       sl_atr=2.0, atr_n=14, tp_r=None):
    """Day-of-week seasonality: enter at the close of the bar with weekday
    `enter_wd` (and hour `enter_hour` for intraday tfs), hold `hold_bars`.
    Default = long at Wednesday close to ride the oil 'Thursday effect'."""
    atr = _atr(df, atr_n); hr, mn, wd = _hm(df)
    c = df.close.to_numpy(); out = [None] * len(df)
    for i in range(len(df)):
        if wd[i] != enter_wd or not np.isfinite(atr[i]):
            continue
        if enter_hour is not None and (hr[i] != enter_hour or mn[i] != 0):
            continue
        out[i] = _entry(side, c[i], sl_atr * atr[i], tp_r, max_hold=hold_bars)
    return out


# ------------------------------------------------- 2. report-bar momentum
def build_report_momentum(df, report_wd=2, report_hour=17, exit_hour=21, sl_atr=1.5,
                          atr_n=20, tp_r=None, min_move_atr=0.0, direction="follow"):
    """Wen et al. (Energy Journal 2023): on EIA days the report half-hour return
    predicts the last half-hour. Signal at the close of the bar containing the
    17:30 release (M30 bar 17:30 / H1 bar 17:00); trade its direction (or fade)
    into settlement (exit_hour 21 -> settles at the 21:xx bar close)."""
    atr = _atr(df, atr_n); hr, mn, wd = _hm(df)
    o, c = df.open.to_numpy(), df.close.to_numpy(); out = [None] * len(df)
    bm = _bar_minutes(df)
    for i in range(len(df)):
        if wd[i] != report_wd or hr[i] != report_hour or not np.isfinite(atr[i]):
            continue
        if bm == 30 and mn[i] != 30:
            continue
        mv = c[i] - o[i]
        if abs(mv) < min_move_atr * atr[i] or mv == 0:
            continue
        side = ("long" if mv > 0 else "short")
        if direction == "fade":
            side = "short" if side == "long" else "long"
        out[i] = _entry(side, c[i], sl_atr * atr[i], tp_r, exit_hour=exit_hour)
    return out


# ------------------------------------------------- 3. pre-report range breakout
def build_report_breakout(df, report_wd=2, report_hour=17, pre_bars=6, window_bars=6,
                          sl_mode="range", sl_atr=1.0, tp_r=1.8, exit_hour=23, atr_n=20):
    """Unger-style EIA play: range of the `pre_bars` bars before the release;
    first close outside it within `window_bars` after the release is the entry.
    Stop = other side of the range (or ATR), target = tp_r x risk, flat by exit_hour."""
    atr = _atr(df, atr_n); hr, mn, wd = _hm(df)
    h, l, c = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    out = [None] * len(df); bm = _bar_minutes(df)
    n = len(df); i = 0
    while i < n:
        hit = wd[i] == report_wd and hr[i] == report_hour and (bm != 30 or mn[i] == 30)
        if not hit or i < pre_bars:
            i += 1; continue
        rh, rl = h[i - pre_bars:i].max(), l[i - pre_bars:i].min()
        placed = False; j = i
        for j in range(i, min(n, i + window_bars)):
            if not np.isfinite(atr[j]):
                continue
            if c[j] > rh:
                d = (c[j] - rl) if sl_mode == "range" else sl_atr * atr[j]
                out[j] = _entry("long", c[j], d, tp_r, exit_hour=exit_hour); placed = True; break
            if c[j] < rl:
                d = (rh - c[j]) if sl_mode == "range" else sl_atr * atr[j]
                out[j] = _entry("short", c[j], d, tp_r, exit_hour=exit_hour); placed = True; break
        i = (j + 1) if placed else i + 1
    return out


# ------------------------------------------------- 4. pit-open opening range breakout
def build_pit_orb(df, open_hour=16, range_bars=2, cutoff_hour=20, sl_mode="mid", sl_atr=1.0,
                  tp_r=2.0, exit_hour=23, atr_n=20, min_range_atr=0.0, max_range_atr=9.0):
    """NY pit open (16:00 server): range of the first `range_bars` bars; close
    outside it before `cutoff_hour` enters; stop = range midpoint / other side /
    ATR; target tp_r x risk; flat at exit_hour."""
    atr = _atr(df, atr_n); hr, mn, wd = _hm(df)
    h, l, c = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    day = df.time.dt.normalize().to_numpy()
    out = [None] * len(df); n = len(df); i = 0
    while i < n:
        if hr[i] != open_hour or mn[i] != 0:
            i += 1; continue
        j1 = i + range_bars
        if j1 >= n or day[j1 - 1] != day[i]:
            i += 1; continue
        rh, rl = h[i:j1].max(), l[i:j1].min(); rng = rh - rl
        j = j1; placed = False
        while j < n and day[j] == day[i] and hr[j] < cutoff_hour:
            a = atr[j]
            if np.isfinite(a) and min_range_atr * a <= rng <= max_range_atr * a:
                if c[j] > rh:
                    d = {"mid": c[j] - (rh + rl) / 2, "range": c[j] - rl, "atr": sl_atr * a}[sl_mode]
                    out[j] = _entry("long", c[j], d, tp_r, exit_hour=exit_hour); placed = True; break
                if c[j] < rl:
                    d = {"mid": (rh + rl) / 2 - c[j], "range": rh - c[j], "atr": sl_atr * a}[sl_mode]
                    out[j] = _entry("short", c[j], d, tp_r, exit_hour=exit_hour); placed = True; break
            j += 1
        i = (j + 1) if placed else (j if j > i else i + 1)
    return out


# ------------------------------------------------- 5. pre-NY session range breakout
def build_session_range_break(df, range_start=3, range_end=15, trade_start=16, trade_end=20,
                              sl_mode="mid", sl_atr=1.0, tp_r=1.5, exit_hour=23, atr_n=20):
    """Range built from the Asian+European session (range_start..range_end h),
    traded on a close outside it during the US session."""
    atr = _atr(df, atr_n); hr, mn, wd = _hm(df)
    h, l, c = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    day = df.time.dt.normalize().to_numpy(); n = len(df); out = [None] * n
    rh = rl = np.nan; cur = None; traded = False
    for i in range(n):
        if day[i] != cur:
            cur = day[i]; rh, rl = -np.inf, np.inf; traded = False
        if range_start <= hr[i] <= range_end:
            rh, rl = max(rh, h[i]), min(rl, l[i])
        elif trade_start <= hr[i] <= trade_end and not traded and np.isfinite(rh) and rh > rl and np.isfinite(atr[i]):
            if c[i] > rh:
                d = {"mid": c[i] - (rh + rl) / 2, "range": c[i] - rl, "atr": sl_atr * atr[i]}[sl_mode]
                out[i] = _entry("long", c[i], d, tp_r, exit_hour=exit_hour); traded = True
            elif c[i] < rl:
                d = {"mid": (rh + rl) / 2 - c[i], "range": rh - c[i], "atr": sl_atr * atr[i]}[sl_mode]
                out[i] = _entry("short", c[i], d, tp_r, exit_hour=exit_hour); traded = True
    return out


# ------------------------------------------------- 6. overnight gap
def build_gap(df, mode="fade", min_gap_atr=0.3, max_gap_atr=3.0, sl_atr=1.5, atr_n=20,
              exit_hour=16, tp_mode="close"):
    """First bar of the server day: gap = that bar's open vs prior day close
    (D1 ATR units). fade -> target prior close, exit by `exit_hour`; follow -> ride it."""
    hr, mn, wd = _hm(df)
    ph, pl, pc, dopen = _day_levels(df)
    day = df.time.dt.normalize()
    drange = (df.groupby(day).high.max() - df.groupby(day).low.min())
    datr = drange.rolling(atr_n).mean().shift().reindex(day.values).to_numpy()
    o, c = df.open.to_numpy(), df.close.to_numpy(); n = len(df); out = [None] * n
    first = np.r_[True, day.values[1:] != day.values[:-1]]
    for i in range(n):
        if not first[i] or not np.isfinite(datr[i]) or not np.isfinite(pc[i]):
            continue
        gap = o[i] - pc[i]
        if not (min_gap_atr * datr[i] <= abs(gap) <= max_gap_atr * datr[i]):
            continue
        if mode == "fade":
            side = "short" if gap > 0 else "long"
            tp = pc[i] if tp_mode == "close" else None
            sl = c[i] + sl_atr * datr[i] if side == "short" else c[i] - sl_atr * datr[i]
            if tp is not None and ((side == "short" and tp >= c[i]) or (side == "long" and tp <= c[i])):
                continue
            out[i] = Entry(side, sl, tp, exit_hour=exit_hour)
        else:
            side = "long" if gap > 0 else "short"
            out[i] = _entry(side, c[i], sl_atr * datr[i], None, exit_hour=exit_hour)
    return out


# ------------------------------------------------- 7. Brent-WTI spread reversion
_other_cache = {}
def _other_close(df, other):
    key = (other, df.attrs.get("tf"))
    if key not in _other_cache:
        o = _hload(other, df.attrs.get("tf", "H1"), split="oos", warmup_bars=6000)
        _other_cache[key] = o[["time", "close"]].rename(columns={"close": "oc"})
    o = _other_cache[key]
    m = pd.merge_asof(df[["time"]], o, on="time", direction="backward")
    return m.oc.to_numpy()

def build_spread_reversion(df, other="XBRUSD", lookback=200, z_in=2.0, z_out=0.0,
                           sl_atr=2.5, atr_n=20, max_hold=72, mode="ratio"):
    """Brent-WTI spread (or ratio) z-score vs a rolling window. When this symbol is
    cheap vs the other (z high for other/this), go long it; exit when z crosses
    z_out, on the ATR stop, or after max_hold bars."""
    oc = _other_close(df, other)
    c = df.close.to_numpy()
    sp = (oc / c) if mode == "ratio" else (oc - c)
    s = pd.Series(sp)
    z = ((s - s.rolling(lookback).mean()) / s.rolling(lookback).std()).to_numpy()
    atr = _atr(df, atr_n); n = len(df); out = [None] * n

    def mk(side):
        def manage(d, i, pos):
            if side == "long" and z[i] <= z_out: return "close"
            if side == "short" and z[i] >= -z_out: return "close"
            return None
        return manage
    for i in range(n):
        if not np.isfinite(z[i]) or not np.isfinite(atr[i]):
            continue
        if z[i] > z_in:
            out[i] = _entry("long", c[i], sl_atr * atr[i], None, max_hold=max_hold, manage=mk("long"))
        elif z[i] < -z_in:
            out[i] = _entry("short", c[i], sl_atr * atr[i], None, max_hold=max_hold, manage=mk("short"))
    return out


# ------------------------------------------------- 8. Donchian trend with ATR trail
def build_donchian(df, n=160, trail_atr=3.0, atr_n=20, sl_atr=2.0, side="both"):
    """Close above the prior n-bar high -> long (and vice versa); ATR trailing stop;
    opposite signal flips. Unger Academy's crude system uses a 160-bar channel."""
    h, l, c = df.high, df.low, df.close
    hh = h.rolling(n).max().shift().to_numpy(); ll = l.rolling(n).min().shift().to_numpy()
    atr = _atr(df, atr_n); cc = c.to_numpy(); out = [None] * len(df)
    trail = _trail_manage(trail_atr, atr)
    for i in range(len(df)):
        if not np.isfinite(hh[i]) or not np.isfinite(atr[i]):
            continue
        if cc[i] > hh[i] and side in ("both", "long"):
            out[i] = Entry("long", cc[i] - sl_atr * atr[i], manage=trail)
        elif cc[i] < ll[i] and side in ("both", "short"):
            out[i] = Entry("short", cc[i] + sl_atr * atr[i], manage=trail)
    return out


# ------------------------------------------------- 9. pullback in trend (D1/H4)
def build_trend_pullback(df, ma_n=100, rsi_n=2, rsi_lo=10, rsi_hi=90, sl_atr=2.0, atr_n=14,
                         max_hold=6, side="both"):
    """Connors-style: in an uptrend (close > SMA ma_n) buy when RSI(rsi_n) < rsi_lo;
    exit when close > prior bar high (manage) or after max_hold bars. Mirror for shorts."""
    c = df.close; sma = c.rolling(ma_n).mean().to_numpy(); r = _rsi(c, rsi_n)
    atr = _atr(df, atr_n); cc = c.to_numpy(); ph = df.high.shift().to_numpy(); pl = df.low.shift().to_numpy()
    out = [None] * len(df)
    def m_long(d, i, pos):
        return "close" if cc[i] > ph[i] else None
    def m_short(d, i, pos):
        return "close" if cc[i] < pl[i] else None
    for i in range(len(df)):
        if not np.isfinite(sma[i]) or not np.isfinite(atr[i]):
            continue
        if cc[i] > sma[i] and r[i] < rsi_lo and side in ("both", "long"):
            out[i] = Entry("long", cc[i] - sl_atr * atr[i], max_hold=max_hold, manage=m_long)
        elif cc[i] < sma[i] and r[i] > rsi_hi and side in ("both", "short"):
            out[i] = Entry("short", cc[i] + sl_atr * atr[i], max_hold=max_hold, manage=m_short)
    return out


# ------------------------------------------------- 10. RSI extreme reversion
def build_rsi_reversion(df, rsi_n=14, lo=25, hi=75, mid=50, sl_atr=2.5, atr_n=14, max_hold=30, side="both"):
    """RSI(rsi_n) below lo -> long until RSI > mid (or max_hold); above hi -> short."""
    r = _rsi(df.close, rsi_n); atr = _atr(df, atr_n); c = df.close.to_numpy(); out = [None] * len(df)
    def ml(d, i, pos): return "close" if r[i] > mid else None
    def ms(d, i, pos): return "close" if r[i] < mid else None
    for i in range(len(df)):
        if not np.isfinite(atr[i]) or i < rsi_n * 3:
            continue
        if r[i] < lo and side in ("both", "long"):
            out[i] = Entry("long", c[i] - sl_atr * atr[i], max_hold=max_hold, manage=ml)
        elif r[i] > hi and side in ("both", "short"):
            out[i] = Entry("short", c[i] + sl_atr * atr[i], max_hold=max_hold, manage=ms)
    return out


# ------------------------------------------------- 11. NR-day / inside-day breakout (intraday tf)
def build_nr_breakout(df, nr_n=7, trade_start=10, trade_end=21, sl_mode="range", sl_atr=1.0,
                      tp_r=2.0, exit_hour=23, atr_n=20, inside_only=False):
    """If the prior day was the narrowest of the last nr_n days (NR7) [or an inside
    day], trade the first close outside its range today; stop other side (or ATR)."""
    hr, mn, wd = _hm(df)
    day = df.time.dt.normalize()
    g = df.groupby(day); dh, dl = g.high.max(), g.low.min(); rng = dh - dl
    nr = (rng == rng.rolling(nr_n).min()).shift().fillna(False)
    inside = ((dh < dh.shift()) & (dl > dl.shift())).shift().fillna(False)
    ok = (inside if inside_only else nr).reindex(day.values).to_numpy().astype(bool)
    ph, pl, pc, dopen = _day_levels(df); atr = _atr(df, atr_n)
    h, l, c = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    out = [None] * len(df); cur = None; traded = False; dv = day.values
    for i in range(len(df)):
        if dv[i] != cur:
            cur = dv[i]; traded = False
        if traded or not ok[i] or not (trade_start <= hr[i] <= trade_end) or not np.isfinite(atr[i]):
            continue
        if c[i] > ph[i]:
            d = (c[i] - pl[i]) if sl_mode == "range" else (c[i] - (ph[i] + pl[i]) / 2) if sl_mode == "mid" else sl_atr * atr[i]
            out[i] = _entry("long", c[i], d, tp_r, exit_hour=exit_hour); traded = True
        elif c[i] < pl[i]:
            d = (ph[i] - c[i]) if sl_mode == "range" else ((ph[i] + pl[i]) / 2 - c[i]) if sl_mode == "mid" else sl_atr * atr[i]
            out[i] = _entry("short", c[i], d, tp_r, exit_hour=exit_hour); traded = True
    return out


# ------------------------------------------------- 12. Bollinger squeeze breakout
def build_squeeze(df, bb_n=20, bw_lookback=120, bw_pct=0.2, trail_atr=3.0, atr_n=20, sl_atr=2.0, max_hold=None):
    """Bandwidth in the bottom bw_pct of the last bw_lookback bars, then a close
    outside the band -> trade the break with an ATR trail."""
    c = df.close; ma = c.rolling(bb_n).mean(); sd = c.rolling(bb_n).std()
    up, dn = ma + 2 * sd, ma - 2 * sd; bw = (up - dn) / ma
    thr = bw.rolling(bw_lookback).quantile(bw_pct).shift()
    sq = (bw.shift() <= thr).to_numpy()
    atr = _atr(df, atr_n); cc = c.to_numpy(); upv, dnv = up.to_numpy(), dn.to_numpy()
    trail = _trail_manage(trail_atr, atr); out = [None] * len(df)
    for i in range(len(df)):
        if not sq[i] or not np.isfinite(atr[i]) or not np.isfinite(upv[i]):
            continue
        if cc[i] > upv[i]:
            out[i] = Entry("long", cc[i] - sl_atr * atr[i], manage=trail, max_hold=max_hold)
        elif cc[i] < dnv[i]:
            out[i] = Entry("short", cc[i] + sl_atr * atr[i], manage=trail, max_hold=max_hold)
    return out


# ------------------------------------------------- 13. prior-day level sweep & reclaim
def build_pdhl_sweep(df, trade_start=16, trade_end=21, tp_mode="mid", tp_r=1.5, exit_hour=23,
                     sl_buf_atr=0.2, atr_n=20, level="day"):
    """During the US session a bar trades through the prior day (or week) low and
    closes back above it -> long; stop under the sweep low; target the prior
    range midpoint (or tp_r x risk). Mirror for highs."""
    hr, mn, wd = _hm(df)
    if level == "week":
        ph, pl = _week_levels(df)
    else:
        ph, pl, _, _ = _day_levels(df)
    atr = _atr(df, atr_n); h, l, c = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy()
    out = [None] * len(df); day = df.time.dt.normalize().to_numpy(); cur = None; traded = False
    for i in range(len(df)):
        if day[i] != cur:
            cur = day[i]; traded = False
        if traded or not (trade_start <= hr[i] <= trade_end) or not np.isfinite(atr[i]) or not np.isfinite(ph[i]):
            continue
        mid = (ph[i] + pl[i]) / 2
        if l[i] < pl[i] < c[i]:
            sl = l[i] - sl_buf_atr * atr[i]; d = c[i] - sl
            tp = mid if tp_mode == "mid" else c[i] + tp_r * d
            if tp > c[i]:
                out[i] = Entry("long", sl, tp, exit_hour=exit_hour); traded = True
        elif h[i] > ph[i] > c[i]:
            sl = h[i] + sl_buf_atr * atr[i]; d = sl - c[i]
            tp = mid if tp_mode == "mid" else c[i] - tp_r * d
            if tp < c[i]:
                out[i] = Entry("short", sl, tp, exit_hour=exit_hour); traded = True
    return out


# ------------------------------------------------- 14. intraday momentum / time-of-day drift
def build_intraday_momentum(df, signal_hour=19, exit_hour=21, ref="dopen", sl_atr=1.5, atr_n=20,
                            min_move_atr=0.0, direction="follow", weekdays=None):
    """Gao et al. style: at `signal_hour` trade the direction of the day so far
    (close vs day open, or vs prior close) into settlement/close."""
    hr, mn, wd = _hm(df); ph, pl, pc, dopen = _day_levels(df)
    atr = _atr(df, atr_n); c = df.close.to_numpy(); out = [None] * len(df)
    refv = dopen if ref == "dopen" else pc
    for i in range(len(df)):
        if hr[i] != signal_hour or mn[i] != 0 or not np.isfinite(atr[i]) or not np.isfinite(refv[i]):
            continue
        if weekdays is not None and wd[i] not in weekdays:
            continue
        mv = c[i] - refv[i]
        if abs(mv) < min_move_atr * atr[i] or mv == 0:
            continue
        side = "long" if mv > 0 else "short"
        if direction == "fade":
            side = "short" if side == "long" else "long"
        out[i] = _entry(side, c[i], sl_atr * atr[i], None, exit_hour=exit_hour)
    return out


def build_time_drift(df, enter_hour=16, exit_hour=21, side="long", sl_atr=1.5, atr_n=20, weekdays=None):
    """Pure time-of-day drift: enter at `enter_hour`, exit at `exit_hour`, fixed side."""
    hr, mn, wd = _hm(df); atr = _atr(df, atr_n); c = df.close.to_numpy(); out = [None] * len(df)
    for i in range(len(df)):
        if hr[i] != enter_hour or mn[i] != 0 or not np.isfinite(atr[i]):
            continue
        if weekdays is not None and wd[i] not in weekdays:
            continue
        out[i] = _entry(side, c[i], sl_atr * atr[i], None, exit_hour=exit_hour)
    return out


# ------------------------------------------------- 15. settlement -> overnight
def build_settlement_overnight(df, settle_hour=21, exit_hour=16, ref="dopen", direction="follow",
                               sl_atr=1.5, atr_n=20, min_move_atr=0.0):
    """At the 21:xx settlement bar close, trade the day's direction (or fade it) and
    hold overnight to the next pit open (16:00)."""
    return build_intraday_momentum(df, signal_hour=settle_hour, exit_hour=exit_hour, ref=ref,
                                   sl_atr=sl_atr, atr_n=atr_n, min_move_atr=min_move_atr, direction=direction)


# ------------------------------------------------- 16. London fade of the Asian move
def build_london_fade(df, london_hour=10, exit_hour=16, min_move_atr=0.5, sl_atr=1.5, atr_n=20, direction="fade"):
    """At 10:00 server, if the Asian session moved > min_move_atr from the day open,
    fade it back toward the open (exit by NY pit open) - or follow it."""
    return build_intraday_momentum(df, signal_hour=london_hour, exit_hour=exit_hour, ref="dopen",
                                   sl_atr=sl_atr, atr_n=atr_n, min_move_atr=min_move_atr, direction=direction)


# ------------------------------------------------- 17. EMA pullback trend (H4/D1)
def build_ema_pullback(df, fast=20, slow=50, sl_atr=2.0, atr_n=14, trail_atr=3.0, tp_r=None, side="both"):
    """EMA fast > slow, price dipped to/below EMA fast on the prior bar and closes
    back above it -> long with ATR trail (mirror for shorts)."""
    c = df.close; ef = c.ewm(span=fast, adjust=False).mean().to_numpy(); es = c.ewm(span=slow, adjust=False).mean().to_numpy()
    lo = df.low.to_numpy(); hi = df.high.to_numpy(); cc = c.to_numpy(); atr = _atr(df, atr_n)
    trail = _trail_manage(trail_atr, atr); out = [None] * len(df)
    for i in range(slow, len(df)):
        if not np.isfinite(atr[i]):
            continue
        if ef[i] > es[i] and lo[i - 1] <= ef[i - 1] and cc[i] > ef[i] and cc[i - 1] < cc[i] and side in ("both", "long"):
            out[i] = _entry("long", cc[i], sl_atr * atr[i], tp_r, manage=trail)
        elif ef[i] < es[i] and hi[i - 1] >= ef[i - 1] and cc[i] < ef[i] and cc[i - 1] > cc[i] and side in ("both", "short"):
            out[i] = _entry("short", cc[i], sl_atr * atr[i], tp_r, manage=trail)
    return out


# ------------------------------------------------- 18. D1 time-series momentum with vol regime
def build_tsmom(df, mom_n=20, vol_n=20, vol_filter="none", vol_lookback=120, sl_atr=3.0, atr_n=14,
                hold=5, side="both"):
    """Time-series momentum: sign of the mom_n-bar return, rebalanced every `hold`
    bars, optional realized-vol regime filter (trade only low/high vol)."""
    c = df.close; mom = c.pct_change(mom_n).to_numpy()
    rv = np.log(c).diff().rolling(vol_n).std()
    rank = rv.rolling(vol_lookback).rank(pct=True).to_numpy()
    atr = _atr(df, atr_n); cc = c.to_numpy(); out = [None] * len(df)
    for i in range(len(df)):
        if not np.isfinite(mom[i]) or not np.isfinite(atr[i]) or i % hold:
            continue
        if vol_filter == "low" and not (np.isfinite(rank[i]) and rank[i] < 0.5):
            continue
        if vol_filter == "high" and not (np.isfinite(rank[i]) and rank[i] >= 0.5):
            continue
        if mom[i] > 0 and side in ("both", "long"):
            out[i] = Entry("long", cc[i] - sl_atr * atr[i], max_hold=hold)
        elif mom[i] < 0 and side in ("both", "short"):
            out[i] = Entry("short", cc[i] + sl_atr * atr[i], max_hold=hold)
    return out


# ------------------------------------------------- 19. week-structure (short early week, long late week)
def build_week_structure(df, short_wd=0, short_hold=2, long_wd=2, long_hold=2, sl_atr=2.5, atr_n=14,
                         use_short=True, use_long=True, hour=None):
    """D1/H1: oil's week shape (Mon/Tue weak, Thu/Fri strong): short at the close of
    weekday short_wd for short_hold bars, long at the close of long_wd for long_hold bars."""
    hr, mn, wd = _hm(df); atr = _atr(df, atr_n); c = df.close.to_numpy(); out = [None] * len(df)
    for i in range(len(df)):
        if not np.isfinite(atr[i]) or (hour is not None and (hr[i] != hour or mn[i] != 0)):
            continue
        if use_short and wd[i] == short_wd:
            out[i] = Entry("short", c[i] + sl_atr * atr[i], max_hold=short_hold)
        elif use_long and wd[i] == long_wd:
            out[i] = Entry("long", c[i] - sl_atr * atr[i], max_hold=long_hold)
    return out


# ------------------------------------------------- 20. round-number reaction (oil $1 / gas $0.10)
def build_round_number(df, step=1.0, buf=0.15, trade_start=10, trade_end=21, sl_atr=1.0, tp_r=1.5,
                       exit_hour=23, atr_n=20, mode="bounce"):
    """A bar pierces a round level (multiple of `step`) and closes back on its
    original side -> bounce trade away from the level. mode='break': close through
    a round level -> continuation."""
    hr, mn, wd = _hm(df); atr = _atr(df, atr_n)
    h, l, c, o = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy(), df.open.to_numpy()
    out = [None] * len(df)
    for i in range(1, len(df)):
        if not (trade_start <= hr[i] <= trade_end) or not np.isfinite(atr[i]):
            continue
        lvl_dn = np.floor(c[i] / step) * step; lvl_up = lvl_dn + step
        if mode == "bounce":
            if l[i] < lvl_dn <= c[i] and o[i] > lvl_dn and (c[i] - lvl_dn) < buf * step:
                out[i] = _entry("long", c[i], sl_atr * atr[i], tp_r, exit_hour=exit_hour)
            elif h[i] > lvl_up >= c[i] and o[i] < lvl_up and (lvl_up - c[i]) < buf * step:
                out[i] = _entry("short", c[i], sl_atr * atr[i], tp_r, exit_hour=exit_hour)
        else:
            if o[i] < lvl_dn <= c[i] and (c[i] - lvl_dn) < buf * step:
                out[i] = _entry("long", c[i], sl_atr * atr[i], tp_r, exit_hour=exit_hour)
            elif o[i] > lvl_up >= c[i] and (lvl_up - c[i]) < buf * step:
                out[i] = _entry("short", c[i], sl_atr * atr[i], tp_r, exit_hour=exit_hour)
    return out


# ------------------------------------------------- 21. MA cross (Unger Academy crude: 30/140 on 15-min)
def build_ma_cross(df, fast=15, slow=70, sl_atr=2.0, atr_n=20, tp_r=None, trail_atr=None,
                   trade_start=None, trade_end=None, exit_hour=None, side="both"):
    """Fast SMA crosses slow SMA -> enter in that direction (the opposite cross is the
    next entry). ATR stop, optional target / ATR trail / hour filter."""
    c = df.close; f = c.rolling(fast).mean().to_numpy(); s = c.rolling(slow).mean().to_numpy()
    hr, mn, wd = _hm(df); atr = _atr(df, atr_n); cc = c.to_numpy(); out = [None] * len(df)
    trail = _trail_manage(trail_atr, atr) if trail_atr else None
    for i in range(1, len(df)):
        if not np.isfinite(s[i]) or not np.isfinite(s[i - 1]) or not np.isfinite(atr[i]):
            continue
        if trade_start is not None and not (trade_start <= hr[i] <= trade_end):
            continue
        up = f[i] > s[i] and f[i - 1] <= s[i - 1]
        dn = f[i] < s[i] and f[i - 1] >= s[i - 1]
        if up and side in ("both", "long"):
            out[i] = _entry("long", cc[i], sl_atr * atr[i], tp_r, manage=trail, exit_hour=exit_hour)
        elif dn and side in ("both", "short"):
            out[i] = _entry("short", cc[i], sl_atr * atr[i], tp_r, manage=trail, exit_hour=exit_hour)
    return out


# ------------------------------------------------- 22. prior-day high/low breakout (any day)
def build_pdhl_breakout(df, trade_start=16, trade_end=20, sl_mode="mid", sl_atr=1.0, tp_r=2.0,
                        exit_hour=23, atr_n=20, level="day", min_dist_atr=0.0):
    """Unger RB-gasoline style: first close above the prior day (or week) high during
    liquid hours -> long; below the low -> short. One trade a day. Stop = range
    midpoint / other side / ATR; target tp_r x risk; flat at exit_hour."""
    hr, mn, wd = _hm(df)
    if level == "week":
        ph, pl = _week_levels(df)
    else:
        ph, pl, _, _ = _day_levels(df)
    atr = _atr(df, atr_n); c = df.close.to_numpy(); out = [None] * len(df)
    day = df.time.dt.normalize().to_numpy(); cur = None; traded = False
    for i in range(len(df)):
        if day[i] != cur:
            cur = day[i]; traded = False
        if traded or not (trade_start <= hr[i] <= trade_end) or not np.isfinite(atr[i]) or not np.isfinite(ph[i]):
            continue
        mid = (ph[i] + pl[i]) / 2
        if c[i] > ph[i] and (c[i] - ph[i]) >= min_dist_atr * atr[i]:
            d = (c[i] - mid) if sl_mode == "mid" else (c[i] - pl[i]) if sl_mode == "range" else sl_atr * atr[i]
            out[i] = _entry("long", c[i], d, tp_r, exit_hour=exit_hour); traded = True
        elif c[i] < pl[i] and (pl[i] - c[i]) >= min_dist_atr * atr[i]:
            d = (mid - c[i]) if sl_mode == "mid" else (ph[i] - c[i]) if sl_mode == "range" else sl_atr * atr[i]
            out[i] = _entry("short", c[i], d, tp_r, exit_hour=exit_hour); traded = True
    return out


# ------------------------------------------------- 23. inside-bar breakout on H4/D1
def build_inside_bar(df, sl_mode="range", sl_atr=1.5, tp_r=2.0, max_hold=6, atr_n=14):
    """Prior bar is an inside bar; a close beyond the mother bar's high/low enters;
    stop = other side of the mother bar (or ATR); target tp_r x risk; time stop."""
    h, l, c = df.high.to_numpy(), df.low.to_numpy(), df.close.to_numpy(); atr = _atr(df, atr_n)
    out = [None] * len(df)
    for i in range(2, len(df)):
        if not np.isfinite(atr[i]):
            continue
        if not (h[i - 1] <= h[i - 2] and l[i - 1] >= l[i - 2]):
            continue
        mh, ml = h[i - 2], l[i - 2]
        if c[i] > mh:
            d = (c[i] - ml) if sl_mode == "range" else sl_atr * atr[i]
            out[i] = _entry("long", c[i], d, tp_r, max_hold=max_hold)
        elif c[i] < ml:
            d = (mh - c[i]) if sl_mode == "range" else sl_atr * atr[i]
            out[i] = _entry("short", c[i], d, tp_r, max_hold=max_hold)
    return out


# ------------------------------------------------- 24. big-bar fade (D1/H4 overreaction)
def build_close_fade(df, min_move_atr=1.0, sl_atr=1.5, atr_n=14, max_hold=2, tp_r=None, side="both"):
    """After an outsized bar (|close-open| > min_move_atr x ATR) fade it at the close,
    hold max_hold bars with an ATR stop (overreaction reversal)."""
    o, c = df.open.to_numpy(), df.close.to_numpy(); atr = _atr(df, atr_n); out = [None] * len(df)
    for i in range(len(df)):
        if not np.isfinite(atr[i]):
            continue
        mv = c[i] - o[i]
        if abs(mv) < min_move_atr * atr[i]:
            continue
        if mv > 0 and side in ("both", "short"):
            out[i] = _entry("short", c[i], sl_atr * atr[i], tp_r, max_hold=max_hold)
        elif mv < 0 and side in ("both", "long"):
            out[i] = _entry("long", c[i], sl_atr * atr[i], tp_r, max_hold=max_hold)
    return out
