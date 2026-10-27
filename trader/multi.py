"""Multi-strategy live runner: the 66-strategy portfolio from
docs/board/portfolio-lp300-66.json, each strategy run EXACTLY as the research
judge (research/prop/harness.py) ran it, on a rolling window of broker bars.

Pure logic lives here (no MetaTrader5 import): the runner talks to a `Market`
(trader/mt5_market.py live, a replay fake in the tests), which is what lets
the parity tests feed the same cached bars through this path and through
harness.simulate and demand identical entries, stops and lots.

Per strategy, at every NEW CLOSED bar of its symbol/timeframe:
  1. sync with the broker (a position that vanished was stopped/targeted),
  2. time exits (Entry.max_hold / Entry.exit_hour) exactly like the harness,
  3. Entry.manage(df, i, pos) -> None | new stop | "close",
  4. the signal for the latest bar: an opposite signal flips (close, then
     open), a same-side signal while in a trade is ignored,
  5. sizing = fixed-dollar risk at the stop, commission reserved, rounded to
     the broker's lot step - the harness formula, number for number.

One MT5 magic number per strategy (BASE_MAGIC + index) so several strategies
can hold the same symbol at once on a hedging account.

Account-wide guard (AccountGuard): floating equity down DAILY_STOP from the
server-day-start balance -> close everything, no new entries until the next
server day. Equity at or below FLOOR -> close everything, permanent halt.

Risk rules on top (docs/2026-10-25-overlay-lab-results.md, approved by Veer):
  * drawdown scaling: every NEW trade at SCALE_SIZE of its normal risk while
    equity (balance + floating) is below SCALE_LOW, full size again only once
    equity is above SCALE_HIGH;
  * monthly loss stop: month-to-date P&L = equity minus the balance at the
    last close of the previous server-time calendar month (= the sum of every
    deal on the account before the month started: deposits, closed P&L,
    commission, swap); at or below -MONTHLY_STOP no new entries for the rest
    of that month, open trades untouched, cleared on the first server day of
    the next month. The anchor is kept in the state file for restarts within
    the month; MULTI_MONTH_START_BALANCE overrides it;
  * minimum sizing stop: lots are computed from max(strategy stop distance,
    MIN_STOP_K x the symbol's average daily range over the last 20 completed
    D1 bars); the real stop order is unchanged.
"""
from __future__ import annotations

import importlib
import json
import logging
import math
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Protocol

import numpy as np
import pandas as pd

from research.prop import harness as H

log = logging.getLogger("trader")

ROOT = Path(__file__).resolve().parents[1]
MIX_PATH = ROOT / "docs" / "board" / "portfolio-lp300-66.json"
SYMBOL_MAP_PATH = ROOT / "config" / "symbols.json"
STATE_PATH = ROOT / "logs" / "multi_state.json"

BASE_MAGIC = 500_000
WINDOW_BARS = 6000          # warmup: bos_lookback 2000 on M30, SMA1000 on H1, D1 200-bar filters
DAILY_STOP = 300.0          # $ floating loss on the server day -> close all, block the day
FLOOR = 9_300.0             # equity at/below this -> permanent halt (buffer above the $9,200 rail)
SCALE_LOW = 9_700.0         # equity below this -> new trades at SCALE_SIZE of their risk ...
SCALE_HIGH = 9_900.0        # ... until equity is back above this
SCALE_SIZE = 0.5
MONTHLY_STOP = 500.0        # month-to-date loss (incl. floating) -> no new entries this month
MIN_STOP_K = 0.15           # sizing stop >= MIN_STOP_K x 20-day average daily range (0 = off)
ADR_DAYS = 20
SPECS_PATHS = (ROOT / "config" / "symbol_specs.json", ROOT / "data" / "search" / "symbol_specs.json")
TF_MINUTES = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440}


# --------------------------------------------------------------------------- #
# Mix file                                                                     #
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class StrategySpec:
    idx: int
    module: str
    fn: str
    params: dict
    symbol: str          # research name (XAUUSD, DE40, ...)
    tf: str
    risk: float

    @property
    def magic(self) -> int:
        return BASE_MAGIC + self.idx

    @property
    def name(self) -> str:
        return f"#{self.idx:02d} {self.fn.removeprefix('build_')} {self.symbol} {self.tf}"

    @property
    def short(self) -> str:
        return f"#{self.idx:02d}"

    def builder(self) -> Callable:
        return getattr(importlib.import_module(self.module), self.fn)

    def build(self, df: pd.DataFrame) -> list:
        return self.builder()(df, **self.params)


def load_mix(path: Path | str = MIX_PATH) -> list[StrategySpec]:
    data = json.loads(Path(path).read_text())
    return [StrategySpec(i, m["module"], m["fn"], dict(m["params"]), m["symbol"].upper(),
                         m["tf"].upper(), float(m["risk"]))
            for i, m in enumerate(data["mix"])]


def load_symbol_map(path: Path | str = SYMBOL_MAP_PATH) -> dict[str, str]:
    """research symbol -> broker symbol. Missing names map to themselves."""
    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    return {k.upper(): v for k, v in data.get("map", {}).items()}


