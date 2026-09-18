# Other pairs for the 12-hour session strategy — 13 September 2026

Fixed candidates before results: EURJPY, GBPJPY, NZDJPY, CHFJPY. AUDJPY is the reference. All use the same hour0 H1 closed-bar long signal, 2 times simple ATR14 stop, no take-profit, and 12 elapsed hours maximum holding until the next executable bar close. No timing or stop parameters were optimized per pair. A completed hour0 candle entry is modeled at its close, not at exactly midnight. Dataset/broker clock is retained; its market-session/DST interpretation is not independently verified.

Each simulation starts a separate $10,000 account, 1% modeled balance risk, maximum1 lot and 0.01 lot steps, with the existing $300 daily / $600 static total closed-balance guard. The base spread is 2.5 pips for every pair; wide-spread sensitivity uses5 pips. Both include assumed $7/lot round-trip commission and0.1 pip slippage per market fill, plus JPY-to-USD conversion. Swap/conversion spread and floating-equity risk checks are not included. These are controlled cost assumptions, not verified pair-specific execution costs.

Latest year means September1,2025–August31,2026. Latest month means August2026. Calendar-year averages use separate annual starts and include halted years. AUDJPY is rerun at the higher common costs, so its numbers differ from the earlier 1.5-pip report. All accounts are standalone; no shared-account portfolio or payout model is tested here.

## Comparison

| Pair | Mean annual net: 2.5 pips | Profitable years | Mean annual net: 5 pips | Last year: 2.5 pips | Last year: 5 pips | August2026: 2.5 pips |
|---|---:|---:|---:|---:|---:|---:|
| EURJPY | $+335.76 | 5/10 | $-456.87 | $+2589.36 | $+711.01 | $+272.27 |
| GBPJPY | $+540.20 | 4/10 | $+6.63 | $+4801.24 | $+2967.84 | $+269.03 |
| NZDJPY | $+164.61 | 4/10 | $-583.41 | $-613.71 | $-665.30 | $+344.72 |
| CHFJPY | $+350.11 | 4/10 | $-352.06 | $+6312.35 | $+4186.52 | $+406.22 |
| AUDJPY | $+227.10 | 3/10 | $-467.20 | $+3248.64 | $+967.18 | $+823.45 |

## Risk-stop and median results

| Pair | Median annual net: base | Halted years: base | Profitable years: wide | Halted years: wide | Recent year halted: base / wide |
|---|---:|---:|---:|---:|---|
| EURJPY | $-249.56 | 5/10 | 1/10 | 9/10 | No / No |
| GBPJPY | $-607.60 | 6/10 | 3/10 | 7/10 | No / No |
| NZDJPY | $-548.65 | 6/10 | 0/10 | 9/10 | 2025-11-05 03:00:00 / 2025-10-16 03:00:00 |
| CHFJPY | $-611.85 | 6/10 | 2/10 | 8/10 | No / No |
| AUDJPY | $-609.21 | 7/10 | 2/10 | 8/10 | No / No |

## All annual attempts

