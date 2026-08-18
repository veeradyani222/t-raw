"""Live loop: poll for each newly closed candle, run the engine, and alert on
everything that matters. Ctrl+C to stop — open positions are left running (they
carry SL/TP on the server side).

Two things run on EVERY poll (not just at candle close):
- the risk limits are re-checked against live equity (which includes floating
  P&L), because a prop daily/total limit can be breached mid-candle;
- a floating-P&L heartbeat is sent every STATUS_EVERY_SECONDS while a position
  is open.

The engine (signals, sizing, opening) still runs only when a new candle closes.
"""
import logging
import time

from . import broker_mt5
from .alerts import send_alert
from .broker_mt5 import MT5Broker
from .config import Config
from .engine import on_bar
from .risk import RiskGuard

log = logging.getLogger("trader")

POLL_SECONDS = 10
STATUS_EVERY_SECONDS = 30 * 60   # floating-P&L heartbeat while in a trade
DAILY_HEARTBEAT_SECONDS = 24 * 60 * 60   # "still alive" ping even when flat/idle


def _heartbeat_due(now: float, last: float, interval: float) -> bool:
    """True once `interval` seconds have elapsed since the last heartbeat.
    Pulled out of the loop so the timing is unit-testable on its own."""
    return now - last >= interval


def _daily_cap(cfg: Config) -> float:
    return cfg.daily_loss_halt * cfg.loss_baseline


def _total_cap(cfg: Config) -> float:
    return cfg.total_loss_halt * cfg.loss_baseline


def _report_open(cfg: Config, event: dict | None) -> None:
    if not event or event.get("kind") != "open":
        return
    send_alert(cfg, f"\U0001F4C8 OPENED {event['side'].upper()} {event['lots']} "
                    f"{cfg.symbol} @ {event['entry']:.2f} | SL {event['sl']:.2f} "
                    f"| TP {event['tp']:.2f}")


def _report_closes(cfg: Config, broker: MT5Broker, before: dict, after: dict) -> None:
    for ticket, pos in before.items():
        if ticket in after:
            continue
        try:
            pnl = broker.realized_pnl(ticket)
        except broker_mt5.MT5Error:
            pnl = float("nan")
        equity = broker.equity()
        won = pnl == pnl and pnl >= 0        # pnl == pnl is False for NaN
        send_alert(cfg, f"{'✅' if won else '❌'} CLOSED {pos.side.upper()} "
                        f"{pos.lots} {cfg.symbol} @ {pos.entry_price:.2f} | "
                        f"P/L {pnl:+.2f} | equity {equity:.2f}")


def _report_floating(cfg: Config, broker: MT5Broker, candles) -> None:
    positions = broker.open_positions()
    if not positions:
        return
    equity = broker.equity()
    floating = equity - broker.balance()
    price = float(candles["close"].iloc[-1])
    held = ", ".join(f"{p.side.upper()} {p.lots} @ {p.entry_price:.2f}" for p in positions)
    send_alert(cfg, f"⏳ Holding {held} | price {price:.2f} | "
                    f"floating {floating:+.2f} | equity {equity:.2f}")


def _report_daily_heartbeat(cfg: Config, broker: MT5Broker, bars_checked: int) -> None:
    """Once-a-day 'I'm alive' ping, sent even when flat. This is what makes
    silence meaningful: if this stops arriving, the bot is DOWN — not just a
    quiet market — so an outage can't go unnoticed for days again."""
    positions = broker.open_positions()
    equity = broker.equity()
    held = ("flat" if not positions
            else ", ".join(f"{p.side.upper()} {p.lots} @ {p.entry_price:.2f}"
                           for p in positions))
    send_alert(cfg, f"✅ alive: {cfg.symbol} {cfg.timeframe} ({cfg.strategy}) | "
                    f"equity {equity:.2f} | {held} | "
                    f"{bars_checked} candles since last check")


def run_live(cfg: Config) -> None:
    broker_mt5.connect(cfg)
    broker = MT5Broker(cfg)
    guard = RiskGuard(cfg.max_open_positions, cfg.daily_loss_halt,
                      cfg.max_drawdown_halt, cfg.loss_baseline,
                      cfg.total_loss_halt)
    send_alert(cfg, f"\U0001F7E2 mt5-trader started: {cfg.symbol} {cfg.timeframe} "
                    f"({cfg.strategy}), equity {broker.equity():.2f}. Risk "
                    f"{cfg.risk_per_trade:.0%}/trade | daily stop -{_daily_cap(cfg):.0f} "
                    f"| total stop -{_total_cap(cfg):.0f}.")

    last_bar_time = None
    was_halted = False
    was_blown = False
    last_status = time.time()
    last_heartbeat = time.time()
    bars_since_heartbeat = 0
    try:
        while True:
            try:
                candles = broker.candles(2)
                bar_time = candles["time"].iloc[-1]
                equity = broker.equity()

                # Risk limits every poll, on live (floating) equity.
                guard.on_new_bar(bar_time.date(), equity)
                if guard.blown and not was_blown:
                    send_alert(cfg, f"\U0001F6D1 TOTAL-LOSS HALT — equity {equity:.2f} "
                                    f"breached the -{_total_cap(cfg):.0f} limit. "
                                    f"No more trades (permanent).")
                if guard.halted and not was_halted:
                    down = guard._day_start_equity - equity
                    send_alert(cfg, f"⏸️ DAILY LOSS HALT — down {down:.2f} today "
                                    f"(limit {_daily_cap(cfg):.0f}). No new trades until tomorrow.")
                was_blown, was_halted = guard.blown, guard.halted

                # New closed candle → run the strategy/engine once.
                if bar_time != last_bar_time:
                    last_bar_time = bar_time
                    bars_since_heartbeat += 1
                    before = {p.ticket: p for p in broker.open_positions()}
                    event = on_bar(broker, guard, cfg)
                    after = {p.ticket: p for p in broker.open_positions()}
                    _report_open(cfg, event)
                    _report_closes(cfg, broker, before, after)
                    was_halted = guard.halted

                # Heartbeat: floating P&L while a position is open.
                if time.time() - last_status >= STATUS_EVERY_SECONDS:
                    _report_floating(cfg, broker, candles)
                    last_status = time.time()

                # Daily "still alive" ping — fires even when flat and idle, so
                # a stalled/killed bot shows up as missing heartbeats.
                if _heartbeat_due(time.time(), last_heartbeat, DAILY_HEARTBEAT_SECONDS):
                    _report_daily_heartbeat(cfg, broker, bars_since_heartbeat)
                    last_heartbeat = time.time()
                    bars_since_heartbeat = 0

            except broker_mt5.MT5Error as exc:
                log.error("MT5 error: %s", exc)
                send_alert(cfg, f"⚠️ ERROR: {exc}")
                time.sleep(60)  # back off, then keep trying
            time.sleep(POLL_SECONDS)
    finally:
        broker_mt5.shutdown()
