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

TREND FILTER ON (bos_trend_ma=200), added 2026-09-07 after testing four
price-action variants. Only take breaks in the direction of the 200-bar MA
(~4 days on M30). Across 10 rolling start dates, 1% risk, rails on:

    variant           blown    mean net    worst
    BASE (no filter)   5/10       +2188     -672
    trend_ma=200       0/10       +4304     +670   <- shipped
    swing_window=4     2/10       +4040     -724
    sw=4 + ma=200      0/10       +4864     +722

swing_window=4 was NOT shipped: it looks best on 2024-26 but its out-of-sample
mean rests entirely on one +9532 outlier, with 11 of 12 starts losing.
Sizing up was TESTED AND REJECTED — with the filter on, 1.5% blows 4/10 and
2% blows 5/10, with no gain in mean. The lower drawdown does NOT buy size.

READ THIS BEFORE TRUSTING ANY OF THE ABOVE. Year by year, rails off, $10k
reset each year, this strategy makes money in only 2 of the last 8:

    year from   BASE      ma=200          year from   BASE      ma=200
    2018-09    -2244        -129          2022-09    -2931       -3410
    2019-09    -3480       -1283          2023-09     -258        +137
    2020-09    -2653       -1263          2024-09    +1521        +823
    2021-09    -2562       -2140          2025-09    +3926       +4908

Eight years of BASE sums to about -8700. Win rate barely moves (41-45%), so
the difference is payoff, not accuracy: structure targets get reached when
gold trends and don't when it ranges. This is a BULL-TREND RIDER, not an edge.
The +6296 two-year headline is the tail of a two-year gold run, and every
start date from 2018 to early 2024 hits the permanent stop. The trend filter
roughly halves the bleed in 4 of the 5 losing years, which is why it ships —
but it reduces a loss, it does not create an edge. Do not scale this up, and
do not put real money behind it on the strength of the recent window.

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
    bos_swing_window=2, bos_cmf_n=20, bos_cmf_min=0.0, bos_trend_ma=200,
    bos_lookback=2000, bos_tp_mode="structure", bos_tp_r=3.0, bos_tp_min_r=1.0,
    **RAILS,
)

if __name__ == "__main__":
    run_live([GOLD])
