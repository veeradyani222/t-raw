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

Drawdown scaling on top (docs/2026-10-25-overlay-lab-results.md, approved by
Veer): every NEW trade at SCALE_SIZE of its normal risk while equity (balance
+ floating) is below SCALE_LOW, full size again only once equity is above
SCALE_HIGH. Open trades are never touched by it.
"""
from __future__ import annotations

import importlib
import json
import logging
import math
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable, Protocol

import numpy as np
import pandas as pd

from research.prop import harness as H

log = logging.getLogger("trader")

ROOT = Path(__file__).resolve().parents[1]
MIX_PATH = ROOT / "docs" / "board" / "portfolio-lp300-66.json"     # default; env MULTI_MIX_PATH overrides
SYMBOL_MAP_PATH = ROOT / "config" / "symbols.json"
SKIP_PATH = ROOT / "config" / "live_skip.json"
STATE_PATH = ROOT / "logs" / "multi_state.json"

BASE_MAGIC = 500_000


def base_magic() -> int:
    """Magic base: env MULTI_BASE_MAGIC (default 500000). Give each mix its own
    range so a new mix never adopts positions another mix left open."""
    v = os.environ.get("MULTI_BASE_MAGIC", "").strip()
    return int(v) if v else BASE_MAGIC
WINDOW_BARS = 6000          # warmup: bos_lookback 2000 on M30, SMA1000 on H1, D1 200-bar filters
DAILY_STOP = 300.0          # $ floating loss on the server day -> close all, block the day
FLOOR = 9_300.0             # equity at/below this -> permanent halt (buffer above the $9,200 rail)
SCALE_LOW = 9_700.0         # equity below this -> new trades at SCALE_SIZE of their risk ...
SCALE_HIGH = 9_900.0        # ... until equity is back above this
SCALE_SIZE = 0.5
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
        return base_magic() + self.idx

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


def mix_path() -> Path:
    """The mix file to run: env MULTI_MIX_PATH (absolute, or relative to the
    repo root) when set, else MIX_PATH (the 66). Read at call time so .env
    (loaded by trader.config) is honoured."""
    env = os.environ.get("MULTI_MIX_PATH", "").strip()
    if not env:
        return MIX_PATH
    p = Path(env).expanduser()
    return p if p.is_absolute() else ROOT / p


def load_mix(path: Path | str | None = None) -> list[StrategySpec]:
    """Strategies of a mix file (default: mix_path()). Also applies the
    research cost patches (apply_research_patches) so sizing matches the judge
    that produced the mix, whichever path loads it (live, compare, tests)."""
    apply_research_patches()
    path = mix_path() if path is None else path
    data = json.loads(Path(path).read_text())
    cap = max_risk()
    return [StrategySpec(i, m["module"], m["fn"], dict(m["params"]), m["symbol"].upper(),
                         m["tf"].upper(), min(float(m["risk"]), cap))
            for i, m in enumerate(data["mix"])]


def max_risk() -> float:
    """Per-trade risk cap: env MULTI_MAX_RISK as a fraction (0.0275 = 2.75%).
    FundedNext funded accounts forbid any single trade risking more than 3% of
    the starting balance; a cap a little under keeps fills with slippage legal.
    Unset = no cap."""
    v = os.environ.get("MULTI_MAX_RISK", "").strip()
    return float(v) if v else float("inf")


def load_symbol_map(path: Path | str = SYMBOL_MAP_PATH, server: str | None = None) -> dict[str, str]:
    """research symbol -> broker symbol. Missing names map to themselves.

    config/symbols.json: "map" applies to every broker; "servers" holds
    per-server overrides keyed by a prefix of the MT5 server name
    ("ICMarketsSC" matches ICMarketsSC-Demo and ICMarketsSC-Live). Keys
    starting with "_" are comments."""
    p = Path(path)
    if not p.exists():
        return {}
    data = json.loads(p.read_text())
    out = {k.upper(): v for k, v in data.get("map", {}).items() if not k.startswith("_")}
    if server:
        srv = server.lower()
        for key, section in data.get("servers", {}).items():
            if key.startswith("_"):
                continue
            if srv.startswith(key.lower()):
                out.update({k.upper(): v for k, v in section.items() if not k.startswith("_")})
    return out


def load_skip_list(path: Path | str = SKIP_PATH) -> list[dict]:
    """config/live_skip.json: strategies the live runner must never trade,
    each with module, fn, optional symbol / tf and a reason (see
    docs/2026-10-31-round3-live-readiness.md). Missing file = nothing skipped."""
    p = Path(path)
    if not p.exists():
        return []
    data = json.loads(p.read_text())
    return [e for e in data.get("skip", []) if not str(e.get("module", "")).startswith("_")]


def skip_reasons(specs: list[StrategySpec], skip: list[dict]) -> dict[int, str]:
    """idx -> reason for every spec matched by an entry of the skip list.
    An entry matches on module + fn, and on symbol / tf when it names them.
    One log line per skipped strategy: never a silent drop."""
    out: dict[int, str] = {}
    for s in specs:
        for e in skip:
            if e.get("module") != s.module or e.get("fn") != s.fn:
                continue
            if e.get("symbol") and str(e["symbol"]).upper() != s.symbol:
                continue
            if e.get("tf") and str(e["tf"]).upper() != s.tf:
                continue
            reason = "skip list: " + str(e.get("reason", "no reason given"))
            out[s.idx] = reason
            log.warning("%s SKIPPED (%s)", s.name, reason)
            break
    return out


def conv_symbols(specs: list[StrategySpec]) -> dict[str, list[str]]:
    """conversion pair -> research symbols that need its bars (quote-only use)."""
    out: dict[str, list[str]] = {}
    for sym in sorted({s.symbol for s in specs}):
        pair = conv_pair_for(sym)
        if pair is not None and pair[0] != sym:
            out.setdefault(pair[0], []).append(sym)
    return out


# --------------------------------------------------------------------------- #
# Research cost patches - the judge (research/search3/portfolio/core3.py)      #
# --------------------------------------------------------------------------- #
CRYPTO = {"BTCUSD", "ETHUSD", "LTCUSD", "XRPUSD", "SOLUSD", "ADAUSD", "BNBUSD", "DOTUSD"}
_patched = False


def apply_research_patches() -> None:
    """Teach research.prop.harness the round-3 symbols exactly as the round-3
    judge did (spread floors, commission-free index/energy/crypto sets, pip
    sizes) so size_trade() reserves the same costs the research sized with.
    Idempotent. Only harness tables are touched; nothing reads data/."""
    global _patched
    if _patched:
        return
    from research.search3.asia_indices import strategies as asia       # patches at import too
    asia.patch_harness()                                               # JPN225/HK50/CHINA50/AUS200
    from research.search3.exotics import strategies as exo
    exo.patch_harness()                                                # exotic spread floors
    import research.search3.europe_indices.common                      # noqa: F401  UK100/FRA40/... (import)
    import research.search3.oil_gas.common                             # noqa: F401  energies (import)
    import research.search3.us_indices.strategies                      # noqa: F401  US2000 (import)
    from research.search3.commodity_fx import run as cfx
    H.SPREAD_FLOOR.update(cfx.EXTRA_FLOOR)                             # cross floors only (no conv patch)
    from research.search3.crypto import costs
    sim_before = H.simulate
    costs.apply()                                                      # crypto floors/pips, no commission
    H.simulate = sim_before                                            # live never calls simulate; keep the judge's
    H.SPREAD_FLOOR.update({"XPTUSD": 2.0, "XPDUSD": 3.0})
    H.INDICES.update({"XPTUSD", "XPDUSD"})
    _pip = H._pip

    def pip(symbol):
        return 0.1 if symbol in ("XPTUSD", "XPDUSD") else _pip(symbol)
    H._pip = pip
    _patched = True


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
               spread_mult: float = 1.0, max_lots: float | None = None) -> dict | None:
    """Replicates harness.simulate's entry block. Returns None when the harness
    would have skipped the signal (invalid levels or stop too wide to fund),
    else dict(lots, entry_est, loss_per_lot, risk_usd). max_lots defaults to
    the judge's: 50 everywhere, uncapped for crypto (XRPUSD's lot minimum is
    100, so the 50 cap would make every XRPUSD signal unfundable)."""
    if max_lots is None:
        max_lots = 1e9 if symbol in CRYPTO else 50.0
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
    loss_per_lot = (abs(entry - sl) + slip) * contract * conv + comm
    if loss_per_lot <= 0:
        return None
    risk_usd = risk * H.BASELINE
    lots = math.floor(risk_usd / loss_per_lot / vstep) * vstep
    lots = min(round(lots, 2), max_lots)
    if lots < vmin:
        return None
    return dict(lots=lots, entry_est=entry, loss_per_lot=loss_per_lot,
                risk_usd=lots * loss_per_lot)


# profit currency -> (pair whose close converts it to USD, invert). The round-3
# groups add AUD (AUS200), NOK (EURNOK), MXN (USDMXN), CNH (USDCNH), HKD (HK50),
# NZD; the research converted with the same pairs (asia/exotics patch_harness).
CONV_PAIR = {"JPY": ("USDJPY", True), "CHF": ("USDCHF", True), "CAD": ("USDCAD", True),
             "GBP": ("GBPUSD", False), "EUR": ("EURUSD", False),
             "AUD": ("AUDUSD", False), "NZD": ("NZDUSD", False),
             "NOK": ("USDNOK", True), "SEK": ("USDSEK", True), "MXN": ("USDMXN", True),
             "CNH": ("USDCNH", True), "ZAR": ("USDZAR", True), "SGD": ("USDSGD", True),
             "PLN": ("USDPLN", True), "HKD": ("USDHKD", True)}


def conv_pair_for(symbol: str) -> tuple[str, bool] | None:
    """(pair, invert) whose close converts this symbol's P&L to USD; None = USD.
    Raises KeyError naming the currency when no conversion pair is known."""
    spec = research_spec(symbol)
    ccy = spec.get("profit_ccy") or ("JPY" if symbol.endswith("JPY") else "USD")
    if ccy == "USD":
        return None
    if ccy not in CONV_PAIR:
        raise KeyError(f"{symbol}: no conversion pair for profit currency {ccy} (add it to CONV_PAIR)")
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

    def update(self, now: pd.Timestamp, equity: float, balance: float,
               day_start_balance: float | None = None) -> list[str]:
        """Returns events: 'new_day', 'daily_stop', 'blown', 'scale_on',
        'scale_off' (each at most once per state change). `day_start_balance`
        lets the caller supply the true 00:00 balance on a mid-day (re)start."""
        events = []
        now = pd.Timestamp(now)
        day = str(now.normalize().date())
        if day != self.day:
            self.day = day
            self.day_start_balance = balance if day_start_balance is None else day_start_balance
            events.append("new_day")
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
        return events

    @property
    def blocked(self) -> bool:
        return self.blown or self.blocked_day == self.day

    @property
    def size_factor(self) -> float:
        return self.scale_size if self.scaled else 1.0

    def may_open(self) -> tuple[bool, str]:
        if self.blown:
            return False, f"permanent halt: equity reached {self.floor:.0f}"
        if self.blocked_day == self.day:
            return False, f"daily stop hit ({self.daily_stop:.0f}) — no entries until next server day"
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
                 disabled: dict[int, str] | None = None, spread_mult: float = 1.0):
        self.market = market
        self.specs = specs
        self.symbol_map = symbol_map
        self.alert = alert
        self.state_path = Path(state_path) if state_path else None
        self.window = window
        self.guard = guard or AccountGuard()
        self.disabled = dict(disabled or {})       # idx -> reason (never traded)
        self.spread_mult = spread_mult
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
            pair_df = df if pair[0] == symbol else \
                self.market.rates(self.broker_symbol(pair[0]), tf, self.window)
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
        day_start = None
        if str(now.normalize().date()) != self.guard.day:
            # true 00:00-server balance = balance now minus what closed today
            try:
                day_start = balance - self.market.realized_since(now.normalize())
            except Exception as exc:      # noqa: BLE001 — a history hiccup must not stop the guard
                log.warning("realized_since failed (%s); anchoring day on current balance", exc)
        events = self.guard.update(now, equity, balance, day_start)
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
        self.save_state()
        return events

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
                        conv, spec.risk * factor, self.spread_mult)
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
        log.info("%s | OPEN %s %.2f @ %.5f sl %.5f tp %s (bar %s, risk $%.0f)%s", spec.name,
                 entry.side, sz["lots"], pos.entry, entry.sl, entry.tp, bar_t, sz["risk_usd"],
                 (" | " + "; ".join(notes)) if notes else "")
        self._emit("open", magic=spec.magic, strategy=spec.name, time=bar_t, side=entry.side,
                   lots=sz["lots"], sl=float(entry.sl), tp=entry.tp, entry=pos.entry,
                   ticket=pos.ticket, risk_usd=sz["risk_usd"], size_factor=factor)
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
        lines.append(f"\U0001F4CF size {size_txt}")
        if g.blown:
            lines.append("\U0001F6D1 PERMANENT HALT active")
        elif g.blocked_day == g.day:
            lines.append("⏸️ daily stop active — no new entries today")
        open_ = [(s, self.states[s.idx]) for s in self.specs if self.states[s.idx].open]
        if not open_:
            lines.append("flat (no open positions)")
        for s, st in open_:
            lines.append(f"• {s.name}: {st.side.upper()} {st.lots} @ {st.entry:.5g} sl {st.sl:.5g}"
                         f"{' tp ' + format(st.tp, '.5g') if st.tp else ''} since {st.entry_bar}")
        if self.disabled:
            lines.append(f"disabled: {len(self.disabled)} strategies (see startup message)")
        return lines
