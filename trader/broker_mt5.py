"""The only module that imports MetaTrader5. Implements the Broker interface
against the real terminal."""
import logging
import math
import time
from decimal import Decimal, ROUND_FLOOR

import MetaTrader5 as mt5
import pandas as pd

from .broker import Position
from .config import Config

log = logging.getLogger("trader")

TIMEFRAMES = {
    "M1": mt5.TIMEFRAME_M1, "M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15,
    "M30": mt5.TIMEFRAME_M30, "H1": mt5.TIMEFRAME_H1, "H4": mt5.TIMEFRAME_H4,
    "D1": mt5.TIMEFRAME_D1,
}


class MT5Error(RuntimeError):
    pass


def _filling_order() -> list[int]:
    """Order-filling modes to try, in preference order. Try IOC first (what gold
    fills with — keeps its behavior unchanged), fall back to FOK (which USDJPY
    needs on this demo — IOC there is rejected with retcode 10030), and keep
    RETURN as a final backstop. The SYMBOL_FILLING_* bitmask constants aren't
    exposed by this MT5 build, so we probe by trying rather than reading flags."""
    return [mt5.ORDER_FILLING_IOC, mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN]


def _send_order(request: dict, symbol: str):
    """order_send with automatic filling-mode fallback: on an INVALID_FILL
    (10030) rejection, retry the same order with the next filling mode. Any
    other failure is real and stops the retry."""
    result = None
    for fill in _filling_order():
        request["type_filling"] = fill
        result = mt5.order_send(request)
        if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
            return result
        if result is None or result.retcode != mt5.TRADE_RETCODE_INVALID_FILL:
            break        # a non-filling failure — don't keep retrying
    raise MT5Error(f"order_send failed: {getattr(result, 'retcode', None)} "
                   f"{getattr(result, 'comment', '')} {mt5.last_error()}")


def connect(cfg: Config) -> None:
    """Attach to the running/installed terminal. Uses .env credentials if set,
    otherwise whatever account the terminal is logged into."""
    kwargs = {}
    if cfg.mt5_path:
        kwargs["path"] = cfg.mt5_path
    if cfg.mt5_login:
        kwargs.update(login=cfg.mt5_login, password=cfg.mt5_password,
                      server=cfg.mt5_server)
    if not mt5.initialize(**kwargs):
        raise MT5Error(f"mt5.initialize failed: {mt5.last_error()}")
    info = mt5.account_info()
    if info is None:
        raise MT5Error(f"no account: {mt5.last_error()}")
    if not info.trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO:
        raise MT5Error(
            f"account {info.login} is NOT a demo account — refusing to trade. "
            "This guard is removed manually, on purpose, or not at all."
        )
    if not mt5.symbol_select(cfg.symbol, True):
        raise MT5Error(f"symbol_select({cfg.symbol}) failed: {mt5.last_error()}")
    log.info("connected: account %s (%s), balance %.2f %s",
             info.login, info.server, info.balance, info.currency)


def select_symbol(symbol: str) -> None:
    """Make a symbol tradable in the terminal (needed for every symbol the bot
    trades beyond the one connect() selected)."""
    if not mt5.symbol_select(symbol, True):
        raise MT5Error(f"symbol_select({symbol}) failed: {mt5.last_error()}")


def shutdown() -> None:
    mt5.shutdown()


