"""Run the live loop against the demo account. Ctrl+C to stop.

Runs TWO strategies on one account:
  1. Gold (XAUUSD) break-of-structure + Chaikin Money Flow, M30, structure-derived
     exits. Break of the most recent fractal swing, confirmed by a candle close
     and CMF direction. Replaced the H1 ORB strategy 2026-08-23: BOS beat ORB in
     every recent window (backtest) and both are gold, so they can't share the
     account (they'd fight over the XAUUSD slot). See docs/2026-08-23-*.
  2. USDJPY session (Tokyo-morning long): enter at server hour 6, protective ATR
     stop, no take-profit, closed by time after 12 bars. Validated in
     wf_search.py and survives real morning spreads (see docs).

Both share ONE account-wide set of prop rails — 1% risk/trade each, daily stop
$300 (3%), total stop $600 (6%), measured on floating equity against the FIXED
$10k baseline (see trader/risk.py). Those buffers sit under the firm's real
4%/8% limits.

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

# Shared prop rails — the same values on every config, because they gate ONE
# combined account.
RAILS = dict(
    risk_per_trade=0.01, max_open_positions=1,
    loss_baseline=10_000.0,
    daily_loss_halt=0.03,    # flat $300/day
    total_loss_halt=0.06,    # flat $600 total (permanent)
)

GOLD = Config(
    symbol="XAUUSD", timeframe="M30", strategy="bos",
    pip_size=0.1, pip_value_per_lot=10.0, spread_pips=3.0,
    bos_swing_window=2, bos_cmf_n=20, bos_cmf_min=0.0, bos_trend_ma=0,
    bos_lookback=2000, bos_tp_mode="structure", bos_tp_r=3.0, bos_tp_min_r=1.0,
    **RAILS,
)

USDJPY = Config(
    symbol="USDJPY", timeframe="H1", strategy="session",
    pip_size=0.01, pip_value_per_lot=10.0, spread_pips=1.0,
    session_entry_hour=6, session_hold_bars=12, session_side="long",
    session_stop_atr_mult=2.0, session_atr_n=14,
    **RAILS,
)

if __name__ == "__main__":
    run_live([GOLD, USDJPY])
