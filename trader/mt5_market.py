"""MetaTrader5 adapter for the multi-strategy runner (trader/multi.py): the
only other module besides broker_mt5 that imports MetaTrader5.

Positions are tracked by MAGIC (one per strategy), several per symbol — the
account must be a hedging account, which connect() verifies. Bars come back
as the research harness expects them (open time in broker time, spread in
points). Prices sent to the broker are rounded to the symbol's digits.
"""
from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone

import MetaTrader5 as mt5
import pandas as pd

from .broker_mt5 import TIMEFRAMES, MT5Error, _send_order, assert_demo
from .config import Config
from .multi import LivePos, balance_from_deals, conv_pair_for, research_spec

log = logging.getLogger("trader")

DEVIATION = 50          # points of slippage tolerance on market orders
COLS = ["time", "open", "high", "low", "close", "tick_volume", "spread"]


def _ts(t) -> int:
    """Broker-time naive Timestamp -> the integer MT5 wants (same basis)."""
    return int(pd.Timestamp(t).timestamp())


HISTORY_FLOOR = datetime(2000, 1, 1)


def _history_dt(t) -> datetime:
    """A naive datetime MT5's history calls accept: broker-time basis, no
    tzinfo, clamped to 2000-01-01 .. now + 1 day. The C extension returns
    'a result with an exception set' for dates before 1970, far-future
    dates or tz-aware datetimes."""
    dt = pd.Timestamp(t)
    if dt.tzinfo is not None:
        dt = dt.tz_localize(None)
    dt = dt.to_pydatetime().replace(microsecond=0)
    hi = datetime.now().replace(microsecond=0) + timedelta(days=1)
    return min(max(dt, HISTORY_FLOOR), hi)


def connect(cfg: Config) -> dict:
    """Initialise the bridge, enforce demo-only + hedging + algo-trading-on.
    Returns a small dict about the account for the startup message."""
    kwargs = {}
    if cfg.mt5_path:
        kwargs["path"] = cfg.mt5_path
    if cfg.mt5_login:
        kwargs.update(login=cfg.mt5_login, password=cfg.mt5_password, server=cfg.mt5_server)
    if not mt5.initialize(**kwargs):
        raise MT5Error(f"mt5.initialize failed: {mt5.last_error()}")
    info = mt5.account_info()
    if info is None:
        raise MT5Error(f"no account: {mt5.last_error()}")
    assert_demo(info)
    if info.margin_mode != mt5.ACCOUNT_MARGIN_MODE_RETAIL_HEDGING:
        raise MT5Error(f"account {info.login} is a NETTING account (margin_mode {info.margin_mode}); "
                       "several strategies cannot hold the same symbol at once. Use a hedging account.")
    term = mt5.terminal_info()
    if term is None or not term.connected:
        raise MT5Error("terminal is NOT connected to the trade server")
    if not term.trade_allowed:
        raise MT5Error("Algo Trading is OFF in the terminal (every order would be rejected, retcode 10027). "
                       "Click the 'Algo Trading' toolbar button, or start the terminal via ops/run_bot.ps1.")
    if not account_ok(info):
        raise MT5Error(f"account {info.login}: trading or EA trading disabled server-side")
    log.info("connected: account %s (%s), balance %.2f %s, hedging, algo trading on",
             info.login, info.server, info.balance, info.currency)
    return dict(login=info.login, server=info.server, balance=info.balance, equity=info.equity,
                currency=info.currency, company=info.company)


def account_ok(info) -> bool:
    return bool(info.trade_allowed and info.trade_expert)


def shutdown() -> None:
    mt5.shutdown()


# --------------------------------------------------------------------------- #
# Pre-flight                                                                   #
# --------------------------------------------------------------------------- #
def _usd_per_unit(ccy: str) -> float | None:
    """Current USD value of 1 unit of `ccy` from the conversion pair's tick."""
    if ccy == "USD":
        return 1.0
    pair, invert = {"JPY": ("USDJPY", True), "CHF": ("USDCHF", True), "CAD": ("USDCAD", True),
                    "GBP": ("GBPUSD", False), "EUR": ("EURUSD", False)}.get(ccy, (None, None))
    if pair is None:
        return None
    mt5.symbol_select(pair, True)
    t = mt5.symbol_info_tick(pair)
    if t is None or not t.bid:
        return None
    return 1.0 / t.bid if invert else t.bid


