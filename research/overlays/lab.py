"""Overlay lab: replay the live 66-strategy account with account-level rules on top.

The 66 strategies are simulated EXACTLY (research.overlays.sim == the harness) at
their live risks, each starting flat at the window start. The combined account
is the sum of their curves. Because sizing is fixed-dollar, a trade's P&L and
its floating excursion scale linearly with the size used at entry, so an
overlay that changes SIZE at entry (or skips the entry) is replayed by giving
every trade a factor f in [0, 1.5]: 0 = skipped, 0.5 = half size, 1 = as live.
The factor is decided from what the bot would know at the entry bar: the
account's equity so far (close of the previous bar), the day-end equity
history, the month-to-date P&L, the strategy's own earlier trades, the clock.

Live rule set (always on, = trader/multi.py):
    * CLOSE ALL when the combined floating equity is down $300 on the server
      day (vs the previous day's last close), no new entries that day; the day
      is pinned at -$300 - $25 slippage (same as the sizing session's replay)
    * permanent halt when equity touches $9,300 (reported separately so the
      overlays can still be compared on the whole window)

Windows (each starts flat at $10,000):
    A = 2024-10-20 .. 2026-10-20   the window the mix was sized on
    B = 2023-10-20 .. 2026-10-20   adds the unseen bad year 2023-10..2024-10

    python -m research.overlays.lab <cache_dir> [--out research/overlays/results.json]

<cache_dir> is built by research.overlays.runs (per-strategy curves/trades).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

os.environ.setdefault("PROP_OOS", "1")
from research.prop import harness as H  # noqa: E402
from research.overlays import runs  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
HALT = 300.0          # account-wide daily stop ($, floating)
SLIP = 25.0           # $ lost closing everything at market at once
PERM_FLOOR = 9_300.0  # bot's permanent halt
FIRM_FLOOR = 9_200.0  # FundedNext static rail
START_EQ = 10_000.0
UNSEEN_END = pd.Timestamp("2024-10-20")   # window B's unseen year ends here
TF_MIN = {"M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}


# ----------------------------------------------------------------- strategy data
@dataclass
class Strat:
    """One strategy's exact run on the common bar index."""
    name: str
    symbol: str
    tf: str
    close: np.ndarray          # cumulative P&L at bar close (ffilled onto idx)
    worst: np.ndarray          # cumulative P&L at the bar's worst intrabar point
    e: np.ndarray              # entry bar per trade (bar index on idx)
    x: np.ndarray              # exit bar per trade
    p: np.ndarray              # trade profit ($) at live size
    rb: np.ndarray             # realized P&L before the trade
    resized: np.ndarray        # min-stop sizing changed the lots (sim.py flag)

    @property
    def tf_min(self):
        return TF_MIN[self.tf]


def build_index(runs_):
    """Common timeline = union of every strategy's bar times (+ trade times)."""
    s = set()
    for r in runs_:
        cv, t = r
        s |= set(cv.time)
        if len(t):
            s |= set(t.entry_time) | set(t.exit_time)
    return pd.DatetimeIndex(sorted(s))


def make_strats(mix, runs_, idx) -> list[Strat]:
    out = []
    for m, (cv, t) in zip(mix, runs_):
        g = cv.set_index("time")
        close = g.close.reindex(idx).ffill().fillna(0).to_numpy(np.float64)
        worst = g.worst.reindex(idx).ffill().fillna(0).to_numpy(np.float64)
        if len(t):
            e = idx.get_indexer(pd.DatetimeIndex(t.entry_time))
            x = idx.get_indexer(pd.DatetimeIndex(t.exit_time))
            p = t.profit.to_numpy(np.float64)
            rz = t.resized.to_numpy(bool) if "resized" in t else np.zeros(len(t), bool)
        else:
            e = x = np.zeros(0, int); p = np.zeros(0); rz = np.zeros(0, bool)
        rb = np.r_[0.0, np.cumsum(p)[:-1]] if len(p) else np.zeros(0)
        out.append(Strat(m["name"], m["symbol"], m["tf"], close, worst, e, x, p, rb, rz))
    return out


