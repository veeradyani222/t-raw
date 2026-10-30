"""Round-3 US index strategies (US30 / US500 / USTEC / US2000), from scratch.

Every builder: build_<name>(df, **params) -> list[H.Entry | None] of len(df), causal
(bar i uses rows <= i only; day/week/month aggregates come from COMPLETED periods
or a calendar, never from the current period's future bars).

Server clock = EET. NY cash session 16:30-23:00. On M30 the 16:00 bar closes at
16:30 (= cash open) and the 22:30 bar closes at 23:00 (= cash close). On H1 the
16:00 bar closes 17:00 and the 22:00 bar closes 23:00.

Known stale-feed days (data-quality pass, see NOTES.md) are excluded from entries, together
with the following day (its prior-day levels would be stale). Intraday builders also exclude
any day containing a frozen-feed stretch (bar-level detector in P), plus the next day.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop import harness as H

# ---- cost model additions for symbols the harness does not know -----------------
H.SPREAD_FLOOR.setdefault("US2000", 0.5)
H.INDICES.add("US2000")

# stale-feed days found by study.py (all four indices share the feed)
EXCLUDE_DAYS = {"2018-04-07", "2018-04-08", "2024-10-30", "2024-11-14", "2024-11-15",
                "2024-12-03", "2024-12-31", "2025-01-01", "2025-01-02", "2025-01-03"}

FOMC = ["2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19", "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
        "2020-01-29", "2020-03-03", "2020-03-15", "2020-04-29", "2020-06-10", "2020-07-29", "2020-09-16", "2020-11-05", "2020-12-16",
        "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16", "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
        "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15", "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
        "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14", "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
        "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
        "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
        "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09"]

ROUND = {"US30": (1000, 500), "US500": (100, 50), "USTEC": (1000, 500), "US2000": (100, 50)}


# ---- helpers ---------------------------------------------------------------------
class P:
    """Precomputed causal arrays for one df."""

    def __init__(self, df):
        self.df = df
        self.n = len(df)
        self.o, self.h, self.l, self.c = (df[k].to_numpy(float) for k in ("open", "high", "low", "close"))
        self.v = df["tick_volume"].to_numpy(float)
        t = pd.DatetimeIndex(df["time"])
        self.t = t
        self.hour = t.hour.to_numpy(); self.minute = t.minute.to_numpy(); self.dow = t.dayofweek.to_numpy()
        self.hm = self.hour * 100 + self.minute
        dates = t.normalize()
        self.dates = dates
        self.date_str = dates.strftime("%Y-%m-%d").to_numpy()
        _, self.day_id, counts = np.unique(dates.to_numpy(), return_inverse=True, return_counts=True)
        self.day_start = np.r_[0, np.cumsum(counts)[:-1]]
        self.nday = len(counts)
        # completed-day aggregates (index = day id)
        self.d_high = np.maximum.reduceat(self.h, self.day_start)
        self.d_low = np.minimum.reduceat(self.l, self.day_start)
        self.d_open = self.o[self.day_start]
        self.d_close = self.c[np.r_[self.day_start[1:] - 1, self.n - 1]]
        self.d_vol = np.add.reduceat(self.v, self.day_start)
        # per-bar previous-day levels (day id - 1), nan for first day
        pid = self.day_id - 1
        ok = pid >= 0
        def prev(arr):
            out = np.full(self.n, np.nan); out[ok] = arr[pid[ok]]; return out
        self.pd_high, self.pd_low, self.pd_close, self.pd_open = prev(self.d_high), prev(self.d_low), prev(self.d_close), prev(self.d_open)
        # daily ATR (mean of last 14 completed day ranges), per bar
        drng = self.d_high - self.d_low
        datr = pd.Series(drng).rolling(14, min_periods=5).mean().to_numpy()
        self.d_atr = prev(datr)
        self.d_atr_med100 = prev(pd.Series(drng).rolling(100, min_periods=30).median().to_numpy())
        # running intraday high/low up to and including bar i
        self.run_high = np.empty(self.n); self.run_low = np.empty(self.n)
        for s, e in zip(self.day_start, np.r_[self.day_start[1:], self.n]):
            self.run_high[s:e] = np.maximum.accumulate(self.h[s:e])
            self.run_low[s:e] = np.minimum.accumulate(self.l[s:e])
        self.bar_in_day = np.arange(self.n) - self.day_start[self.day_id]
        # excluded days: stale days and the day after
        excl = np.zeros(self.nday, bool)
        udates = pd.DatetimeIndex(np.unique(dates.to_numpy()))
        ds = udates.strftime("%Y-%m-%d")
        for k, d in enumerate(ds):
            if d in EXCLUDE_DAYS:
                excl[k] = True
                if k + 1 < self.nday:
                    excl[k + 1] = True
        self.sym = df.attrs.get("symbol", "")
        self.tf = str(df.attrs.get("tf", "")).upper()
        self.is_d1 = self.tf == "D1"
        # bar-level stale-feed detector (intraday only): the broker feed froze for hours inside
        # otherwise normal days (Oct 2024 - Jan 2025), which the daily-range check misses. A bar
        # is stale when the 14-bar ATR is < 20% of its rolling 500-bar median, or the last 6 bars
        # all have the same high/low. The whole day and the following day are excluded.
        self.stale = np.zeros(self.n, bool)
        if not self.is_d1:
            a = atr(self.h, self.l, self.c, 14)
            med = pd.Series(a).rolling(500, min_periods=50).median().to_numpy()
            rng = self.h - self.l
            frozen = (pd.Series(self.h).rolling(6).max().to_numpy() == pd.Series(self.h).rolling(6).min().to_numpy()) &                      (pd.Series(self.l).rolling(6).max().to_numpy() == pd.Series(self.l).rolling(6).min().to_numpy())
            self.stale = ((a < 0.2 * med) & np.isfinite(med)) | frozen | (rng <= 0)
            stale_days = np.zeros(self.nday, bool)
            stale_days[np.unique(self.day_id[self.stale])] = True
            nxt = np.r_[False, stale_days[:-1]]
            excl |= stale_days | nxt
        self.excluded = excl[self.day_id]
        # fomc per bar
        fomc = set(FOMC)
        self.is_fomc = np.array([d in fomc for d in ds])[self.day_id]
        nxt = np.r_[np.array([d in fomc for d in ds])[1:], False]
        self.is_pre_fomc = nxt[self.day_id]
        # bar-level ATR(14)
        self.atr = atr(self.h, self.l, self.c, 14)
        self._wk = None; self._mo = None

    def ema(self, n):
        return pd.Series(self.c).ewm(span=n, adjust=False).mean().to_numpy()

    def sma(self, n):
        return pd.Series(self.c).rolling(n).mean().to_numpy()

    def daily_sma_prev(self, n):
        """SMA of completed daily closes, per bar (uses yesterday's and earlier closes)."""
        s = pd.Series(self.d_close).rolling(n, min_periods=max(5, n // 2)).mean().to_numpy()
        pid = self.day_id - 1; out = np.full(self.n, np.nan); ok = pid >= 0
        out[ok] = s[pid[ok]]; return out

    def daily_closes_prev(self, k):
        """k-th previous completed daily close (k=1 yesterday)."""
        pid = self.day_id - k; out = np.full(self.n, np.nan); ok = pid >= 0
        out[ok] = self.d_close[pid[ok]]; return out

    def week(self):
        if self._wk is None:
            iso = self.t.isocalendar()
            key = (iso.year.to_numpy() * 100 + iso.week.to_numpy())
            _, wid, cnt = np.unique(key, return_inverse=True, return_counts=True)
            ws = np.r_[0, np.cumsum(cnt)[:-1]]
            w_high = np.maximum.reduceat(self.h, ws); w_low = np.minimum.reduceat(self.l, ws)
            w_close = self.c[np.r_[ws[1:] - 1, self.n - 1]]
            pw = wid - 1; ok = pw >= 0
            def prev(a):
                out = np.full(self.n, np.nan); out[ok] = a[pw[ok]]; return out
            self._wk = dict(id=wid, high=prev(w_high), low=prev(w_low), close=prev(w_close),
                            bar_in_week=np.arange(self.n) - ws[wid])
        return self._wk

    def days_to_month_end(self):
        """Weekdays remaining in the calendar month AFTER this bar's date (calendar-based)."""
        d = self.dates
        me = (d + pd.offsets.MonthEnd(0)).to_numpy().astype("datetime64[D]")
        today = d.to_numpy().astype("datetime64[D]")
        return np.busday_count(today + np.timedelta64(1, "D"), me + np.timedelta64(1, "D"))

    def trading_day_of_month(self):
        """1-based count of completed-or-current distinct trading days in this bar's month (data-based, causal)."""
        ym = (self.dates.year * 100 + self.dates.month).to_numpy()
        _, mid, cnt = np.unique(ym, return_inverse=True, return_counts=True)
        out = np.empty(self.n, int)
        for m in range(len(cnt)):
            idx = np.where(mid == m)[0]
            dd = self.day_id[idx]
            out[idx] = dd - dd[0] + 1
        return out


def atr(h, l, c, n):
    pc = np.r_[np.nan, c[:-1]]
    tr = np.maximum(h - l, np.maximum(np.abs(h - pc), np.abs(l - pc)))
    return pd.Series(tr).rolling(n, min_periods=max(3, n // 2)).mean().to_numpy()


def rsi(c, n):
    d = np.diff(c, prepend=np.nan)
    up = pd.Series(np.where(d > 0, d, 0.0)).ewm(alpha=1 / n, adjust=False).mean()
    dn = pd.Series(np.where(d < 0, -d, 0.0)).ewm(alpha=1 / n, adjust=False).mean()
    rs = up / dn.replace(0, np.nan)
    return (100 - 100 / (1 + rs)).to_numpy()


def _ok(x):
    return x is not None and np.isfinite(x)


def _entry(side, c, stop_dist, tp_r=None, **kw):
    if not _ok(stop_dist) or stop_dist <= 0:
        return None
    if side == "long":
        sl = c - stop_dist; tp = c + tp_r * stop_dist if tp_r else None
    else:
        sl = c + stop_dist; tp = c - tp_r * stop_dist if tp_r else None
    return H.Entry(side, sl, tp, **kw)


def _trend_ok(p, i, trend, ema_n=50):
    """Daily-trend gate from completed daily closes: 'with' = yesterday close > daily SMA."""
    if trend is None or trend == "none":
        return True, True
    s = p.daily_sma_prev(ema_n)[i] if not hasattr(p, "_tsma") else p._tsma[i]
    pc = p.pd_close[i]
    if not (_ok(s) and _ok(pc)):
        return False, False
    up = pc > s
    if trend == "with":
        return up, not up
    return (not up), up   # against


def _gate_arrays(p, trend, ema_n=50):
    if trend in (None, "none"):
        return np.ones(p.n, bool), np.ones(p.n, bool)
    s = p.daily_sma_prev(ema_n); pc = p.pd_close
    up = (pc > s) & np.isfinite(s)
    dn = (pc < s) & np.isfinite(s)
    return (up, dn) if trend == "with" else (dn, up)


# ---- 1. turn of month ------------------------------------------------------------
def build_tom(df, days_before=1, days_after=3, sl_atr=1.5, side="long", trend=None):
    """Long at the close `days_before` weekdays before month end, exit at the close of
    trading day `days_after` of the new month (D1). Stop = sl_atr x daily ATR."""
    p = P(df); out = [None] * p.n
    dtm = p.days_to_month_end()
    long_ok, short_ok = _gate_arrays(p, trend)
    for i in range(p.n):
        if p.excluded[i] or dtm[i] != days_before or not _ok(p.d_atr[i]):
            continue
        ok = long_ok[i] if side == "long" else short_ok[i]
        if not ok:
            continue
        hold = days_before + days_after
        out[i] = _entry(side, p.c[i], sl_atr * p.d_atr[i], max_hold=hold, meta=dict(k="tom"))
    return out


# ---- 2. options-expiry week ------------------------------------------------------
def build_opex(df, mode="short_week", sl_atr=1.5, trend=None):
    """mode 'short_week': short at the close of the Friday before OpEx week, cover at
    OpEx Friday close. 'long_after': long at OpEx Friday close, exit next Friday close.
    'long_week': long over OpEx week (QuantifiedStrategies' published version). D1."""
    p = P(df); out = [None] * p.n
    dom = p.dates.day.to_numpy()
    third_fri = (p.dow == 4) & (dom >= 15) & (dom <= 21)
    fri_before = (p.dow == 4) & (dom >= 8) & (dom <= 14)
    long_ok, short_ok = _gate_arrays(p, trend)
    for i in range(p.n):
        if p.excluded[i] or not _ok(p.d_atr[i]):
            continue
        if mode == "short_week" and fri_before[i] and short_ok[i]:
            out[i] = _entry("short", p.c[i], sl_atr * p.d_atr[i], max_hold=5, meta=dict(k="opex"))
        elif mode == "long_week" and fri_before[i] and long_ok[i]:
            out[i] = _entry("long", p.c[i], sl_atr * p.d_atr[i], max_hold=5, meta=dict(k="opex"))
        elif mode == "long_after" and third_fri[i] and long_ok[i]:
            out[i] = _entry("long", p.c[i], sl_atr * p.d_atr[i], max_hold=5, meta=dict(k="opex"))
    return out


# ---- 3. FOMC ---------------------------------------------------------------------
def build_fomc(df, mode="pre_drift", entry_hour=20, sl_atr=1.0, exit_hour=20, side="long"):
    """H1/M30. 'pre_drift' (Lucca-Moench): long at `entry_hour` close the day before the
    announcement, exit at `exit_hour` on FOMC day (bar before the 21:00 statement).
    'post_mom': at the close of the 21:00 bar on FOMC day go WITH that bar, flat at 23:00.
    'post_fade': same bar, against. Stop = sl_atr x daily ATR."""
    p = P(df); out = [None] * p.n
    for i in range(p.n):
        if p.excluded[i] or not _ok(p.d_atr[i]):
            continue
        if mode == "pre_drift" and p.is_pre_fomc[i] and p.hour[i] == entry_hour and p.minute[i] == 0:
            out[i] = _entry(side, p.c[i], sl_atr * p.d_atr[i], exit_hour=exit_hour, meta=dict(k="fomc_pre"))
        elif mode in ("post_mom", "post_fade") and p.is_fomc[i] and p.hour[i] == 21 and p.minute[i] == (30 if p.tf == "M30" else 0):
            # bar covering the 21:00 statement: H1 21:00 bar closes 22:00; M30 use 21:30 bar (21:30-22:00)
            j = i if p.tf != "M30" else i - 1
            d = np.sign(p.c[i] - p.o[j])
            if d == 0:
                continue
            s = ("long" if d > 0 else "short") if mode == "post_mom" else ("short" if d > 0 else "long")
            out[i] = _entry(s, p.c[i], sl_atr * p.d_atr[i], exit_hour=22, meta=dict(k="fomc_post"))
    return out


# ---- 4. overnight drift ----------------------------------------------------------
def build_overnight(df, sl_atr=0.8, trend=None, dow=None, after="any", tp_r=None):
    """M30/H1: long at the cash close (22:30 bar on M30 / 22:00 bar on H1 -> 23:00), exit at
    the cash open (first bar with hour 16: M30 16:00 bar closes 16:30; H1 16:00 bar closes 17:00).
    `after`: 'any' | 'down' (cash session closed below its open) | 'up'. `dow`: list of weekdays."""
    p = P(df); out = [None] * p.n
    long_ok, _ = _gate_arrays(p, trend)
    close_hm = 2230 if p.tf == "M30" else 2200
    # cash open price of the day: open of the 16:30 bar (M30) / 16:00 bar (H1), causal at the close
    cash_open = np.full(p.n, np.nan)
    cur = np.nan; last_day = -1
    for i in range(p.n):
        if p.day_id[i] != last_day:
            cur = np.nan; last_day = p.day_id[i]
        if p.hm[i] == (1630 if p.tf == "M30" else 1600):
            cur = p.o[i]
        cash_open[i] = cur
    for i in range(p.n):
        if p.excluded[i] or p.hm[i] != close_hm or not long_ok[i] or not _ok(p.d_atr[i]):
            continue
        if dow is not None and p.dow[i] not in dow:
            continue
        if after != "any":
            if not _ok(cash_open[i]):
                continue
            if after == "down" and not (p.c[i] < cash_open[i]):
                continue
            if after == "up" and not (p.c[i] > cash_open[i]):
                continue
        out[i] = _entry("long", p.c[i], sl_atr * p.d_atr[i], tp_r=tp_r, exit_hour=16, meta=dict(k="on"))
    return out


# ---- 5. opening-range breakout with relative-volume filter --------------------------
def build_orb(df, or_bars=1, rvol_min=None, stop="mid", tp_r=2.0, last_entry_hm=1900, trend=None,
              sides="both", exit_hm=2230):
    """M30. Opening range = first `or_bars` bars from 16:30. Enter on the first bar that CLOSES
    beyond the range (one trade per day). Stop at the range midpoint ('mid') or opposite
    edge ('far'). TP tp_r x risk, else flat at `exit_hm` (22:30 bar close = 23:00).
    rvol_min: opening-bar volume / median of the last 20 opening-bar volumes."""
    p = P(df); out = [None] * p.n
    long_ok, short_ok = _gate_arrays(p, trend)
    or_hi = or_lo = np.nan; done = False; last_day = -1; n_in = 0
    open_vols = []; rvol = np.nan; or_end_vol = 0.0
    for i in range(p.n):
        if p.day_id[i] != last_day:
            last_day = p.day_id[i]; or_hi = or_lo = np.nan; done = False; n_in = 0; rvol = np.nan; or_end_vol = 0.0
        if p.hm[i] < 1630:
            continue
        if n_in < or_bars:
            or_hi = p.h[i] if n_in == 0 else max(or_hi, p.h[i])
            or_lo = p.l[i] if n_in == 0 else min(or_lo, p.l[i])
            or_end_vol += p.v[i]
            n_in += 1
            if n_in == or_bars:
                med = np.median(open_vols[-20:]) if len(open_vols) >= 10 else np.nan
                rvol = or_end_vol / med if _ok(med) and med > 0 else np.nan
                open_vols.append(or_end_vol)
            continue
        if done or p.excluded[i] or p.hm[i] > last_entry_hm:
            continue
        if rvol_min is not None and not (_ok(rvol) and rvol >= rvol_min):
            continue
        mid = (or_hi + or_lo) / 2
        if p.c[i] > or_hi and sides in ("both", "long") and long_ok[i]:
            sl = mid if stop == "mid" else or_lo
            d = p.c[i] - sl
            out[i] = _entry("long", p.c[i], d, tp_r=tp_r, exit_hour=exit_hm // 100, meta=dict(k="orb", rvol=rvol)); done = True
        elif p.c[i] < or_lo and sides in ("both", "short") and short_ok[i]:
            sl = mid if stop == "mid" else or_hi
            d = sl - p.c[i]
            out[i] = _entry("short", p.c[i], d, tp_r=tp_r, exit_hour=exit_hm // 100, meta=dict(k="orb", rvol=rvol)); done = True
    return out


# ---- 6. hour-of-day windows (lunch effect / afternoon drift / first hour) ------------
def build_hour_window(df, entry_hour=19, exit_hour=21, side="long", sl_atr=0.5, trend=None, dow=None,
                      cond=None):
    """H1/M30: enter at the close of the bar whose hour == entry_hour (minute 0), exit at the close
    of the next bar with hour == exit_hour (H1: 19 -> 21 means hold 20:00-22:00).
    Stop = sl_atr x daily ATR. `cond`: None | 'day_down' (price below the day's open so far)
    | 'day_up' | 'below_pdc' | 'above_pdc'."""
    p = P(df); out = [None] * p.n
    long_ok, short_ok = _gate_arrays(p, trend)
    for i in range(p.n):
        if p.excluded[i] or p.hour[i] != entry_hour or p.minute[i] != 0 or not _ok(p.d_atr[i]):
            continue
        if dow is not None and p.dow[i] not in dow:
            continue
        if not (long_ok[i] if side == "long" else short_ok[i]):
            continue
        dopen = p.o[p.day_start[p.day_id[i]]]
        if cond == "day_down" and not p.c[i] < dopen: continue
        if cond == "day_up" and not p.c[i] > dopen: continue
        if cond == "below_pdc" and not p.c[i] < p.pd_close[i]: continue
        if cond == "above_pdc" and not p.c[i] > p.pd_close[i]: continue
        out[i] = _entry(side, p.c[i], sl_atr * p.d_atr[i], exit_hour=exit_hour, meta=dict(k="hw"))
    return out


# ---- 7. prior-day-low sweep and reclaim (intraday liquidity sweep) -----------------
def build_pdl_sweep(df, tp="pd_mid", sl_pad=0.1, start_hm=1630, end_hm=2100, trend=None, sides="long",
                    exit_hm=2230, max_hold=None):
    """M30/H1 during cash hours: the bar trades BELOW yesterday's low but CLOSES back above it
    -> long; stop below the sweep low (pad = sl_pad x daily ATR); TP yesterday's midpoint
    ('pd_mid'), yesterday's high ('pd_high') or 'pd_close'. Mirror for shorts at yesterday's high.
    One trade per day, flat at exit_hm."""
    p = P(df); out = [None] * p.n
    long_ok, short_ok = _gate_arrays(p, trend)
    last_day = -1; done = False
    for i in range(p.n):
        if p.day_id[i] != last_day:
            last_day = p.day_id[i]; done = False
        if done or p.excluded[i] or not (start_hm <= p.hm[i] <= end_hm) or not _ok(p.pd_low[i]) or not _ok(p.d_atr[i]):
            continue
        pdl, pdh, pdc = p.pd_low[i], p.pd_high[i], p.pd_close[i]
        mid = (pdl + pdh) / 2
        if sides in ("long", "both") and long_ok[i] and p.l[i] < pdl and p.c[i] > pdl:
            sl = p.l[i] - sl_pad * p.d_atr[i]
            tpv = {"pd_mid": mid, "pd_high": pdh, "pd_close": pdc, None: None}[tp]
            if tpv is not None and tpv <= p.c[i]:
                tpv = None if tp is None else max(tpv, p.c[i] + (p.c[i] - sl))
            out[i] = H.Entry("long", sl, tpv, exit_hour=exit_hm // 100, max_hold=max_hold, meta=dict(k="pdl")); done = True
        elif sides in ("short", "both") and short_ok[i] and p.h[i] > pdh and p.c[i] < pdh:
            sl = p.h[i] + sl_pad * p.d_atr[i]
            tpv = {"pd_mid": mid, "pd_high": pdl, "pd_close": pdc, None: None}[tp]
            if tpv is not None and tpv >= p.c[i]:
                tpv = None if tp is None else min(tpv, p.c[i] - (sl - p.c[i]))
            out[i] = H.Entry("short", sl, tpv, exit_hour=exit_hm // 100, max_hold=max_hold, meta=dict(k="pdh")); done = True
    return out


# ---- 8. D1 failed breakdown / breakout (turtle soup at N-day extremes) --------------
def build_turtle_soup(df, n=20, mode="long", hold=5, sl_pad=0.2, tp_r=None, trend=None, exit_rule="hold"):
    """D1. Long: today's low < the prior n-day low but the close is back above it (failed
    breakdown). Short: mirror at the n-day high. Stop below today's low (pad x ATR14).
    exit_rule 'hold' = max_hold days; 'pdh' = close above yesterday's high (manage)."""
    p = P(df); out = [None] * p.n
    lo_n = pd.Series(p.l).rolling(n).min().shift(1).to_numpy()
    hi_n = pd.Series(p.h).rolling(n).max().shift(1).to_numpy()
    long_ok, short_ok = _gate_arrays(p, trend)
    h, l, c = p.h, p.l, p.c
    for i in range(p.n):
        if p.excluded[i] or not _ok(lo_n[i]) or not _ok(p.atr[i]):
            continue
        if mode in ("long", "both") and long_ok[i] and l[i] < lo_n[i] and c[i] > lo_n[i]:
            sl = l[i] - sl_pad * p.atr[i]
            mg = None
            if exit_rule == "pdh":
                def mg(d, j, pos, _h=h, _c=c):
                    return "close" if _c[j] > _h[j - 1] else None
            out[i] = H.Entry("long", sl, c[i] + tp_r * (c[i] - sl) if tp_r else None,
                             max_hold=hold, manage=mg, meta=dict(k="ts"))
        elif mode in ("short", "both") and short_ok[i] and h[i] > hi_n[i] and c[i] < hi_n[i]:
            sl = h[i] + sl_pad * p.atr[i]
            mg = None
            if exit_rule == "pdh":
                def mg(d, j, pos, _l=l, _c=c):
                    return "close" if _c[j] < _l[j - 1] else None
            out[i] = H.Entry("short", sl, c[i] - tp_r * (sl - c[i]) if tp_r else None,
                             max_hold=hold, manage=mg, meta=dict(k="ts"))
    return out


# ---- 9. NR7 / inside-day breakout traded intraday ---------------------------------
def build_nr_break(df, mode="nr7", stop="far", tp_r=2.0, exit_hm=2230, trend=None, start_hm=1630, end_hm=2100):
    """M30/H1. Yesterday was an NR7 day (narrowest range of 7) or an inside day; today,
    during cash hours, the first bar that CLOSES beyond yesterday's high/low is entered
    with the stop at yesterday's other extreme ('far') or midpoint ('mid'). One trade/day."""
    p = P(df); out = [None] * p.n
    drng = p.d_high - p.d_low
    nr7 = np.zeros(p.nday, bool); inside = np.zeros(p.nday, bool)
    for d in range(7, p.nday):
        nr7[d] = drng[d] <= drng[d - 6:d + 1].min()
    for d in range(1, p.nday):
        inside[d] = p.d_high[d] < p.d_high[d - 1] and p.d_low[d] > p.d_low[d - 1]
    flag = nr7 if mode == "nr7" else inside
    pid = p.day_id - 1
    y_flag = np.zeros(p.n, bool); ok = pid >= 0; y_flag[ok] = flag[pid[ok]]
    long_ok, short_ok = _gate_arrays(p, trend)
    last_day = -1; done = False
    for i in range(p.n):
        if p.day_id[i] != last_day:
            last_day = p.day_id[i]; done = False
        if done or p.excluded[i] or not y_flag[i] or not (start_hm <= p.hm[i] <= end_hm):
            continue
        ph, pl = p.pd_high[i], p.pd_low[i]
        if not (_ok(ph) and _ok(pl)):
            continue
        mid = (ph + pl) / 2
        if p.c[i] > ph and long_ok[i]:
            sl = pl if stop == "far" else mid
            out[i] = _entry("long", p.c[i], p.c[i] - sl, tp_r=tp_r, exit_hour=exit_hm // 100, meta=dict(k="nr")); done = True
        elif p.c[i] < pl and short_ok[i]:
            sl = ph if stop == "far" else mid
            out[i] = _entry("short", p.c[i], sl - p.c[i], tp_r=tp_r, exit_hour=exit_hm // 100, meta=dict(k="nr")); done = True
    return out


# ---- 10. Connors RSI(2) ----------------------------------------------------------
def build_rsi2(df, thresh=10, sma_trend=200, exit_sma=5, sl_atr=2.0, max_hold=10, side="long"):
    """D1. Long when RSI(2) < thresh and close > SMA(sma_trend); exit at the first close above
    SMA(exit_sma) (manage) or after max_hold days. Short mirror (RSI2 > 100-thresh below SMA)."""
    p = P(df); out = [None] * p.n
    r = rsi(p.c, 2); s_tr = p.sma(sma_trend); s_ex = p.sma(exit_sma); c = p.c
    for i in range(p.n):
        if p.excluded[i] or not (_ok(r[i]) and _ok(s_tr[i]) and _ok(p.atr[i])):
            continue
        if side == "long" and r[i] < thresh and c[i] > s_tr[i]:
            def mg(d, j, pos, _c=c, _s=s_ex):
                return "close" if _c[j] > _s[j] else None
            out[i] = _entry("long", c[i], sl_atr * p.atr[i], max_hold=max_hold, manage=mg, meta=dict(k="rsi2"))
        elif side == "short" and r[i] > 100 - thresh and c[i] < s_tr[i]:
            def mg(d, j, pos, _c=c, _s=s_ex):
                return "close" if _c[j] < _s[j] else None
            out[i] = _entry("short", c[i], sl_atr * p.atr[i], max_hold=max_hold, manage=mg, meta=dict(k="rsi2"))
    return out


# ---- 11. consecutive down closes in an uptrend (buy the dip) ------------------------
def build_down_streak(df, k=3, sma_trend=200, hold=5, sl_atr=2.0, exit_rule="hold", tp_r=None, trend_req=True):
    """D1. After k consecutive lower closes (close > SMA200 if trend_req) go long at the close.
    Exit after `hold` days, or on the first close above yesterday's high ('pdh')."""
    p = P(df); out = [None] * p.n
    s_tr = p.sma(sma_trend); c, h = p.c, p.h
    dn = np.r_[False, np.diff(c) < 0]
    streak = np.zeros(p.n, int)
    for i in range(1, p.n):
        streak[i] = streak[i - 1] + 1 if dn[i] else 0
    for i in range(p.n):
        if p.excluded[i] or streak[i] < k or not _ok(p.atr[i]):
            continue
        if trend_req and not (_ok(s_tr[i]) and c[i] > s_tr[i]):
            continue
        mg = None
        if exit_rule == "pdh":
            def mg(d, j, pos, _c=c, _h=h):
                return "close" if _c[j] > _h[j - 1] else None
        out[i] = _entry("long", c[i], sl_atr * p.atr[i], tp_r=tp_r, max_hold=hold, manage=mg, meta=dict(k="dn"))
    return out


# ---- 12. weekday effects --------------------------------------------------------
def build_weekday(df, enter_dow=4, hold=1, side="long", sl_atr=1.5, trend=None):
    """D1. Enter at the close of weekday `enter_dow` (0=Mon..4=Fri), exit after `hold` daily bars.
    Friday close -> Monday close captures the documented Monday strength."""
    p = P(df); out = [None] * p.n
    long_ok, short_ok = _gate_arrays(p, trend)
    for i in range(p.n):
        if p.excluded[i] or p.dow[i] != enter_dow or not _ok(p.atr[i]):
            continue
        if not (long_ok[i] if side == "long" else short_ok[i]):
            continue
        out[i] = _entry(side, p.c[i], sl_atr * p.atr[i], max_hold=hold, meta=dict(k="dow"))
    return out


# ---- 13. round numbers -----------------------------------------------------------
def build_round(df, step="big", mode="bounce", sl_atr=0.4, tp_r=1.5, start_hm=1630, end_hm=2130, exit_hm=2230, trend=None):
    """M30/H1 cash hours. Level grid = ROUND[sym] ('big' or 'small' step). 'bounce': the bar
    touches a level from above (low <= level) and closes back above it -> long (mirror short).
    'break': the bar closes through a level that the previous bar was on the other side of ->
    continuation. Stop sl_atr x daily ATR, TP tp_r x risk, flat at exit_hm. One trade/day."""
    p = P(df); out = [None] * p.n
    big, small = ROUND.get(p.sym, (100, 50))
    st = big if step == "big" else small
    long_ok, short_ok = _gate_arrays(p, trend)
    last_day = -1; done = False
    for i in range(1, p.n):
        if p.day_id[i] != last_day:
            last_day = p.day_id[i]; done = False
        if done or p.excluded[i] or not (start_hm <= p.hm[i] <= end_hm) or not _ok(p.d_atr[i]):
            continue
        d = sl_atr * p.d_atr[i]
        if mode == "bounce":
            lev = np.floor(p.o[i] / st) * st          # nearest level below the open
            if p.l[i] <= lev and p.c[i] > lev and p.o[i] > lev and long_ok[i]:
                out[i] = _entry("long", p.c[i], d, tp_r=tp_r, exit_hour=exit_hm // 100, meta=dict(k="rn", lev=lev)); done = True; continue
            lev = np.ceil(p.o[i] / st) * st
            if p.h[i] >= lev and p.c[i] < lev and p.o[i] < lev and short_ok[i]:
                out[i] = _entry("short", p.c[i], d, tp_r=tp_r, exit_hour=exit_hm // 100, meta=dict(k="rn", lev=lev)); done = True
        else:
            lev_up = np.ceil(p.c[i - 1] / st) * st
            lev_dn = np.floor(p.c[i - 1] / st) * st
            if p.c[i] > lev_up and p.c[i - 1] < lev_up and long_ok[i]:
                out[i] = _entry("long", p.c[i], d, tp_r=tp_r, exit_hour=exit_hm // 100, meta=dict(k="rnb", lev=lev_up)); done = True
            elif p.c[i] < lev_dn and p.c[i - 1] > lev_dn and short_ok[i]:
                out[i] = _entry("short", p.c[i], d, tp_r=tp_r, exit_hour=exit_hm // 100, meta=dict(k="rnb", lev=lev_dn)); done = True
    return out


# ---- 14. prior-week high/low -------------------------------------------------------
def build_prev_week(df, mode="break", stop="mid", tp_r=None, sides="both", trend=None, hold_bars=None):
    """H1/H4. 'break': first close of the week beyond last week's high/low -> continuation;
    stop at last week's midpoint ('mid') or an ATR multiple ('atr' = 1.5 x ATR14 of the tf).
    'fade': the bar pierces last week's high/low and closes back inside -> reversal toward
    the week's midpoint (TP). Exit: TP, stop, or the last bar of the week (Friday 22:00)."""
    p = P(df); out = [None] * p.n; w = p.week()
    long_ok, short_ok = _gate_arrays(p, trend)
    wk_done = -1
    def eow(d, j, pos, _dow=p.dow, _hour=p.hour):
        return "close" if (_dow[j] == 4 and _hour[j] >= (22 if p.tf == "H1" else 20)) else None
    for i in range(p.n):
        if p.excluded[i] or not _ok(w["high"][i]) or not _ok(p.atr[i]) or w["id"][i] == wk_done:
            continue
        if p.dow[i] == 4 and p.hour[i] >= 20:
            continue
        wh, wl = w["high"][i], w["low"][i]; mid = (wh + wl) / 2
        if mode == "break":
            if p.c[i] > wh and sides in ("both", "long") and long_ok[i]:
                sl = mid if stop == "mid" else p.c[i] - 1.5 * p.atr[i]
                out[i] = _entry("long", p.c[i], p.c[i] - sl, tp_r=tp_r, manage=eow, max_hold=hold_bars, meta=dict(k="pw")); wk_done = w["id"][i]
            elif p.c[i] < wl and sides in ("both", "short") and short_ok[i]:
                sl = mid if stop == "mid" else p.c[i] + 1.5 * p.atr[i]
                out[i] = _entry("short", p.c[i], sl - p.c[i], tp_r=tp_r, manage=eow, max_hold=hold_bars, meta=dict(k="pw")); wk_done = w["id"][i]
        else:
            if p.h[i] > wh and p.c[i] < wh and sides in ("both", "short") and short_ok[i]:
                sl = p.h[i] + 0.3 * p.atr[i]
                out[i] = H.Entry("short", sl, mid if mid < p.c[i] else None, manage=eow, max_hold=hold_bars, meta=dict(k="pwf")); wk_done = w["id"][i]
            elif p.l[i] < wl and p.c[i] > wl and sides in ("both", "long") and long_ok[i]:
                sl = p.l[i] - 0.3 * p.atr[i]
                out[i] = H.Entry("long", sl, mid if mid > p.c[i] else None, manage=eow, max_hold=hold_bars, meta=dict(k="pwf")); wk_done = w["id"][i]
    return out


# ---- 15. intraday momentum: first half hour -> last half hour (Gao et al.) ----------
def build_first_last(df, thresh_atr=0.3, sl_atr=0.4, entry_hm=2200, exit_hm=2230, mode="mom"):
    """M30. Signal = (17:00 close - yesterday's close) in daily-ATR units; if |signal| >= thresh,
    at the close of the `entry_hm` bar take the same direction ('mom') or opposite ('fade'),
    flat at the cash close."""
    p = P(df); out = [None] * p.n
    fh = np.full(p.n, np.nan); cur = np.nan; last_day = -1
    for i in range(p.n):
        if p.day_id[i] != last_day:
            cur = np.nan; last_day = p.day_id[i]
        if p.hm[i] == 1630:
            cur = p.c[i]
        fh[i] = cur
    for i in range(p.n):
        if p.excluded[i] or p.hm[i] != entry_hm or not _ok(fh[i]) or not _ok(p.d_atr[i]) or not _ok(p.pd_close[i]):
            continue
        sig = (fh[i] - p.pd_close[i]) / p.d_atr[i]
        if abs(sig) < thresh_atr:
            continue
        side = ("long" if sig > 0 else "short") if mode == "mom" else ("short" if sig > 0 else "long")
        out[i] = _entry(side, p.c[i], sl_atr * p.d_atr[i], exit_hour=exit_hm // 100, meta=dict(k="fl"))
    return out


# ---- 16. gap relative to yesterday's range -------------------------------------------
def build_gap_struct(df, where="inside", mode="fade", gmin=0.2, sl_atr=0.5, tp="pdc", exit_hm=2230):
    """M30. At the cash open (16:30 bar close): gap = open - yesterday's close, in daily-ATR
    units, |gap| >= gmin. where='inside': the open is inside yesterday's range (fill is
    'easy'); 'outside': beyond yesterday's high/low. mode 'fade' targets yesterday's close
    ('pdc') or the range midpoint ('pd_mid'); 'cont' goes with the gap, TP 2R."""
    p = P(df); out = [None] * p.n
    for i in range(p.n):
        if p.excluded[i] or p.hm[i] != 1630 or not _ok(p.d_atr[i]) or not _ok(p.pd_close[i]):
            continue
        op = p.o[i]; pdc, pdh, pdl = p.pd_close[i], p.pd_high[i], p.pd_low[i]
        g = (op - pdc) / p.d_atr[i]
        if abs(g) < gmin:
            continue
        inside = pdl < op < pdh
        if (where == "inside") != inside:
            continue
        d = sl_atr * p.d_atr[i]
        if mode == "fade":
            side = "short" if g > 0 else "long"
            tpv = pdc if tp == "pdc" else (pdh + pdl) / 2
            if (side == "long" and tpv <= p.c[i]) or (side == "short" and tpv >= p.c[i]):
                continue
            e = _entry(side, p.c[i], d, exit_hour=exit_hm // 100, meta=dict(k="gap"))
            if e: e.tp = tpv
            out[i] = e
        else:
            side = "long" if g > 0 else "short"
            out[i] = _entry(side, p.c[i], d, tp_r=2.0, exit_hour=exit_hm // 100, meta=dict(k="gapc"))
    return out


# ---- 17. H4 pullback to EMA in a trend ---------------------------------------------
def build_h4_pullback(df, fast=20, slow=50, sl_atr=1.5, tp_r=2.0, max_hold=30, sides="long", trail=False):
    """H4/H1. Trend: EMA(fast) > EMA(slow) and EMA(slow) rising. Setup: a close below EMA(fast)
    followed by a close back above it -> long. Stop sl_atr x ATR14, TP tp_r x risk (or a
    trailing stop at EMA(fast) when trail=True). Mirror for shorts."""
    p = P(df); out = [None] * p.n
    ef, es = p.ema(fast), p.ema(slow); c = p.c
    for i in range(slow + 2, p.n):
        if p.excluded[i] or not _ok(p.atr[i]):
            continue
        up = ef[i] > es[i] and es[i] > es[i - 3]
        dn = ef[i] < es[i] and es[i] < es[i - 3]
        mg = None
        if trail:
            def mg(d, j, pos, _ef=ef):
                v = float(_ef[j]) - 0.0
                if pos["side"] == "long":
                    return v if v > pos["sl"] else None
                return v if v < pos["sl"] else None
        if sides in ("long", "both") and up and c[i - 1] < ef[i - 1] and c[i] > ef[i]:
            out[i] = _entry("long", c[i], sl_atr * p.atr[i], tp_r=None if trail else tp_r, max_hold=max_hold, manage=mg, meta=dict(k="pb"))
        elif sides in ("short", "both") and dn and c[i - 1] > ef[i - 1] and c[i] < ef[i]:
            out[i] = _entry("short", c[i], sl_atr * p.atr[i], tp_r=None if trail else tp_r, max_hold=max_hold, manage=mg, meta=dict(k="pb"))
    return out


# ---- 18. overnight (Asia) range break at the European open --------------------------
def build_asia_break(df, sl="range", tp_r=1.5, exit_hour=16, trend=None, end_hm=1200):
    """H1/M30. Range = 01:00-09:59 bars. Between 10:00 and end_hm the first close beyond the
    range enters with the stop at the range midpoint; exits at TP, stop or the 16:00 bar
    (before the cash open, 17:00 on H1)."""
    p = P(df); out = [None] * p.n
    long_ok, short_ok = _gate_arrays(p, trend)
    last_day = -1; rh = rl = np.nan; done = False
    for i in range(p.n):
        if p.day_id[i] != last_day:
            last_day = p.day_id[i]; rh = rl = np.nan; done = False
        if p.hm[i] < 1000:
            rh = p.h[i] if not _ok(rh) else max(rh, p.h[i]); rl = p.l[i] if not _ok(rl) else min(rl, p.l[i]); continue
        if done or p.excluded[i] or p.hm[i] > end_hm or not _ok(rh):
            continue
        mid = (rh + rl) / 2
        if p.c[i] > rh and long_ok[i]:
            out[i] = _entry("long", p.c[i], p.c[i] - mid, tp_r=tp_r, exit_hour=exit_hour, meta=dict(k="asia")); done = True
        elif p.c[i] < rl and short_ok[i]:
            out[i] = _entry("short", p.c[i], mid - p.c[i], tp_r=tp_r, exit_hour=exit_hour, meta=dict(k="asia")); done = True
    return out


# ---- 19. volatility-regime capitulation (D1) ---------------------------------------
def build_capitulation(df, vol_mult=1.3, drop_atr=1.5, hold=5, sl_atr=2.0, exit_rule="hold"):
    """D1. High-vol regime (ATR14 > vol_mult x 100-day median) AND today's close is at least
    drop_atr ATRs below the 5-day high -> long at the close; exit after `hold` days or on the
    first close above yesterday's high ('pdh')."""
    p = P(df); out = [None] * p.n
    med = pd.Series(p.atr).rolling(100, min_periods=30).median().to_numpy()
    hi5 = pd.Series(p.h).rolling(5).max().to_numpy(); c, h = p.c, p.h
    for i in range(p.n):
        if p.excluded[i] or not (_ok(med[i]) and _ok(p.atr[i])):
            continue
        if p.atr[i] > vol_mult * med[i] and (hi5[i] - c[i]) >= drop_atr * p.atr[i]:
            mg = None
            if exit_rule == "pdh":
                def mg(d, j, pos, _c=c, _h=h):
                    return "close" if _c[j] > _h[j - 1] else None
            out[i] = _entry("long", c[i], sl_atr * p.atr[i], max_hold=hold, manage=mg, meta=dict(k="cap"))
    return out


# ---- 20. first-hour drive continuation / fade of the first hour --------------------
def build_first_hour(df, mode="cont", thresh_atr=0.4, sl_atr=0.5, tp_r=None, exit_hm=2230, trend=None):
    """M30. At 17:30 (close of the 17:00 bar) the first hour's move (17:30 close - 16:30 open)
    in daily-ATR units is >= thresh -> 'cont' goes with it, 'fade' against; flat at the close."""
    p = P(df); out = [None] * p.n
    long_ok, short_ok = _gate_arrays(p, trend)
    cash_open = np.full(p.n, np.nan); cur = np.nan; last_day = -1
    for i in range(p.n):
        if p.day_id[i] != last_day:
            cur = np.nan; last_day = p.day_id[i]
        if p.hm[i] == 1630:
            cur = p.o[i]
        cash_open[i] = cur
    for i in range(p.n):
        if p.excluded[i] or p.hm[i] != 1700 or not _ok(cash_open[i]) or not _ok(p.d_atr[i]):
            continue
        mv = (p.c[i] - cash_open[i]) / p.d_atr[i]
        if abs(mv) < thresh_atr:
            continue
        side = ("long" if mv > 0 else "short") if mode == "cont" else ("short" if mv > 0 else "long")
        if not (long_ok[i] if side == "long" else short_ok[i]):
            continue
        out[i] = _entry(side, p.c[i], sl_atr * p.d_atr[i], tp_r=tp_r, exit_hour=exit_hm // 100, meta=dict(k="fh"))
    return out



# ---- 22. internal bar strength (IBS) mean reversion ----------------------------------
def build_ibs(df, lo=0.2, hi=0.8, sma_trend=200, sl_atr=2.0, max_hold=8, trend_req=True):
    """D1. IBS = (close-low)/(high-low). Long at the close when IBS < lo (and close > SMA200 if
    trend_req); exit at the first close with IBS > hi, or after max_hold days. Stop sl_atr x ATR."""
    p = P(df); out = [None] * p.n
    rng = p.h - p.l
    ibs = np.where(rng > 0, (p.c - p.l) / np.where(rng > 0, rng, 1.0), 0.5)
    s_tr = p.sma(sma_trend)
    for i in range(p.n):
        if p.excluded[i] or not _ok(p.atr[i]) or ibs[i] >= lo:
            continue
        if trend_req and not (_ok(s_tr[i]) and p.c[i] > s_tr[i]):
            continue
        def mg(d, j, pos, _ibs=ibs, _hi=hi):
            return "close" if _ibs[j] > _hi else None
        out[i] = _entry("long", p.c[i], sl_atr * p.atr[i], max_hold=max_hold, manage=mg, meta=dict(k="ibs"))
    return out


# ---- 23. Connors Double-7s --------------------------------------------------------------
def build_double7s(df, n=7, sma_trend=200, sl_atr=2.5, max_hold=15):
    """D1. Close > SMA200 and close is the lowest close of the last n days -> long at the close;
    exit when the close is the highest close of the last n days, or after max_hold days."""
    p = P(df); out = [None] * p.n
    c = pd.Series(p.c)
    low_n = c.rolling(n).min().to_numpy(); high_n = c.rolling(n).max().to_numpy()
    s_tr = p.sma(sma_trend)
    for i in range(p.n):
        if p.excluded[i] or not (_ok(low_n[i]) and _ok(s_tr[i]) and _ok(p.atr[i])):
            continue
        if p.c[i] <= low_n[i] and p.c[i] > s_tr[i]:
            def mg(d, j, pos, _c=p.c, _h=high_n):
                return "close" if _c[j] >= _h[j] else None
            out[i] = _entry("long", p.c[i], sl_atr * p.atr[i], max_hold=max_hold, manage=mg, meta=dict(k="d7"))
    return out


# ---- 24. H4 pullback to an N-bar low in a daily uptrend --------------------------------
def build_h4_dip(df, n=8, sl_atr=1.5, max_hold=18, tp_r=None, exit_rule="nhigh", daily_sma=50):
    """H4/H1. Daily trend = yesterday's close > daily SMA(daily_sma). Long when the bar's close is
    the lowest close of the last n bars; exit when close > highest high of the previous n bars
    ('nhigh'), or at tp_r, or after max_hold bars."""
    p = P(df); out = [None] * p.n
    c = pd.Series(p.c); low_n = c.rolling(n).min().to_numpy()
    hh_prev = pd.Series(p.h).rolling(n).max().shift(1).to_numpy()
    up = p.daily_sma_prev(daily_sma)
    for i in range(p.n):
        if p.excluded[i] or not (_ok(low_n[i]) and _ok(up[i]) and _ok(p.pd_close[i]) and _ok(p.atr[i])):
            continue
        if p.c[i] <= low_n[i] and p.pd_close[i] > up[i]:
            mg = None
            if exit_rule == "nhigh":
                def mg(d, j, pos, _c=p.c, _hh=hh_prev):
                    return "close" if _ok(_hh[j]) and _c[j] > _hh[j] else None
            out[i] = _entry("long", p.c[i], sl_atr * p.atr[i], tp_r=tp_r, max_hold=max_hold, manage=mg, meta=dict(k="h4dip"))
    return out


# ---- 25. late-day dip buy (afternoon reversal of a down day) ---------------------------
def build_late_dip(df, entry_hm=2000, thresh_atr=0.4, sl_atr=0.5, exit_hm=2230, trend=None, mode="dip"):
    """M30/H1. At the close of the entry_hm bar: 'dip' = price below the day's open by more than
    thresh_atr daily ATRs -> long into the close (mean reversion of afternoon weakness, exits at
    the exit_hm bar); 'rip' = mirror short after a strong afternoon."""
    p = P(df); out = [None] * p.n
    long_ok, short_ok = _gate_arrays(p, trend)
    for i in range(p.n):
        if p.excluded[i] or p.hm[i] != entry_hm or not _ok(p.d_atr[i]):
            continue
        dopen = p.o[p.day_start[p.day_id[i]]]
        move = (p.c[i] - dopen) / p.d_atr[i]
        if mode == "dip" and move <= -thresh_atr and long_ok[i]:
            out[i] = _entry("long", p.c[i], sl_atr * p.d_atr[i], exit_hour=exit_hm // 100, meta=dict(k="ld"))
        elif mode == "rip" and move >= thresh_atr and short_ok[i]:
            out[i] = _entry("short", p.c[i], sl_atr * p.d_atr[i], exit_hour=exit_hm // 100, meta=dict(k="ld"))
    return out


# ---- 26. prior-day high/low break during cash hours ------------------------------------
def build_pdh_break(df, sides="long", stop="mid", tp_r=None, start_hm=1630, end_hm=2100, exit_hm=2230,
                    trend=None, sl_atr=0.4, min_dist=0.0):
    """M30/H1. First close above yesterday's high (below yesterday's low for shorts) within the
    cash window -> continuation entry, one per day. Stop: 'mid' = halfway between the level and the
    day's running low/high, 'atr' = sl_atr x daily ATR, 'level' = the level itself. Flat at exit_hm."""
    p = P(df); out = [None] * p.n
    long_ok, short_ok = _gate_arrays(p, trend)
    done_day = -1
    for i in range(p.n):
        if p.excluded[i] or not (start_hm <= p.hm[i] <= end_hm) or not (_ok(p.pd_high[i]) and _ok(p.d_atr[i])):
            continue
        if p.day_id[i] == done_day:
            continue
        prev_c = p.c[i - 1] if i > 0 and p.day_id[i - 1] == p.day_id[i] else p.o[i]
        side = None
        if sides in ("long", "both") and p.c[i] > p.pd_high[i] and prev_c <= p.pd_high[i] and long_ok[i] \
                and (p.c[i] - p.pd_high[i]) >= min_dist * p.d_atr[i]:
            side = "long"; level = p.pd_high[i]; ref = p.run_low[i]
        elif sides in ("short", "both") and p.c[i] < p.pd_low[i] and prev_c >= p.pd_low[i] and short_ok[i] \
                and (p.pd_low[i] - p.c[i]) >= min_dist * p.d_atr[i]:
            side = "short"; level = p.pd_low[i]; ref = p.run_high[i]
        if side is None:
            continue
        if stop == "mid":
            dist = abs(p.c[i] - (level + ref) / 2)
        elif stop == "level":
            dist = abs(p.c[i] - level) + 0.1 * p.d_atr[i]
        else:
            dist = sl_atr * p.d_atr[i]
        dist = max(dist, 0.15 * p.d_atr[i])
        out[i] = _entry(side, p.c[i], dist, tp_r=tp_r, exit_hour=exit_hm // 100, meta=dict(k="pdh"))
        done_day = p.day_id[i]
    return out


# ---- 27. D1 breakout with chandelier trail ----------------------------------------------
def build_d1_breakout(df, n=20, trail_atr=3.0, sl_atr=2.0, sides="long", squeeze=None, max_hold=60):
    """D1. Long at the close above the highest close of the previous n days (short mirror).
    Optional `squeeze`: ATR(14) / ATR(100) must be below this (volatility contraction before the
    break). Exit by chandelier trail (highest close since entry - trail_atr x ATR), hard stop sl_atr."""
    p = P(df); out = [None] * p.n
    c = pd.Series(p.c)
    hh = c.rolling(n).max().shift(1).to_numpy(); ll = c.rolling(n).min().shift(1).to_numpy()
    atr100 = pd.Series(p.atr).rolling(100, min_periods=30).mean().to_numpy()
    for i in range(p.n):
        if p.excluded[i] or not (_ok(hh[i]) and _ok(p.atr[i])):
            continue
        if squeeze is not None and not (_ok(atr100[i]) and p.atr[i] / atr100[i] < squeeze):
            continue
        if sides in ("long", "both") and p.c[i] > hh[i]:
            def mg(d, j, pos, _c=p.c, _a=p.atr, _k=trail_atr):
                b = pos["bar"]; peak = _c[b:j + 1].max()
                return float(peak - _k * _a[j])
            out[i] = _entry("long", p.c[i], sl_atr * p.atr[i], max_hold=max_hold, manage=mg, meta=dict(k="bo"))
        elif sides in ("short", "both") and p.c[i] < ll[i]:
            def mg(d, j, pos, _c=p.c, _a=p.atr, _k=trail_atr):
                b = pos["bar"]; trough = _c[b:j + 1].min()
                return float(trough + _k * _a[j])
            out[i] = _entry("short", p.c[i], sl_atr * p.atr[i], max_hold=max_hold, manage=mg, meta=dict(k="bo"))
    return out


BUILDERS = {k[6:]: v for k, v in globals().items() if k.startswith("build_")}