# --------------------------------------------------------------------------- #
# Sizing — the harness formula, number for number                              #
# --------------------------------------------------------------------------- #
_SPECS: dict | None = None


def load_symbol_specs(paths=SPECS_PATHS) -> dict:
    """Contract / point / lot-step / profit currency per research symbol, the
    numbers the research was sized with. config/symbol_specs.json is the
    tracked copy; data/search/symbol_specs.json (git-ignored) the fallback.
    Refuses to run without either: the defaults would size trades wrong."""
    for p in paths:
        p = Path(p)
        if p.exists():
            d = json.loads(p.read_text())
            if not d:
                continue
            log.info("symbol specs: %s (%d symbols)", p, len(d))
            return d
    raise FileNotFoundError(
        "symbol_specs.json not found in " + " or ".join(str(p) for p in paths) +
        " - the bot cannot size trades without the contract/point/lot-step table. "
        "Restore config/symbol_specs.json from git.")


def research_spec(symbol: str) -> dict:
    """Contract/point/lot-step assumptions the research was run with."""
    global _SPECS
    if _SPECS is None:
        _SPECS = load_symbol_specs()
    return _SPECS.get(symbol, {})


def size_trade(symbol: str, side: str, close: float, sl: float, tp: float | None,
               bar_spread_points: float, conv: float, risk: float,
               spread_mult: float = 1.0, max_lots: float = 50.0,
               min_stop_dist: float = 0.0) -> dict | None:
    """Replicates harness.simulate's entry block. Returns None when the harness
    would have skipped the signal (invalid levels or stop too wide to fund),
    else dict(lots, entry_est, loss_per_lot, risk_usd, size_dist, resized).

    `min_stop_dist` (price units) is the minimum stop distance used for
    SIZING only: lots come from max(|entry - sl|, min_stop_dist) while
    risk_usd and the stop itself stay on the real stop. 0 = the harness."""
    spec = research_spec(symbol)
    contract = float(spec.get("contract", 100.0 if symbol == "XAUUSD" else 100000.0))
    point = float(spec.get("point", 0.01))
    vstep = float(spec.get("vol_step", 0.01)) or 0.01
    vmin = float(spec.get("vol_min", 0.01)) or 0.01
    comm = 0.0 if symbol in H.INDICES else H.COMMISSION_RT
    slip = 0.1 * H._pip(symbol)
    floor = H.SPREAD_FLOOR.get(symbol, 0.0)
    sp = max(floor, float(bar_spread_points) * point) * spread_mult
    entry = close + sp + slip if side == "long" else close - sp - slip
    if side == "long":
        ok = sl < close and (tp is None or tp > entry)
    else:
        ok = sl > close and (tp is None or tp < entry)
    if not ok or not math.isfinite(sl):
        return None
    stop_dist = abs(entry - sl)
    size_dist = max(stop_dist, float(min_stop_dist or 0.0))
    loss_per_lot = (stop_dist + slip) * contract * conv + comm
    size_loss_per_lot = (size_dist + slip) * contract * conv + comm
    if loss_per_lot <= 0:
        return None
    risk_usd = risk * H.BASELINE
    lots = math.floor(risk_usd / size_loss_per_lot / vstep) * vstep
    lots = min(round(lots, 2), max_lots)
    if lots < vmin:
        return None
    return dict(lots=lots, entry_est=entry, loss_per_lot=loss_per_lot,
                risk_usd=lots * loss_per_lot, stop_dist=stop_dist, size_dist=size_dist,
                resized=size_dist > stop_dist)


def balance_from_deals(deals, before: pd.Timestamp) -> float:
    """Account balance as it stood just before `before` (broker time): the
    sum of profit + swap + commission over every deal with time < before,
    balance deals (deposits / withdrawals) included. `deals` are MT5 deal
    records or anything with .time (epoch seconds or Timestamp), .profit,
    .swap and .commission."""
    cut = pd.Timestamp(before)
    cut_s = int(cut.timestamp())
    total = 0.0
    for d in deals:
        t = d.time
        early = (t < cut_s) if isinstance(t, (int, float)) else (pd.Timestamp(t) < cut)
        if early:
            total += float(d.profit) + float(getattr(d, "swap", 0.0)) + float(getattr(d, "commission", 0.0))
    return total


