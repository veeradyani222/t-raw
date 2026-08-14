"""Backtest the strategy on historical candles pulled from MT5.

Usage: python run_backtest.py [bars]   (default 5000)
"""
import logging
import sys

from trader import broker_mt5
from trader.broker_mt5 import MT5Broker
from trader.config import CONFIG
from trader.sim import run_backtest

logging.basicConfig(level=logging.INFO, format="%(message)s")


def main() -> None:
    bars = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    broker_mt5.connect(CONFIG)
    try:
        history = MT5Broker(CONFIG).candles(bars)
    finally:
        broker_mt5.shutdown()

    result = run_backtest(history, CONFIG)
    print(f"\n=== Backtest: {CONFIG.symbol} {CONFIG.timeframe}, "
          f"{result['bars']} bars ===")
    print(f"trades:       {result['trades']}")
    print(f"win rate:     {result['win_rate']:.1%}")
    print(f"net profit:   {result['net_profit']:+.2f}")
    print(f"final equity: {result['final_equity']:.2f} (from 10000.00)")


if __name__ == "__main__":
    main()
