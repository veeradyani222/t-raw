# Gold intraday strategy study — 12 September 2026

No candidate passed the predeclared first-11-month screen (positive net, profit factor at least 1.10, at least 80 trades, and no modeled firm breach/internal total halt). The frozen shortlist is empty. No live strategy was added or enabled; the production registry remains BOS-only.

The screenshot's LuxAlgo trendline idea was implemented for offline testing. Its M5 recent-month profit did not persist over the year. M15 EMA pullback was the only variant positive in both requested windows, but its small yearly gain disappeared under cost stress. These results do not establish a robust profitable strategy.

## Dates, data and execution

Year: 12 September 2025 through 11 September 2026. Recent month: 12 August through 11 September 2026. Each simulation starts flat with $10,000 and preceding indicator warmup. The recent month overlaps the year; its fresh $10,000 start means its results need not match the final month of the year simulation.

Primary risk is 0.25% of current cash equity per trade, reduced by lot rounding and remaining daily/total loss headroom. User-confirmed external limits are 4% daily / 8% total, with internal 3% / 6% buffers. The model uses a fixed $300 daily allowance from day-start equity and a static $9,400 internal floor; actual firm reset time, trailing-versus-static terms and news restrictions remain unverified.

Completed-bar signals fill at the next available bar open. One position at a time; entries 07:00–18:59, forced flat from 20:00, reset at midnight, all in dataset timestamps. Base costs: maximum of recorded spread and $0.30 per ounce, $7 per lot round-trip commission, $0.03 per ounce adverse slippage on market fills. Contract size is 100 ounces, lot step/minimum 0.01, maximum 1 lot. Bars with recorded spreads above $0.60 cannot open trades. Costs are assumptions, not verified account charges.

