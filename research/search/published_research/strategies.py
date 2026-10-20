"""published_research family: faithful, few-parameter implementations of
effects with published evidence, scored by research.prop.harness.

Every builder: build_<name>(df, **params) -> list[Entry|None] of len(df).
Causal: the Entry at bar i only uses rows <= i (ATR/MA/returns end at i; the
calendar - month ends, holidays, FOMC dates - is known in advance).

Broker server time = EET with US DST (NY 17:00 == 00:00 server all year),
so NY 09:30 open = server 16:30, NY 16:00 close = server 23:00, London
15:00 (PM fix) = server 17:00, Tokyo 09:00 = server 02:00/03:00.
H1 bars are labelled by their OPEN hour; entering "after bar h" means at
the close of the bar that opened at h (i.e. at h+1:00).

Sources are listed in NOTES.md next to each idea.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.prop.harness import Entry


# ----------------------------------------------------------------- helpers
def _atr(df, n):
    h, l, c = df.high.to_numpy(float), df.low.to_numpy(float), df.close.to_numpy(float)
    pc = np.r_[c[0], c[:-1]]
    tr = np.maximum(h - l, np.maximum(abs(h - pc), abs(l - pc)))
    return pd.Series(tr).rolling(n, min_periods=n).mean().to_numpy()


def _daily_atr_on_bars(df, n=14):
    """ATR of COMPLETED daily bars, aligned so bar i sees only days < its day
    plus nothing of today (causal)."""
    t = pd.DatetimeIndex(df.time)
    d = pd.DataFrame({"day": t.normalize(), "h": df.high.values, "l": df.low.values,
                      "c": df.close.values})
    g = d.groupby("day").agg(h=("h", "max"), l=("l", "min"), c=("c", "last"))
    pc = g.c.shift()
    tr = np.maximum(g.h - g.l, np.maximum((g.h - pc).abs(), (g.l - pc).abs()))
    atr = tr.rolling(n, min_periods=n).mean().shift(1)     # yesterday's value
    return atr.reindex(t.normalize()).to_numpy()


def _out(n):
    return [None] * n


# ------------------------------------------- 1. session / time-of-day drift
def build_session_drift(df, side="long", entry_hour=1, exit_hour=8,
                        sl_datr=1.0, weekdays=None):
    """Time-of-day effect: enter `side` at the close of the bar that opened at
    `entry_hour`, exit at close of the bar that opened at `exit_hour`.
    Stop = sl_datr x daily ATR(14) of completed days.
    Gold: rises in Asian hours / falls in the West (Donati & Jung, CBS).
    FX: currencies depreciate in their home trading hours (Breedon & Ranaldo)."""
    n = len(df)
    out = _out(n)
    t = pd.DatetimeIndex(df.time)
    hr, wd = t.hour.to_numpy(), t.weekday.to_numpy()
    datr = _daily_atr_on_bars(df)
    c = df.close.to_numpy(float)
    sgn = 1 if side == "long" else -1
    for i in np.flatnonzero(hr == entry_hour):
        if weekdays is not None and wd[i] not in weekdays:
            continue
        a = datr[i]
        if not np.isfinite(a) or a <= 0:
            continue
        out[i] = Entry(side, c[i] - sgn * sl_datr * a, exit_hour=exit_hour,
                       max_hold=30)
    return out


def build_two_leg_session(df, long_entry=1, long_exit=8, short_entry=15,
                          short_exit=20, sl_datr=1.0):
    """Gold 'day cycle': long the Asian session, short the London-PM-fix/NY
    window (Donati & Jung; Abrantes-Metz & Metz on the PM fix)."""
    a = build_session_drift(df, "long", long_entry, long_exit, sl_datr)
    b = build_session_drift(df, "short", short_entry, short_exit, sl_datr)
    return [x if x is not None else y for x, y in zip(a, b)]


# --------------------------------------- 2. time-series momentum (TSMOM)
def build_tsmom(df, lookback=252, rebalance="M", sl_atr=3.0, atr_n=20,
                hold=None, deadband=0.0):
    """Moskowitz, Ooi & Pedersen (2012): sign of trailing `lookback`-bar
    return, re-decided at each rebalance (first bar of new month / week).
    Stop = sl_atr x ATR(atr_n). Flips are allowed by the harness. After a
    stop-out we re-enter at the next rebalance only."""
    n = len(df)
    out = _out(n)
    c = df.close.to_numpy(float)
    atr = _atr(df, atr_n)
    t = pd.DatetimeIndex(df.time)
    key = t.to_period(rebalance).asi8 if rebalance else np.arange(n)
    newp = np.r_[True, key[1:] != key[:-1]]
    for i in np.flatnonzero(newp):
        if i < lookback or not np.isfinite(atr[i]):
            continue
        r = c[i] / c[i - lookback] - 1
        if abs(r) <= deadband:
            continue
        side = "long" if r > 0 else "short"
        sl = c[i] - sl_atr * atr[i] if side == "long" else c[i] + sl_atr * atr[i]
        out[i] = Entry(side, sl, max_hold=hold)
    return out


# --------------------------------------- 3. Donchian / turtle trend
def build_donchian(df, entry_n=55, exit_n=20, sl_atr=2.0, atr_n=20, long_only=False):
    """Turtle system 2 style (Faith 2003; Hurst, Ooi & Pedersen 'A Century of
    Evidence on Trend-Following'): enter on close beyond prior entry_n-bar
    extreme, 2N stop, exit on opposite exit_n-bar extreme (via manage)."""
    n = len(df)
    out = _out(n)
    h, l, c = (df[k].to_numpy(float) for k in ("high", "low", "close"))
    hi = pd.Series(h).rolling(entry_n).max().shift(1).to_numpy()
    lo = pd.Series(l).rolling(entry_n).min().shift(1).to_numpy()
    xhi = pd.Series(h).rolling(exit_n).max().shift(1).to_numpy()
    xlo = pd.Series(l).rolling(exit_n).min().shift(1).to_numpy()
    atr = _atr(df, atr_n)

    def manage(_df, i, pos):
        if pos["side"] == "long" and c[i] < xlo[i]:
            return "close"
        if pos["side"] == "short" and c[i] > xhi[i]:
            return "close"
        return None

    for i in range(n):
        if not np.isfinite(atr[i]) or not np.isfinite(hi[i]):
            continue
        if c[i] > hi[i]:
            out[i] = Entry("long", c[i] - sl_atr * atr[i], manage=manage)
        elif c[i] < lo[i] and not long_only:
            out[i] = Entry("short", c[i] + sl_atr * atr[i], manage=manage)
    return out


# --------------------------------------- 4. turn of the month (indices)
def _bdays_to_month_end(t):
    """For each timestamp: number of business days left in its month after its
    own day (0 = last business day). Calendar-only, so causal."""
    days = pd.DatetimeIndex(t).normalize()
    uniq = days.unique()
    me = uniq + pd.offsets.MonthEnd(0)
    left = np.array([np.busday_count(d.date() + pd.Timedelta(days=1).to_pytimedelta(),
                                     (m + pd.Timedelta(days=1)).date())
                     for d, m in zip(uniq, me)])
    return pd.Series(left, index=uniq).reindex(days).to_numpy()


def build_turn_of_month(df, days_before=1, hold_days=4, entry_hour=22,
                        sl_datr=2.0, side="long"):
    """Lakonishok & Smidt (1988); McConnell & Xu (2008): equity returns
    concentrate from the last trading day to the 3rd of the next month.
    Enter near the US close `days_before`+1 business days before month end
    (days_before=1 -> enter on the 2nd-to-last day, holding the last day),
    hold `hold_days` trading days."""
    n = len(df)
    out = _out(n)
    t = pd.DatetimeIndex(df.time)
    left = _bdays_to_month_end(t)
    datr = _daily_atr_on_bars(df)
    datr_d = _atr(df, 14)
    c = df.close.to_numpy(float)
    hr = t.hour.to_numpy()
    daily = (t[1:] - t[:-1]).median() >= pd.Timedelta(hours=20) if n > 2 else False
    per_day = 1 if daily else max(1, int(round(pd.Series(t.normalize()).value_counts().median())))
    sgn = 1 if side == "long" else -1
    for i in range(n):
        if left[i] != days_before or not (daily or hr[i] == entry_hour):
            continue
        a = datr_d[i] if daily else datr[i]
        if not np.isfinite(a):
            continue
        out[i] = Entry(side, c[i] - sgn * sl_datr * a, max_hold=hold_days * per_day)
    return out


# --------------------------------------- 5. overnight drift (indices)
def build_overnight(df, entry_hour=22, exit_hour=15, sl_datr=1.5, weekdays=None):
    """Kelly & Clark (2011), Lou, Polk & Skouras (2019): US equity returns
    accrue overnight (close->open). Buy at the close of the bar opened at
    `entry_hour` (22 = NY 15:00-16:00, closes at the cash close), sell at the
    close of the bar opened at `exit_hour` (15 -> 16:00 server = NY 09:00)."""
    return build_session_drift(df, "long", entry_hour, exit_hour, sl_datr, weekdays)


# --------------------------------------- 6. intraday momentum (indices)
def build_intraday_momentum(df, signal_close="17:00", entry_close=None,
                            exit_close="23:00", ref_close="23:00", sl_datr=0.5,
                            min_move=0.0):
    """Gao, Han, Li & Zhou (JFE 2018): the first half hour's return (prior
    cash close -> NY 10:00 = server 17:00) predicts the last half hour.
    Times are bar CLOSE times (server). Enter at `entry_close` (default: one
    bar before exit_close, i.e. 22:30 on M30, 22:00 on H1), trade the sign
    of the signal return, exit at `exit_close`."""
    n = len(df)
    out = _out(n)
    t = pd.DatetimeIndex(df.time)
    bar = (t[1:] - t[:-1]).to_series().mode().iloc[0] if n > 2 else pd.Timedelta(hours=1)
    ct = t + bar
    hm = (ct.hour * 60 + ct.minute).to_numpy()
    f = lambda s_: int(s_[:2]) * 60 + int(s_[3:])
    ex = f(exit_close)
    en = f(entry_close) if entry_close else ex - int(bar.total_seconds() // 60)
    hold = max(1, (ex - en) // int(bar.total_seconds() // 60))
    day = ct.normalize().to_numpy()
    c = df.close.to_numpy(float)
    datr = _daily_atr_on_bars(df)
    ref, prev_ref, sig, cur = np.nan, np.nan, np.nan, None
    for i in range(n):
        if day[i] != cur:
            cur, sig, prev_ref = day[i], np.nan, ref
        if hm[i] == f(signal_close):
            sig = c[i]
        if hm[i] == en and np.isfinite(sig) and np.isfinite(prev_ref) and np.isfinite(datr[i]):
            r = sig / prev_ref - 1
            if abs(r) > min_move:
                side = "long" if r > 0 else "short"
                sl = c[i] - sl_datr * datr[i] if side == "long" else c[i] + sl_datr * datr[i]
                out[i] = Entry(side, sl, max_hold=hold)
        if hm[i] == f(ref_close):
            ref = c[i]
    return out


# --------------------------------------- 7. pre-holiday (indices)
def _us_holidays():
    from pandas.tseries.holiday import (USFederalHolidayCalendar, GoodFriday)
    cal = USFederalHolidayCalendar()
    hol = cal.holidays("2010-01-01", "2030-12-31")
    gf = pd.DatetimeIndex(GoodFriday.dates("2010-01-01", "2030-12-31"))
    # NYSE does not close Columbus / Veterans day
    keep = [d for d in hol if not (d.month == 10 and d.weekday() == 0 and 8 <= d.day <= 14)
            and not (d.month == 11 and d.day == 11)]
    return pd.DatetimeIndex(sorted(set(keep) | set(gf)))


def build_pre_holiday(df, entry_hour=22, hold_bars=None, sl_datr=1.5):
    """Ariel (1990), Kim & Park (1994): stock returns on the trading day before
    a market holiday are several times normal. Buy at the US close two
    sessions before the holiday-eve... simplified: buy at the close of the
    bar opened at entry_hour on the day BEFORE the pre-holiday session and
    hold through the pre-holiday session (exit the next day's same hour)."""
    n = len(df)
    out = _out(n)
    t = pd.DatetimeIndex(df.time)
    hr = t.hour.to_numpy()
    days = t.normalize()
    hol = _us_holidays()
    # pre-holiday session = last business day before a holiday
    pre = set((hol - pd.offsets.BDay(1)).normalize())
    # entry day = the business day before the pre-holiday session
    ent = set((pd.DatetimeIndex(sorted(pre)) - pd.offsets.BDay(1)).normalize())
    datr = _daily_atr_on_bars(df)
    c = df.close.to_numpy(float)
    for i in range(n):
        if hr[i] != entry_hour or days[i] not in ent or not np.isfinite(datr[i]):
            continue
        out[i] = Entry("long", c[i] - sl_datr * datr[i], exit_hour=entry_hour,
                       max_hold=hold_bars or 40)
    return out


# --------------------------------------- 8. pre-FOMC drift (indices)
FOMC = pd.to_datetime([
    "2015-01-28", "2015-03-18", "2015-04-29", "2015-06-17", "2015-07-29", "2015-09-17", "2015-10-28", "2015-12-16",
    "2016-01-27", "2016-03-16", "2016-04-27", "2016-06-15", "2016-07-27", "2016-09-21", "2016-11-02", "2016-12-14",
    "2017-02-01", "2017-03-15", "2017-05-03", "2017-06-14", "2017-07-26", "2017-09-20", "2017-11-01", "2017-12-13",
    "2018-01-31", "2018-03-21", "2018-05-02", "2018-06-13", "2018-08-01", "2018-09-26", "2018-11-08", "2018-12-19",
    "2019-01-30", "2019-03-20", "2019-05-01", "2019-06-19", "2019-07-31", "2019-09-18", "2019-10-30", "2019-12-11",
    "2020-01-29", "2020-04-29", "2020-06-10", "2020-07-29", "2020-09-16", "2020-11-05", "2020-12-16",
    "2021-01-27", "2021-03-17", "2021-04-28", "2021-06-16", "2021-07-28", "2021-09-22", "2021-11-03", "2021-12-15",
    "2022-01-26", "2022-03-16", "2022-05-04", "2022-06-15", "2022-07-27", "2022-09-21", "2022-11-02", "2022-12-14",
    "2023-02-01", "2023-03-22", "2023-05-03", "2023-06-14", "2023-07-26", "2023-09-20", "2023-11-01", "2023-12-13",
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12", "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18", "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17", "2026-07-29", "2026-09-16", "2026-10-28", "2026-12-09",
])  # scheduled statement days (2pm ET). Public calendar, known in advance.


def build_pre_fomc(df, side="long", sl_datr=1.5, entry_hour=20, exit_hour=20,
                   hold_bars=None, tp_datr=None):
    """Lucca & Moench (JF 2015): S&P 500 rises ~49bp in the 24h before
    scheduled FOMC announcements. Enter at 14:00 ET the day before (server
    21:00 = close of bar opened at 20), exit at 14:00 ET on FOMC day.
    For gold/FX the same window is tested as a USD-event drift."""
    n = len(df)
    out = _out(n)
    t = pd.DatetimeIndex(df.time)
    hr = t.hour.to_numpy()
    days = t.normalize()
    eve = set((FOMC - pd.offsets.BDay(1)).normalize())
    datr = _daily_atr_on_bars(df)
    c = df.close.to_numpy(float)
    sgn = 1 if side == "long" else -1
    for i in range(n):
        if hr[i] == entry_hour and days[i] in eve and np.isfinite(datr[i]):
            tp = None if tp_datr is None else c[i] + sgn * tp_datr * datr[i]
            if hold_bars:
                out[i] = Entry(side, c[i] - sgn * sl_datr * datr[i], tp=tp, max_hold=hold_bars)
            else:
                out[i] = Entry(side, c[i] - sgn * sl_datr * datr[i], tp=tp,
                               exit_hour=exit_hour, max_hold=40)
    return out


# --------------------------------------- 9. short-term reversal RSI(2)
def build_rsi2(df, rsi_n=2, lo=10, hi=90, trend_n=200, exit_n=5, sl_atr=2.5,
               atr_n=14, long_only=True, max_hold=10):
    """Connors & Alvarez (2009) RSI(2): in an uptrend (close > SMA200) buy
    when RSI(2) < lo, exit when close > SMA(exit_n). Widely replicated on
    equity indices (e.g. Quantpedia 'short-term reversal in indices').
    Stop = sl_atr x ATR (prop rule requires one)."""
    n = len(df)
    out = _out(n)
    c = pd.Series(df.close.to_numpy(float))
    d = c.diff()
    up = d.clip(lower=0).ewm(alpha=1 / rsi_n, adjust=False).mean()
    dn = (-d.clip(upper=0)).ewm(alpha=1 / rsi_n, adjust=False).mean()
    rsi = (100 - 100 / (1 + up / dn.replace(0, np.nan))).to_numpy()
    sma = c.rolling(trend_n).mean().to_numpy()
    sx = c.rolling(exit_n).mean().to_numpy()
    atr = _atr(df, atr_n)
    cv = c.to_numpy()

    def manage(_df, i, pos):
        if pos["side"] == "long" and cv[i] > sx[i]:
            return "close"
        if pos["side"] == "short" and cv[i] < sx[i]:
            return "close"
        return None

    for i in range(n):
        if not (np.isfinite(sma[i]) and np.isfinite(atr[i]) and np.isfinite(rsi[i])):
            continue
        if cv[i] > sma[i] and rsi[i] < lo:
            out[i] = Entry("long", cv[i] - sl_atr * atr[i], manage=manage, max_hold=max_hold)
        elif not long_only and cv[i] < sma[i] and rsi[i] > hi:
            out[i] = Entry("short", cv[i] + sl_atr * atr[i], manage=manage, max_hold=max_hold)
    return out


# --------------------------------------- 10. opening-gap fade (indices)
def build_gap_fade(df, open_hour=16, min_gap_datr=0.2, sl_datr=0.5, exit_hour=22,
                   ref_hour=22):
    """Opening gaps in index futures tend to (partially) fill intraday
    (e.g. Plastun et al. 2019 on S&P gaps; Quantpedia 'gap fading').
    Gap = close of the first cash-session bar (opened at open_hour) vs
    previous day's cash-close bar (opened at ref_hour). Fade it, exit at
    close of the bar opened at exit_hour."""
    n = len(df)
    out = _out(n)
    t = pd.DatetimeIndex(df.time)
    hr = t.hour.to_numpy()
    c = df.close.to_numpy(float)
    datr = _daily_atr_on_bars(df)
    ref = np.nan
    for i in range(n):
        if hr[i] == open_hour and np.isfinite(ref) and np.isfinite(datr[i]):
            g = c[i] - ref
            if abs(g) >= min_gap_datr * datr[i]:
                side = "short" if g > 0 else "long"
                sl = c[i] + sl_datr * datr[i] if side == "short" else c[i] - sl_datr * datr[i]
                out[i] = Entry(side, sl, exit_hour=exit_hour, max_hold=12)
        if hr[i] == ref_hour:
            ref = c[i]
    return out


# --------------------------------------- 11. day-of-week filter on a session
def build_session_dow(df, side="long", entry_hour=1, exit_hour=8, sl_datr=1.0,
                      days=(0, 1, 2, 3, 4)):
    return build_session_drift(df, side, entry_hour, exit_hour, sl_datr, set(days))


# --------------------------------------- 12. FOMC cycle (Cieslak et al.)
def _fomc_week(t):
    """Cieslak, Morse & Vissing-Jorgensen (JF 2019) FOMC-cycle week for each
    bar's day: week 0 = trading days -1..+3 around the last FOMC day, then
    blocks of 5 trading days. Uses only the (pre-scheduled) calendar."""
    days = pd.DatetimeIndex(t).normalize()
    uniq = days.unique()
    f = pd.DatetimeIndex(FOMC)
    pos = np.searchsorted(f.values, (uniq + pd.offsets.BDay(1)).values, side="right") - 1
    wk = np.full(len(uniq), -1)
    for k, (d, p) in enumerate(zip(uniq, pos)):
        if p < 0:
            continue
        start = f[p] - pd.offsets.BDay(1)
        nb = np.busday_count(start.date(), d.date())
        wk[k] = nb // 5
    return pd.Series(wk, index=uniq).reindex(days).to_numpy()


def build_fomc_cycle(df, side="long", weeks=(0, 2, 4, 6), entry_hour=22, sl_datr=2.0):
    """Even-week FOMC cycle: at the US close of the LAST day before an even
    week begins, go `side`, hold 5 trading days (exit by max_hold)."""
    n = len(df)
    out = _out(n)
    t = pd.DatetimeIndex(df.time)
    wk = _fomc_week(t)
    hr = t.hour.to_numpy()
    days = t.normalize()
    nxt = _fomc_week(pd.DatetimeIndex(days + pd.offsets.BDay(1)))
    datr = _daily_atr_on_bars(df)
    c = df.close.to_numpy(float)
    per_day = max(1, int(round(pd.Series(days).value_counts().median())))
    sgn = 1 if side == "long" else -1
    for i in range(n):
        if hr[i] != entry_hour or not np.isfinite(datr[i]):
            continue
        if nxt[i] in weeks and nxt[i] != wk[i]:
            out[i] = Entry(side, c[i] - sgn * sl_datr * datr[i], max_hold=5 * per_day)
    return out


# --------------------------------------- 13. autumn effect in gold (Baur)
def build_month_season(df, months=(9, 11), side="long", sl_atr=3.0, atr_n=20,
                       daily_atr=True):
    """Baur (2013) 'The autumn effect of gold': September and November are the
    only months with significantly positive gold returns (1980-2010).
    Enter at the first bar of each chosen month, exit at the month's last bar
    (manage closes when the month changes). Stop sl_atr x daily ATR."""
    n = len(df)
    out = _out(n)
    t = pd.DatetimeIndex(df.time)
    m = t.month.to_numpy()
    key = t.to_period("M").asi8
    newp = np.r_[True, key[1:] != key[:-1]]
    a = _daily_atr_on_bars(df) if daily_atr else _atr(df, atr_n)
    c = df.close.to_numpy(float)
    sgn = 1 if side == "long" else -1
    # close on the last bar of the month: the next bar starts a new month,
    # which is known in advance from the calendar (bar i is last if the next
    # business day falls in a new month and the hour is the final one).
    last_day = _bdays_to_month_end(t) == 0
    hr = t.hour.to_numpy()
    final_hour = 22

    def manage(_df, i, pos):
        if last_day[i] and (hr[i] >= final_hour or (len(set(hr)) == 1)):
            return "close"
        return None

    for i in np.flatnonzero(newp):
        if m[i] in months and np.isfinite(a[i]):
            out[i] = Entry(side, c[i] - sgn * sl_atr * a[i], manage=manage)
    return out


# --------------------------------------- 14. gold calendar combo
def build_gold_calendar(df, tom=True, fomc=True, fomc_sl=1.5, tom_sl=2.0,
                        tom_days_before=1, tom_hold=4):
    """Union of two calendar edges that both point to gold strength
    (USD weakness): pre-FOMC drift + turn of month. One position at a time
    (harness ignores a same-side signal while a trade is open)."""
    a = build_pre_fomc(df, "long", sl_datr=fomc_sl) if fomc else _out(len(df))
    b = build_turn_of_month(df, days_before=tom_days_before, hold_days=tom_hold,
                            sl_datr=tom_sl) if tom else _out(len(df))
    return [x if x is not None else y for x, y in zip(a, b)]


# --------------------------------------- 15. equity calendar combo
def build_equity_calendar(df, tom=True, holiday=True, fomc=True, sl_datr=1.5,
                          tom_days_before=1, tom_hold=4):
    """Union of three published US-equity calendar edges, all long:
    turn of month (Lakonishok & Smidt), pre-holiday (Ariel), pre-FOMC drift
    (Lucca & Moench). One position at a time."""
    n = len(df)
    parts = []
    if fomc:
        parts.append(build_pre_fomc(df, "long", sl_datr=sl_datr))
    if holiday:
        parts.append(build_pre_holiday(df, sl_datr=sl_datr))
    if tom:
        parts.append(build_turn_of_month(df, days_before=tom_days_before,
                                         hold_days=tom_hold, sl_datr=sl_datr))
    out = _out(n)
    for p in parts:
        for i, e in enumerate(p):
            if out[i] is None and e is not None:
                out[i] = e
    return out


# --------------------------------------- control: calendar-blind long
def build_control_long(df, every=10, offset=0, hold_days=4, entry_hour=22, sl_datr=1.5):
    """Placebo for the equity/gold calendar edges: go long every `every`-th
    trading day (no calendar logic), same hold and stop. If a calendar edge
    is real, it must beat this drift-only baseline."""
    n = len(df)
    out = _out(n)
    t = pd.DatetimeIndex(df.time)
    hr = t.hour.to_numpy()
    days = t.normalize()
    uniq = days.unique()
    k = pd.Series(np.arange(len(uniq)), index=uniq).reindex(days).to_numpy()
    datr = _daily_atr_on_bars(df)
    c = df.close.to_numpy(float)
    per_day = max(1, int(round(pd.Series(days).value_counts().median())))
    for i in range(n):
        if hr[i] == entry_hour and (k[i] + offset) % every == 0 and np.isfinite(datr[i]):
            out[i] = Entry("long", c[i] - sl_datr * datr[i], max_hold=hold_days * per_day)
    return out