# ----------------------------------------------------------------- the replay
class Account:
    """What a rule may look at when deciding an entry's size factor."""
    __slots__ = ("idx", "eq_prev", "prev_close", "day_closes", "month_start", "month_halts",
                 "time", "strat", "k", "e")

    def __init__(self, idx):
        self.idx = idx
        self.eq_prev = 0.0        # combined close equity (P&L $) at the bar before the entry
        self.prev_close = 0.0     # yesterday's last close equity
        self.day_closes = []      # end-of-day close equity so far (completed days)
        self.month_start = 0.0    # equity at the end of the previous calendar month
        self.month_halts = 0      # close-all halts so far this calendar month
        self.time = None          # bar time of the entry bar (fill = time + tf)
        self.strat = None
        self.k = 0
        self.e = 0

    @property
    def equity(self):
        return START_EQ + self.eq_prev

    @property
    def mtd(self):
        return self.eq_prev - self.month_start

    @property
    def fill_time(self):
        return self.time + pd.Timedelta(minutes=self.strat.tf_min)


@dataclass
class Result:
    C: np.ndarray
    W: np.ndarray
    halts: int
    n_entries: int
    n_taken: int
    n_scaled: int
    factors: list = field(default_factory=list)


class Replay:
    def __init__(self, strats: list[Strat], idx: pd.DatetimeIndex):
        self.strats, self.idx = strats, idx
        n = len(idx)
        day = idx.normalize().to_numpy()
        self.starts = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
        self.ends = np.r_[self.starts[1:], n]
        self.month = idx.to_period("M").to_numpy()
        ev = [(int(e), s, k) for s, st in enumerate(strats) for k, e in enumerate(st.e)]
        ev.sort()
        self.events = ev
        # events grouped per day
        ev_day = np.searchsorted(self.starts, [e for e, _, _ in ev], side="right") - 1
        self.day_events = {}
        for (e, s, k), d in zip(ev, ev_day):
            self.day_events.setdefault(int(d), []).append((e, s, k))

    def run(self, rule=None, halt=HALT, slip=SLIP) -> Result:
        strats, idx = self.strats, self.idx
        n = len(idx)
        C = np.zeros(n); W = np.zeros(n); D = np.zeros(n + 1)
        f_of = {}            # (s,k) -> factor actually used (0 = skipped/blocked)
        x_cur = {}           # (s,k) -> current exit bar (cut by a halt or original)
        p_cur = {}
        acct = Account(idx)
        real_before = 0.0
        prev_close = 0.0
        halts = n_scaled = 0
        cur_month = None
        if rule is not None and hasattr(rule, "reset"):
            rule.reset()

        def add(s, k, f):
            st = strats[s]
            e, x = int(st.e[k]), int(st.x[k])
            C[e:x] += f * (st.close[e:x] - st.rb[k])
            W[e:x] += f * (st.worst[e:x] - st.rb[k])
            D[x] += f * st.p[k]
            f_of[(s, k)] = f; x_cur[(s, k)] = x; p_cur[(s, k)] = f * st.p[k]

        def remove(s, k):
            st = strats[s]
            f = f_of[(s, k)]
            e, x = int(st.e[k]), x_cur[(s, k)]
            C[e:x] -= f * (st.close[e:x] - st.rb[k])
            W[e:x] -= f * (st.worst[e:x] - st.rb[k])
            D[x] -= p_cur[(s, k)]
            f_of[(s, k)] = 0.0

        def cut(s, k, t):
            st = strats[s]
            f = f_of[(s, k)]
            x = x_cur[(s, k)]
            C[t:x] -= f * (st.close[t:x] - st.rb[k])
            W[t:x] -= f * (st.worst[t:x] - st.rb[k])
            D[x] -= p_cur[(s, k)]
            newp = f * (st.close[t] - st.rb[k])
            D[t] += newp
            x_cur[(s, k)] = t; p_cur[(s, k)] = newp

        for d, (lo, hi) in enumerate(zip(self.starts, self.ends)):
            if self.month[lo] != cur_month:
                cur_month = self.month[lo]
                acct.month_start = prev_close
                acct.month_halts = 0
            acct.prev_close = prev_close
            todays = self.day_events.get(d, ())
            for e, s, k in todays:
                if rule is None:
                    f = 1.0
                else:
                    acct.eq_prev = (C[e - 1] + real_before + D[lo:e].sum()) if e > lo else prev_close
                    acct.time = idx[e]; acct.strat = strats[s]; acct.k = k; acct.e = e
                    f = float(rule.factor(acct))
                if f > 0:
                    add(s, k, f)
                    if f != 1.0:
                        n_scaled += 1
                else:
                    f_of[(s, k)] = 0.0
            wday = W[lo:hi] + real_before + np.cumsum(D[lo:hi])
            hit = np.flatnonzero(wday - prev_close <= -halt)
            if len(hit):
                t = lo + int(hit[0]); halts += 1; acct.month_halts += 1
                cuts = []
                for e, s, k in todays:
                    if e > t and f_of[(s, k)] > 0:
                        remove(s, k)
                for (s, k), f in f_of.items():
                    if f > 0 and strats[s].e[k] <= t < x_cur[(s, k)]:
                        cut(s, k, t); cuts.append((s, k))
                if cuts:
                    c_t = C[t] + real_before + D[lo:t + 1].sum()
                    delta = c_t - (prev_close - halt - slip)
                    D[t] -= delta
                    for s, k in cuts:
                        p_cur[(s, k)] -= delta / len(cuts)
                wday = W[lo:hi] + real_before + np.cumsum(D[lo:hi])
            cday = C[lo:hi] + real_before + np.cumsum(D[lo:hi])
            C[lo:hi] = cday; W[lo:hi] = wday
            real_before += D[lo:hi].sum()
            prev_close = float(cday[-1])
            acct.day_closes.append(prev_close)
        taken = sum(1 for f in f_of.values() if f > 0)
        return Result(C, W, halts, len(self.events), taken, n_scaled,
                      [f_of[(s, k)] for _, s, k in self.events])


