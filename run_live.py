"""Run only CHFJPY H1 session trading against the demo account.

Long after the broker-labelled hour-0 H1 candle closes (normally around 01:00).
Stop: 2 x simple ATR14. No TP. Exit after 12 elapsed hours from actual entry.
Risk: 1% equity, max 1 lot / 1 position, existing $300 daily / $600 total
entry halts against a fixed $10,000 baseline. MT5 supplies account-currency
stop valuation; sizing reserves $14/lot round-trip commission and 0.1 pip
slippage per fill. These reserves are assumptions, not measured charges.

The clock uses broker bar labels, not local India time. Research-to-broker
session mapping is unverified. Timed exits require the loop and market to be
available; they recover from MT5 position timestamps after a restart.
GOLD below is retained only for existing BOS research imports.
Credentials come from .env. The broker still refuses non-demo accounts.
"""
import logging

from trader.config import Config
from trader.live import run_live

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler("trader.log", encoding="utf-8")],
)

# Account-wide prop rails.
RAILS = dict(
    risk_per_trade=0.01, max_open_positions=1,
    loss_baseline=10_000.0,
    daily_loss_halt=0.03,    # flat $300/day
    total_loss_halt=0.06,    # flat $600 total (permanent)
)

GOLD = Config(
    symbol="XAUUSD", timeframe="M30", strategy="bos",
    pip_size=0.1, pip_value_per_lot=10.0, spread_pips=3.0,
    bos_swing_window=2, bos_cmf_n=20, bos_cmf_min=0.0, bos_trend_ma=200,
    bos_lookback=2000, bos_tp_mode="structure", bos_tp_r=3.0, bos_tp_min_r=1.0,
    **RAILS,
)

CHFJPY = Config(
    symbol="CHFJPY", timeframe="H1", strategy="session",
    pip_size=0.01, spread_pips=2.5,
    session_hour=0, session_entry_at_open=False, session_atr_n=14, session_sl_atr=2.0,
    session_hold_hours=12.0, session_entry_window_seconds=60.0,
    session_commission_per_lot=14.0, session_slippage_pips=0.1,
    **RAILS,
)

LIVE_CONFIGS = (CHFJPY,)

if __name__ == "__main__":
    run_live(LIVE_CONFIGS)
