"""Round-3 from-scratch strategies for the Asia index group: JPN225 HK50 CHINA50 AUS200.

Every build_<name>(df, **params) returns a list of H.Entry|None, len(df), causal
(bar i only uses rows <= i). Importing this module patches the prop harness for
the Asia symbols (see patch_harness): spread floors, index set (no commission)
and HKD/AUD profit-currency conversion, which the stock harness lacks.

Server time = EET (UTC+2 winter, UTC+3 summer). Cash sessions in server time:
  Tokyo  09:00-15:30 JST  -> 02:00-08:30 (winter) / 03:00-09:30 (summer)
  HK     09:30-16:00 HKT  -> 03:30-10:00 (winter) / 04:30-11:00 (summer)
  Sydney 10:00-16:00 AEST -> 02:00-08:00 (EET winter = AEDT summer) ... shifts 0-2h
Strategies take the session hours as parameters so sweeps can test both offsets.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H

# ----------------------------------------------------------------------------
# harness patches
# ----------------------------------------------------------------------------
ASIA_SPREADS = {"JPN225": 10.0, "HK50": 15.0, "CHINA50": 10.0, "AUS200": 2.0}
USDHKD = 7.80   # HKD is pegged 7.75-7.85; constant is good to <1%


def _attach_conv_patched(df, symbol, tf):
    spec = H._spec().get(symbol, {})
    ccy = spec.get("profit_ccy") or ("JPY" if symbol.endswith("JPY") else "USD")
    if ccy == "HKD":
        df["conv"] = 1.0 / USDHKD
        return df
    if ccy == "AUD":
        src = None
        for t in (tf, "H1"):
            p = H.DATA / f"audusd-{t.lower()}.csv"
            if p.exists():
                src = pd.read_csv(p, usecols=["time", "close"], parse_dates=["time"])
                break
        if src is None:
            df["conv"] = 0.66
            return df
        src = src.drop_duplicates("time").sort_values("time")
        src["conv"] = src["close"]
        out = pd.merge_asof(df, src[["time", "conv"]], on="time", direction="backward")
        out["conv"] = out["conv"].bfill()
        return out
    return _orig_attach_conv(df, symbol, tf)


_orig_attach_conv = H._attach_conv


def patch_harness():
    H.SPREAD_FLOOR.update(ASIA_SPREADS)
    H.INDICES.update(ASIA_SPREADS.keys())
    H._attach_conv = _attach_conv_patched


patch_harness()

# ----------------------------------------------------------------------------
# helpers (all causal)
# ----------------------------------------------------------------------------

def _arr(df):
    return (df["open"].to_numpy(float), df["high"].to_numpy(float),
            df["low"].to_numpy(float), df["close"].to_numpy(float))


def _atr(df, n=14):
    o, h, l, c = _arr(df)
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).ewm(alpha=1.0 / n, adjust=False).mean().to_numpy()


def _hours(df):
    t = pd.DatetimeIndex(df["time"])
    return t.hour.to_numpy(), t.minute.to_numpy(), t.normalize().to_numpy(), t.dayofweek.to_numpy()


def _day_index(days):
    """Index of the first bar of each day (array len(df): day id)."""
    new = np.r_[True, days[1:] != days[:-1]]
    return np.cumsum(new) - 1


def _prev_day_levels(df):
    """Per bar: prior full day's high/low/close (causal; uses days strictly before)."""
    o, h, l, c = _arr(df)
    _, _, days, _ = _hours(df)
    did = _day_index(days)
    n = len(df)
    nd = did[-1] + 1
    dh = np.full(nd, -np.inf); dl = np.full(nd, np.inf); dc = np.full(nd, np.nan)
    np.maximum.at(dh, did, h); np.minimum.at(dl, did, l)
    last_idx = np.zeros(nd, int)
    for i in range(n):
        last_idx[did[i]] = i
    dc = c[last_idx]
    ph = np.full(n, np.nan); pl = np.full(n, np.nan); pc = np.full(n, np.nan)
    m = did >= 1
    ph[m] = dh[did[m] - 1]; pl[m] = dl[did[m] - 1]; pc[m] = dc[did[m] - 1]
    return ph, pl, pc


def _eu_dst(times: pd.DatetimeIndex) -> np.ndarray:
    """1 where EU summer time applies (last Sun Mar .. last Sun Oct), in server stamps."""
    out = np.zeros(len(times), dtype=bool)
    for y in np.unique(times.year):
        mar = pd.Timestamp(y, 3, 31); mar -= pd.Timedelta(days=(mar.weekday() + 1) % 7)
        octo = pd.Timestamp(y, 10, 31); octo -= pd.Timedelta(days=(octo.weekday() + 1) % 7)
        s = mar + pd.Timedelta(hours=3); e = octo + pd.Timedelta(hours=4)
        out |= np.asarray((times >= s) & (times < e))
    return out.astype(int)


def _au_dst(times: pd.DatetimeIndex) -> np.ndarray:
    """1 where Australian (NSW) summer time applies: first Sun Oct 16:00 UTC .. first Sun Apr 16:00 UTC
    (server stamps are UTC+2/+3; a 2-hour error at the switch weekend is harmless)."""
    out = np.zeros(len(times), dtype=bool)
    for y in np.unique(times.year):
        oc = pd.Timestamp(y, 10, 1); oc += pd.Timedelta(days=(6 - oc.weekday()) % 7)
        ap = pd.Timestamp(y, 4, 1); ap += pd.Timedelta(days=(6 - ap.weekday()) % 7)
        out |= np.asarray(times >= oc + pd.Timedelta(hours=18) - pd.Timedelta(days=1))
        out &= ~np.asarray((times >= ap + pd.Timedelta(hours=18) - pd.Timedelta(days=1)) & (times < oc + pd.Timedelta(hours=18) - pd.Timedelta(days=1)))
    return out.astype(int)


