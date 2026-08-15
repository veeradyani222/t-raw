"""Run the live loop against the demo account. Ctrl+C to stop.

Configured here for the strategy we actually forward-test: gold (XAUUSD)
opening-range breakout on H1 with structure-derived exits, plus the prop-account
risk rails — 1% risk/trade, daily stop $300, total stop $600 — all measured
against the FIXED $10k baseline on floating equity (see trader/risk.py).

MT5 login and Telegram come from .env (never hard-coded here).
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

CONFIG = Config(
    # --- market / strategy (gold ORB, the validated config) ---
    symbol="XAUUSD", timeframe="H1", strategy="orb",
    pip_size=0.1, pip_value_per_lot=10.0, spread_pips=3.0,
    orb_session_start_hour=1, orb_box_candles=3,
    orb_tp_mode="structure", orb_tp_r=3.0, orb_tp_min_r=1.0,
    orb_structure_filter=True, orb_vol_filter=False,
    # --- prop risk rails, measured off the FIXED $10k baseline ---
    risk_per_trade=0.01, max_open_positions=1,
    loss_baseline=10_000.0,
    daily_loss_halt=0.03,    # flat $300/day
    total_loss_halt=0.06,    # flat $600 total (permanent)
)

if __name__ == "__main__":
    run_live(CONFIG)