# ----------------------------------------------------------------- rules
class Rule:
    name = "rule"
    params: dict = {}

    def reset(self):
        pass

    def factor(self, a: Account) -> float:
        return 1.0

    def label(self):
        return f"{self.name} {self.params}" if self.params else self.name


class MonthlyStop(Rule):
    """(a) once the calendar month is down more than $x: no new entries until next month."""
    name = "monthly_stop"

    def __init__(self, x):
        self.x = x; self.params = dict(x=x)

    def factor(self, a):
        return 0.0 if a.mtd <= -self.x else 1.0


class HaltStop(Rule):
    """(a') after n close-all halts in a calendar month: no new entries until next month."""
    name = "halt_stop"

    def __init__(self, n=2):
        self.n = n; self.params = dict(n=n)

    def factor(self, a):
        return 0.0 if a.month_halts >= self.n else 1.0


class DrawdownScale(Rule):
    """(b) below $low cut every size to `size` until the account is back above $high."""
    name = "dd_scale"

    def __init__(self, low=9700.0, high=9900.0, size=0.5):
        self.low, self.high, self.size = low, high, size
        self.params = dict(low=low, high=high, size=size)
        self.on = False

    def reset(self):
        self.on = False

    def factor(self, a):
        eq = a.equity
        if self.on and eq > self.high:
            self.on = False
        elif not self.on and eq < self.low:
            self.on = True
        return self.size if self.on else 1.0


class VolTarget(Rule):
    """(c) size = target / realised std of the last n daily P&Ls, capped lo..hi."""
    name = "vol_target"

    def __init__(self, target, n=20, lo=0.5, hi=1.5, min_days=10):
        self.target, self.n, self.lo, self.hi, self.min_days = target, n, lo, hi, min_days
        self.params = dict(target=target, n=n, lo=lo, hi=hi)

    def factor(self, a):
        d = a.day_closes
        if len(d) < self.min_days:
            return 1.0
        pnl = np.diff(np.r_[0.0, d] if len(d) <= self.n else d[-(self.n + 1):])
        sd = float(np.std(pnl, ddof=1)) if len(pnl) > 1 else 0.0
        if sd <= 0:
            return 1.0
        return float(np.clip(self.target / sd, self.lo, self.hi))


class EquityFilter(Rule):
    """(d) pause a strategy whose last n trades net negative; resume after a
    (skipped) trade would have won."""
    name = "equity_filter"

    def __init__(self, n=10):
        self.n = n; self.params = dict(n=n); self.paused = {}

    def reset(self):
        self.paused = {}

    def factor(self, a):
        st, k = a.strat, a.k
        key = id(st)
        if self.paused.get(key):
            if k >= 1 and st.p[k - 1] > 0:
                self.paused[key] = False
                return 1.0
            return 0.0
        if k >= self.n and st.p[k - self.n:k].sum() < 0:
            self.paused[key] = True
            return 0.0
        return 1.0