class MT5Broker:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.timeframe = TIMEFRAMES[cfg.timeframe]

    def candles(self, count: int) -> pd.DataFrame:
        # Position 1 = most recent *closed* bar (0 is the forming bar).
        rates = mt5.copy_rates_from_pos(self.cfg.symbol, self.timeframe, 1, count)
        if rates is None:
            raise MT5Error(f"copy_rates failed: {mt5.last_error()}")
        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        return df[["time", "open", "high", "low", "close", "tick_volume"]]

    def equity(self) -> float:
        info = mt5.account_info()
        if info is None:
            raise MT5Error(f"account_info failed: {mt5.last_error()}")
        return info.equity

    def balance(self) -> float:
        info = mt5.account_info()
        if info is None:
            raise MT5Error(f"account_info failed: {mt5.last_error()}")
        return info.balance

    def market_time(self) -> pd.Timestamp:
        """Latest quote timestamp, in the same time basis as MT5 positions/bars."""
        tick = mt5.symbol_info_tick(self.cfg.symbol)
        if tick is None or tick.time <= 0:
            raise MT5Error(f"no market time: {mt5.last_error()}")
        return pd.to_datetime(tick.time, unit="s")

    def session_stop_price(self, sl: float) -> float:
        """Round a long stop outward to an executable broker price increment."""
        info = mt5.symbol_info(self.cfg.symbol)
        if info is None or not math.isfinite(info.trade_tick_size) or info.trade_tick_size <= 0:
            raise MT5Error("missing or invalid broker price increment")
        if not math.isfinite(sl) or sl <= 0:
            raise MT5Error("invalid session stop price")
        step = Decimal(str(info.trade_tick_size))
        return float((Decimal(str(sl)) / step).to_integral_value(rounding=ROUND_FLOOR) * step)

    def session_entry_lots(self, bar_time, sl: float, equity: float, *, entry_time=None) -> float:
        """Eligible long-session size, with converted stop loss and cost reserves.

        No fixed USD pip-value shortcut. History checks prevent re-entry after
        a restart/stop-out; an unavailable broker read never means 'flat'.
        """
        cfg = self.cfg
        tick = mt5.symbol_info_tick(cfg.symbol)
        if tick is None:
            raise MT5Error(f"no tick: {mt5.last_error()}")
        now = pd.to_datetime(tick.time, unit="s")
        closed_at = (pd.Timestamp(entry_time) if entry_time is not None
                     else pd.Timestamp(bar_time) + pd.Timedelta(hours=1))
        age = (now - closed_at).total_seconds()
        if not 0 <= age <= cfg.session_entry_window_seconds:
            return 0.0
        if not 0 <= time.time() - tick.time <= cfg.session_entry_window_seconds:
            return 0.0
        positions = mt5.positions_get()
        if positions is None:
            raise MT5Error(f"positions_get failed: {mt5.last_error()}")
        if positions:
            return 0.0
        deals = mt5.history_deals_get(int(now.normalize().timestamp()), int(now.timestamp()) + 1)
        if deals is None:
            raise MT5Error(f"history_deals_get failed: {mt5.last_error()}")
        if any(d.symbol == cfg.symbol and d.entry in (mt5.DEAL_ENTRY_IN, mt5.DEAL_ENTRY_INOUT)
               for d in deals):
            return 0.0
        if not all(math.isfinite(v) for v in (equity, sl, tick.ask, tick.bid)):
            return 0.0
        if equity <= 0 or sl <= 0 or tick.bid <= sl or tick.ask < tick.bid:
            return 0.0
        info = mt5.symbol_info(cfg.symbol)
        if info is None:
            raise MT5Error(f"symbol_info failed: {mt5.last_error()}")
        if not all(math.isfinite(v) and v > 0 for v in
                   (info.volume_min, info.volume_max, info.volume_step)):
            raise MT5Error("invalid broker volume limits")
        slip = cfg.session_slippage_pips * cfg.pip_size
        loss = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, cfg.symbol, 1.0,
                                     tick.ask + slip, sl - slip)
        if loss is None or not math.isfinite(loss) or loss >= 0:
            raise MT5Error(f"invalid stop-loss calculation: {mt5.last_error()}")
        risk_per_lot = -loss + cfg.session_commission_per_lot
        raw = min(equity * cfg.risk_per_trade / risk_per_lot,
                  cfg.max_lot, info.volume_max)
        step = Decimal(str(info.volume_step))
        lots = float((Decimal(str(raw)) / step).to_integral_value(rounding=ROUND_FLOOR) * step)
        return lots if lots >= max(cfg.min_lot, info.volume_min) else 0.0

    def realized_pnl(self, ticket: int) -> float:
        """Net closed profit for a position (profit + swap + commission), read
        from the deal history — used to report what a trade actually made."""
        deals = mt5.history_deals_get(position=ticket) or []
        return sum(d.profit + d.swap + d.commission
                   for d in deals if d.entry == mt5.DEAL_ENTRY_OUT)

    def open_positions(self) -> list[Position]:
        raw = mt5.positions_get(symbol=self.cfg.symbol)
        if raw is None:
            raise MT5Error(f"positions_get failed: {mt5.last_error()}")
        return [
            Position(
                side="long" if p.type == mt5.POSITION_TYPE_BUY else "short",
                lots=p.volume, entry_price=p.price_open,
                sl=p.sl, tp=p.tp, ticket=p.ticket,
                open_time=pd.to_datetime(p.time, unit="s"),
            )
            for p in raw
        ]

    def open_position(self, side: str, lots: float, sl: float, tp: float) -> Position:
        tick = mt5.symbol_info_tick(self.cfg.symbol)
        if tick is None:
            raise MT5Error(f"no tick: {mt5.last_error()}")
        is_long = side == "long"
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.cfg.symbol,
            "volume": lots,
            "type": mt5.ORDER_TYPE_BUY if is_long else mt5.ORDER_TYPE_SELL,
            "price": tick.ask if is_long else tick.bid,
            "sl": sl,
            "tp": tp,
            "deviation": 10,
            "magic": 424242,
            "comment": "mt5-trader",
            "type_time": mt5.ORDER_TIME_GTC,
        }
        result = _send_order(request, self.cfg.symbol)
        return Position(side, lots, result.price, sl, tp, ticket=result.order)

    def close_position(self, position: Position) -> float:
        tick = mt5.symbol_info_tick(self.cfg.symbol)
        if tick is None:
            raise MT5Error(f"no tick: {mt5.last_error()}")
        closing_long = position.side == "long"
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": self.cfg.symbol,
            "volume": position.lots,
            "type": mt5.ORDER_TYPE_SELL if closing_long else mt5.ORDER_TYPE_BUY,
            "position": position.ticket,
            "price": tick.bid if closing_long else tick.ask,
            "deviation": 10,
            "magic": 424242,
            "comment": "mt5-trader close",
            "type_time": mt5.ORDER_TIME_GTC,
        }
        _send_order(request, self.cfg.symbol)   # raises on failure
        deals = mt5.history_deals_get(position=position.ticket) or []
        return sum(d.profit for d in deals if d.entry == mt5.DEAL_ENTRY_OUT)