def average_daily_range(daily: pd.DataFrame, days: int = ADR_DAYS) -> float | None:
    """Mean high-low of the last `days` completed D1 bars; None with fewer
    than half of them (no resizing rather than a guess)."""
    if daily is None or len(daily) < max(5, days // 2):
        return None
    d = daily.tail(days)
    return float((d["high"] - d["low"]).mean())


CONV_PAIR = {"JPY": ("USDJPY", True), "CHF": ("USDCHF", True), "CAD": ("USDCAD", True),
             "GBP": ("GBPUSD", False), "EUR": ("EURUSD", False)}


def conv_pair_for(symbol: str) -> tuple[str, bool] | None:
    """(pair, invert) whose close converts this symbol's P&L to USD; None = USD."""
    spec = research_spec(symbol)
    ccy = spec.get("profit_ccy") or ("JPY" if symbol.endswith("JPY") else "USD")
    if ccy == "USD":
        return None
    return CONV_PAIR[ccy]


def attach_conv(df: pd.DataFrame, symbol: str, pair_df: pd.DataFrame | None) -> pd.DataFrame:
    """Same as harness._attach_conv but with the conversion bars supplied."""
    pair = conv_pair_for(symbol)
    df = df.copy()
    if pair is None:
        df["conv"] = 1.0
        return df
    if pair_df is None or pair_df.empty:
        raise ValueError(f"conversion series {pair[0]} missing for {symbol}")
    src = pair_df[["time", "close"]].drop_duplicates("time").sort_values("time")
    src = src.assign(conv=(1.0 / src["close"]) if pair[1] else src["close"])
    out = pd.merge_asof(df.sort_values("time"), src[["time", "conv"]], on="time",
                        direction="backward")
    out["conv"] = out["conv"].bfill()
    return out.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# Market interface                                                             #
# --------------------------------------------------------------------------- #
@dataclass
class LivePos:
    ticket: int
    symbol: str          # BROKER symbol
    magic: int
    side: str
    lots: float
    entry: float
    sl: float
    tp: float
    open_time: pd.Timestamp
    profit: float = 0.0


class Market(Protocol):
    def rates(self, symbol: str, tf: str, count: int) -> pd.DataFrame:
        """Most recent `count` CLOSED bars (time, open, high, low, close,
        tick_volume, spread), oldest first, broker time."""
        ...
    def tick_time(self, symbol: str) -> pd.Timestamp | None: ...
    def account(self) -> tuple[float, float]:
        """(equity, balance)"""
        ...
    def positions(self) -> list[LivePos]: ...
    def open(self, symbol: str, side: str, lots: float, sl: float, tp: float,
             magic: int, comment: str) -> LivePos: ...
    def close(self, pos: LivePos, comment: str) -> float: ...
    def modify(self, pos: LivePos, sl: float, tp: float) -> None: ...
    def cancel_pending(self) -> int: ...
    def realized_since(self, t: pd.Timestamp) -> float:
        """Net closed P&L (profit+swap+commission) of deals at/after broker time t."""
        ...
    def balance_at(self, t: pd.Timestamp) -> float:
        """Balance as it stood just before broker time t (every deal before t summed)."""
        ...


# --------------------------------------------------------------------------- #
# Account-wide guard                                                           #
# --------------------------------------------------------------------------- #
@dataclass
class AccountGuard:
    daily_stop: float = DAILY_STOP
    floor: float = FLOOR
    day: str | None = None               # server day 'YYYY-MM-DD'
    day_start_balance: float = 0.0
    blocked_day: str | None = None       # no new entries on this server day
    blown: bool = False                  # permanent halt
    last_equity: float = 0.0
    # drawdown scaling
    scale_low: float = SCALE_LOW
    scale_high: float = SCALE_HIGH
    scale_size: float = SCALE_SIZE
    scaled: bool = False                 # new trades at scale_size of their risk
    # monthly loss stop
    monthly_stop: float = MONTHLY_STOP
    month: str | None = None             # server month 'YYYY-MM'
    month_start_balance: float = 0.0     # balance at the last close of the previous month
    month_anchor: str = ""               # where it came from: 'history' | 'override' | 'balance' (fallback)
    blocked_month: str | None = None     # no new entries for the rest of this month

    def update(self, now: pd.Timestamp, equity: float, balance: float,
               day_start_balance: float | None = None,
               month_start_balance: float | None = None) -> list[str]:
        """Returns events: 'new_day', 'daily_stop', 'blown', 'scale_on',
        'scale_off', 'month_stop', 'month_released' (each at most once per
        state change). `day_start_balance` / `month_start_balance` let the
        caller supply the true 00:00 / 1st-of-month balance on a (re)start."""
        events = []
        now = pd.Timestamp(now)
        day = str(now.normalize().date())
        month = f"{now.year:04d}-{now.month:02d}"
        if day != self.day:
            self.day = day
            self.day_start_balance = balance if day_start_balance is None else day_start_balance
            events.append("new_day")
        if month != self.month:
            was_blocked = self.blocked_month is not None and self.blocked_month == self.month
            self.month = month
            self.month_start_balance = balance if month_start_balance is None else month_start_balance
            self.month_anchor = "balance" if month_start_balance is None else self.month_anchor
            if was_blocked:
                events.append("month_released")
        elif month_start_balance is not None and month_start_balance != self.month_start_balance:
            self.month_start_balance = month_start_balance      # a better anchor for the same month
        self.last_equity = equity
        if not self.blown and equity <= self.floor:
            self.blown = True
            events.append("blown")
        if self.blocked_day != day and equity - self.day_start_balance <= -self.daily_stop:
            self.blocked_day = day
            events.append("daily_stop")
        if self.scaled and equity > self.scale_high:
            self.scaled = False
            events.append("scale_off")
        elif not self.scaled and self.scale_size < 1.0 and equity < self.scale_low:
            self.scaled = True
            events.append("scale_on")
        if self.monthly_stop > 0 and self.blocked_month != month and \
                equity - self.month_start_balance <= -self.monthly_stop:
            self.blocked_month = month
            events.append("month_stop")
        return events

    @property
    def blocked(self) -> bool:
        return self.blown or self.blocked_day == self.day or self.month_blocked

    @property
    def month_blocked(self) -> bool:
        return self.blocked_month is not None and self.blocked_month == self.month

    @property
    def size_factor(self) -> float:
        return self.scale_size if self.scaled else 1.0

    def mtd(self, equity: float | None = None) -> float:
        """Month-to-date P&L including floating."""
        return (self.last_equity if equity is None else equity) - self.month_start_balance

    def may_open(self) -> tuple[bool, str]:
        if self.blown:
            return False, f"permanent halt: equity reached {self.floor:.0f}"
        if self.blocked_day == self.day:
            return False, f"daily stop hit ({self.daily_stop:.0f}) — no entries until next server day"
        if self.month_blocked:
            return False, f"monthly stop hit ({self.monthly_stop:.0f}) — no entries until next month"
        return True, ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "AccountGuard":
        g = cls()
        for k, v in d.items():
            if hasattr(g, k):
                setattr(g, k, v)
        return g


# --------------------------------------------------------------------------- #
# Per-strategy state                                                           #
# --------------------------------------------------------------------------- #
@dataclass
class StratState:
    ticket: int = 0
    side: str = ""
    entry: float = 0.0
    sl: float = 0.0
    sl0: float = 0.0
    tp: float | None = None
    lots: float = 0.0
    entry_bar: str = ""            # open time of the bar whose close triggered the entry
    max_hold: int | None = None
    exit_hour: int | None = None
    risk_usd: float = 0.0
    meta: dict = field(default_factory=dict)
    extra: dict = field(default_factory=dict)   # keys manage() stashes in pos (e.g. 'ext')

    @property
    def open(self) -> bool:
        return self.ticket != 0

    def clear(self):
        self.__init__()


# --------------------------------------------------------------------------- #
# The runner                                                                   #
# --------------------------------------------------------------------------- #
MANAGE_KEYS = {"side", "entry", "sl", "sl0", "tp", "lots", "bar", "max_hold", "exit_hour",
               "manage", "risk_usd", "meta"}


class MultiRunner:
    def __init__(self, market: Market, specs: list[StrategySpec], symbol_map: dict[str, str],
                 alert: Callable[[str], None] = lambda s: None, state_path: Path | None = STATE_PATH,
                 window: int = WINDOW_BARS, guard: AccountGuard | None = None,
                 disabled: dict[int, str] | None = None, spread_mult: float = 1.0,
                 min_stop_k: float = MIN_STOP_K, month_start_override: float | None = None):
        self.market = market
        self.specs = specs
        self.symbol_map = symbol_map
        self.alert = alert
        self.state_path = Path(state_path) if state_path else None
        self.window = window
        self.guard = guard or AccountGuard()
        self.disabled = dict(disabled or {})       # idx -> reason (never traded)
        self.spread_mult = spread_mult
        self.min_stop_k = min_stop_k
        self.month_start_override = month_start_override
        self._adr: dict[str, tuple[str, float | None]] = {}     # symbol -> (server day, ADR)
        self.states: dict[int, StratState] = {s.idx: StratState() for s in specs}
        self.last_bar: dict[tuple[str, str], pd.Timestamp | None] = {}
        self.keys: dict[tuple[str, str], list[StrategySpec]] = {}
        for s in specs:
            self.keys.setdefault((s.symbol, s.tf), []).append(s)
        self.events: list[dict] = []        # what happened (tests + reports)
        self._sig_cache: dict[int, tuple[pd.Timestamp, list]] = {}
        self._was_blocked = False
        self._load_state()

    # ---------------------------------------------------------------- utils
    def broker_symbol(self, research: str) -> str:
        return self.symbol_map.get(research, research)

    def active_specs(self) -> list[StrategySpec]:
        return [s for s in self.specs if s.idx not in self.disabled]

    def _emit(self, kind: str, **kw):
        ev = dict(kind=kind, **kw)
        self.events.append(ev)
        return ev

    # ---------------------------------------------------------------- state
    def _load_state(self):
        if not self.state_path or not self.state_path.exists():
            return
        try:
            d = json.loads(self.state_path.read_text())
        except (OSError, ValueError) as exc:
            log.error("state file unreadable (%s) — starting clean", exc)
            return
        self.guard = AccountGuard.from_dict(d.get("guard", {}))
        for k, v in d.get("strategies", {}).items():
            idx = int(k)
            if idx in self.states:
                st = StratState()
                for kk, vv in v.items():
                    if hasattr(st, kk):
                        setattr(st, kk, vv)
                self.states[idx] = st

    def save_state(self):
        if not self.state_path:
            return
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        d = dict(guard=self.guard.to_dict(),
                 strategies={str(i): asdict(s) for i, s in self.states.items() if s.open})
        tmp = self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(d, indent=1, default=str))
        tmp.replace(self.state_path)

    # ---------------------------------------------------------------- bars
    def fetch_window(self, symbol: str, tf: str) -> pd.DataFrame:
        """`window` closed bars of the BROKER symbol with the research
        conversion column attached, exactly as harness.load would."""
        df = self.market.rates(self.broker_symbol(symbol), tf, self.window)
        if df is None or df.empty:
            raise RuntimeError(f"no bars for {symbol} {tf}")
        df = df.drop_duplicates("time").sort_values("time").reset_index(drop=True)
        pair = conv_pair_for(symbol)
        pair_df = None
        if pair is not None:
            pair_df = self.market.rates(self.broker_symbol(pair[0]), tf, self.window)
        df = attach_conv(df, symbol, pair_df)
        df.attrs.update(symbol=symbol, tf=tf, split="live", score_from=None)
        return df

    def latest_closed(self, symbol: str, tf: str) -> pd.Timestamp | None:
        df = self.market.rates(self.broker_symbol(symbol), tf, 2)
        if df is None or df.empty:
            return None
        return pd.Timestamp(df["time"].iloc[-1])

    def server_time(self) -> pd.Timestamp | None:
        ts = [self.market.tick_time(self.broker_symbol(s)) for s in {sp.symbol for sp in self.active_specs()}]
        ts = [t for t in ts if t is not None]
        return max(ts) if ts else None

    # ---------------------------------------------------------------- guard
    def check_guard(self, now: pd.Timestamp | None = None) -> list[str]:
        now = now or self.server_time()
        if now is None:
            return []
        equity, balance = self.market.account()
        now = pd.Timestamp(now)
        day_start = month_start = None
        if str(now.normalize().date()) != self.guard.day:
            # true 00:00-server balance = balance now minus what closed today
            try:
                day_start = balance - self.market.realized_since(now.normalize())
            except Exception as exc:      # noqa: BLE001 — a history hiccup must not stop the guard
                log.warning("realized_since failed (%s); anchoring day on current balance", exc)
        month = f"{now.year:04d}-{now.month:02d}"
        anchor = self.guard.month_anchor if month == self.guard.month else ""
        if anchor not in ("history", "override"):
            # balance at the last close of the previous month = every deal before the 1st summed
            if self.month_start_override is not None:
                month_start, anchor = float(self.month_start_override), "override"
            else:
                try:
                    month_start = self.market.balance_at(now.normalize().replace(day=1))
                    anchor = "history"
                except Exception as exc:      # noqa: BLE001 — a history hiccup must not stop the guard
                    log.warning("balance_at failed (%s); anchoring month on current balance until "
                                "the next poll", exc)
        prev = (self.guard.month, self.guard.month_start_balance)
        events = self.guard.update(now, equity, balance, day_start, month_start)
        if month_start is not None:
            self.guard.month_anchor = anchor
        if (self.guard.month, self.guard.month_start_balance) != prev:
            log.info("server month %s | month-start balance %.2f (%s) | equity %.2f",
                     self.guard.month, self.guard.month_start_balance, self.guard.month_anchor, equity)
        for ev in events:
            if ev == "new_day":
                log.info("server day %s | day-start balance %.2f | equity %.2f",
                         self.guard.day, self.guard.day_start_balance, equity)
                self._emit("new_day", day=self.guard.day, balance=self.guard.day_start_balance)
            elif ev == "daily_stop":
                down = equity - self.guard.day_start_balance
                n = self.close_everything("daily_stop")
                self.alert(f"\U0001F6D1 DAILY STOP: equity {equity:.2f} is {down:+.2f} vs the "
                           f"server-day start ({self.guard.day_start_balance:.2f}). Closed {n} "
                           f"position(s), cancelled pending orders. No new trades until the next "
                           f"server day ({self.guard.day}).")
                self._emit("daily_stop", equity=equity, closed=n)
            elif ev == "blown":
                n = self.close_everything("floor")
                self.alert(f"\U0001F6D1\U0001F6D1 PERMANENT HALT: equity {equity:.2f} reached the "
                           f"{self.guard.floor:.0f} floor. Closed {n} position(s). The bot will "
                           f"not trade again until the halt is cleared by hand "
                           f"(delete {self.state_path}).")
                self._emit("blown", equity=equity, closed=n)
            elif ev == "scale_on":
                self.alert(f"\U0001F53B SIZE CUT: equity {equity:.2f} is below {self.guard.scale_low:.0f}. "
                           f"New trades at {self.guard.scale_size:g}x their risk until equity is back "
                           f"above {self.guard.scale_high:.0f}. Open trades untouched.")
                self._emit("scale_on", equity=equity)
            elif ev == "scale_off":
                self.alert(f"\U0001F53C FULL SIZE again: equity {equity:.2f} is above "
                           f"{self.guard.scale_high:.0f}.")
                self._emit("scale_off", equity=equity)
            elif ev == "month_stop":
                self.alert(f"\u23F8\uFE0F MONTHLY STOP: month {self.guard.month} is "
                           f"{self.guard.mtd(equity):+.2f} vs the month-start balance "
                           f"({self.guard.month_start_balance:.2f}). No new trades until "
                           f"next month; open trades run to their own exits.")
                self._emit("month_stop", equity=equity, mtd=self.guard.mtd(equity))
            elif ev == "month_released":
                self.alert(f"\u25B6\uFE0F new month {self.guard.month}: the monthly stop is "
                           f"released, trading resumes. Month-start balance "
                           f"{self.guard.month_start_balance:.2f}.")
                self._emit("month_released", month=self.guard.month)
        self.save_state()
        return events

    # ---------------------------------------------------------------- sizing stop
    def min_stop_dist(self, symbol: str) -> float:
        """MIN_STOP_K x the symbol's 20-day average daily range from the
        broker's D1 bars, in price units; 0 when the rule is off or the
        daily history is too short. Cached per symbol per server day."""
        if self.min_stop_k <= 0:
            return 0.0
        day = self.guard.day or ""
        hit = self._adr.get(symbol)
        if hit is None or hit[0] != day:
            adr = None
            try:
                daily = self.market.rates(self.broker_symbol(symbol), "D1", ADR_DAYS)
                adr = average_daily_range(daily, ADR_DAYS)
                if adr is None:
                    log.warning("%s: only %d daily bars; minimum sizing stop off for today",
                                symbol, 0 if daily is None else len(daily))
            except Exception as exc:      # noqa: BLE001 — a history hiccup must not block entries
                log.warning("%s: daily bars unavailable (%s); minimum sizing stop off for today",
                            symbol, exc)
            self._adr[symbol] = (day, adr)
            hit = self._adr[symbol]
        return self.min_stop_k * hit[1] if hit[1] else 0.0

    def close_everything(self, reason: str) -> int:
        n = 0
        for p in self.market.positions():
            try:
                pnl = self.market.close(p, f"ms {reason}")
                n += 1
                self._emit("close", magic=p.magic, ticket=p.ticket, reason=reason, pnl=pnl)
                log.info("closed ticket %s (%s %s %.2f) reason=%s pnl=%.2f",
                         p.ticket, p.symbol, p.side, p.lots, reason, pnl)
            except Exception as exc:      # noqa: BLE001 — keep closing the rest
                log.error("close %s failed: %s", p.ticket, exc)
                self.alert(f"⚠️ could not close ticket {p.ticket} ({p.symbol}): {exc}")
        try:
            self.market.cancel_pending()
        except Exception as exc:          # noqa: BLE001
            log.error("cancel_pending failed: %s", exc)
        for st in self.states.values():
            st.clear()
        return n

    # ---------------------------------------------------------------- poll
    def poll(self) -> list[dict]:
        """One pass: guard, then every symbol/timeframe that has a new closed
        bar. Returns the events produced in this pass."""
        start = len(self.events)
        self.check_guard()
        for key, group in self.keys.items():
            group = [s for s in group if s.idx not in self.disabled]
            if not group:
                continue
            t = self.latest_closed(*key)
            if t is None or t == self.last_bar.get(key):
                continue
            window = self.fetch_window(*key)
            if pd.Timestamp(window["time"].iloc[-1]) != t:
                log.warning("%s %s: window end %s != latest %s; retry next poll",
                            key[0], key[1], window["time"].iloc[-1], t)
                continue
            for spec in group:
                try:
                    self.on_bar(spec, window)
                except Exception as exc:    # noqa: BLE001 — one strategy must not stop the rest
                    log.exception("%s failed on bar %s", spec.name, t)
                    self.alert(f"⚠️ {spec.name} error on bar {t}: {exc}")
            self.last_bar[key] = t
            self.save_state()
        return self.events[start:]

    # ---------------------------------------------------------------- per bar
    def _signals(self, spec: StrategySpec, window: pd.DataFrame) -> list:
        t = pd.Timestamp(window["time"].iloc[-1])
        hit = self._sig_cache.get(spec.idx)
        if hit is not None and hit[0] == t:
            return hit[1]
        sig = spec.build(window)
        self._sig_cache[spec.idx] = (t, sig)
        return sig

    def _live_pos(self, spec: StrategySpec) -> LivePos | None:
        for p in self.market.positions():
            if p.magic == spec.magic:
                return p
        return None

    def _sync(self, spec: StrategySpec, st: StratState, window: pd.DataFrame, sig: list):
        """Reconcile our state with the broker's positions for this magic."""
        live = self._live_pos(spec)
        if st.open and live is None:
            # closed by the broker (stop / target) since we last looked
            self._emit("close", magic=spec.magic, ticket=st.ticket, reason="broker",
                       strategy=spec.name)
            log.info("%s | ticket %s closed by the broker (sl/tp)", spec.name, st.ticket)
            st.clear()
        elif live is not None and (not st.open or st.ticket != live.ticket):
            # adopted after a restart: rebuild what we can from the entry bar's signal
            tf_min = TF_MINUTES[spec.tf]
            opened = pd.Timestamp(live.open_time)
            bar_open = opened.floor(f"{tf_min}min") - pd.Timedelta(minutes=tf_min)
            times = window["time"].to_numpy()
            k = int(np.searchsorted(times, np.datetime64(bar_open)))
            ent = sig[k] if 0 <= k < len(sig) and times[k] == np.datetime64(bar_open) else None
            st.ticket, st.side, st.entry, st.lots = live.ticket, live.side, live.entry, live.lots
            st.sl = st.sl0 = live.sl
            st.tp = live.tp or None
            st.entry_bar = str(bar_open)
            if ent is not None and ent.side == live.side:
                st.sl0 = float(ent.sl)
                st.max_hold, st.exit_hour, st.meta = ent.max_hold, ent.exit_hour, dict(ent.meta)
            else:
                st.max_hold = st.exit_hour = None
                log.warning("%s | adopted ticket %s but found no matching entry signal at %s; "
                            "time exits/manage unavailable for it", spec.name, live.ticket, bar_open)
            log.info("%s | adopted open ticket %s (%s %.2f @ %.5f)", spec.name, live.ticket,
                     live.side, live.lots, live.entry)
        elif live is not None:
            st.sl = live.sl if live.sl else st.sl      # the broker's stop is the truth
        return live

    def _pos_dict(self, st: StratState, bar_idx: int) -> dict:
        d = dict(side=st.side, entry=st.entry, sl=st.sl, sl0=st.sl0, tp=st.tp, lots=st.lots,
                 bar=bar_idx, max_hold=st.max_hold, exit_hour=st.exit_hour, manage=None,
                 risk_usd=st.risk_usd, meta=dict(st.meta))
        d.update(st.extra)
        return d

    def on_bar(self, spec: StrategySpec, window: pd.DataFrame) -> None:
        st = self.states[spec.idx]
        sig = self._signals(spec, window)
        i = len(window) - 1
        bar_t = pd.Timestamp(window["time"].iloc[i])
        close = float(window["close"].iloc[i])
        hour = int(bar_t.hour)
        live = self._sync(spec, st, window, sig)

        # ---- 2/3. time exits and manage, mirroring harness.simulate's order
        if st.open and live is not None:
            times = window["time"].to_numpy()
            k = int(np.searchsorted(times, np.datetime64(pd.Timestamp(st.entry_bar))))
            have_k = 0 <= k < len(times) and times[k] == np.datetime64(pd.Timestamp(st.entry_bar))
            bars_held = (i - k) if have_k else None
            timed = (st.max_hold is not None and bars_held is not None and bars_held >= st.max_hold) or \
                    (st.exit_hour is not None and hour == st.exit_hour and (bars_held or 0) > 0)
            if timed:
                self._close(spec, st, live, "time")
                live = None
            else:
                ent = sig[k] if have_k else None
                if ent is not None and ent.manage is not None and ent.side == st.side:
                    pos = self._pos_dict(st, k)
                    act = ent.manage(window, i, pos)
                    st.extra = {kk: vv for kk, vv in pos.items() if kk not in MANAGE_KEYS}
                    if act == "close":
                        self._close(spec, st, live, "manage")
                        live = None
                    elif act is not None:
                        new_sl = float(act)
                        if abs(new_sl - st.sl) > 1e-12:
                            self.market.modify(live, new_sl, st.tp or 0.0)
                            log.info("%s | stop %.5f -> %.5f (manage)", spec.name, st.sl, new_sl)
                            self._emit("modify", magic=spec.magic, sl=new_sl, strategy=spec.name)
                            st.sl = new_sl

        # ---- 4/5. the latest bar's signal
        entry = sig[i]
        if entry is None:
            return
        if st.open and live is not None and entry.side != st.side:
            self._close(spec, st, live, "flip")
            live = None
        if st.open:
            return
        allowed, why = self.guard.may_open()
        if not allowed:
            log.info("%s | %s signal at %s skipped: %s", spec.name, entry.side, bar_t, why)
            self._emit("skipped", magic=spec.magic, reason=why, strategy=spec.name, time=bar_t)
            return
        spread_pts = float(window["spread"].iloc[i]) if "spread" in window else 0.0
        conv = float(window["conv"].iloc[i])
        factor = self.guard.size_factor
        sz = size_trade(spec.symbol, entry.side, close, float(entry.sl), entry.tp, spread_pts,
                        conv, spec.risk * factor, self.spread_mult,
                        min_stop_dist=self.min_stop_dist(spec.symbol))
        if sz is None:
            log.info("%s | %s signal at %s skipped: stop %.5f cannot be funded at %.2f%% risk",
                     spec.name, entry.side, bar_t, entry.sl, spec.risk * 100)
            self._emit("skipped", magic=spec.magic, reason="unfundable", strategy=spec.name, time=bar_t)
            return
        pos = self.market.open(self.broker_symbol(spec.symbol), entry.side, sz["lots"],
                               float(entry.sl), float(entry.tp) if entry.tp is not None else 0.0,
                               spec.magic, f"ms{spec.idx}")
        st.ticket, st.side, st.entry, st.lots = pos.ticket, entry.side, pos.entry, sz["lots"]
        st.sl = st.sl0 = float(entry.sl)
        st.tp = float(entry.tp) if entry.tp is not None else None
        st.entry_bar = str(bar_t)
        st.max_hold, st.exit_hour = entry.max_hold, entry.exit_hour
        st.risk_usd, st.meta, st.extra = sz["risk_usd"], dict(entry.meta), {}
        notes = []
        if factor != 1.0:
            notes.append(f"size x{factor:g} (equity below {self.guard.scale_low:.0f})")
        if sz["resized"]:
            notes.append(f"min sizing stop: stop {sz['stop_dist']:.5g} < {sz['size_dist']:.5g} "
                         f"({self.min_stop_k:g} x ADR{ADR_DAYS}), lots reduced")
            log.info("%s | RESIZED: stop distance %.5g, sizing distance %.5g, lots %.2f",
                     spec.name, sz["stop_dist"], sz["size_dist"], sz["lots"])
            self._emit("resized", magic=spec.magic, strategy=spec.name, time=bar_t,
                       stop_dist=sz["stop_dist"], size_dist=sz["size_dist"], lots=sz["lots"])
        log.info("%s | OPEN %s %.2f @ %.5f sl %.5f tp %s (bar %s, risk $%.0f)%s", spec.name,
                 entry.side, sz["lots"], pos.entry, entry.sl, entry.tp, bar_t, sz["risk_usd"],
                 (" | " + "; ".join(notes)) if notes else "")
        self._emit("open", magic=spec.magic, strategy=spec.name, time=bar_t, side=entry.side,
                   lots=sz["lots"], sl=float(entry.sl), tp=entry.tp, entry=pos.entry,
                   ticket=pos.ticket, risk_usd=sz["risk_usd"], size_factor=factor,
                   resized=sz["resized"])
        tp_txt = f"TP {entry.tp:.5g}" if entry.tp is not None else "no TP"
        self.alert(f"\U0001F4C8 {spec.name}: {entry.side.upper()} {sz['lots']} "
                   f"{self.broker_symbol(spec.symbol)} @ {pos.entry:.5g} | SL {entry.sl:.5g} | "
                   f"{tp_txt} | risk ${sz['risk_usd']:.0f}" +
                   (" | " + "; ".join(notes) if notes else ""))

    def _close(self, spec: StrategySpec, st: StratState, live: LivePos, reason: str):
        pnl = self.market.close(live, f"ms{spec.idx} {reason}")
        log.info("%s | CLOSE %s %.2f ticket %s reason=%s pnl=%.2f", spec.name, st.side, st.lots,
                 live.ticket, reason, pnl)
        self._emit("close", magic=spec.magic, strategy=spec.name, ticket=live.ticket,
                   reason=reason, pnl=pnl)
        self.alert(f"{'✅' if pnl >= 0 else '❌'} {spec.name}: closed {st.side.upper()} {st.lots} "
                   f"({reason}) P/L {pnl:+.2f}")
        st.clear()

    # ---------------------------------------------------------------- startup
    def warmup(self, tries: int = 20, sleep: Callable[[float], None] = lambda s: None) -> None:
        """Fetch every window until the newest closed bar stops moving (MT5
        hands back stale history right after a cold start), then remember the
        latest closed bar per key so the first poll does not re-trade history."""
        for key in self.keys:
            if all(s.idx in self.disabled for s in self.keys[key]):
                continue
            prev = None
            log.info("warmup %s %s: checking the newest closed bar", key[0], key[1])
            for _ in range(tries):
                t = self.latest_closed(*key)
                if t is not None and t == prev:
                    break
                prev = t
                sleep(1.0)
            self.last_bar[key] = prev
            log.info("warmup %s %s: newest closed bar %s, fetching %d bars", key[0], key[1], prev, self.window)
            window = self.fetch_window(*key)
            if len(window) < self.window:
                log.warning("%s %s: only %d bars of history (wanted %d)", key[0], key[1],
                            len(window), self.window)
            for spec in self.keys[key]:
                if spec.idx in self.disabled:
                    continue
                sig = self._signals(spec, window)
                self._sync(spec, self.states[spec.idx], window, sig)
        self.save_state()

    def status_lines(self) -> list[str]:
        equity, balance = self.market.account()
        g = self.guard
        lines = [f"\U0001F4B0 equity {equity:.2f} | balance {balance:.2f} | day {g.day} start "
                 f"{g.day_start_balance:.2f} ({equity - g.day_start_balance:+.2f} today, stop at "
                 f"-{g.daily_stop:.0f}) | floor {g.floor:.0f}"]
        size_txt = (f"x{g.size_factor:g} (equity below {g.scale_low:.0f}; full size above {g.scale_high:.0f})"
                    if g.scaled else f"x1 (half below {g.scale_low:.0f})")
        lines.append(f"\U0001F4CF size {size_txt} | month {g.month} {g.mtd(equity):+.2f} vs "
                     f"-{g.monthly_stop:.0f} stop | month block {'ON' if g.month_blocked else 'off'}"
                     f" | min sizing stop {self.min_stop_k:g} x ADR{ADR_DAYS}")
        if g.blown:
            lines.append("\U0001F6D1 PERMANENT HALT active")
        elif g.blocked_day == g.day:
            lines.append("⏸️ daily stop active — no new entries today")
        elif g.month_blocked:
            lines.append("⏸️ monthly stop active — no new entries until next month")
        open_ = [(s, self.states[s.idx]) for s in self.specs if self.states[s.idx].open]
        if not open_:
            lines.append("flat (no open positions)")
        for s, st in open_:
            lines.append(f"• {s.name}: {st.side.upper()} {st.lots} @ {st.entry:.5g} sl {st.sl:.5g}"
                         f"{' tp ' + format(st.tp, '.5g') if st.tp else ''} since {st.entry_bar}")
        if self.disabled:
            lines.append(f"disabled: {len(self.disabled)} strategies (see startup message)")
        return lines