def nfp_dates(start="2015-01-01", end="2027-01-01"):
    """First Friday of each month, 15:30 server (08:30 ET). Approximation: the
    BLS occasionally moves the release (holidays); those months are missed."""
    months = pd.period_range(start, end, freq="M")
    out = []
    for m in months:
        d = m.to_timestamp()
        d = d + pd.Timedelta(days=(4 - d.weekday()) % 7)
        out.append(d + pd.Timedelta(hours=15, minutes=30))
    return pd.DatetimeIndex(out)


def fomc_dates():
    from research.search.published_research.strategies import FOMC
    return pd.DatetimeIndex(FOMC) + pd.Timedelta(hours=21)    # 14:00 ET = 21:00 server


class EventBlackout(Rule):
    """(e) no new entries within `before` minutes before (and `after` after) FOMC / NFP."""
    name = "event_blackout"

    def __init__(self, before=60, after=0):
        self.before, self.after = before, after
        self.params = dict(before=before, after=after)
        self.events = np.sort(np.r_[fomc_dates().to_numpy(), nfp_dates().to_numpy()])

    def factor(self, a):
        ft = a.fill_time.to_datetime64()
        j = np.searchsorted(self.events, ft)        # first event >= fill
        for cand in (j - 1, j):
            if 0 <= cand < len(self.events):
                ev = self.events[cand]
                lo = ev - np.timedelta64(self.before, "m")
                hi = ev + np.timedelta64(self.after, "m")
                if lo <= ft <= hi:
                    return 0.0
        return 1.0


class FridayCutoff(Rule):
    """(f) no new entries on Friday from `hour`:00 server time."""
    name = "friday_cutoff"

    def __init__(self, hour=20):
        self.hour = hour; self.params = dict(hour=hour)

    def factor(self, a):
        ft = a.fill_time
        return 0.0 if (ft.weekday() == 4 and ft.hour >= self.hour) else 1.0


class Combo(Rule):
    """(h) product of the member rules (a 0 anywhere skips the entry)."""
    name = "combo"

    def __init__(self, *rules, name=None):
        self.rules = rules
        self.params = {}
        self._label = name or " + ".join(r.label() for r in rules)

    def reset(self):
        for r in self.rules:
            r.reset()

    def factor(self, a):
        f = 1.0
        for r in self.rules:
            f *= r.factor(a)
            if f == 0.0:
                return 0.0
        return f

    def label(self):
        return self._label


# ----------------------------------------------------------------- judging
def apply_perm_halt(C, W, floor=PERM_FLOOR):
    """The bot's permanent halt: freeze the account when worst equity touches the floor."""
    hit = np.flatnonzero(W <= floor - START_EQ)
    if not len(hit):
        return C, W, None
    t = int(hit[0])
    C2, W2 = C.copy(), W.copy()
    C2[t:] = W2[t:] = W[t]
    return C2, W2, t


