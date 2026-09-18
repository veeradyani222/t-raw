# BOS yearly results over available history — 13 September 2026

Cached XAUUSD M30 history spans 2018-02-22 14:30:00 through 2026-09-11 21:30:00: 100,655 bars. There are 8 complete September-to-September years with at least 2,000 preceding warmup bars. A full ten-year test is unavailable. MT5 requests for 2016 and 2017 returned a single out-of-range 2018 bar, which was rejected as evidence of coverage. Existing cached early-2018 data was retained. The recent snapshot supersedes overlapping cached bars; overlap differences are logged in the manifest.

Every row is a new hypothetical $10,000 account with the same current local live BOS M30 settings, 1% risk, MA200, CMF20, 2-bar fractal swings, 2,000-bar context, structure exits, minimum1R / fallback3R, opposite-signal exits, $300 daily and $600 static total guard. No settings are tuned for individual years. Monthly cash-flow periods start on the 12th. Losing accounts remain stopped until that yearly run ends; the following row starts a separate account, not a reset of the same account.

The monthly-withdrawal variant pays out every positive month's realized gain even when the account is below $10,000, as requested. Losses remain in the account. Its net result is withdrawals plus ending account balance minus $10,000. Gross cash withdrawn alone is not net profit. The fixed $9,400 floor is a simulation assumption; actual firm's payout eligibility, split, fees and post-payout rules are unverified.

## Yearly comparison

Each period starts September 12 and ends September 11 of the following year. All net figures include losing years and the effect of risk stops.

| Year | Keep profits: net | Keep profits: ending balance | Monthly withdrawals: cash out | Monthly withdrawals: ending balance | Monthly withdrawals: net |
|---|---:|---:|---:|---:|---:|
| 2018–2019 | $-683.96 | $9316.04 | $0.00 | $9316.04 | $-683.96 |
| 2019–2020 | $-656.74 | $9343.26 | $0.00 | $9343.26 | $-656.74 |
| 2020–2021 | $-661.04 | $9338.96 | $706.08 | $9385.98 | $+92.06 |
| 2021–2022 | $-626.55 | $9373.45 | $0.00 | $9373.45 | $-626.55 |
| 2022–2023 | $-672.47 | $9327.53 | $450.39 | $9357.11 | $-192.50 |
| 2023–2024 | $+332.00 | $10332.00 | $2060.16 | $9391.58 | $+1451.74 |
| 2024–2025 | $+1092.61 | $11092.61 | $835.25 | $9340.42 | $+175.67 |
| 2025–2026 | $+3104.21 | $13104.21 | $3313.65 | $9347.05 | $+2660.70 |

## Averages across independent yearly starts

| Policy | Profitable years | Mean annual net | Mean annual return | Median annual net | Years halted | Mean cash withdrawn |
|---|---:|---:|---:|---:|---:|---:|
| none | 3/8 | $+153.51 | +1.54% | $-641.64 | 5/8 | $0.00 |
| positive_month | 4/8 | $+277.55 | +2.78% | $-50.22 | 8/8 | $920.69 |

These are arithmetic averages of separate $10,000 yearly trials, not a compounded multi-year return or a prediction of annual income. Halted years remain in the denominator; their zero-trade remainder is not omitted. Simulated losses can exceed $600 because the guard blocks new entries after the threshold is breached rather than guaranteeing an exit at exactly $9,400.

One account carried from 2018-09-12 through the entire history, with no withdrawals or yearly resets, ended at $9316.04; net $-683.96, 10 trades. Permanent halt: 2018-09-25 09:00:00. Thus independent yearly results must not be presented as what that one account would have earned.

## Halt dates

| Year start | Keeping profits | Monthly withdrawals |
|---|---|---|
| 2018-09-12 | 2018-09-25 09:00:00 | 2018-09-25 09:00:00 |
| 2019-09-12 | 2019-09-25 15:00:00 | 2019-09-25 15:00:00 |
| 2020-09-12 | 2021-03-29 04:00:00 | 2020-10-20 17:00:00 |
| 2021-09-12 | 2021-09-23 11:00:00 | 2021-09-23 11:00:00 |
| 2022-09-12 | 2022-12-28 19:30:00 | 2022-12-16 13:00:00 |
| 2023-09-12 | No | 2024-02-28 15:30:00 |
| 2024-09-12 | No | 2025-02-25 16:00:00 |
| 2025-09-12 | No | 2026-05-26 03:00:00 |

## Verification and limits

The existing fast BOS signal implementation matched the original production function on 383 deterministic checks spread across years, including actual signal bars and year boundaries. It ran through the same production decision engine and cash-flow simulator. Both recent-year variants reproduced every saved trade's entry, exit, size, stop, target, profit and post-trade equity. Trade P&L, monthly P&L, withdrawals and ending balances reconciled in all yearly runs.

The execution model remains deliberately simplified: fixed 3-pip spread, signal-close entry, stop-first OHLC ties, exact stop fills across gaps, closed-balance guards, and no commission, swap, slippage or latency. Live risk uses floating equity. History spans the stated dates but is not certified gap-free or tick-complete. The current strategy was selected using historical research; this is retrospective application of current settings, not eight years of live or fully unseen performance. No live strategy, risk setting, order or payout changed.

Reproduce with `.venv\Scripts\python.exe -m research.bos_long_history`. Data/provenance, complete monthly and trade logs, yearly results and averages are in `logs/bos-long-history-20260913/`.

Additional verification: 41 BOS, backtest, risk and withdrawal tests passed. A separate aggregation of all 16 saved monthly ledgers reproduced annual profit, payouts, ending balances and both annual averages. Each yearly dataset contained 11,576?11,875 bars, with no gap longer than seven days; maximum observed gaps were 73.5?76.5 hours. This is a span check, not proof that every expected bar or tick exists. Coverage details are in `coverage-audit.json`.
