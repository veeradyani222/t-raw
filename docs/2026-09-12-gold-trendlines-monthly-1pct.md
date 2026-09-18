# Gold trendline breakouts: monthly results at 1% risk

Tested on 12 September 2026. The 12 completed calendar months are September 2025 through August 2026. September 2026 through the 11th is a separate partial-month result. Every timeframe is a separate hypothetical $10,000 account; these are not simultaneous positions in a shared account.

The existing unfiltered LuxAlgo-style length14 / multiplier1 / ATR trendline candidate is unchanged: first confirmed close above resistance buys, first close below support sells. Wick-only crossings do not qualify. Pivot confirmation waits 14 bars, with no backpainted entries. No EMA200, TRAMA or RSI filter. Stops are 1.5 ATR, targets 2R from signal close, maximum holding time 180 minutes (36 M5 / 12 M15 / 6 M30 / 3 H1 bars). Gaps and trading costs can change the executed reward/risk ratio.

Risk is up to 1% of current cash equity per trade, initially $100. Lot rounding, a 1-lot cap and remaining loss headroom can reduce actual risk. Internal buffers remain 3% daily / 6% static total; the model separately checks the user-confirmed external 4% / 8%. This does not change the live risk setting or enable this strategy live.

Entries use the next available bar open between 07:00 and 18:59, with forced closing from 20:00, one position at a time. All times and the daily reset use dataset timestamps. Base costs remain a $0.30/ounce spread floor (or recorded spread if higher), $7/lot round-trip commission and $0.03/ounce adverse slippage on market fills. Recorded spread above $0.60 blocks new entries. Costs and exact firm rules are not independently verified.

## One account carried through all 12 months

Dollar P&L after modeled costs. Balance, risk sizing and the original $9,400 loss floor carry forward. Each cell shows net P&L and closed trade count. Zero with no trades can mean the account has insufficient loss headroom for the minimum lot; it does not mean the strategy had a flat month of trading.

| Month | M5 | M15 | M30 | H1 |
|---|---:|---:|---:|---:|
| 2025-09 | $-597.82 (18) | $+661.13 (34) | $-262.57 (22) | $-264.39 (5) |
| 2025-10 | $+0.00 (0) | $+1860.65 (37) | $-15.31 (19) | $+75.18 (8) |
| 2025-11 | $+0.00 (0) | $-1428.92 (39) | $-268.03 (20) | $+13.91 (11) |
| 2025-12 | $+0.00 (0) | $-185.67 (40) | $-50.19 (3) | $-333.58 (11) |
| 2026-01 | $+0.00 (0) | $-632.64 (43) | $+0.00 (0) | $-82.01 (2) |
| 2026-02 | $+0.00 (0) | $+81.81 (40) | $+0.00 (0) | $+0.00 (0) |
| 2026-03 | $+0.00 (0) | $-43.02 (44) | $+0.00 (0) | $+0.00 (0) |
| 2026-04 | $+0.00 (0) | $-906.47 (30) | $+0.00 (0) | $+0.00 (0) |
| 2026-05 | $+0.00 (0) | $+0.00 (0) | $+0.00 (0) | $+0.00 (0) |
| 2026-06 | $+0.00 (0) | $+0.00 (0) | $+0.00 (0) | $+0.00 (0) |
| 2026-07 | $+0.00 (0) | $+0.00 (0) | $+0.00 (0) | $+0.00 (0) |
| 2026-08 | $+0.00 (0) | $+0.00 (0) | $+0.00 (0) | $+0.00 (0) |
| **Year total** | **$-597.82** | **$-593.14** | **$-596.09** | **$-590.89** |

| Timeframe | Final equity | Year trades | Profit factor | Float peak-to-trough DD | Worst day loss | Last trade |
|---|---:|---:|---:|---:|---:|---|
| M5 | $9402.18 | 18 | 0.465 | 9.71% | 2.98% | 2025-09-05 14:35:00 |
| M15 | $9406.86 | 307 | 0.964 | 34.13% | 3.00% | 2026-04-23 09:45:00 |
| M30 | $9403.91 | 64 | 0.764 | 7.97% | 1.59% | 2025-12-02 17:00:00 |
| H1 | $9409.11 | 37 | 0.501 | 6.17% | 0.96% | 2026-01-16 15:00:00 |

Drawdown above is the maximum floating peak-to-trough dollar decline divided by the starting $10,000. It can exceed 6% after accumulated profits without crossing a static $9,400 floor. It is not a trailing-rule compliance measurement.

## Fresh $10,000 account each month

