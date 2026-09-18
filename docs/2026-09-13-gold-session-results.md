# Gold hour-0 / 12-hour exit research - 13 September 2026

Exact transfer of the JPY research signal: long only, H1 bar labelled 00:00, enter at its completed close plus spread/slippage, stop at close minus twice the simple ATR14, no TP, close after 12 elapsed hours unless stopped first. With regular bars the entry is around 01:00 and timed exit around 13:00 in dataset clock. This is not a literal midnight order or a verified FundedNext timezone.

Gold rarely has an hour-0 bar on this feed. Missing midnight candles produce no entries; no replacement hour was selected or optimized. The 17 eligible candles in the latest 12 months are concentrated in October 2025 and March 2026. Fourteen trades execute; March 20, 23 and 24 are skipped because even 0.01 lot exceeds the 1% risk budget. The seasonal pattern suggests a clock/session-calendar effect, but its cause is not independently verified.

Data: 57063 H1 bars from 2017-01-03 01:00:00 through 2026-09-11 22:00:00. Two isolated 2009 records were excluded. 2017 is used as warmup; eight full calendar years 2018-2025 are reported. Source hashes and annual hour-0 counts are in results.json.

Each year independently starts flat at $10,000; the latest-12-month table is one continuous $10,000 account with no withdrawals. Target risk 1% of balance including estimated stopped-trade costs, max 1 lot, 0.01 step, 100oz/lot. Existing 3% daily / 6% static CLOSED-BALANCE guards: no new trades after a total halt. Gaps fill at opening price less slippage; stop takes priority over timed exit.

Cost scenarios: $0.30 or $0.60 price spread (3 or 6 gold pips at $0.10/pip), $0.03 slippage per fill, commission 0.0018% of notional on EACH side. This deliberately models the literal Stellar Lite general-page wording; it is not verified against a FundedNext account ledger. [FundedNext published conditions](https://fundednext.com/general-rules/cfds/symbols-and-conditions). Local terminal is MetaQuotes-Demo, not FundedNext. These costs are applied to all historical years to assess the strategy under this assumed current cost profile.

No swap, funded news-profit adjustment, intrabar floating-equity enforcement, margin model or FundedNext timezone mapping. Results do not certify prop-rule compliance or predict payouts. Trade ledger timestamps are bar labels, not exact fill timestamps. Live BOS code and strategy registry were not changed.

## Calendar years

| Year | Base net | Trades | Wide-spread net |
|---|---:|---:|---:|
| 2018 | $+0.00 | 0 | $+0.00 |
| 2019 | $+0.00 | 0 | $+0.00 |
| 2020 | $+45.95 | 5 | $+22.52 |
| 2021 | $-202.20 | 15 | $-252.17 |
| 2022 | $+155.92 | 15 | $+105.75 |
| 2023 | $+41.64 | 15 | $+7.27 |
| 2024 | $+360.26 | 19 | $+323.45 |
| 2025 | $+559.43 | 20 | $+526.67 |

Mean annual base profit: $+120.12, including zero-trade years. Full summary: `{'base': {'years': 8, 'mean_net': 120.1245539471298, 'profitable_years': 5, 'zero_trade_years': 2, 'halted_years': 0}, 'wide_spread': {'years': 8, 'mean_net': 91.68651630285488, 'profitable_years': 5, 'zero_trade_years': 2, 'halted_years': 0}}`.

## Latest 12 complete months: September 2025-August 2026

| Month | Base net | Trades | Ending balance |
|---|---:|---:|---:|
| 2025-09 | $+0.00 | 0 | $10000.00 |
| 2025-10 | $+21.59 | 5 | $10021.59 |
| 2025-11 | $+0.00 | 0 | $10021.59 |
| 2025-12 | $+0.00 | 0 | $10021.59 |
| 2026-01 | $+0.00 | 0 | $10021.59 |
| 2026-02 | $+0.00 | 0 | $10021.59 |
| 2026-03 | $-113.06 | 9 | $9908.53 |
| 2026-04 | $+0.00 | 0 | $9908.53 |
| 2026-05 | $+0.00 | 0 | $9908.53 |
| 2026-06 | $+0.00 | 0 | $9908.53 |
| 2026-07 | $+0.00 | 0 | $9908.53 |
| 2026-08 | $+0.00 | 0 | $9908.53 |

## Window summaries

| Window | Profile | Net | Trades | Win rate | Closed DD | Halt |
|---|---|---:|---:|---:|---:|---|
| 2026_YTD | base | $-113.06 | 9 | 33.33% | $202.49 | None |
| latest_12_months | base | $-91.47 | 14 | 35.71% | $209.12 | None |
| August_2026_fresh | base | $+0.00 | 0 | - | $0.00 | None |
| 2026_YTD | wide_spread | $-116.96 | 9 | 33.33% | $204.89 | None |
| latest_12_months | wide_spread | $-98.07 | 14 | 35.71% | $212.72 | None |
| August_2026_fresh | wide_spread | $+0.00 | 0 | - | $0.00 | None |