def challenges(curve: pd.DataFrame, immediate: bool = True, every_days: int = 14) -> dict:
    """harness._challenges, plus `immediate=False`: a phase only counts as
    passed if the target still holds at the END of the server day it was hit
    (what happens without rule (g): the account keeps trading that day)."""
    if immediate:
        return H._challenges(curve, every_days)
    t = curve.time.to_numpy()
    w, cl = curve.worst.to_numpy(), curve.close.to_numpy()
    days = curve.time.dt.normalize().to_numpy()
    n = len(cl)
    day_end = np.r_[days[1:] != days[:-1], True]
    starts = pd.date_range(curve.time.iloc[0], curve.time.iloc[-1] - pd.Timedelta(days=60),
                           freq=f"{every_days}D")
    new_day = np.r_[True, days[1:] != days[:-1]]
    first_idx = np.maximum.accumulate(np.where(new_day, np.arange(n), 0))
    prev_cl = np.r_[0.0, cl[:-1]]
    day_start = prev_cl[first_idx]
    daily_fail = (w - day_start) <= -H.FIRM_DAILY * H.BASELINE

    def first(mask):
        k = int(np.argmax(mask))
        return k if mask.size and mask[k] else None

    def phase(i0, target):
        base = prev_cl[i0]
        seg_fail = daily_fail[i0:].copy()
        same_day = days[i0:] == days[i0]
        seg_fail[same_day] = (w[i0:][same_day] - base) <= -H.FIRM_DAILY * H.BASELINE
        seg_fail |= (w[i0:] - base) <= -H.FIRM_TOTAL * H.BASELINE
        f = first(seg_fail)
        p = first(((cl[i0:] - base) >= target * H.BASELINE) & day_end[i0:])
        if f is not None and (p is None or f <= p):
            return "fail", i0 + f
        if p is not None:
            return "pass", i0 + p
        return "open", n - 1

    passed = failed = open_ = 0; dur = []
    for s in starts:
        i0 = int(np.searchsorted(t, s.to_datetime64()))
        r1, i1 = phase(i0, H.PHASE_TARGETS[0])
        if r1 != "pass":
            failed += r1 == "fail"; open_ += r1 == "open"; continue
        r2, i2 = phase(i1 + 1, H.PHASE_TARGETS[1]) if i1 + 1 < n else ("open", i1)
        if r2 == "pass":
            passed += 1; dur.append((t[i2] - t[i0]) / np.timedelta64(1, "D"))
        else:
            failed += r2 == "fail"; open_ += r2 == "open"
    tot = passed + failed
    return dict(challenge_attempts=len(starts), challenge_pass=passed, challenge_fail=failed,
                challenge_unfinished=open_, challenge_pass_rate=passed / tot if tot else 0.0,
                challenge_median_days=float(np.median(dur)) if dur else None)


def judge(idx, res: Result, window: str) -> dict:
    C, W = res.C, res.W
    curve = pd.DataFrame({"time": idx, "worst": W, "close": C})
    m = H._metrics(curve, pd.DataFrame({"entry_time": [], "profit": []}))
    out = dict(net=float(C[-1]), avg_month=float(m["avg_month"]), worst_day=float(m["worst_day"]),
               lowest_equity=START_EQ + float(W.min()), max_dd=float(m["max_dd"]),
               green_months=float(m["green_months"]), worst_month=float(m["worst_month"]),
               months=int(m["months"]), halts=res.halts, entries=res.n_entries,
               taken=res.n_taken, scaled=res.n_scaled,
               challenge_pass=int(m["challenge_pass"]), challenge_fail=int(m["challenge_fail"]),
               challenge_pass_rate=float(m["challenge_pass_rate"]),
               challenge_median_days=m["challenge_median_days"],
               floor_breached=bool(W.min() <= FIRM_FLOOR - START_EQ),
               daily_breached=bool(m["worst_day"] <= -H.FIRM_DAILY * H.BASELINE),
               monthly=m["monthly"])
    C2, W2, t = apply_perm_halt(C, W)
    out["perm_halt_net"] = float(C2[-1])
    out["perm_halt_date"] = str(idx[t].date()) if t is not None else None
    if window == "B":
        j = int(np.searchsorted(idx.values, UNSEEN_END.to_datetime64()))
        out["unseen_net"] = float(C[j - 1]) if j > 0 else 0.0
        out["unseen_lowest_equity"] = START_EQ + float(W[:j].min())
        out["since_2024_10_net"] = out["net"] - out["unseen_net"]
    return out


# ----------------------------------------------------------------- variants
def single_rules():
    return [
        MonthlyStop(500), MonthlyStop(750), MonthlyStop(1000),
        DrawdownScale(9700, 9900, 0.5), DrawdownScale(9800, 9950, 0.5),
        DrawdownScale(9700, 9900, 0.25), DrawdownScale(9500, 9800, 0.5),
        VolTarget(150), VolTarget(200), VolTarget(250),
        VolTarget(200, hi=1.0), VolTarget(250, hi=1.0), VolTarget(300, hi=1.0),
        HaltStop(1), HaltStop(2), HaltStop(3),
        EquityFilter(10), EquityFilter(20),
        EventBlackout(30, 0), EventBlackout(60, 0), EventBlackout(60, 30),
        FridayCutoff(20), FridayCutoff(18),
    ]


