"""Live loop: poll for each newly closed candle, run the engine, alert on
changes. Ctrl+C to stop — open positions are left running (they carry SL/TP
on the server side)."""
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


def run_live(cfg: Config) -> None:
    broker_mt5.connect(cfg)
    broker = MT5Broker(cfg)
    guard = RiskGuard(cfg.max_open_positions, cfg.daily_loss_halt,
                      cfg.max_drawdown_halt)
    send_alert(cfg, f"mt5-trader started: {cfg.symbol} {cfg.timeframe}, "
                    f"equity {broker.equity():.2f}")

    last_bar_time = None
    was_halted = False
    try:
        while True:
            try:
                candles = broker.candles(2)
                bar_time = candles["time"].iloc[-1]
                if bar_time != last_bar_time:
                    last_bar_time = bar_time
                    before = {p.ticket: p for p in broker.open_positions()}
                    on_bar(broker, guard, cfg)
                    after = {p.ticket: p for p in broker.open_positions()}

                    for t, p in after.items():
                        if t not in before:
                            send_alert(cfg, f"OPENED {p.side} {p.lots} lots "
                                            f"{cfg.symbol} @ {p.entry_price:.5f}")
                    for t, p in before.items():
                        if t not in after:
                            send_alert(cfg, f"CLOSED {p.side} {p.lots} lots "
                                            f"{cfg.symbol}; equity now "
                                            f"{broker.equity():.2f}")
                    if guard.halted and not was_halted:
                        send_alert(cfg, "DAILY LOSS HALT hit — no new trades today")
                    was_halted = guard.halted
            except broker_mt5.MT5Error as exc:
                log.error("MT5 error: %s", exc)
                send_alert(cfg, f"ERROR: {exc}")
                time.sleep(60)  # back off, then keep trying
            time.sleep(POLL_SECONDS)
    finally:
        broker_mt5.shutdown()
