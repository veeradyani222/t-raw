"""The per-bar decision step. Backtest and live both call on_bar() — this is
the single place where signal, risk, and orders meet.

on_bar() returns an event dict describing what happened on this bar (an
order opened, a signal blocked by a filter, a signal skipped by the risk
rails) or None when there was nothing to say. The backtest collects these
into the trade log; live just logs them. Keys: kind ("open" | "blocked" |
"skipped"), time, side, reason/meta and, for opens, ticket/entry/sl/tp/lots.
"""
import logging

from .broker import Broker
from .config import Config
from .risk import RiskGuard, position_size_lots
from .strategies import get_strategy
from .strategy import Blocked, Setup, Signal

log = logging.getLogger("trader")


def on_bar(broker: Broker, guard: RiskGuard, cfg: Config) -> dict | None:
    """Run once per newly closed candle."""
    strategy = get_strategy(cfg.strategy)
    candles = broker.candles(strategy.lookback(cfg))
    if candles.empty:
        return None

    equity = broker.equity()
    bar_time = candles["time"].iloc[-1]
    guard.on_new_bar(bar_time.date(), equity)

    result = strategy.compute_signal(candles, cfg)
    if result is None or result is Signal.FLAT:
        return None

    if isinstance(result, Blocked):
        log.info("%s | %s signal blocked: %s", bar_time, result.side, result.reason)
        return {"kind": "blocked", "time": bar_time, "side": result.side,
                "reason": result.reason, "meta": result.meta or {}}

    if isinstance(result, Setup):
        side, setup_sl, setup_tp = result.side, result.sl, result.tp
        meta = result.meta or {}
    else:
        side = "long" if result is Signal.LONG else "short"
        setup_sl = setup_tp = None
        meta = {}
    price = candles["close"].iloc[-1]

    # A crossover against our open position closes it first.
    for pos in broker.open_positions():
        if pos.side != side:
            profit = broker.close_position(pos)
            log.info("%s | closed %s %.2f lots, profit %.2f",
                     bar_time, pos.side, pos.lots, profit)

    allowed, reason = guard.may_open(len(broker.open_positions()))
    if not allowed:
        log.info("%s | %s signal skipped: %s", bar_time, side, reason)
        return {"kind": "skipped", "time": bar_time, "side": side,
                "reason": reason, "meta": meta}

    # Setup-supplied levels win; missing ones fall back to the fixed-pip config.
    sl_dist = cfg.sl_pips * cfg.pip_size
    tp_dist = cfg.tp_pips * cfg.pip_size
    if side == "long":
        sl = setup_sl if setup_sl is not None else price - sl_dist
        tp = setup_tp if setup_tp is not None else price + tp_dist
        valid = sl < price < tp
    else:
        sl = setup_sl if setup_sl is not None else price + sl_dist
        tp = setup_tp if setup_tp is not None else price - tp_dist
        valid = tp < price < sl
    if not valid:
        log.info("%s | %s setup skipped: levels invalid (price %.5f sl %.5f tp %.5f)",
                 bar_time, side, price, sl, tp)
        return {"kind": "skipped", "time": bar_time, "side": side,
                "reason": "levels invalid", "meta": meta}

    # Size from the ACTUAL stop distance so risk per trade stays constant
    # however wide or narrow the setup is.
    sl_pips = abs(price - sl) / cfg.pip_size
    lots = position_size_lots(
        equity, cfg.risk_per_trade, sl_pips, cfg.pip_value_per_lot,
        cfg.min_lot, cfg.max_lot,
    )
    if lots <= 0:
        log.info("%s | %s signal skipped: equity too small to size a trade",
                 bar_time, side)
        return {"kind": "skipped", "time": bar_time, "side": side,
                "reason": "equity too small to size a trade", "meta": meta}

    pos = broker.open_position(side, lots, sl, tp)
    log.info("%s | opened %s %.2f lots @ %.5f (sl %.5f, tp %.5f)",
             bar_time, side, lots, pos.entry_price, sl, tp)
    return {"kind": "open", "time": bar_time, "side": side, "ticket": pos.ticket,
            "entry": pos.entry_price, "sl": sl, "tp": tp, "lots": lots,
            "meta": meta}