def _asia_clock(df):
    """Hours in a DST-free 'asia clock' = UTC+2 (= server winter time).
    Returns (ahour float, day id int, weekday). Session params use this clock:
    Tokyo cash 02:00-08:30, HK 03:30-10:00 (lunch 06:00-07:00), FTSE China A50
    futures 03:00-10:30, Sydney 02:00-08:00 AEST / 01:00-07:00 AEDT."""
    t = pd.DatetimeIndex(df["time"])
    shift = -_eu_dst(t)
    if df.attrs.get("symbol") == "AUS200":
        shift = shift + _au_dst(t)      # AEDT: Sydney 10:00 = 23:00 UTC -> read as 02:00
    adj = t + pd.to_timedelta(shift, unit="h")
    ahour = adj.hour.to_numpy() + adj.minute.to_numpy() / 60.0
    did = _day_index(adj.normalize().to_numpy())
    return ahour, did, adj.dayofweek.to_numpy()


def _stale(df, n=3, frac=0.03, atr_n=200):
    """True where quotes look frozen (last n true ranges all < frac of the long median TR)."""
    o, h, l, c = _arr(df)
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    long_atr = pd.Series(tr).rolling(atr_n, min_periods=20).median().to_numpy()
    small = tr < frac * np.where(np.isnan(long_atr), np.inf, long_atr)
    out = pd.Series(small.astype(float)).rolling(n).sum().to_numpy() >= n
    return np.nan_to_num(out).astype(bool)


def _bar_step(ahour):
    """Bar size in hours, from the clock itself (mode of the positive hour differences in the
    first 500 bars). Constant per dataframe, so it never depends on where the data ends."""
    d = np.diff(ahour[:500])
    d = d[(d > 0) & (d <= 4)]
    if len(d) == 0:
        return 1.0
    vals, cnt = np.unique(np.round(d, 4), return_counts=True)
    return float(vals[np.argmax(cnt)])


def _bars_to_hour(ahour, did, i, target):
    """Bars from i until the clock reaches `target` on the same asia-day, computed from the bar
    size (schedule), NOT by scanning later rows, so the value is identical whether or not the
    later bars exist yet (look-ahead-safe). Always >= 1. A missing bar in the data makes the
    real exit one bar later, which is the conservative direction."""
    step = _bar_step(ahour)
    return max(1, int(np.ceil((target - ahour[i]) / step - 1e-9))) + 3


def _bars_overnight(ahour, i, open_h, break_h=1.0):
    """Bars from the close-bar i to the next asia-day's first bar >= open_h, from the schedule:
    (24 - hour) + open_h minus the broker's daily break (1h on IC Markets indices)."""
    step = _bar_step(ahour)
    return max(1, int(np.ceil(((24.0 - ahour[i]) + open_h - break_h) / step - 1e-9))) + 3


def _exit_at(ahour, did, i, target):
    """Clock exit as an Entry.manage: close on the first later bar whose asia-hour >= target on the
    entry day (target < 24) or on the next asia-day (target >= 24, e.g. overnight to the open).
    Any bar beyond that day also closes (safety). Causal: it reads only bar j's own stamp."""
    d0 = did[i]
    if target >= 24.0:
        t = target - 24.0

        def manage(df_, j, pos):
            if did[j] > d0 + 1 or (did[j] == d0 + 1 and ahour[j] >= t - 1e-9):
                return "close"
            return None
        return manage

    def manage(df_, j, pos):
        if did[j] > d0 or ahour[j] >= target - 1e-9:
            return "close"
        return None
    return manage


def _both(m1, m2):
    """Chain two manage functions: 'close' wins, else the first stop move."""
    def manage(df_, j, pos):
        a = m1(df_, j, pos); b = m2(df_, j, pos)
        if a == "close" or b == "close":
            return "close"
        return a if a is not None else b
    return manage


def _session_arrays(df, open_h, close_h):
    """Per asia-day session: running open/high/low and bars since the open bar (0 = open bar,
    -1 = outside the session)."""
    o, h, l, c = _arr(df)
    ahour, did, dow = _asia_clock(df)
    n = len(df)
    s_open = np.full(n, np.nan); s_hi = np.full(n, np.nan); s_lo = np.full(n, np.nan)
    bars_in = np.full(n, -1)
    cur = -1; so = sh = sl = np.nan; k = -1
    for i in range(n):
        if did[i] != cur:
            cur = did[i]; so = sh = sl = np.nan; k = -1
        if k >= 0 and ahour[i] >= close_h - 1e-9:
            k = -1; so = np.nan
        if np.isnan(so) and open_h <= ahour[i] < close_h:
            so, sh, sl, k = o[i], h[i], l[i], 0
        elif k >= 0:
            k += 1; sh = max(sh, h[i]); sl = min(sl, l[i])
        s_open[i], s_hi[i], s_lo[i], bars_in[i] = so, sh, sl, k
    return dict(s_open=s_open, s_hi=s_hi, s_lo=s_lo, bars_in=bars_in, ahour=ahour, did=did, dow=dow)


def _prev_session_close(df, close_h):
    """Per bar: close of the last bar before close_h on the most recent earlier asia-day."""
    o, h, l, c = _arr(df)
    ahour, did, _ = _asia_clock(df)
    n = len(df)
    out = np.full(n, np.nan)
    cur = -1; last_c = np.nan; prev = np.nan
    for i in range(n):
        if did[i] != cur:
            if cur >= 0 and not np.isnan(last_c):
                prev = last_c
            cur = did[i]; last_c = np.nan
        out[i] = prev
        if ahour[i] < close_h:
            last_c = c[i]
    return out