These independent monthly starts show later-month behavior even if the continuous account stopped earlier. Each month resets balance and loss buffers; profits are not carried forward. Do not add these cells and call the sum one account's yearly return. A $100 gain/loss is +1%/-1% of the monthly starting account. Parentheses contain closed trade counts.

| Month | M5 | M15 | M30 | H1 |
|---|---:|---:|---:|---:|
| 2025-09 | $-597.82 (18) | $+661.13 (34) | $-262.57 (22) | $-264.39 (5) |
| 2025-10 | $-597.89 (17) | $+1807.27 (37) | $-82.94 (19) | $+75.39 (8) |
| 2025-11 | $-597.94 (96) | $-597.00 (15) | $-146.69 (20) | $+0.78 (11) |
| 2025-12 | $-599.32 (53) | $-593.47 (23) | $+18.40 (18) | $-330.53 (11) |
| 2026-01 | $-599.45 (26) | $-589.80 (29) | $-339.51 (18) | $-82.52 (4) |
| 2026-02 | $-589.18 (68) | $-4.97 (40) | $-121.59 (25) | $-1.61 (9) |
| 2026-03 | $+1159.27 (109) | $-9.09 (44) | $+507.72 (24) | $+105.14 (14) |
| 2026-04 | $-598.83 (41) | $-591.28 (11) | $+12.48 (15) | $-235.43 (10) |
| 2026-05 | $-597.92 (43) | $-594.34 (28) | $-129.92 (18) | $+54.96 (13) |
| 2026-06 | $+539.44 (97) | $+95.19 (41) | $-353.43 (17) | $-14.72 (7) |
| 2026-07 | $-598.04 (27) | $+587.54 (36) | $+245.36 (21) | $-282.81 (12) |
| 2026-08 | $-596.30 (58) | $-575.50 (40) | $-387.96 (19) | $+129.93 (13) |
| 2026-09 (through 11th) | $+897.04 (41) | $+140.21 (15) | $-138.09 (7) | $-82.18 (8) |

| Timeframe | Profitable completed months / 12 | Months touching below $9,410 | Worst month | Best month |
|---|---:|---:|---:|---:|
| M5 | 2 | 10 | $-599.45 | $+1159.27 |
| M15 | 4 | 4 | $-597.00 | $+1807.27 |
| M30 | 4 | 0 | $-387.96 | $+507.72 |
| H1 | 5 | 0 | $-330.53 | $+129.93 |

## Verification and limits

All 56 simulations reconciled trade P&L, cumulative equity, daily P&L and reported ending equity. Planned stop loss including fees was checked against the 1% budget. No trade crossed a calendar date. Modeled external 4%/8% breach runs: 0. Internal daily-halt events across these overlapping runs: 0. Risk guards restrict entries rather than inventing fills at a loss threshold.

The same OHLC adverse-first approximation is used on every timeframe; a stop wins when both stop and target lie inside a bar. Larger bars leave more unknown intrabar ordering. No lower-timeframe or real-tick replay was used to resolve M30/H1 fills. A 1% target risk is not a guarantee against gaps or actual firm-rule breaches. [MetaQuotes on OHLC testing](https://www.mql5.com/en/docs/runtime/testing).

Data spans the year with prior warmup, but missing intervals remain. Same-day daytime gaps within the requested span:

- M5: 2025-04-07 08:50:00 to 2026-09-11 22:30:00; gaps: 2025-09-22 16:25:00 to 2025-09-22 16:55:00; 2025-10-10 15:55:00 to 2025-10-10 16:10:00; 2025-11-28 10:10:00 to 2025-11-28 10:20:00; 2026-01-15 14:55:00 to 2026-01-15 15:10:00.
- M15: 2024-02-20 22:30:00 to 2026-09-11 22:15:00; gaps: 2025-09-22 16:15:00 to 2025-09-22 16:45:00.
- M30: 2024-07-24 07:00:00 to 2026-09-11 22:00:00; gaps: none found.
- H1: 2022-06-14 15:00:00 to 2026-09-11 21:00:00; gaps: none found.

The historical feed is MT5 XAUUSD, not the OANDA screenshot feed. Pivot/tie and TradingView parity are not certified. Firm reset timezone, static-versus-trailing rules, news restrictions and real account charges remain unresolved. The results are historical tests, not proof of future profitability.

Run `.venv\Scripts\python.exe -m research.gold_intraday.run_monthly_trendlines` to reproduce. CSV/JSON monthly tables, every trade and daily ledger, data hashes, source hashes and configuration are in `logs/gold-trendlines-monthly-1pct-20260912/`. Prior methodology and source notes: [original study](2026-09-12-gold-intraday-results.md).