def combo_rules():
    """(h) built from the singles that cut the bad year most per $ of good-year profit."""
    dd = lambda: DrawdownScale(9700, 9900, 0.5)
    dd25 = lambda: DrawdownScale(9700, 9900, 0.25)
    return [
        Combo(MonthlyStop(500), dd(), name="monthly_stop 500 + dd_scale 9700/9900 x0.5"),
        Combo(MonthlyStop(750), dd(), name="monthly_stop 750 + dd_scale 9700/9900 x0.5"),
        Combo(MonthlyStop(500), dd25(), name="monthly_stop 500 + dd_scale 9700/9900 x0.25"),
        Combo(HaltStop(2), dd(), name="halt_stop 2 + dd_scale 9700/9900 x0.5"),
        Combo(HaltStop(2), dd25(), name="halt_stop 2 + dd_scale 9700/9900 x0.25"),
        Combo(HaltStop(1), dd(), name="halt_stop 1 + dd_scale 9700/9900 x0.5"),
        Combo(MonthlyStop(500), HaltStop(2), dd(), name="monthly_stop 500 + halt_stop 2 + dd_scale 9700/9900 x0.5"),
        Combo(MonthlyStop(750), dd(), VolTarget(250, hi=1.0),
              name="monthly_stop 750 + dd_scale 9700/9900 x0.5 + vol_target 250 (down only)"),
        Combo(HaltStop(2), dd(), VolTarget(250, hi=1.0),
              name="halt_stop 2 + dd_scale 9700/9900 x0.5 + vol_target 250 (down only)"),
        Combo(MonthlyStop(750), dd(), EventBlackout(30, 0),
              name="monthly_stop 750 + dd_scale 9700/9900 x0.5 + blackout 30"),
    ]


def candidates():
    """The rules the report recommends or compares head-to-head."""
    return [
        Combo(HaltStop(1), DrawdownScale(9700, 9900, 0.5), name="halt_stop 1 + dd_scale 9700/9900 x0.5"),
        Combo(HaltStop(2), DrawdownScale(9700, 9900, 0.25), name="halt_stop 2 + dd_scale 9700/9900 x0.25"),
        Combo(MonthlyStop(500), DrawdownScale(9700, 9900, 0.5), name="monthly_stop 500 + dd_scale 9700/9900 x0.5"),
        DrawdownScale(9700, 9900, 0.5),
        HaltStop(1),
    ]


def stress(cache: Path, halt: float = 250.0):
    """Window A has zero $300 halts BY CONSTRUCTION (the sizer required worst
    day > -$300), so a halt-triggered rule looks free there. Re-run with a
    tighter $250 stop so halts do happen in the good years and the rule's
    real cost shows."""
    out = {}
    for window in ("A", "B"):
        mix, strats, idx = load_window(cache, window)
        rp = Replay(strats, idx)
        rows = {}
        for rule in [None] + candidates():
            r = rp.run(rule, halt=halt)
            j = judge(idx, r, window)
            rows["baseline" if rule is None else rule.label()] = {
                k: j[k] for k in ["net", "worst_day", "lowest_equity", "halts", "taken",
                                  "challenge_pass_rate", "perm_halt_net"] + (["unseen_net"] if window == "B" else [])}
        out[window] = rows
        del strats, rp
    return out


def flat_day_trades(cache: Path):
    """Index CSVs contain 'flat' days (high-low < 10% of the median daily
    range: stale bars). Trades ENTERED on such a day were sized off a bogus
    tiny stop. Reports them so the headline can be read honestly."""
    import pandas as pd
    mix = runs.load_mix()
    flat, n_flat = {}, {}
    for sym in sorted(H.INDICES):
        df = pd.read_csv(H.DATA / f"{sym.lower()}-h1.csv", usecols=["time", "high", "low"], parse_dates=["time"])
        df = df[df.time >= "2023-10-01"]
        g = df.assign(d=df.time.dt.normalize()).groupby("d").agg(h=("high", "max"), l=("low", "min"))
        rng = g.h - g.l
        flat[sym] = set(rng[rng < 0.1 * rng.median()].index)
        n_flat[sym] = dict(days=int(len(flat[sym])), median_range=float(rng.median()),
                           first=[str(d.date()) for d in sorted(flat[sym])[:12]])
    out = dict(flat_days=n_flat)
    for window in ("A", "B"):
        rows, tot = [], 0.0
        for m, rr in zip(mix, runs.load(cache, window, mix)):
            if m["symbol"] not in flat:
                continue
            cv, t = rr[0.0]
            if not len(t):
                continue
            hit = t[pd.DatetimeIndex(t.entry_time).normalize().isin(flat[m["symbol"]])]
            if len(hit):
                tot += float(hit.profit.sum())
                rows.append(dict(strategy=f"{m['name']} {m['symbol']} {m['tf']}", trades=int(len(hit)),
                                 profit=float(hit.profit.sum()), max_lots=float(hit.lots.max())))
        out[window] = dict(total_profit=tot, by_strategy=rows)
    return out


