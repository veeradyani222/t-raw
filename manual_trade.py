"""Manual trade control from the command line — prove the live account can place
and close orders without waiting for the strategy to fire a setup. The SAME
commands are also available by texting the Telegram bot (see trader/live.py);
this CLI shares their logic via trader.commands.

Run ON THE SERVER (needs the MT5 terminal). Safe to run while the live bot is
up — both share the one terminal and the demo-only guard. The bot caps open
positions at 1, so `close` a manual position once you've eyeballed it.

    python manual_trade.py status        # equity + any open positions
    python manual_trade.py buy           # market BUY 0.01 lot, no SL/TP
    python manual_trade.py sell          # market SELL 0.01 lot, no SL/TP
    python manual_trade.py buy --lots 0.02
    python manual_trade.py close         # close ALL open positions on the symbol

Demo only: broker_mt5.connect() refuses a live account.
"""
import argparse

from trader import broker_mt5
from trader.alerts import send_alert
from trader.broker_mt5 import MT5Broker
from trader.commands import run_command
from trader.config import Config

# The live account/market — mirrors run_live.py's market settings.
CONFIG = Config(
    symbol="XAUUSD", timeframe="H1", strategy="orb",
    pip_size=0.1, pip_value_per_lot=10.0, spread_pips=3.0,
)


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(
        description="Manually open/close a trade to test the live order path.")
    p.add_argument("command", choices=["status", "buy", "sell", "close"])
    p.add_argument("--lots", type=float, default=0.01,
                   help="lot size for buy/sell (default 0.01 = broker minimum)")
    args = p.parse_args(argv)

    broker_mt5.connect(CONFIG)          # demo-only guard lives here
    try:
        broker = MT5Broker(CONFIG)
        summary = run_command(broker, CONFIG, args.command, args.lots)
    finally:
        broker_mt5.shutdown()

    print(summary)
    send_alert(CONFIG, f"\U0001F6E0 manual {args.command}: {summary}")


if __name__ == "__main__":
    main()
