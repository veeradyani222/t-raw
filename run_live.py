"""Run the live loop against the demo account. Ctrl+C to stop.

Runs ONE strategy on the account:
  Gold (XAUUSD) break-of-structure + Chaikin Money Flow, M30, structure-derived
  exits. Break of the most recent fractal swing, confirmed by a candle close
  and CMF direction. Replaced the H1 ORB strategy 2026-08-23: BOS beat ORB in
  every recent window (backtest) and both are gold, so they can't share the
  account (they'd fight over the XAUUSD slot). See docs/2026-08-23-*.

The prop rails — 0.5% risk/trade, daily stop $300 (3%), total stop $600 (6%),
measured on floating equity against the FIXED $10k baseline (see trader/risk.py) —
sit under the firm's real 4%/8% limits.

Risk was HALVED from 1% to 0.5% on 2026-09-07. At 1% this strategy is sized
about 2x too big for its own rail: its natural drawdown is 15-19% of the
baseline, so the 6% permanent total-loss stop fires long before the edge plays
out. A 12-month replay from 2025-09-04 with the live rails on:

    risk    trades   net $     outcome
    1.00%       15   -666      BLOWN — permanent halt in month one
    0.75%       19   -641      BLOWN
    0.50%      403  +1211      survived the year (max DD -680)
    0.40%      357  +1127      survived, smoothest (max DD -430)
    0.30%      273   +104      survives but too small to earn

The same 12 months with the rails OFF is +$3,250, so the strategy was never the
problem — the sizing was. 0.4% is one character away if the drawdown still runs
hotter than the remaining headroom allows.

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

# Account-wide prop rails.
RAILS = dict(
    risk_per_trade=0.005, max_open_positions=1,
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

if __name__ == "__main__":
    run_live([GOLD])
