# CHFJPY session provenance and trend context — 17 September 2026

This is a bounded offline audit of existing source, cached prices and ledgers. No strategy optimization, live configuration change, MT5 connection or new simulated strategy was performed.

## What was selected

The archived research harness explicitly searches **144 session configurations**: 24 entry hours, three holds (3, 6, 12 bars), and two directions. `session_search` maximizes training net subject to at least 25 trades. ATR length14 and stop multiplier2 are fixed defaults in this grid, not searched dimensions. Walk-forward defaults are two training years and six testing months. The `session_hours` command also compares every hour with long/hold12 fixed, and the session command describes hour0/hold12 as the winning fold configuration before replaying it and its short mirror. Thus it would be incorrect to present the time, hold and direction as an entirely unselected hypothesis. [Archived harness](https://github.com/veeradyani222/t-raw/blob/665430a/wf_search.py).

The archived design explicitly intended walk-forward validation and warned against iterating to a green backtest. Its statement opposing blind grids must be distinguished from the actual code's 144-configuration grid. A walk-forward search can evaluate a selection procedure if cleanly conducted, but does not automatically validate a later pair and fixed rule chosen after reviewing results. [Archived design](https://github.com/veeradyani222/t-raw/blob/665430a/docs/2026-08-22-eurusd-strategy-search-design.md).

The archived launcher actually selected **USDJPY hour6**, long/hold12/ATR14x2. It did not deploy AUDJPY. The archived strategy docstring claims out-of-sample/cost validation, but that prose alone is not a CHFJPY validation record. No saved original AUDJPY fold-output record was located in this bounded audit, so the exact fold/date that first selected AUDJPY hour0 cannot be established. [Archived launcher](https://github.com/veeradyani222/t-raw/blob/665430a/run_live.py), [archived strategy](https://github.com/veeradyani222/t-raw/blob/665430a/trader/strategies/session.py), [September13 history](2026-09-13-jpy-session-history.md).

September13 research compared AUDJPY hour0 and USDJPY hour6. The subsequent pair screen applied the same hour0/12-hour long rule to EURJPY, GBPJPY, NZDJPY, CHFJPY and reference AUDJPY, without per-pair timing or stop optimization. This narrows one source of optimization but selecting CHFJPY after seeing its result still introduces pair-selection bias. The later guarded account comparison narrowed the universe to CHFJPY/EURJPY and changed fees/risk modeling; it did not create unseen market data. [Pair-screen code](../research/jpy_pair_screen.py), [pair-screen report](2026-09-13-jpy-pair-screen.md), [account comparison code](../research/jpy_account_comparison.py).

## Underlying price context versus existing strategy results

Underlying change is `100 * (last available close / first available close - 1)` within each specified window, using the cached CHFJPY H1 file. It is a descriptive spot-price change, not an executable buy-and-hold return: no financing, spread, leverage, USD conversion or matched exposure is included. Strategy results are the existing $10,000 base-cost guarded runs, with separate annual starts and a separate continuous September2025–August2026 run. [Prices](../data/session-chfjpy-h1-screen-20260913.csv), [results and ledger filenames](../logs/jpy-account-comparison-20260913/all-results.csv).

| Window | Underlying change | Strategy net | Trades | First static entry block | Last modeled exit |
|---|---:|---:|---:|---|---|
| 2016 | -4.906% | -$525.77 | 22 | Feb4 | Feb3 |
| 2017 | +0.636% | -$521.19 | 34 | Feb17 | Feb16 |
| 2018 | -3.320% | -$516.75 | 32 | Feb15 | Feb14 |
| 2019 | +0.948% | -$541.62 | 36 | Feb22 | Feb21 |
| 2020 | +4.009% | -$526.74 | 40 | Feb19 | Mar23 |
| 2021 | +8.076% | +$690.37 | 260 | None | Dec31 |
| 2022 | +12.274% | +$2,070.40 | 259 | None | Dec30 |
| 2023 | +18.247% | +$1,057.56 | 259 | None | Dec29 |
| 2024 | +3.358% | +$917.20 | 261 | None | Dec31 |
| 2025 | +14.018% | -$532.96 | 23 | Feb4 | Feb3 |
| Sep2025–Aug2026 | +7.649% | +$5,294.44 | 258 | None | Aug31,2026 |

All four profitable calendar years (2021–2024) had rising underlying prices, consistent with beneficial long exposure during an uptrend. This association does **not** establish that trend caused all profits or that hour0 has no incremental effect. There are eight rising-price calendar years but only four profitable strategy years. Especially, 2025 underlying rose14.018% while the fresh January strategy account lost$532.96 and stopped trading after February3. The later full-year drift cannot be equated with its actual traded exposure. Static entry blocks can sometimes cease when rounded lot risk fits remaining headroom; 2020 has executions after its first block, so first block is not always a permanent stop. [Guard implementation](../research/jpy_guarded_session.py), [ledger manifest](../logs/jpy-account-comparison-20260913/all-results.csv).

These ten independent annual trials have mean net+$157.05 and median net-$518.97, with four profitable years. The recent+$5,294.44 is a different start/path, overlaps prior selection history, and does not supersede the losing annual trials. The strategy is leveraged and volatility-sized with stops/guards; comparing its53% recent account return with7.649% spot appreciation is not evidence of excess return at matched risk.

## Evidence still needed to isolate a timing edge

The reviewed CHFJPY account comparison does not provide same-cost, same-risk comparisons against other entry hours, randomized daily windows, or buy-and-hold with matched exposure/risk; nor a documented untouched CHFJPY holdout selected before pair choice. The old harness contains an all-hours command, but that command's existence is not current CHFJPY evidence under the revised conversion, commission and guards. Those controls should retain the full candidate universe and specify the evaluation period before examining results. Neighboring times/holds/stops, another feed and broker-clock alignment would address robustness separately. These are missing validation controls, not a recommendation to optimize until a winner emerges.

Reproduce the descriptive table and reconciliation checks: `.venv\Scripts\python.exe -m research.chfjpy_provenance_trend`. [Read-only calculation](../research/chfjpy_provenance_trend.py).