def preflight(research_symbols: list[str], symbol_map: dict[str, str]) -> tuple[list[dict], dict[str, str]]:
    """One row per research symbol; `problems` maps research symbol -> reason
    for anything that must not trade: missing, trade disabled, or a contract /
    point / lot step / profit currency that differs from what the research
    assumed (data/search/symbol_specs.json), or a tick value that does not
    match contract x tick size x FX rate within 5%."""
    rows, problems = [], {}
    for rs in sorted(set(research_symbols)):
        bs = symbol_map.get(rs, rs)
        want = research_spec(rs)
        row = dict(research=rs, broker=bs, found=False, tradable=False, contract=None, point=None,
                   vol_min=None, vol_step=None, ccy=None, tick_value=None, tick_expected=None,
                   spread=None, problem="")
        mt5.symbol_select(bs, True)
        si = mt5.symbol_info(bs)
        if si is None:
            row["problem"] = "not found on this broker"
            problems[rs] = row["problem"]
            rows.append(row)
            continue
        row.update(found=True, tradable=si.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL,
                   contract=si.trade_contract_size, point=si.point, vol_min=si.volume_min,
                   vol_step=si.volume_step, ccy=si.currency_profit, tick_value=si.trade_tick_value,
                   spread=si.spread)
        issues = []
        if not row["tradable"]:
            issues.append(f"trade disabled (trade_mode {si.trade_mode})")
        checks = [("contract", float(want.get("contract", si.trade_contract_size)), si.trade_contract_size),
                  ("point", float(want.get("point", si.point)), si.point),
                  ("vol_min", float(want.get("vol_min", si.volume_min)), si.volume_min),
                  ("vol_step", float(want.get("vol_step", si.volume_step)), si.volume_step)]
        for name, w, have in checks:
            if abs(w - have) > 1e-9 * max(1.0, abs(w)):
                issues.append(f"{name} {have} != research {w}")
        wccy = want.get("profit_ccy") or ("JPY" if rs.endswith("JPY") else "USD")
        if si.currency_profit != wccy:
            issues.append(f"profit currency {si.currency_profit} != research {wccy}")
        # P&L per lot as the BROKER computes it vs contract x move x FX rate (what
        # the research sizing assumes). trade_tick_value itself is unreliable on
        # some servers (MetaQuotes-Demo reports 0.1 for gold while a 1-lot $1
        # move really is $100), so ask order_calc_profit instead.
        rate = _usd_per_unit(si.currency_profit)
        tick = mt5.symbol_info_tick(bs)
        if rate is not None and tick is not None and tick.ask and si.trade_tick_size:
            move = si.trade_tick_size * 100
            calc = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, bs, 1.0, tick.ask, tick.ask + move)
            exp = si.trade_contract_size * move * rate
            row["tick_value"] = calc
            row["tick_expected"] = exp
            if calc is None:
                issues.append("order_calc_profit failed")
            elif abs(calc - exp) > 0.05 * exp:
                issues.append(f"P&L per lot per {move:g} move: broker {calc:.4g} != research {exp:.4g}")
        row["problem"] = "; ".join(issues)
        if issues:
            problems[rs] = row["problem"]
        rows.append(row)
    return rows, problems