def _chandelier(mult, atr):
    def manage(df, i, pos):
        a = atr[i]
        if pos["side"] == "long":
            new = df["close"].iat[i] - mult * a
            return new if new > pos["sl"] else None
        new = df["close"].iat[i] + mult * a
        return new if new < pos["sl"] else None
    return manage


def _fill(df, sigs):
    bad = _stale(df)
    return [None if (s is None or bad[i]) else s for i, s in enumerate(sigs)]


def _tp(c, side, dist):
    if not dist:
        return None
    return c + dist if side == "long" else c - dist


# ----------------------------------------------------------------------------
# 1. Opening range breakout (HSI first-30m / Tokyo ORB practitioner rules)
# ----------------------------------------------------------------------------
def build_orb(df, open_h=2.0, close_h=8.0, n_bars=1, window=6, tp_r=1.0, sl_mode="opp",
              min_rng=0.3, max_rng=2.0, side="both", atr_n=14):
    """Range = first n_bars after cash open. Enter on a close beyond the range within `window`
    bars after it completes. SL = opposite side ('opp') or range mid ('mid'). TP = tp_r*range
    (0 -> exit at close). Flat at close_h. One trade per day."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    S = _session_arrays(df, open_h, close_h)
    ahour, did, bars_in = S["ahour"], S["did"], S["bars_in"]
    n = len(df); sigs = [None] * n
    rh = rl = np.nan; done = -1
    for i in range(n):
        k = bars_in[i]
        if k < 0:
            continue
        if k == n_bars - 1:
            rh, rl = S["s_hi"][i], S["s_lo"][i]
            continue
        if k < n_bars or did[i] == done or k > n_bars - 1 + window:
            continue
        rng = rh - rl
        if not (min_rng * atr[i] <= rng <= max_rng * atr[i]):
            continue
        hold = _bars_to_hour(ahour, did, i, close_h)
        if c[i] > rh and side in ("both", "long"):
            sl = rl if sl_mode == "opp" else (rh + rl) / 2
            sigs[i] = H.Entry("long", sl, _tp(c[i], "long", tp_r * rng), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="orb")); done = did[i]
        elif c[i] < rl and side in ("both", "short"):
            sl = rh if sl_mode == "opp" else (rh + rl) / 2
            sigs[i] = H.Entry("short", sl, _tp(c[i], "short", tp_r * rng), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="orb")); done = did[i]
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 2. First-hour reversal / open-drive fade
# ----------------------------------------------------------------------------
def build_orb_fade(df, open_h=2.0, close_h=8.0, n_bars=2, thr=0.8, sl_mult=0.5, tp_mode="open",
                   atr_n=14, side="both"):
    """After n_bars of the session, if |close - session open| > thr*ATR, fade it: SL beyond the
    session extreme + sl_mult*ATR, TP at the session open ('open') or half-way. Flat at close_h."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    S = _session_arrays(df, open_h, close_h)
    ahour, did, bars_in = S["ahour"], S["did"], S["bars_in"]
    n = len(df); sigs = [None] * n
    for i in range(n):
        if bars_in[i] != n_bars - 1:
            continue
        so = S["s_open"][i]; mv = c[i] - so
        if abs(mv) < thr * atr[i]:
            continue
        hold = _bars_to_hour(ahour, did, i, close_h)
        tp = so if tp_mode == "open" else c[i] - mv / 2
        if mv > 0 and side in ("both", "short"):
            sigs[i] = H.Entry("short", S["s_hi"][i] + sl_mult * atr[i], tp, max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="fade"))
        elif mv < 0 and side in ("both", "long"):
            sigs[i] = H.Entry("long", S["s_lo"][i] - sl_mult * atr[i], tp, max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="fade"))
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 3/4. Gap fill toward the prior cash close; gap continuation (Nikkei EA rules)
# ----------------------------------------------------------------------------
def build_gap_fill(df, open_h=3.5, close_h=10.0, min_gap=0.3, max_gap=2.5, sl_mult=1.0,
                   confirm=False, atr_n=14):
    """At the session open bar close: gap = open - prior cash close. If min_gap*ATR <= |gap| <=
    max_gap*ATR trade toward the fill: TP = prior close, SL = entry +/- sl_mult*|gap|.
    confirm=True also needs the open bar to close toward the fill. Flat at close_h."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    S = _session_arrays(df, open_h, close_h)
    pc = _prev_session_close(df, close_h)
    ahour, did, bars_in = S["ahour"], S["did"], S["bars_in"]
    n = len(df); sigs = [None] * n
    for i in range(n):
        if bars_in[i] != 0 or np.isnan(pc[i]):
            continue
        gap = o[i] - pc[i]
        if not (min_gap * atr[i] <= abs(gap) <= max_gap * atr[i]):
            continue
        hold = _bars_to_hour(ahour, did, i, close_h)
        if gap > 0:
            if (confirm and c[i] >= o[i]) or c[i] <= pc[i]:
                continue
            sigs[i] = H.Entry("short", c[i] + sl_mult * abs(gap), pc[i], max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="gapfill"))
        else:
            if (confirm and c[i] <= o[i]) or c[i] >= pc[i]:
                continue
            sigs[i] = H.Entry("long", c[i] - sl_mult * abs(gap), pc[i], max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="gapfill"))
    return _fill(df, sigs)


def build_gap_go(df, open_h=2.0, close_h=8.0, min_gap=0.3, tp_atr=1.5, sl_mode="bar", atr_n=14):
    """Gap > min_gap*ATR AND the open bar closes in the gap direction -> go with it.
    SL = open bar's opposite extreme ('bar') or the prior close ('pc'); TP tp_atr*ATR; flat at close_h."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    S = _session_arrays(df, open_h, close_h)
    pc = _prev_session_close(df, close_h)
    ahour, did, bars_in = S["ahour"], S["did"], S["bars_in"]
    n = len(df); sigs = [None] * n
    for i in range(n):
        if bars_in[i] != 0 or np.isnan(pc[i]):
            continue
        gap = o[i] - pc[i]
        if abs(gap) < min_gap * atr[i]:
            continue
        hold = _bars_to_hour(ahour, did, i, close_h)
        if gap > 0 and c[i] > o[i]:
            sigs[i] = H.Entry("long", l[i] if sl_mode == "bar" else pc[i], _tp(c[i], "long", tp_atr * atr[i]), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="gapgo"))
        elif gap < 0 and c[i] < o[i]:
            sigs[i] = H.Entry("short", h[i] if sl_mode == "bar" else pc[i], _tp(c[i], "short", tp_atr * atr[i]), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="gapgo"))
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 5/6. Prior-day high/low: breakout and rejection fade
# ----------------------------------------------------------------------------
def build_pdhl_break(df, open_h=2.0, close_h=8.0, sl_atr=1.0, tp_atr=2.0, atr_n=14, side="both"):
    """First session close above the prior day's high (below its low) -> long (short).
    SL sl_atr*ATR, TP tp_atr*ATR (0 -> none), flat at close_h. One per day."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    ph, pl, _ = _prev_day_levels(df)
    S = _session_arrays(df, open_h, close_h)
    ahour, did, bars_in = S["ahour"], S["did"], S["bars_in"]
    n = len(df); sigs = [None] * n; done = -1
    pc = np.r_[c[0], c[:-1]]
    for i in range(n):
        if bars_in[i] < 1 or did[i] == done or np.isnan(ph[i]):
            continue
        hold = _bars_to_hour(ahour, did, i, close_h)
        if c[i] > ph[i] and pc[i] <= ph[i] and side in ("both", "long"):
            sigs[i] = H.Entry("long", c[i] - sl_atr * atr[i], _tp(c[i], "long", tp_atr * atr[i]), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="pdh")); done = did[i]
        elif c[i] < pl[i] and pc[i] >= pl[i] and side in ("both", "short"):
            sigs[i] = H.Entry("short", c[i] + sl_atr * atr[i], _tp(c[i], "short", tp_atr * atr[i]), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="pdl")); done = did[i]
    return _fill(df, sigs)


def build_pdhl_fade(df, open_h=2.0, close_h=8.0, sl_atr=0.5, tp_atr=1.5, atr_n=14, side="both"):
    """Bar pierces the prior-day high but closes back below it -> short (mirror at the low).
    SL beyond the bar extreme + sl_atr*ATR, TP tp_atr*ATR, flat at close_h."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    ph, pl, _ = _prev_day_levels(df)
    S = _session_arrays(df, open_h, close_h)
    ahour, did, bars_in = S["ahour"], S["did"], S["bars_in"]
    n = len(df); sigs = [None] * n; done = -1
    for i in range(n):
        if bars_in[i] < 0 or did[i] == done or np.isnan(ph[i]):
            continue
        hold = _bars_to_hour(ahour, did, i, close_h)
        if h[i] > ph[i] and c[i] < ph[i] and side in ("both", "short"):
            sigs[i] = H.Entry("short", h[i] + sl_atr * atr[i], _tp(c[i], "short", tp_atr * atr[i]), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="pdh_fade")); done = did[i]
        elif l[i] < pl[i] and c[i] > pl[i] and side in ("both", "long"):
            sigs[i] = H.Entry("long", l[i] - sl_atr * atr[i], _tp(c[i], "long", tp_atr * atr[i]), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="pdl_fade")); done = did[i]
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 7. Overnight premium: in at cash close, out at next cash open
# ----------------------------------------------------------------------------
def build_overnight(df, close_h=8.0, open_h=2.0, sl_atr=1.5, side="long", filt="none", atr_n=14,
                    skip_fri=False):
    """Enter at the last bar before close_h; exit at the first bar >= open_h of the next asia-day.
    filt: 'none' | 'down_day' (only after a negative cash session) | 'up_day'."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    S = _session_arrays(df, open_h, close_h)
    ahour, did, dow = S["ahour"], S["did"], S["dow"]
    n = len(df); sigs = [None] * n
    for i in range(n - 1):
        if not (ahour[i] < close_h <= ahour[i + 1]) or did[i] != did[i + 1]:
            continue
        if skip_fri and dow[i] == 4:
            continue
        so = S["s_open"][i]
        if filt == "down_day" and not (so > c[i]):
            continue
        if filt == "up_day" and not (so < c[i]):
            continue
        hold = _bars_overnight(ahour, i, open_h)
        if side == "long":
            sigs[i] = H.Entry("long", c[i] - sl_atr * atr[i], None, max_hold=hold, manage=_exit_at(ahour, did, i, open_h + 24.0), meta=dict(k="on"))
        else:
            sigs[i] = H.Entry("short", c[i] + sl_atr * atr[i], None, max_hold=hold, manage=_exit_at(ahour, did, i, open_h + 24.0), meta=dict(k="on"))
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 8/9. Clock / calendar drift: fixed hour entry, weekday filter (Monday, pre-open)
# ----------------------------------------------------------------------------
def build_hour_drift(df, entry_h=0.0, hold_h=2.0, sl_atr=1.5, side="long", dows=(0, 1, 2, 3, 4),
                     atr_n=14, tp_atr=0.0):
    """Enter at the first bar with asia-hour >= entry_h on the allowed weekdays; exit hold_h
    hours later (bar count from the data). SL sl_atr*ATR, optional TP tp_atr*ATR."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    ahour, did, dow = _asia_clock(df)
    n = len(df); sigs = [None] * n; done = -1
    for i in range(n):
        if did[i] == done or dow[i] not in dows or ahour[i] < entry_h:
            continue
        done = did[i]
        if ahour[i] > entry_h + 1.0:
            continue
        hold = _bars_to_hour(ahour, did, i, ahour[i] + hold_h)
        if side == "long":
            sigs[i] = H.Entry("long", c[i] - sl_atr * atr[i], _tp(c[i], "long", tp_atr * atr[i]), max_hold=hold, manage=_exit_at(ahour, did, i, ahour[i] + hold_h), meta=dict(k="drift"))
        else:
            sigs[i] = H.Entry("short", c[i] + sl_atr * atr[i], _tp(c[i], "short", tp_atr * atr[i]), max_hold=hold, manage=_exit_at(ahour, did, i, ahour[i] + hold_h), meta=dict(k="drift"))
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 10. Intraday z-score mean reversion (AUS200 is MR at every timeframe)
# ----------------------------------------------------------------------------
def build_zscore_mr(df, n=20, z_in=2.0, sl_atr=1.5, max_hold=8, hours=(0, 24), side="both",
                    atr_n=14, tp="mean"):
    """z = (close - SMA(n))/std(n). Long below -z_in, short above +z_in inside the asia-hour
    window. TP = SMA ('mean') or none; SL sl_atr*ATR; time stop max_hold bars."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    s = pd.Series(c); ma = s.rolling(n).mean().to_numpy(); sd = s.rolling(n).std().to_numpy()
    ahour, did, dow = _asia_clock(df)
    z = (c - ma) / sd
    sigs = [None] * len(df)
    for i in range(len(df)):
        if np.isnan(z[i]) or not (hours[0] <= ahour[i] < hours[1]):
            continue
        if z[i] < -z_in and side in ("both", "long"):
            sigs[i] = H.Entry("long", c[i] - sl_atr * atr[i], ma[i] if tp == "mean" else None, max_hold=max_hold, meta=dict(k="zmr"))
        elif z[i] > z_in and side in ("both", "short"):
            sigs[i] = H.Entry("short", c[i] + sl_atr * atr[i], ma[i] if tp == "mean" else None, max_hold=max_hold, meta=dict(k="zmr"))
    return _fill(df, sigs)


def build_rsi_mr(df, n=2, lo=10, hi=90, sl_atr=2.0, max_hold=5, side="both", atr_n=14, trend_n=0):
    """Connors-style RSI(n) mean reversion: long when RSI<lo, short when RSI>hi. trend_n>0 takes
    longs only above SMA(trend_n) and shorts below. Exit on RSI crossing 50 (manage) or max_hold."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    d = np.diff(c, prepend=c[0])
    up = pd.Series(np.where(d > 0, d, 0.0)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.where(d < 0, -d, 0.0)).ewm(alpha=1 / n, adjust=False).mean()
    rsi = (100 - 100 / (1 + up / dn.replace(0, np.nan))).fillna(50).to_numpy()
    ma = pd.Series(c).rolling(trend_n).mean().to_numpy() if trend_n else None

    def manage(df_, i, pos):
        if pos["side"] == "long" and rsi[i] > 50:
            return "close"
        if pos["side"] == "short" and rsi[i] < 50:
            return "close"
        return None
    sigs = [None] * len(df)
    for i in range(len(df)):
        if rsi[i] < lo and side in ("both", "long") and (ma is None or (not np.isnan(ma[i]) and c[i] > ma[i])):
            sigs[i] = H.Entry("long", c[i] - sl_atr * atr[i], None, max_hold=max_hold, manage=manage, meta=dict(k="rsi"))
        elif rsi[i] > hi and side in ("both", "short") and (ma is None or (not np.isnan(ma[i]) and c[i] < ma[i])):
            sigs[i] = H.Entry("short", c[i] + sl_atr * atr[i], None, max_hold=max_hold, manage=manage, meta=dict(k="rsi"))
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 11. Daily mean reversion after a big move (D1 autocorrelation is negative on all four)
# ----------------------------------------------------------------------------
def build_daily_mr(df, lb=1, thr=1.5, hold=1, sl_atr=2.0, side="both", atr_n=20):
    """If the lb-bar return < -thr*ATR -> long at close (short mirror). Exit after `hold`
    bars; SL sl_atr*ATR."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    sigs = [None] * len(df)
    for i in range(lb, len(df)):
        mv = c[i] - c[i - lb]
        if mv < -thr * atr[i] and side in ("both", "long"):
            sigs[i] = H.Entry("long", c[i] - sl_atr * atr[i], None, max_hold=hold, meta=dict(k="dmr"))
        elif mv > thr * atr[i] and side in ("both", "short"):
            sigs[i] = H.Entry("short", c[i] + sl_atr * atr[i], None, max_hold=hold, meta=dict(k="dmr"))
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 12/17. Trend: Donchian / prior-week breakout with chandelier trail
# ----------------------------------------------------------------------------
def build_donchian(df, n=20, trail=3.0, side="both", atr_n=14, sl_atr=2.0):
    """Close above the highest high of the prior n bars -> long (mirror short). Initial SL
    sl_atr*ATR then chandelier trail trail*ATR; exits on the trail or an opposite signal."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    hh = pd.Series(h).rolling(n).max().shift(1).to_numpy()
    ll = pd.Series(l).rolling(n).min().shift(1).to_numpy()
    man = _chandelier(trail, atr)
    sigs = [None] * len(df)
    for i in range(len(df)):
        if np.isnan(hh[i]):
            continue
        if c[i] > hh[i] and side in ("both", "long"):
            sigs[i] = H.Entry("long", c[i] - sl_atr * atr[i], None, manage=man, meta=dict(k="don"))
        elif c[i] < ll[i] and side in ("both", "short"):
            sigs[i] = H.Entry("short", c[i] + sl_atr * atr[i], None, manage=man, meta=dict(k="don"))
    return _fill(df, sigs)


