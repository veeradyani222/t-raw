# BOS monthly profit withdrawals — 12 September 2026

Same local live BOS M30 settings and data as the prior one-year replay: $10,000 start, 1% of remaining account equity per trade, $300 daily / $600 static total risk guard, periods from the 12th through the following 11th. Withdrawals occur after the final available candle of each period and affect subsequent sizing. Losses carry forward without deposits; the guard's permanent-halt state is never reset.

Two interpretations are shown: withdraw only balance above the original $10,000 (recover losses first), or withdraw every positive month's net gain even below $10,000. The latter is a mathematical cash-flow scenario; actual payout eligibility has not been established. All amounts are gross account withdrawals before any firm profit split, payout fees or taxes. No actual withdrawal was requested or performed.

Open positions carry across monthly boundaries, with original size/stops/targets. Withdrawal amounts use realized cash balance and ignore floating P&L. The final open position is marked to the final close as in the earlier replay. A real firm's requirement to close positions or use equity for payouts could change these results. Midnight daily anchors use the post-withdrawal balance on the next trading day; payouts are not booked as trading losses. The static $9,400 floor remains fixed as a model assumption; actual post-payout drawdown rules remain unverified.

## Recover $10,000 first, withdraw the excess

| Period start | Trading P&L | Withdrawn | Balance after withdrawal |
|---|---:|---:|---:|
| 2025-09-12 | $+21.23 | $21.23 | $10000.00 |
| 2025-10-12 | $+1210.11 | $1210.11 | $10000.00 |
| 2025-11-12 | $+302.18 | $302.18 | $10000.00 |
| 2025-12-12 | $+576.08 | $576.08 | $10000.00 |
| 2026-01-12 | $+806.17 | $806.17 | $10000.00 |
| 2026-02-12 | $-299.93 | $0.00 | $9700.07 |
| 2026-03-12 | $+149.05 | $0.00 | $9849.12 |
| 2026-04-12 | $+248.83 | $97.95 | $10000.00 |
| 2026-05-12 | $+314.77 | $314.77 | $10000.00 |
| 2026-06-12 | $+155.49 | $155.49 | $10000.00 |
| 2026-07-12 | $+68.21 | $68.21 | $10000.00 |
| 2026-08-12 | $-550.15 | $0.00 | $9449.85 |

Total withdrawn: $3552.19. Remaining account: $9449.85. Combined: $13002.04; net gain after the starting $10,000: $+3002.04. Trades: 273. Permanent halt: No.

## Withdraw every positive month's gain

| Period start | Trading P&L | Withdrawn | Balance after withdrawal |
|---|---:|---:|---:|
| 2025-09-12 | $+21.23 | $21.23 | $10000.00 |
| 2025-10-12 | $+1210.11 | $1210.11 | $10000.00 |
| 2025-11-12 | $+302.18 | $302.18 | $10000.00 |
| 2025-12-12 | $+576.08 | $576.08 | $10000.00 |
| 2026-01-12 | $+806.17 | $806.17 | $10000.00 |
| 2026-02-12 | $-299.93 | $0.00 | $9700.07 |
| 2026-03-12 | $+149.05 | $149.05 | $9700.07 |
| 2026-04-12 | $+248.83 | $248.83 | $9700.07 |
| 2026-05-12 | $-353.02 | $0.00 | $9347.05 |
| 2026-06-12 | $+0.00 | $0.00 | $9347.05 |
| 2026-07-12 | $+0.00 | $0.00 | $9347.05 |
| 2026-08-12 | $+0.00 | $0.00 | $9347.05 |

Total withdrawn: $3313.65. Remaining account: $9347.05. Combined: $12660.70; net gain after the starting $10,000: $+2660.70. Trades: 191. Permanent halt: 2026-05-26 03:00:00.

## Verification and limitations

The no-withdrawal control reproduced all 266 baseline trades' entries, exits, sizes, stops, targets and profits, with 128 winners and +$3,104.21. Signals were calculated by the original production signal function and cached by candle timestamp for reuse; each scenario still ran the production decision engine, position sizing, opposite-signal closes and risk guard. All monthly and trade-level accounting identities reconcile, including cumulative withdrawals.

These are hypothetical backtest cash balances. The inherited simulator has fixed spread, signal-close fills, stop-first OHLC ties, exact stop fills across gaps, closed-balance risk checks and no commission/swap/slippage/latency. Live uses floating equity. This analysis does not verify prop payout eligibility or guarantee future earnings. No production behavior, configuration or live orders changed.

Reproduce: `.venv\Scripts\python.exe -m research.bos_monthly_withdrawals`. Raw monthly tables, trade logs, source/data hashes, sanitized config and results are in `logs/bos-monthly-withdrawals-20260912/`.
