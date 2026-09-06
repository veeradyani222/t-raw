"""Run the live loop against the demo account. Ctrl+C to stop.

Runs ONE strategy on the account:
  Gold (XAUUSD) break-of-structure + Chaikin Money Flow, M30, structure-derived
  exits. Break of the most recent fractal swing, confirmed by a candle close
  and CMF direction. Replaced the H1 ORB strategy 2026-08-23: BOS beat ORB in
  every recent window (backtest) and both are gold, so they can't share the
  account (they'd fight over the XAUUSD slot). See docs/2026-08-23-*.

The prop rails — 1% risk/trade, daily stop $300 (3%), total stop $600 (6%),
measured on floating equity against the FIXED $10k baseline (see trader/risk.py) —
sit under the firm's real 4%/8% limits.

RISK SIZING — decided 2026-09-07, eyes open. Briefly set to 0.5%, then returned
to 1% because over the last two years 1% is 3.6x better:

    2 years, 04 Sep 2024 -> 04 Sep 2026, $10k, rails on
    risk    trades   W/L      net $   final equity   maxDD   worst month
    1.00%      911   408/503  +6296        16,296    -1881       -962
    0.50%      881   393/488  +1731        11,731     -793       -296

THE CATCH, and it is not small: on that same 2-year run 1% bottomed at
$9,618.68 — it cleared the $9,400 permanent kill line by $218. It survived only
because it made +$2,406 in its first three months, and the rail measures from a
FIXED baseline, so early profit becomes permanent armour. Win early and 1% is
safe for years; lose early and it is dead in weeks. Across 11 rolling start
dates, 1% hit the permanent halt on 5 of them; 0.5% on none.

So 1% is ONLY sane on an account with a full $10k of headroom. It needs a clean
baseline to have its fair shot at the early cushion. Running 1% on an account
already down several hundred is the -$640 outcome with near-certainty, followed
by nothing, ever.

Measure any change to this with wf_search.simulate(allow_flip=True) — the
default allow_flip=False does NOT match the live engine's opposite-signal close
and silently produces a different, better-looking trade sequence.

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

if __name__ == "__main__":
    run_live([GOLD])