def build_weekly_break(df, trail=3.0, side="both", atr_n=14, sl_atr=2.0, tp_atr=0.0):
    """Close beyond the PRIOR calendar week's high/low -> trade the break with a chandelier
    trail. One entry per week per direction."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    t = pd.DatetimeIndex(df["time"])
    wk = (t - pd.to_timedelta(t.dayofweek, unit="D")).normalize().to_numpy()
    wid = _day_index(wk)
    nw = wid[-1] + 1
    wh = np.full(nw, -np.inf); wl = np.full(nw, np.inf)
    np.maximum.at(wh, wid, h); np.minimum.at(wl, wid, l)
    man = _chandelier(trail, atr)
    sigs = [None] * len(df); done_l = done_s = -1
    for i in range(len(df)):
        if wid[i] < 1:
            continue
        ph, pl = wh[wid[i] - 1], wl[wid[i] - 1]
        if c[i] > ph and side in ("both", "long") and done_l != wid[i]:
            sigs[i] = H.Entry("long", c[i] - sl_atr * atr[i], _tp(c[i], "long", tp_atr * atr[i]), manage=man, meta=dict(k="wk")); done_l = wid[i]
        elif c[i] < pl and side in ("both", "short") and done_s != wid[i]:
            sigs[i] = H.Entry("short", c[i] + sl_atr * atr[i], _tp(c[i], "short", tp_atr * atr[i]), manage=man, meta=dict(k="wk")); done_s = wid[i]
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 13. Dependence on the prior US session
# ----------------------------------------------------------------------------
def build_us_follow(df, open_h=2.0, close_h=8.0, us_start=16.5, us_end=23.0, thr=0.5, sign=1,
                    sl_atr=1.0, tp_atr=0.0, atr_n=14):
    """Prior asia-day's US-hours return (us_start..us_end). If |ret| > thr*ATR: sign=+1 follows
    it at the Asia open bar close, sign=-1 fades it. Flat at close_h."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    S = _session_arrays(df, open_h, close_h)
    ahour, did, bars_in = S["ahour"], S["did"], S["bars_in"]
    n = len(df); sigs = [None] * n
    us_ret = {}
    cur = -1; p0 = p1 = None
    for i in range(n):
        if did[i] != cur:
            if cur >= 0 and p0 is not None and p1 is not None:
                us_ret[cur] = p1 - p0
            cur = did[i]; p0 = p1 = None
        if ahour[i] >= us_start and p0 is None:
            p0 = o[i]
        if p0 is not None and ahour[i] <= us_end:
            p1 = c[i]
        if bars_in[i] == 0:
            r = us_ret.get(did[i] - 1)
            if r is None or abs(r) < thr * atr[i]:
                continue
            hold = _bars_to_hour(ahour, did, i, close_h)
            go_long = (r > 0) if sign > 0 else (r < 0)
            side = "long" if go_long else "short"
            sl = c[i] - sl_atr * atr[i] if go_long else c[i] + sl_atr * atr[i]
            sigs[i] = H.Entry(side, sl, _tp(c[i], side, tp_atr * atr[i]), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="us"))
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 14. Narrow-range / inside-day breakout
# ----------------------------------------------------------------------------
def build_nr_break(df, nr=4, open_h=2.0, close_h=10.0, tp_r=1.0, inside=False, atr_n=14):
    """Prior asia-day was the narrowest of the last `nr` (or an inside day) -> trade the first
    close beyond its range inside the session; SL = other side; TP tp_r*range; flat at close_h."""
    o, h, l, c = _arr(df)
    ahour, did, dow = _asia_clock(df)
    n = len(df); nd = did[-1] + 1
    dh = np.full(nd, -np.inf); dl = np.full(nd, np.inf)
    np.maximum.at(dh, did, h); np.minimum.at(dl, did, l)
    rng = dh - dl
    sigs = [None] * n; done = -1
    pc = np.r_[c[0], c[:-1]]
    for i in range(n):
        d = did[i]
        if d < nr + 1 or d == done or not (open_h <= ahour[i] < close_h):
            continue
        p = d - 1
        ok = rng[p] <= rng[p - nr + 1:p + 1].min() if not inside else (dh[p] <= dh[p - 1] and dl[p] >= dl[p - 1])
        if not ok:
            continue
        hold = _bars_to_hour(ahour, did, i, close_h)
        if c[i] > dh[p] and pc[i] <= dh[p]:
            sigs[i] = H.Entry("long", dl[p], _tp(c[i], "long", tp_r * rng[p]), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="nr")); done = d
        elif c[i] < dl[p] and pc[i] >= dl[p]:
            sigs[i] = H.Entry("short", dh[p], _tp(c[i], "short", tp_r * rng[p]), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="nr")); done = d
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 15. Lunch-break fade (HK / China morning move faded into the afternoon)
# ----------------------------------------------------------------------------
def build_lunch_fade(df, open_h=3.5, lunch_h=6.0, close_h=10.0, thr=0.7, sl_atr=0.75, tp_mode="open",
                     atr_n=14, sign=-1):
    """At the first bar >= lunch_h: morning move = close - session open. If > thr*ATR, sign=-1
    fades it (TP at the session open or half-way; SL beyond the morning extreme + sl_atr*ATR),
    sign=+1 continues it (TP = move again, SL at the session mean)."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    S = _session_arrays(df, open_h, close_h)
    ahour, did, bars_in = S["ahour"], S["did"], S["bars_in"]
    n = len(df); sigs = [None] * n; done = -1
    for i in range(n):
        if bars_in[i] < 1 or ahour[i] < lunch_h or did[i] == done:
            continue
        done = did[i]
        so = S["s_open"][i]; mv = c[i] - so
        if abs(mv) < thr * atr[i]:
            continue
        hold = _bars_to_hour(ahour, did, i, close_h)
        if sign < 0:
            tp = so if tp_mode == "open" else c[i] - mv / 2
            if mv > 0:
                sigs[i] = H.Entry("short", S["s_hi"][i] + sl_atr * atr[i], tp, max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="lunch"))
            else:
                sigs[i] = H.Entry("long", S["s_lo"][i] - sl_atr * atr[i], tp, max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="lunch"))
        else:
            if mv > 0:
                sigs[i] = H.Entry("long", c[i] - sl_atr * atr[i], c[i] + abs(mv), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="lunch_go"))
            else:
                sigs[i] = H.Entry("short", c[i] + sl_atr * atr[i], c[i] - abs(mv), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="lunch_go"))
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 16. Round-number rejection
# ----------------------------------------------------------------------------
def build_round_bounce(df, step=500.0, sl_atr=0.75, tp_atr=1.5, hours=(2, 10), atr_n=14, side="both",
                       max_hold=12):
    """A bar trades through a round level (multiple of `step`) and closes back on the original
    side -> trade the rejection. SL beyond the bar extreme + sl_atr*ATR, TP tp_atr*ATR."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    ahour, did, dow = _asia_clock(df)
    sigs = [None] * len(df)
    for i in range(1, len(df)):
        if not (hours[0] <= ahour[i] < hours[1]):
            continue
        lv = np.floor(c[i] / step) * step
        if o[i] > lv and l[i] < lv and c[i] > lv and side in ("both", "long"):
            sigs[i] = H.Entry("long", l[i] - sl_atr * atr[i], c[i] + tp_atr * atr[i], max_hold=max_hold, meta=dict(k="rn"))
            continue
        lv2 = np.ceil(c[i] / step) * step
        if o[i] < lv2 and h[i] > lv2 and c[i] < lv2 and side in ("both", "short"):
            sigs[i] = H.Entry("short", h[i] + sl_atr * atr[i], c[i] - tp_atr * atr[i], max_hold=max_hold, meta=dict(k="rn"))
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 19. Session-trend pullback to the running session mean (VWAP-like)
# ----------------------------------------------------------------------------
def build_session_pullback(df, open_h=2.0, close_h=8.0, thr=0.8, tol=0.2, sl_atr=0.75, atr_n=14, side="both"):
    """Session extreme vs open > thr*ATR defines the trend; enter with it when the close comes
    back within tol*ATR of the running mean close. TP = session extreme; SL sl_atr*ATR; flat at close_h."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    S = _session_arrays(df, open_h, close_h)
    ahour, did, bars_in = S["ahour"], S["did"], S["bars_in"]
    n = len(df); sigs = [None] * n; done = -1
    cum = 0.0
    for i in range(n):
        k = bars_in[i]
        if k < 0:
            continue
        cum = c[i] if k == 0 else cum + c[i]
        mean = cum / (k + 1)
        if k < 2 or did[i] == done:
            continue
        so = S["s_open"][i]
        up = S["s_hi"][i] - so; dn = so - S["s_lo"][i]
        hold = _bars_to_hour(ahour, did, i, close_h)
        if up > thr * atr[i] and up > dn and abs(c[i] - mean) < tol * atr[i] and side in ("both", "long") and S["s_hi"][i] > c[i] + 0.3 * atr[i]:
            sigs[i] = H.Entry("long", c[i] - sl_atr * atr[i], S["s_hi"][i], max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="pb")); done = did[i]
        elif dn > thr * atr[i] and dn > up and abs(c[i] - mean) < tol * atr[i] and side in ("both", "short") and S["s_lo"][i] < c[i] - 0.3 * atr[i]:
            sigs[i] = H.Entry("short", c[i] + sl_atr * atr[i], S["s_lo"][i], max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="pb")); done = did[i]
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 20. Asia cash-session result carried into the US session
# ----------------------------------------------------------------------------
def build_asia_to_us(df, open_h=2.0, close_h=8.0, us_start=16.5, us_end=23.0, thr=0.5, sign=1,
                     sl_atr=1.0, atr_n=14):
    """Cash-session return (open_h..close_h). At the first bar >= us_start, if |ret| > thr*ATR,
    sign=+1 continues it, sign=-1 fades it. Exit at us_end."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    S = _session_arrays(df, open_h, close_h)
    ahour, did, bars_in = S["ahour"], S["did"], S["bars_in"]
    n = len(df); sigs = [None] * n; done = -1
    sess_ret = np.nan; cur = -1
    for i in range(n):
        if did[i] != cur:
            cur = did[i]; sess_ret = np.nan
        if bars_in[i] >= 0:
            sess_ret = c[i] - S["s_open"][i]
        if ahour[i] >= us_start and did[i] != done and not np.isnan(sess_ret):
            done = did[i]
            if abs(sess_ret) < thr * atr[i]:
                continue
            hold = _bars_to_hour(ahour, did, i, us_end)
            go_long = (sess_ret > 0) if sign > 0 else (sess_ret < 0)
            if go_long:
                sigs[i] = H.Entry("long", c[i] - sl_atr * atr[i], None, max_hold=hold, manage=_exit_at(ahour, did, i, us_end), meta=dict(k="a2us"))
            else:
                sigs[i] = H.Entry("short", c[i] + sl_atr * atr[i], None, max_hold=hold, manage=_exit_at(ahour, did, i, us_end), meta=dict(k="a2us"))
    return _fill(df, sigs)