def preflight_table(rows: list[dict]) -> str:
    hdr = f"{'research':<8} {'broker':<8}{'ok':<4}{'contract':>9}{'point':>8}{'vmin':>6}{'step':>6}{'ccy':>5}{'$/lot':>9}{'expect':>9}{'spr':>5}  problem"
    out = [hdr, "-" * len(hdr)]
    for r in rows:
        ok = "YES" if r["found"] and not r["problem"] else "NO"
        f = lambda v, fmt: (format(v, fmt) if v is not None else "-")  # noqa: E731
        out.append(f"{r['research']:<8} {r['broker']:<8}{ok:<4}{f(r['contract'], '9.0f')}{f(r['point'], '8.5g')}"
                   f"{f(r['vol_min'], '6.2f')}{f(r['vol_step'], '6.2f')}{str(r['ccy'] or '-'):>5}"
                   f"{f(r['tick_value'], '9.4g')}{f(r['tick_expected'], '9.4g')}{f(r['spread'], '5d')}  {r['problem']}")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# The Market implementation                                                    #
# --------------------------------------------------------------------------- #
class MT5Market:
    def __init__(self, magic_lo: int = 0, magic_hi: int = 2**31):
        self.magic_lo, self.magic_hi = magic_lo, magic_hi
        self._digits: dict[str, int] = {}

    # ---- bars
    @staticmethod
    def _frame(rates) -> pd.DataFrame:
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df[COLS]

    def rates(self, symbol: str, tf: str, count: int) -> pd.DataFrame:
        r = mt5.copy_rates_from_pos(symbol, TIMEFRAMES[tf], 1, count)    # pos 1 = last CLOSED bar
        if r is None:
            raise MT5Error(f"copy_rates_from_pos({symbol},{tf}) failed: {mt5.last_error()}")
        return self._frame(r)

    def rates_until(self, symbol: str, tf: str, end: pd.Timestamp, count: int) -> pd.DataFrame:
        """`count` bars whose OPEN time is <= end (broker time)."""
        r = mt5.copy_rates_from(symbol, TIMEFRAMES[tf], _ts(end), count)
        if r is None:
            raise MT5Error(f"copy_rates_from({symbol},{tf}) failed: {mt5.last_error()}")
        return self._frame(r)

    def tick_time(self, symbol: str) -> pd.Timestamp | None:
        t = mt5.symbol_info_tick(symbol)
        if t is None or t.time <= 0:
            return None
        return pd.to_datetime(t.time, unit="s")

    # ---- account
    def account(self) -> tuple[float, float]:
        info = mt5.account_info()
        if info is None:
            raise MT5Error(f"account_info failed: {mt5.last_error()}")
        return float(info.equity), float(info.balance)

    def positions(self) -> list[LivePos]:
        raw = mt5.positions_get()
        if raw is None:
            raise MT5Error(f"positions_get failed: {mt5.last_error()}")
        return [LivePos(p.ticket, p.symbol, p.magic,
                        "long" if p.type == mt5.POSITION_TYPE_BUY else "short",
                        p.volume, p.price_open, p.sl, p.tp, pd.to_datetime(p.time, unit="s"), p.profit)
                for p in raw]

    # ---- orders
    def _round(self, symbol: str, price: float) -> float:
        if not price:
            return 0.0
        d = self._digits.get(symbol)
        if d is None:
            si = mt5.symbol_info(symbol)
            d = si.digits if si else 5
            self._digits[symbol] = d
        return round(float(price), d)

    def open(self, symbol, side, lots, sl, tp, magic, comment) -> LivePos:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            raise MT5Error(f"no tick for {symbol}: {mt5.last_error()}")
        long_ = side == "long"
        req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": symbol, "volume": float(lots),
               "type": mt5.ORDER_TYPE_BUY if long_ else mt5.ORDER_TYPE_SELL,
               "price": tick.ask if long_ else tick.bid,
               "sl": self._round(symbol, sl), "tp": self._round(symbol, tp),
               "deviation": DEVIATION, "magic": int(magic), "comment": comment[:31],
               "type_time": mt5.ORDER_TIME_GTC}
        res = _send_order(req, symbol)
        ticket = res.order                   # hedging: position id == opening order ticket
        for p in mt5.positions_get(ticket=ticket) or ():
            return LivePos(p.ticket, symbol, magic, side, p.volume, p.price_open, p.sl, p.tp,
                           pd.to_datetime(p.time, unit="s"))
        return LivePos(ticket, symbol, magic, side, float(lots), res.price, req["sl"], req["tp"],
                       pd.to_datetime(tick.time, unit="s"))

    def close(self, pos: LivePos, comment: str) -> float:
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            raise MT5Error(f"no tick for {pos.symbol}: {mt5.last_error()}")
        closing_long = pos.side == "long"
        req = {"action": mt5.TRADE_ACTION_DEAL, "symbol": pos.symbol, "volume": float(pos.lots),
               "type": mt5.ORDER_TYPE_SELL if closing_long else mt5.ORDER_TYPE_BUY,
               "position": int(pos.ticket), "price": tick.bid if closing_long else tick.ask,
               "deviation": DEVIATION, "magic": int(pos.magic), "comment": comment[:31],
               "type_time": mt5.ORDER_TIME_GTC}
        _send_order(req, pos.symbol)
        return self.realized_pnl(pos.ticket)

    def realized_pnl(self, ticket: int) -> float:
        deals = mt5.history_deals_get(position=ticket) or []
        return float(sum(d.profit + d.swap + d.commission for d in deals))

    def modify(self, pos: LivePos, sl: float, tp: float) -> None:
        req = {"action": mt5.TRADE_ACTION_SLTP, "symbol": pos.symbol, "position": int(pos.ticket),
               "sl": self._round(pos.symbol, sl), "tp": self._round(pos.symbol, tp),
               "magic": int(pos.magic)}
        res = mt5.order_send(req)
        if res is None or res.retcode not in (mt5.TRADE_RETCODE_DONE, mt5.TRADE_RETCODE_NO_CHANGES):
            raise MT5Error(f"modify {pos.ticket} failed: {getattr(res, 'retcode', None)} "
                           f"{getattr(res, 'comment', '')} {mt5.last_error()}")

    def cancel_pending(self) -> int:
        n = 0
        for o in mt5.orders_get() or ():
            res = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket})
            if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
                n += 1
            else:
                log.error("cancel order %s failed: %s", o.ticket, mt5.last_error())
        return n

    # ---- history
    def deals_between(self, t0: pd.Timestamp, t1: pd.Timestamp) -> list:
        """Deals with t0 <= time < t1, both clamped to what MT5 accepts."""
        a, b = _history_dt(t0), _history_dt(t1)
        if b <= a:
            return []
        d = mt5.history_deals_get(a, b)
        if d is None:
            raise MT5Error(f"history_deals_get failed: {mt5.last_error()}")
        return list(d)

    def realized_since(self, t: pd.Timestamp) -> float:
        end = pd.Timestamp(t) + pd.Timedelta(days=2)
        return float(sum(d.profit + d.swap + d.commission for d in self.deals_between(t, end)
                         if d.type in (mt5.DEAL_TYPE_BUY, mt5.DEAL_TYPE_SELL)))

    def balance_at(self, t: pd.Timestamp) -> float:
        """Balance just before broker time t: every deal since the account was
        opened (deposits included) summed; for an account opened after t, the
        balance right after its first deposit. Anchors the monthly stop."""
        deals = self.deals_between(HISTORY_FLOOR, datetime.now() + timedelta(days=1))
        return balance_from_deals(deals, t)

    def symbol_spec(self, symbol: str) -> dict:
        si = mt5.symbol_info(symbol)
        if si is None:
            return {}
        return dict(digits=si.digits, point=si.point, contract=si.trade_contract_size,
                    vol_min=si.volume_min, vol_step=si.volume_step, vol_max=si.volume_max,
                    profit_ccy=si.currency_profit, tick_value=si.trade_tick_value,
                    tick_size=si.trade_tick_size,
                    trade_mode_ok=si.trade_mode == mt5.SYMBOL_TRADE_MODE_FULL)


def utc_now_broker(symbol: str = "EURUSD") -> pd.Timestamp | None:
    """Broker clock, from the freshest tick of a symbol that always streams."""
    return MT5Market().tick_time(symbol)
