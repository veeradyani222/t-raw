"""The only module that imports MetaTrader5. Implements the Broker interface
against the real terminal."""
import logging

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


def connect(cfg: Config) -> None:
    """Attach to the running/installed terminal. Uses .env credentials if set,
    otherwise whatever account the terminal is logged into."""
    kwargs = {}
    if cfg.mt5_login:
        kwargs = dict(login=cfg.mt5_login, password=cfg.mt5_password,
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

    def realized_pnl(self, ticket: int) -> float:
        """Net closed profit for a position (profit + swap + commission), read
        from the deal history — used to report what a trade actually made."""
        deals = mt5.history_deals_get(position=ticket) or []
        return sum(d.profit + d.swap + d.commission
                   for d in deals if d.entry == mt5.DEAL_ENTRY_OUT)

    def open_positions(self) -> list[Position]:
        raw = mt5.positions_get(symbol=self.cfg.symbol) or []
        return [
            Position(
                side="long" if p.type == mt5.POSITION_TYPE_BUY else "short",
                lots=p.volume, entry_price=p.price_open,
                sl=p.sl, tp=p.tp, ticket=p.ticket,
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
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            raise MT5Error(f"order_send failed: {getattr(result, 'retcode', None)} "
                           f"{getattr(result, 'comment', '')} {mt5.last_error()}")
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
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        result = mt5.order_send(request)
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            raise MT5Error(f"close failed: {getattr(result, 'retcode', None)} "
                           f"{mt5.last_error()}")
        deals = mt5.history_deals_get(position=position.ticket) or []
        return sum(d.profit for d in deals if d.entry == mt5.DEAL_ENTRY_OUT)