# ----------------------------------------------------------------------------
# 20. Gap continuation, practitioner rule set (Nikkei225 Gap Continuation EA, mql5 #187414):
#     gap >= min_gap_pct of price vs prior cash close; setup cancelled if price retraces half the
#     gap before entry; enter on a close beyond the opening-range (first n_bars) in the gap
#     direction within `window` bars; SL = opposite side of the OR; TP = tp_r * R; flat at close.
#     (The EA also wants price on the gap side of session VWAP; we use the half-gap rule only,
#     and no 40% partial at 1R since the harness manages one exit.)
# ----------------------------------------------------------------------------
def build_gap_continuation(df, open_h=2.0, close_h=8.0, min_gap_pct=1.0, n_bars=1, window=3,
                           tp_r=2.0, be_at_1r=True, atr_n=14):
    o, h, l, c = _arr(df)
    S = _session_arrays(df, open_h, close_h)
    pc = _prev_session_close(df, close_h)
    ahour, did, bars_in = S["ahour"], S["did"], S["bars_in"]
    n = len(df); sigs = [None] * n
    gap = np.nan; rh = rl = np.nan; dead = True

    for i in range(n):
        k = bars_in[i]
        if k < 0:
            continue
        if k == 0:
            dead = True
            if np.isnan(pc[i]) or pc[i] <= 0:
                continue
            gap = o[i] - pc[i]
            if abs(gap) / pc[i] * 100.0 < min_gap_pct:
                continue
            dead = False
            rh, rl = h[i], l[i]
        if dead:
            continue
        half = pc[i] + gap / 2.0
        if (gap > 0 and S["s_lo"][i] <= half) or (gap < 0 and S["s_hi"][i] >= half):
            dead = True
            continue
        if k <= n_bars - 1:
            rh, rl = S["s_hi"][i], S["s_lo"][i]
            continue
        if k > n_bars - 1 + window:
            dead = True
            continue
        hold = _bars_to_hour(ahour, did, i, close_h)
        if gap > 0 and c[i] > rh:
            R = c[i] - rl
            ex = _exit_at(ahour, did, i, close_h)
            sigs[i] = H.Entry("long", rl, c[i] + tp_r * R, max_hold=hold,
                              manage=_both(_be_manage(c[i], rl), ex) if be_at_1r else ex, meta=dict(k="gapcont"))
            dead = True
        elif gap < 0 and c[i] < rl:
            R = rh - c[i]
            ex = _exit_at(ahour, did, i, close_h)
            sigs[i] = H.Entry("short", rh, c[i] - tp_r * R, max_hold=hold,
                              manage=_both(_be_manage(c[i], rh), ex) if be_at_1r else ex, meta=dict(k="gapcont"))
            dead = True
    return _fill(df, sigs)


