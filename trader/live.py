"""Live loop: poll for each newly closed candle, run every configured strategy,
and alert on everything that matters. Ctrl+C to stop — open positions are left
running (they carry a server-side SL).

Runs MULTIPLE strategies on ONE account (e.g. gold BOS + USDJPY session). They
share a single account-wide RiskGuard, so the prop daily/total limits are
measured against the COMBINED equity — exactly how the firm scores you. Each
strategy trades its own symbol (max 1 position each).

Two things run on EVERY poll (not just at candle close):
- the risk limits are re-checked against live (floating) equity, because a prop
  limit can be breached mid-candle;
- session positions are time-exited once they've been held long enough.

The engine (signals, sizing, opening) runs only when a new candle closes.
"""
import logging
import time

from . import broker_mt5
from .alerts import send_alert
from .broker_mt5 import MT5Broker
from .commands import _price_dp, command_keyboard, run_command_multi
from .config import Config
from .engine import on_bar
from .risk import RiskGuard
from .strategies import session as session_strat
from .telegram_commands import fetch_commands

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
    dp = _price_dp(cfg)
    tp = event["tp"]
    tp_str = f"{tp:.{dp}f}" if tp else "none (time exit)"
    send_alert(cfg, f"\U0001F4C8 OPENED {event['side'].upper()} {event['lots']} "
                    f"{cfg.symbol} ({cfg.strategy}) @ {event['entry']:.{dp}f} | "
                    f"SL {event['sl']:.{dp}f} | TP {tp_str}")


def _report_closes(cfg: Config, broker: MT5Broker, before: dict, after: dict) -> None:
    dp = _price_dp(cfg)
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
                        f"{pos.lots} {cfg.symbol} @ {pos.entry_price:.{dp}f} | "
                        f"P/L {pnl:+.2f} | equity {equity:.2f}")


def _session_time_exit(cfg: Config, broker: MT5Broker, now_bar_time) -> None:
    """Close any session position that has been held long enough. Runs every
    poll so the exit is timely, and reads the open time back from the broker so
    it survives a bot restart. No-op for non-session strategies."""
    if cfg.strategy != "session":
        return
    dp = _price_dp(cfg)
    for pos in broker.open_positions():
        if session_strat.should_time_exit(pos.open_time, now_bar_time, cfg):
            try:
                pnl = broker.close_position(pos)
            except broker_mt5.MT5Error as exc:
                send_alert(cfg, f"⚠️ ERROR closing {cfg.symbol} on time exit: {exc}")
                continue
            send_alert(cfg, f"⌛ TIME EXIT {pos.side.upper()} {pos.lots} {cfg.symbol} "
                            f"@ {pos.entry_price:.{dp}f} after {cfg.session_hold_bars} "
                            f"bars | P/L {pnl:+.2f}")


def _report_floating(runners) -> None:
    broker0 = runners[0][1]
    held = []
    for cfg, broker in runners:
        dp = _price_dp(cfg)
        for p in broker.open_positions():
            held.append(f"{cfg.symbol} {p.side.upper()} {p.lots} @ {p.entry_price:.{dp}f}")
    if not held:
        return
    equity = broker0.equity()
    floating = equity - broker0.balance()
    send_alert(runners[0][0], f"⏳ Holding {', '.join(held)} | "
                              f"floating {floating:+.2f} | equity {equity:.2f}")


def _report_daily_heartbeat(runners, bars_checked: int) -> None:
    """Once-a-day 'I'm alive' ping, sent even when flat. If this stops arriving,
    the bot is DOWN — not just a quiet market."""
    broker0 = runners[0][1]
    equity = broker0.equity()
    strat_list = ", ".join(f"{c.symbol}/{c.strategy}" for c, _ in runners)
    held = []
    for cfg, broker in runners:
        dp = _price_dp(cfg)
        for p in broker.open_positions():
            held.append(f"{cfg.symbol} {p.side.upper()} {p.lots} @ {p.entry_price:.{dp}f}")
    held_str = "flat" if not held else ", ".join(held)
    send_alert(runners[0][0], f"✅ alive: {strat_list} | equity {equity:.2f} | "
                              f"{held_str} | {bars_checked} candles since last check")


