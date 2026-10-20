"""Run the live bot against the demo account.

Default: the 66-strategy portfolio from docs/board/portfolio-lp300-66.json
through trader/multi_live.py (one magic number per strategy, account-wide
$300 daily close-all and $9,300 permanent floor, demo-only guard).

    python run_live.py                # the portfolio
    python run_live.py --preflight    # connect, print the symbol table, exit
    python run_live.py --legacy       # the old single-strategy CHFJPY H1 session bot

The legacy configs stay importable (LIVE_CONFIGS / CHFJPY / GOLD) for the
tests and research scripts that use them. Credentials come from .env. The
broker still refuses non-demo accounts.
"""
import logging
import sys

from trader.config import Config

# Windows consoles default to cp1252; the reports carry emoji and arrows.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(),
              logging.FileHandler("trader.log", encoding="utf-8")],
)

# ---- legacy single-strategy configs (kept importable) -------------------------
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
    if "--legacy" in sys.argv:
        from trader.live import run_live
        run_live(LIVE_CONFIGS)
    elif "--preflight" in sys.argv:
        from trader.config import CONFIG
        from trader.multi_live import startup
        startup(CONFIG, preflight_only=True)
    else:
        from trader.multi_live import run_multi
        run_multi()