def _be_manage(entry, sl0):
    """Move the stop to entry once price has travelled 1R in our favour (uses only bar i)."""
    R = abs(entry - sl0)

    def manage(df_, i, pos):
        if pos["side"] == "long":
            if df_["high"].iat[i] >= entry + R and pos["sl"] < entry:
                return entry
        else:
            if df_["low"].iat[i] <= entry - R and pos["sl"] > entry:
                return entry
        return None
    return manage


# ----------------------------------------------------------------------------
# 21. Close-to-close momentum of the cash session with a US-session filter removed: simple
#     "yesterday's cash session direction" continuation at the open (open-drive follow-through).
# ----------------------------------------------------------------------------
def build_prev_session_follow(df, open_h=2.0, close_h=8.0, thr=0.5, sl_atr=1.0, tp_atr=0.0,
                              sign=1, atr_n=14):
    """At the open bar close: prior cash session move (close - open) > thr*ATR -> trade sign*direction
    (sign=1 follow, -1 fade). SL sl_atr*ATR, optional TP, flat at close_h."""
    o, h, l, c = _arr(df)
    atr = _atr(df, atr_n)
    S = _session_arrays(df, open_h, close_h)
    ahour, did, bars_in = S["ahour"], S["did"], S["bars_in"]
    n = len(df); sigs = [None] * n
    prev_mv = np.nan; cur_open = np.nan; last_c = np.nan; cur = -1
    for i in range(n):
        if did[i] != cur:
            if cur >= 0 and not np.isnan(cur_open) and not np.isnan(last_c):
                prev_mv = last_c - cur_open
            cur = did[i]; cur_open = np.nan; last_c = np.nan
        if bars_in[i] == 0:
            cur_open = o[i]
            if not np.isnan(prev_mv) and abs(prev_mv) >= thr * atr[i]:
                d = np.sign(prev_mv) * sign
                hold = _bars_to_hour(ahour, did, i, close_h)
                if d > 0:
                    sigs[i] = H.Entry("long", c[i] - sl_atr * atr[i], _tp(c[i], "long", tp_atr * atr[i]), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="psf"))
                else:
                    sigs[i] = H.Entry("short", c[i] + sl_atr * atr[i], _tp(c[i], "short", tp_atr * atr[i]), max_hold=hold, manage=_exit_at(ahour, did, i, close_h), meta=dict(k="psf"))
        if bars_in[i] >= 0:
            last_c = c[i]
    return _fill(df, sigs)