def run_live(configs) -> None:
    """configs: a Config or a list of Configs to run together on one account.
    All configs must share the same prop rails (they gate one combined account)."""
    if isinstance(configs, Config):
        configs = [configs]
    primary = configs[0]

    broker_mt5.connect(primary)
    for cfg in configs[1:]:
        broker_mt5.select_symbol(cfg.symbol)
    brokers = [MT5Broker(cfg) for cfg in configs]
    runners = list(zip(configs, brokers))

    # One account-wide guard: prop rails come from the primary config (all
    # configs carry the same rails). max_open_positions is per-symbol (each
    # broker reports only its own positions), so 1 gold + 1 usdjpy is allowed.
    guard = RiskGuard(primary.max_open_positions, primary.daily_loss_halt,
                      primary.max_drawdown_halt, primary.loss_baseline,
                      primary.total_loss_halt)

    strat_list = ", ".join(f"{c.symbol} {c.timeframe} ({c.strategy}, "
                           f"{c.risk_per_trade:.0%})" for c in configs)
    keyboard = command_keyboard(runners)
    send_alert(primary, f"\U0001F7E2 mt5-trader started: {strat_list}. "
                        f"Equity {brokers[0].equity():.2f}. Account rails: daily stop "
                        f"-{_daily_cap(primary):.0f} | total stop -{_total_cap(primary):.0f}.",
               reply_markup=keyboard)
    send_alert(primary, run_command_multi(runners, guard, "help"), reply_markup=keyboard)

    # Drain any Telegram backlog WITHOUT acting on it, so a command texted while
    # the bot was down never fires on startup.
    _, tg_offset = fetch_commands(primary, None)

    last_bar_time = {cfg.symbol: None for cfg in configs}
    was_halted = was_blown = False
    last_status = time.time()
    last_heartbeat = time.time()
    bars_since_heartbeat = 0
    try:
        while True:
            try:
                equity = brokers[0].equity()
                # Use the primary's latest bar date for the daily anchor.
                primary_bar_time = brokers[0].candles(2)["time"].iloc[-1]

                # Account-wide risk check every poll, on live (floating) equity.
                guard.on_new_bar(primary_bar_time.date(), equity)
                if guard.blown and not was_blown:
                    send_alert(primary, f"\U0001F6D1 TOTAL-LOSS HALT — equity {equity:.2f} "
                                        f"breached the -{_total_cap(primary):.0f} limit. "
                                        f"No more trades (permanent).")
                if guard.halted and not was_halted:
                    down = guard._day_start_equity - equity
                    send_alert(primary, f"⏸️ DAILY LOSS HALT — down {down:.2f} today "
                                        f"(limit {_daily_cap(primary):.0f}). No new trades until tomorrow.")
                was_blown, was_halted = guard.blown, guard.halted

                # Each strategy: time-exit its session positions, then run the
                # engine once per newly closed candle.
                for cfg, broker in runners:
                    bar_time = broker.candles(2)["time"].iloc[-1]
                    _session_time_exit(cfg, broker, bar_time)
                    if bar_time != last_bar_time[cfg.symbol]:
                        last_bar_time[cfg.symbol] = bar_time
                        if cfg.symbol == primary.symbol:
                            bars_since_heartbeat += 1
                        before = {p.ticket: p for p in broker.open_positions()}
                        event = on_bar(broker, guard, cfg)
                        after = {p.ticket: p for p in broker.open_positions()}
                        _report_open(cfg, event)
                        _report_closes(cfg, broker, before, after)
                was_halted = guard.halted

                # Heartbeat: floating P&L while any position is open.
                if time.time() - last_status >= STATUS_EVERY_SECONDS:
                    _report_floating(runners)
                    last_status = time.time()

                # Daily "still alive" ping — fires even when flat and idle.
                if _heartbeat_due(time.time(), last_heartbeat, DAILY_HEARTBEAT_SECONDS):
                    _report_daily_heartbeat(runners, bars_since_heartbeat)
                    last_heartbeat = time.time()
                    bars_since_heartbeat = 0

                # Inbound Telegram commands (manual buy/sell/close/status/risk).
                # Locked to the owner's chat; acts across ALL symbols.
                cmds, tg_offset = fetch_commands(primary, tg_offset)
                for cmd in cmds:
                    send_alert(primary, run_command_multi(runners, guard, cmd),
                               reply_markup=keyboard)

            except broker_mt5.MT5Error as exc:
                log.error("MT5 error: %s", exc)
                send_alert(primary, f"⚠️ ERROR: {exc}")
                time.sleep(60)  # back off, then keep trying
            time.sleep(POLL_SECONDS)
    finally:
        broker_mt5.shutdown()
