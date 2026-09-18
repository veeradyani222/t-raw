# BOS monthly loss diagnosis — 12 September 2026

This reproduces the saved local live-configuration BOS M30 backtest, not executed live-account P&L. Remote deployed code and actual deals have not been verified. Both saved baselines reproduce to numerical tolerance: 28 trades / -$466.60 for 12 August–11 September 2026, and 266 trades / +$3,104.21 for 12 September 2025–11 September 2026.

Configuration: run_live.GOLD, 1% equity risk, MA200, CMF20 sign, swing window2, 2000-bar context, structure stop/target, minimum1R target, 3R fallback, one position, opposite-signal exits, $300 daily / $600 static total guard. All prior context is available before each start; each fresh run starts flat with $10,000. No session filter or three-hour holding cap was added.

## Comparable months

Each period runs from the 12th through the following 11th. Fresh results reset to $10,000 and start flat, directly matching the recent-month test. The continuous column groups the one-year account's realized exits and carries capital and positions forward. These different capital/exposure histories cannot be mixed.

| Period start | Fresh net | Fresh trades | Win rate | Fresh permanent halt | Continuous net |
|---|---:|---:|---:|---|---:|
| 2025-09-12 | $+12.07 | 25 | 32.0% | No | $+21.23 |
| 2025-10-12 | $+1225.08 | 27 | 63.0% | No | $+1210.11 |
| 2025-11-12 | $+138.80 | 26 | 50.0% | No | $+330.88 |
| 2025-12-12 | $+505.24 | 17 | 58.8% | No | $+571.36 |
| 2026-01-12 | $+806.17 | 14 | 57.1% | No | $+876.60 |
| 2026-02-12 | $-324.38 | 22 | 36.4% | No | $-631.29 |
| 2026-03-12 | $+179.05 | 21 | 52.4% | No | $+579.74 |
| 2026-04-12 | $+272.70 | 25 | 52.0% | No | $-21.38 |
| 2026-05-12 | $+240.99 | 26 | 50.0% | No | $+590.15 |
| 2026-06-12 | $+221.71 | 19 | 52.6% | No | $+146.81 |
| 2026-07-12 | $+113.65 | 27 | 48.1% | No | $+143.69 |
| 2026-08-12 | $-466.60 | 28 | 32.1% | No | $-713.69 |

Of the preceding 11 fresh monthly windows, 0 lost at least as much as the latest -$466.60. The worst fresh window started 2026-08-12.

Worst daily-shifted trailing calendar month on the continuous account: 2026-02-18 to 2026-03-18 (exclusive), $-765.43, -5.94% of its opening closed balance. These overlapping windows are descriptive, not independent trials or new monthly-reset simulations.

## What drove the recent loss

Recent month: 9 wins / 19 losses, 32.14% win rate versus 48.12% over the year. Gross winners $1063.78; gross losses $-1530.38; net $-466.60. Average winner $118.20, average loser $-80.55; profit factor 0.695. Longest consecutive losing-trade run: 6.

| Exit reason | Trades | Net |
|---|---:|---:|
| end | 1 | $-41.73 |
| signal | 1 | $-29.44 |
| sl | 17 | $-1459.21 |
| tp | 9 | $+1063.78 |

| Side | Trades | Net |
|---|---:|---:|
| long | 14 | $-382.20 |
| short | 14 | $-84.40 |

The losses predominantly came from qualifying breakouts subsequently hitting their structural stops. Both directions lost; long trades contributed more net loss. The body-close rule passed on every entry in the one-year replay, so wick-only entries do not explain this backtest loss. The MA200 and CMF-sign filters do not prevent all failed breakouts. This does not establish a particular macroeconomic or news cause.

Structure exits are not universally 3R targets: 3R is only the fallback. In the latest month, 23 trades used structure targets and five used the fallback. The realized win rate and payouts together were insufficient to cover the losers. The last losing trade is an artificial end-of-test mark, not necessarily an actual live exit.

Changing filters to remove these particular past losers would be retrospective fitting. This diagnosis establishes the failure pattern, not a verified repair or a promise of positive future returns. Current settings were selected after earlier historical testing; the one-year replay is not a fully unseen forward test.

## Limits and artifacts

SimBroker matches the production decision engine but simplifies execution: signal-bar close plus fixed spread, stop-first ties, exact stop fills even on gaps, no commission/swap/slippage/latency, and risk guards based on closed balance. Actual live risk checks use floating equity. The earlier intraday research BOS numbers used different hours, costs and holding limits and are not this model. No live configuration was changed.

Data ends 11 September 2026 at 21:30 in dataset timestamps, matching the original saved replay. Recorded bars include gaps; broker feed and execution parity remain unverified. Trade accounting, saved-baseline reproduction and every entry's body-cross condition were checked. Raw trades, event logs, monthly tables, rolling windows, source/data hashes and sanitized settings are in `logs/bos-monthly-diagnosis-20260912/`. Reproduce with `.venv\Scripts\python.exe -m research.bos_loss_diagnosis`.

## Pre-discussion version check

The user clarified that they mean the version before the candle-body discussion. The original BOS commit (`c5290c7`, 23 August 2026) already required a bullish close beyond resistance / bearish close beyond support. Comparing current code with committed HEAD found identical executable syntax for `lookback`, `_cmf_last`, and `compute_signal`; the moved `swing_points` helper also has identical executable syntax. Changes were explanatory comments, documentation and the helper import location, not the entry rule. The live configuration file is unchanged from HEAD. This is the pre-discussion entry logic with the same local live settings.

Additional descriptive check: all 17 recent-month stop-loss trades had a subsequent candle close back inside the broken boundary before their exit bar. However, 5 of the 9 winners also did, as did 49 of the 128 yearly winners. Returning inside is a useful diagnostic, not proof that immediately exiting there improves the strategy. At the recent realized average winner/loser sizes, break-even requires about 40.53% wins, versus the observed 32.14%.

Verification: 35 BOS, backtest and risk tests passed. The two saved baseline results reproduced, and all 13 new simulations reconciled. No strategy or live-risk change was made.