Bid OHLC is converted to executable bid/ask prices. An adverse-first path gives the stop priority if both stop and target lie inside a bar; gap stops fill at the worse available opening quote. Floating liquidation equity includes closing costs. This is an OHLC approximation, not tick-accurate execution or proof of prop-firm compliance. [MetaQuotes on OHLC testing limits](https://www.mql5.com/en/docs/runtime/testing).

## Your screenshot's trendlines

The visible indicator is LuxAlgo Trendlines with Breaks, apparently length 14, slope multiplier 1, ATR method. Descending green resistance supplies a first-close-above buy signal; rising red support supplies a first-close-below sell signal. A wick-only excursion does not qualify. This close-based rule is the tested interpretation; it does not implement every possible body-overlap variant. Breakouts can fail.

The published recurrence confirms a pivot only 14 bars later: 3.5 hours on M15. Its slope is ATR at confirmation divided by 14. The boundary is projected forward and emits one close breakout per confirmed pivot. Historical backpainting is not used for entries. The implementation follows these published rules but has not been certified against TradingView bar-for-bar; feed differences (screenshot OANDA versus fetched MT5 history) and pivot-tie behavior can matter. [LuxAlgo source and explanation](https://www.luxalgo.com/library/indicator/Trendlines-with-Breaks/).

An indicator is not a complete trading strategy. For this test we added a 1.5 ATR stop, 2R target, maximum 180-minute holding period, the above session/risk rules, and a second variant with an EMA200 direction filter. RSI and TRAMA visible in the screenshot were not entry filters.

## All primary results

Net dollars include modeled costs. Drawdown is the maximum floating peak-to-trough dollar drop divided by the original $10,000, not loss below initial balance. A run can therefore show drawdown above 6% while remaining above a static $9,400 floor after earlier profits.

### M5

| Variant | Month net | Year net | Year trades | Year PF | Year float DD | Worst day |
|---|---:|---:|---:|---:|---:|---:|
| channel_break | $-26.81 | $-595.93 | 332 | 0.85 | 7.48% | 1.46% |
| channel_long | $+115.78 | $-594.94 | 258 | 0.80 | 6.49% | 1.04% |
| ema_pullback | $-114.86 | $-598.77 | 315 | 0.86 | 8.35% | 1.47% |
| range_reentry | $-31.33 | $-233.86 | 441 | 0.95 | 5.76% | 0.82% |
| sweep_reclaim | $-90.52 | $-180.32 | 526 | 0.97 | 5.83% | 1.34% |
| compression_break | $-150.39 | $+112.60 | 485 | 1.02 | 8.42% | 1.00% |
| bos_baseline | $-181.95 | $-597.58 | 409 | 0.86 | 7.79% | 1.08% |
| lux_trendline | $+316.49 | $-598.17 | 433 | 0.90 | 9.93% | 1.55% |
| lux_trendline_trend | $+145.88 | $-599.04 | 257 | 0.84 | 8.98% | 1.41% |

### M15

| Variant | Month net | Year net | Year trades | Year PF | Year float DD | Worst day |
|---|---:|---:|---:|---:|---:|---:|
| channel_break | $-56.68 | $-63.21 | 430 | 0.98 | 6.47% | 0.77% |
| channel_long | $-22.39 | $-120.88 | 255 | 0.94 | 4.76% | 0.52% |
| ema_pullback | $+100.51 | $+42.92 | 342 | 1.01 | 4.80% | 0.69% |
| range_reentry | $+11.99 | $-298.56 | 127 | 0.74 | 4.01% | 0.45% |
| sweep_reclaim | $-51.28 | $-281.32 | 180 | 0.85 | 4.38% | 0.57% |
| compression_break | $-44.84 | $+99.68 | 215 | 1.05 | 2.88% | 0.47% |
| bos_baseline | $-98.05 | $-570.91 | 293 | 0.77 | 6.80% | 0.64% |
| lux_trendline | $-133.44 | $-230.88 | 442 | 0.95 | 8.29% | 0.76% |
| lux_trendline_trend | $-177.44 | $-228.26 | 289 | 0.92 | 4.22% | 0.53% |

### M1 — month only

M1 history begins 28 May 2026, so a yearly M1 result is unavailable.

| Variant | Month net | Trades | Float DD | Worst day |
|---|---:|---:|---:|---:|
| channel_break | $-598.29 | 118 | 6.22% | 2.98% |
| channel_long | $-599.98 | 146 | 6.58% | 2.06% |
| ema_pullback | $-467.99 | 336 | 8.81% | 2.98% |
| range_reentry | $-599.96 | 106 | 6.04% | 1.17% |
| sweep_reclaim | $-599.20 | 151 | 7.04% | 2.02% |
| compression_break | $+261.00 | 191 | 6.29% | 2.13% |
| bos_baseline | $-599.50 | 320 | 6.26% | 2.07% |
| lux_trendline | $-599.98 | 150 | 8.04% | 2.99% |
| lux_trendline_trend | $-599.24 | 117 | 6.51% | 2.99% |

Several losing runs stop finding affordable minimum-lot trades near $9,400. Their lack of a formal halt/breach flag is not evidence of useful safety or recovery. For example, the M5 trendline year's trades stop before the recent-month window; the positive standalone month starts with fresh capital.

## Cost and position-size sensitivity

M15 trendlines were included because you requested them. M15 EMA pullback was added after observing positive year/month results and is explicitly post hoc, not a successful held-out selection. Higher-cost stress uses $0.60 minimum spread, $10 commission and $0.10 slippage at 0.25% risk. The separate 0.5% risk runs retain base costs.

| M15 variant | Profile | Month net | Year net | Year float DD |
|---|---|---:|---:|---:|
| ema_pullback | cost_stress | $+92.76 | $-236.48 | 6.09% |
| ema_pullback | risk_0p5 | $+303.59 | $+251.99 | 12.50% |
| lux_trendline | cost_stress | $-158.64 | $-592.24 | 10.10% |
| lux_trendline | risk_0p5 | $-234.21 | $-599.21 | 16.92% |
| lux_trendline_trend | cost_stress | $-179.73 | $-501.53 | 6.13% |
| lux_trendline_trend | risk_0p5 | $-326.18 | $-482.37 | 9.36% |

Twelve fresh starts (the 12th of each month, September 2025–August 2026) all end on 12 September 2026. These overlap and have different lengths; they are start-date sensitivity checks, not twelve independent validation periods. 'Near floor' means minimum modeled equity below $9,410.

| M15 variant | Risk | Profitable starts / 12 | Near floor / 12 | Worst net |
|---|---:|---:|---:|---:|
| ema_pullback | 0.25% | 10 | 0 | $-101.17 |
| ema_pullback | 0.50% | 8 | 4 | $-599.97 |
| lux_trendline | 0.25% | 1 | 3 | $-595.46 |
| lux_trendline | 0.50% | 1 | 7 | $-599.77 |
| lux_trendline_trend | 0.25% | 0 | 0 | $-320.84 |
| lux_trendline_trend | 0.50% | 0 | 2 | $-597.75 |

## Candidate definitions

- `channel_break`: 20-bar channel breakout, MA200, 2 ATR stop, 2R target.
- `channel_long`: Same channel breakout, long only.
- `ema_pullback`: EMA20 reclaim within EMA50/200 trend, local stop, 2R.
- `range_reentry`: Bollinger20/2 re-entry, ADX14 below 20, mean target.
- `sweep_reclaim`: 20-bar wick sweep and body reclaim, EMA200, 2R.
- `compression_break`: Compressed bands then 10-bar channel break, trend, 3R.
- `bos_baseline`: Existing BOS + CMF20 + SMA200 and structure exits.
- `lux_trendline`: ATR trendlines: length14, slope1, first close break, 2R.
- `lux_trendline_trend`: Same trendline break with EMA200 direction filter.

BOS here uses the common research session, costs, sizing and maximum-holding wrapper. These are not the same execution settings as the earlier live/BOS M30 replay, so the reports should not be compared as identical implementations.

## Coverage and verification

M5/M15 history spans the requested year, but there are missing intraday intervals. The following same-day gaps occur inside the study's daytime window; their origin is unverified. Holidays, weekends and other session closures also exist.

- M1: 99,999 bars, 2026-05-28 20:28:00 to 2026-09-11 22:37:00.
  - 2026-06-04 11:31:00 → 2026-06-04 11:34:00.
  - 2026-07-24 15:59:00 → 2026-07-24 16:02:00.
- M5: 99,999 bars, 2025-04-07 08:50:00 to 2026-09-11 22:30:00.
  - 2025-09-22 16:25:00 → 2025-09-22 16:55:00.
  - 2025-10-10 15:55:00 → 2025-10-10 16:10:00.
  - 2025-11-28 10:10:00 → 2025-11-28 10:20:00.
  - 2026-01-15 14:55:00 → 2026-01-15 15:10:00.
- M15: 60,000 bars, 2024-02-20 22:30:00 to 2026-09-11 22:15:00.
  - 2025-09-22 16:15:00 → 2025-09-22 16:45:00.

No same-day missing daytime interval was found in the recent-month window. This does not establish tick coverage. Data hashes, source hashes, settings and all attempted outcomes are retained in the manifest and CSV/JSON artifacts.

Accounting reconciled across 147 runs: every trade cumulative balance, daily net and ending equity agrees with its summary. There were 0 overnight trades and 0 day-gap exits across these runs (overlapping runs count repeated trades). Modeled external 4%/8% breach runs: 0. That count uses the stated static-floor assumptions and does not certify the firm's actual rules.

The repository test suite passed: 112 tests, including 13 candidate-signal tests and 20 simulator tests. Independent reviews checked signal causality, the published Lux recurrence, execution semantics, accounting assumptions and data gaps. Review findings led to explicit post-hoc labels and a source/data/configuration consistency check between screen and stress phases.

Reproduce with `.venv\Scripts\python.exe -m research.gold_intraday.run_study --phase all`, then `.venv\Scripts\python.exe -m research.gold_intraday.report_study`. Raw outputs: `logs/gold-intraday-20260912/` (local, ignored by Git). Research code: `research/gold_intraday/`. The first-11-month results are in `selection-results.json`; the frozen selection is `[]`.

The fixed settings were not tuned after viewing results. Nonetheless this is a multi-strategy historical screen, and any promising result needs new unseen data and verified execution/rules. [Source notes](2026-09-12-gold-intraday-sources.md).