def load_window(cache: Path, window: str, k: float = 0.0):
    mix = runs.load_mix()
    rr = [r[k] for r in runs.load(cache, window, mix)]
    idx = build_index(rr)
    return mix, make_strats(mix, rr, idx), idx


def run_all(cache: Path, out_path: Path, ks=(0.15, 0.25, 0.35)):
    results = {"windows": {w: str(s.date()) for w, s in runs.WINDOWS.items()}, "variants": []}
    rows = {}

    def put(group, label, params, window, judged):
        row = rows.setdefault(label, dict(group=group, overlay=label, params=params))
        row[window] = judged

    for window in ("A", "B"):
        mix, strats, idx = load_window(cache, window)
        rp = Replay(strats, idx)
        base = rp.run(None)
        j = judge(idx, base, window)
        j["challenge_eod"] = challenges(pd.DataFrame({"time": idx, "worst": base.W, "close": base.C}), immediate=False)
        put("baseline", "baseline (live rules)", {}, window, j)
        print(f"[{window}] baseline net {j['net']:,.0f} worst day {j['worst_day']:,.0f} lowest {j['lowest_equity']:,.0f} halts {j['halts']}", flush=True)
        for rule in single_rules() + combo_rules():
            r = rp.run(rule)
            j = judge(idx, r, window)
            put(rule.name, rule.label(), rule.params, window, j)
            print(f"[{window}] {rule.label():<60} net {j['net']:>8,.0f} worst {j['worst_day']:>6,.0f} low {j['lowest_equity']:>7,.0f} halts {j['halts']:>3} taken {j['taken']}/{j['entries']}", flush=True)
        del strats, rp
        for k in ks:
            mix, strats, idx = load_window(cache, window, k)
            rp = Replay(strats, idx)
            r = rp.run(None)
            j = judge(idx, r, window)
            j["resized_trades"] = int(sum(int(s.resized.sum()) for s in strats))
            j["resized_by_strategy"] = {s.name + " " + s.symbol + " " + s.tf: int(s.resized.sum())
                                        for s in strats if s.resized.sum()}
            put("min_stop", f"min_stop k={k}", dict(k=k), window, j)
            print(f"[{window}] min_stop k={k} net {j['net']:,.0f} worst {j['worst_day']:,.0f} low {j['lowest_equity']:,.0f} resized {j['resized_trades']}", flush=True)
            if k == 0.15:   # the recommended package: min-stop sizing + the account rules
                for x in (500, 750):
                    rule = Combo(MonthlyStop(x), DrawdownScale(9700, 9900, 0.5),
                                 name=f"PACKAGE: min_stop k=0.15 + monthly_stop {x} + dd_scale 9700/9900 x0.5")
                    j = judge(idx, rp.run(rule), window)
                    put("package", rule.label(), dict(k=k, x=x), window, j)
                    print(f"[{window}] {rule.label()} net {j['net']:,.0f} low {j['lowest_equity']:,.0f} halts {j['halts']}", flush=True)
            del strats, rp
    results["variants"] = list(rows.values())
    results["stress_halt_250"] = stress(cache, 250.0)
    results["flat_day_trades"] = flat_day_trades(cache)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    json.dump(results, open(out_path, "w"), indent=1, default=str)
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cache")
    ap.add_argument("--out", default=str(ROOT / "research" / "overlays" / "results.json"))
    a = ap.parse_args()
    sys.path.insert(0, str(ROOT))
    run_all(Path(a.cache), Path(a.out))
