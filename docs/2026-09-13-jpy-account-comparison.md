# CHFJPY and EURJPY account comparison - 13 September 2026

Historical prices are from the MetaQuotes-Demo research feed, not FundedNext quotes. The earlier pair-screen latest-year results were reproduced exactly before changing costs and guard modeling.

Same H1 hour-0 completed-candle long signal, simple ATR14 x2 stop, no take-profit, exit after 12 elapsed hours unless stopped first. Dataset clock retained: hour0 is an H1 opening label; regular execution is around 01:00 and timed exit around 13:00. FundedNext clock mapping is unverified.

Each pair is a separate account. Each Jan-Dec year independently starts at $10,000 or $50,000; the latest twelve months are one continuous account beginning September 1, 2025. No deposits or withdrawals. Do not sum separate pair results as a shared portfolio.

Target risk is 1% of current balance, including modeled stop execution costs. 0.01 lot steps; the historical 1-lot cap at $10k is scaled to 5 lots at $50k. These are separately simulated accounts, not profit multiplied by five. Rounding, caps and guard decisions can alter proportionality.

Base spread 2.5 pips; wide-spread sensitivity 5 pips; 0.1 pip slippage per market fill; commission $14 per lot round trip ($7 each side). This is the cautious literal interpretation of the Stellar Lite general page, not a verified FundedNext account charge. Actual spreads remain unmeasured. [FundedNext costs](https://fundednext.com/general-rules/cfds/symbols-and-conditions). Previous screen used $7 total commission, closed-balance checks and no entry-budget check; its profits should not be substituted into these tables.

Internal daily allowance $300/$1,500 and static floor $9,400/$47,000. Full-size entries are rejected if modeled stopped-trade risk would exceed remaining daily/static headroom; open losses are monitored at bar open, adverse low and close, with a liquidation-cost reserve. Guard exit takes priority if its price is above the strategy SL. Gaps exit at actual modeled open, so losses beyond limits are recorded, never clipped. Daily reset follows dataset midnight and realized balance; these timestamps have not been mapped independently to FundedNext server time. [Daily rule](https://help.fundednext.com/en/articles/8019811-how-can-i-calculate-the-daily-loss-limit).

JPY profit converts to USD using contemporary USDJPY closes for scheduled exits and previous closes for intrabar exits. H1 OHLC cannot establish tick sequencing or exact simultaneous conversion prices. No swap history, news-profit adjustment, margin simulation, actual execution quotes or payout split. This tests stated drawdown buffers under assumptions; it is not a guarantee of FundedNext compliance. $50k results are hypothetical: current FundedNext policy prohibits automation at $50k and above. [EA policy](https://help.fundednext.com/en/articles/8020763-is-ea-allowed-in-fundednext).

## Calendar years: base costs

| Year | CHFJPY $10k | CHFJPY $50k | EURJPY $10k | EURJPY $50k |
|---|---:|---:|---:|---:|
| 2016 | $-525.77* | $-2,641.75* | $-543.47* | $-2,728.63* |
| 2017 | $-521.19* | $-2,686.54* | $-565.98* | $-2,908.90* |
| 2018 | $-516.75* | $-2,620.52* | $-547.41* | $-2,811.30* |
| 2019 | $-541.62* | $-2,705.64* | $-511.74* | $-2,974.37* |
| 2020 | $-526.74* | $-2,597.87* | $-562.16* | $-2,834.40* |
| 2021 | $+690.37 | $+3,438.87 | $+875.56 | $+4,229.58 |
| 2022 | $+2,070.40 | $+10,456.01 | $-581.17* | $-2,558.57* |
| 2023 | $+1,057.56 | $+5,452.47 | $-342.51 | $-1,654.16 |
| 2024 | $+917.20 | $+4,617.13 | $+290.17 | $+1,483.25 |
| 2025 | $-532.96* | $-2,670.70* | $+1,505.42* | $-2,587.02* |
| **Annual mean** | **$+157.05 (+1.57%)** | **$+804.15 (+1.61%)** | **$-98.33 (-0.98%)** | **$-1,534.45 (-3.07%)** |

* A static guard hit or insufficient headroom prevented one or more entries. Losing and limited years remain in the arithmetic average.

## Latest twelve months: September 2025-August 2026

| Month | CHFJPY $10k | CHFJPY $50k | EURJPY $10k | EURJPY $50k |
|---|---:|---:|---:|---:|
| Sep 2025 | $+836.88 | $+4,273.63 | $+399.50 | $+2,025.42 |
| Oct 2025 | $+511.62 | $+2,640.03 | $+67.50 | $+410.64 |
| Nov 2025 | $+642.23 | $+3,264.52 | $+285.34 | $+1,457.18 |
| Dec 2025 | $+582.66 | $+2,930.32 | $+248.15 | $+1,252.33 |
| Jan 2026 | $+464.78 | $+2,361.02 | $+81.05 | $+414.36 |
| Feb 2026 | $+617.78 | $+3,200.28 | $+215.44 | $+1,058.07 |
| Mar 2026 | $-807.64 | $-4,093.27 | $-850.04 | $-4,310.65 |
| Apr 2026 | $+968.13 | $+4,963.13 | $+709.94 | $+3,585.87 |
| May 2026 | $+499.85 | $+2,513.70 | $-71.80 | $-356.48 |
| Jun 2026 | $+279.58 | $+1,440.50 | $+233.29 | $+1,182.17 |
| Jul 2026 | $+175.56 | $+882.26 | $+129.25 | $+650.94 |
| Aug 2026 | $+523.00 | $+2,634.89 | $+235.54 | $+1,185.59 |
| **Total** | **$+5,294.44** | **$+27,011.01** | **$+1,683.17** | **$+8,555.44** |
| **Ending balance** | **$15,294.44** | **$77,011.01** | **$11,683.17** | **$58,555.44** |

## Guard and spread sensitivity

| Pair/account | Profile | Recent net | Trades | Lowest modeled liquidation equity | Maximum daily loss | Internal daily/static breaches | Firm 4%/8% breaches |
|---|---|---:|---:|---:|---:|---|---|
| CHFJPY / $10,000 | base | $+5,294.44 | 258 | $9,978.58 | $151.18 | 0 / 0 | 0 / 0 |
| CHFJPY / $10,000 | wide | $+3,429.57 | 258 | $9,975.03 | $133.29 | 0 / 0 | 0 / 0 |
| CHFJPY / $50,000 | base | $+27,011.01 | 258 | $49,892.90 | $771.44 | 0 / 0 | 0 / 0 |
| CHFJPY / $50,000 | wide | $+17,191.73 | 258 | $49,872.57 | $673.61 | 0 / 0 | 0 / 0 |
| EURJPY / $10,000 | base | $+1,683.17 | 258 | $9,988.35 | $117.31 | 0 / 0 | 0 / 0 |
| EURJPY / $10,000 | wide | $+2.08 | 258 | $9,593.75 | $105.85 | 0 / 0 | 0 / 0 |
| EURJPY / $50,000 | base | $+8,555.44 | 258 | $49,941.42 | $594.20 | 0 / 0 | 0 / 0 |
| EURJPY / $50,000 | wide | $+66.51 | 258 | $47,956.18 | $537.84 | 0 / 0 | 0 / 0 |

EURJPY calendar 2025 differs sharply across account sizes: the $10k run blocked 41 entries near its static floor but could later resume when rounded lot risk fit the remaining headroom; the $50k run blocked 233 entries and did not resume after February 6. This makes outcomes sensitive to minimum lot steps and the entry-budget rule. It is not evidence that a smaller account has a reliable advantage.

Validation: 27 simulator/risk tests passed. An independent ledger check reconciled all 88 runs, 9,450 trade rows, eight annual means and 96 monthly rows, including fees, USD conversion, sizing, timing and ending balances. No modeled 3%/6% or 4%/8% threshold breaches occurred across these runs; many historical years stopped accepting trades because remaining headroom was insufficient. Unmodeled execution and firm-specific rules still matter.

All 88 runs, detailed guard events/counts, annual wide-spread results, monthly ending balances, input hashes and trade ledgers are under `logs/jpy-account-comparison-20260913/`. Reproduce with `.venv\Scripts\python.exe -m research.jpy_account_comparison`. Live BOS settings and registry were not changed.
