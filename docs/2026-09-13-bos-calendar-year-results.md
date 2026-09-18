# BOS January–December yearly results — 13 September 2026

Same current local main BOS M30 configuration: CMF20, MA200, 1% risk of remaining account balance, $300 daily and $600 static total loss guards, structure exits and opposite-signal closes. Each year starts a separate $10,000 account on January1, with preceding warmup. Full calendar years are 2019–2025. History starts in February2018, so 2018 is excluded. The 2026 row is January1 through September11, not a complete year and not annualized.

The withdrawal column uses the requested rule: withdraw every positive calendar month's realized gain, including when balance is below $10,000. Losses carry forward. Positions carry over month ends. For the final partial September period, the remaining position is marked at the last available close and positive realized gain is hypothetically withdrawn at the cutoff. Net profit is cash withdrawn plus remaining account minus $10,000; it is not just the withdrawal amount.

| Calendar year | Keep profits: net | Ending balance | Monthly withdrawals: cash out | Ending balance after withdrawals | Monthly withdrawals: net |
|---|---:|---:|---:|---:|---:|
| 2019 Jan–Dec | $-647.14 | $9352.86 | $164.67 | $9367.37 | $-467.96 |
| 2020 Jan–Dec | $-643.54 | $9356.46 | $990.17 | $9335.68 | $+325.85 |
| 2021 Jan–Dec | $-634.37 | $9365.63 | $479.37 | $9477.58 | $-43.05 |
| 2022 Jan–Dec | $-650.89 | $9349.11 | $0.00 | $9349.11 | $-650.89 |
| 2023 Jan–Dec | $-630.73 | $9369.27 | $189.01 | $9485.27 | $-325.72 |
| 2024 Jan–Dec | $-680.99 | $9319.01 | $245.65 | $9390.51 | $-363.84 |
| 2025 Jan–Dec | $+3024.94 | $13024.94 | $128.76 | $9289.55 | $-581.69 |
| 2026 YTD through Sep11 | $+1097.61 | $11097.61 | $1506.76 | $9359.08 | $+865.84 |

## Full-year averages (2019–2025 only)

| Policy | Mean net/year | Mean return/year | Profitable years | Years internally halted |
|---|---:|---:|---:|---:|
| none | $-123.25 | -1.23% | 1/7 | 6/7 |
| positive_month | $-301.04 | -3.01% | 1/7 | 7/7 |

These are arithmetic averages of independent yearly starts. Loss-limited years remain in the sample through December, including the zero-trade time after permanent halts. They are not a compounded return on a single surviving account. Different January/September start dates change capital, positions and risk-stop timing, so rebinning the older yearly totals would not reproduce these results.

| Year | Halt date: keep profits | Halt date: withdrawals |
|---|---|---|
| 2019 | 2019-04-11 14:00:00 | 2019-04-05 15:30:00 |
| 2020 | 2020-06-26 18:30:00 | 2020-05-01 18:00:00 |
| 2021 | 2021-07-26 15:00:00 | 2021-03-23 15:30:00 |
| 2022 | 2022-01-18 05:30:00 | 2022-01-18 05:30:00 |
| 2023 | 2023-03-02 09:00:00 | 2023-02-21 05:30:00 |
| 2024 | 2024-06-19 14:00:00 | 2024-02-29 12:00:00 |
| 2025 | No | 2025-03-26 16:00:00 |
| 2026 | No | 2026-05-25 01:00:00 |

## Verification and assumptions

The partial-period test verifies future candles are excluded and the final open position is marked before the cutoff payout. Both original September-year control scenarios reproduced every saved trade's price, size, profit and equity. January-boundary fast/production signal agreement was checked on 64 bars. Every run reconciles trade P&L, monthly P&L, cash payouts and ending balances.

Same simplified simulator as previous reports: fixed 3-pip spread, signal-close entries, stop-first OHLC ties, exact stop fills across gaps, closed-balance risk checks, no commission/swap/slippage/latency. Live checks floating equity. Static loss-floor and gross-withdrawal assumptions do not verify a firm's actual payout rules, splits, taxes or fees. Historical spans contain gaps and current settings were chosen using prior historical research. No live settings, trades or withdrawals were changed.

Reproduce with `.venv\Scripts\python.exe -m research.bos_calendar_years`. Monthly and trade logs, CSV/JSON tables, data/source hashes and sanitized configuration: `logs/bos-calendar-years-20260913/`.