| Pair | Year | Base net | Wide-spread net |
|---|---|---:|---:|
| EURJPY | 2016 | $-665.17 | $-610.49 |
| EURJPY | 2017 | $-686.89 | $-657.99 |
| EURJPY | 2018 | $-616.00 | $-628.30 |
| EURJPY | 2019 | $-619.21 | $-641.86 |
| EURJPY | 2020 | $-653.67 | $-659.67 |
| EURJPY | 2021 | $+1547.39 | $-626.67 |
| EURJPY | 2022 | $+1354.93 | $-633.16 |
| EURJPY | 2023 | $+116.87 | $-640.63 |
| EURJPY | 2024 | $+853.05 | $-618.50 |
| EURJPY | 2025 | $+2726.32 | $+1148.54 |
| GBPJPY | 2016 | $-603.06 | $-668.30 |
| GBPJPY | 2017 | $-637.96 | $-604.84 |
| GBPJPY | 2018 | $-614.14 | $-614.89 |
| GBPJPY | 2019 | $-612.14 | $-673.03 |
| GBPJPY | 2020 | $-628.54 | $-687.17 |
| GBPJPY | 2021 | $+4347.17 | $+2326.08 |
| GBPJPY | 2022 | $+1475.99 | $+447.73 |
| GBPJPY | 2023 | $+163.76 | $-613.05 |
| GBPJPY | 2024 | $+3142.92 | $+1836.60 |
| GBPJPY | 2025 | $-632.06 | $-682.84 |
| NZDJPY | 2016 | $-670.09 | $-609.61 |
| NZDJPY | 2017 | $-674.20 | $-644.91 |
| NZDJPY | 2018 | $-492.97 | $-631.74 |
| NZDJPY | 2019 | $-638.09 | $-612.73 |
| NZDJPY | 2020 | $-674.32 | $-683.42 |
| NZDJPY | 2021 | $+2066.34 | $-187.97 |
| NZDJPY | 2022 | $+1133.01 | $-628.97 |
| NZDJPY | 2023 | $+1767.65 | $-604.39 |
| NZDJPY | 2024 | $+433.09 | $-620.74 |
| NZDJPY | 2025 | $-604.34 | $-609.63 |
| CHFJPY | 2016 | $-623.11 | $-676.09 |
| CHFJPY | 2017 | $-629.57 | $-618.85 |
| CHFJPY | 2018 | $-660.07 | $-610.42 |
| CHFJPY | 2019 | $-620.34 | $-527.90 |
| CHFJPY | 2020 | $-628.87 | $-605.48 |
| CHFJPY | 2021 | $+1396.01 | $-627.72 |
| CHFJPY | 2022 | $+2704.69 | $+1106.29 |
| CHFJPY | 2023 | $+1632.69 | $+368.83 |
| CHFJPY | 2024 | $+1533.02 | $-651.50 |
| CHFJPY | 2025 | $-603.36 | $-677.73 |
| AUDJPY | 2016 | $-604.57 | $-641.61 |
| AUDJPY | 2017 | $-641.46 | $-645.34 |
| AUDJPY | 2018 | $-682.63 | $-603.39 |
| AUDJPY | 2019 | $-658.36 | $-602.49 |
| AUDJPY | 2020 | $-637.85 | $-629.38 |
| AUDJPY | 2021 | $-602.13 | $-613.85 |
| AUDJPY | 2022 | $+1694.97 | $+136.56 |
| AUDJPY | 2023 | $-613.85 | $-613.68 |
| AUDJPY | 2024 | $+2242.10 | $+225.43 |
| AUDJPY | 2025 | $+2774.82 | $-684.22 |

## Interpretation and source context

This is an exploratory historical pair screen. Choosing the best-looking pair afterward creates selection bias, even without a parameter grid. A strong recent year alone is insufficient; the annual median, losing years and cost sensitivity matter. All these long positions sell JPY, so combining them increases shared yen exposure rather than establishing independent returns. No correlation or joint-account drawdown test was performed.

Time-of-day currency effects have been documented in primary research, including depreciation during a currency's local trading hours. This motivates testing a time-window hypothesis; it does not establish that our broker's hour0, 12-hour long strategy works for any particular pair. [Breedon and Ranaldo, Intraday Patterns in FX Returns and Order Flow](https://onlinelibrary.wiley.com/doi/10.1111/jmcb.12032).

The simulator's JPY profit conversion follows the contract-size/price-change arithmetic, with an approximate historical conversion rate for cross-pair intrabar exits. [MetaQuotes profit formulas](https://www.mql5.com/en/book/automation/experts/experts_ordercalcprofit). Stop-first OHLC fills, previous-USDJPY-close conversion on cross-pair stops and closed-balance guards do not certify real execution or prop-firm compliance. Data spans and dropped FX-conversion rows are recorded in the manifest; history is not certified gap-free.

No live strategy, setting or order was changed. Reproduce with `.venv\Scripts\python.exe -m research.jpy_pair_screen`. Every trade, attempted result, data/source hash and summary is in `logs/jpy-pair-screen-20260913/`.

Verification completed: 15 JPY execution/risk tests passed. All120 saved trade ledgers independently reconcile to their run summaries, and all10 pair/cost annual averages were independently recalculated from the individual yearly results. CHFJPY history arrived after an initial partial screen; the final report includes all five pairs.
