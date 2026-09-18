# AUDJPY and USDJPY session strategy history — 13 September 2026

Candidates: AUDJPY H1 signal hour0 and USDJPY H1 signal hour6, long only, 2 times ATR14 stop, no take profit, exit after 12 elapsed hours unless stopped first. Signals use the completed H1 bar with that opening-hour label; executable entry is modeled at its close plus costs. Thus hour0 is not an order precisely at midnight. Times are dataset/broker labels, not independently verified local/UTC trading-session times.

GitHub main was checked remotely at f41d13e. The archived live configuration at commit665430a enabled USDJPY hour6, not AUDJPY. AUDJPY hour0 is the research candidate checked here; its former live deployment was not found. The pure archived strategy matched 160 sampled signals in the initial recheck. Nothing was restored to the live registry.

All yearly and fresh-month runs start flat at $10,000 with 1% modeled balance risk, maximum1 lot, 0.01 lot steps, and existing $300 daily / $600 static total closed-balance guard. Commission is assumed $7/lot round-trip, slippage0.1 pip per market fill, spread1.5 pips AUDJPY / 1 pip USDJPY. These are assumptions, not verified account costs. Historical zero bar-spread fields are not treated as free execution. No monthly withdrawals.

JPY P&L is converted to USD using USDJPY: same-symbol exit price for USDJPY and contemporaneous USDJPY close for AUDJPY scheduled exits, previous close for AUDJPY intrabar stops. Currency-conversion spread is not modeled. This replaces the old harness's fixed $10/pip-per-lot shortcut. Both pairs have 100,000-unit contracts. [MetaQuotes profit formulas](https://www.mql5.com/en/book/automation/experts/experts_ordercalcprofit).

## Full calendar years

Each row independently starts January1 and ends December31. A halted account stays stopped until its row ends; the next year is a separate fresh account.

| Year | AUDJPY hour0 net | USDJPY hour6 net |
|---|---:|---:|
| 2016 | $-662.24 | $-627.52 |
| 2017 | $-623.70 | $-618.43 |
| 2018 | $-675.31 | $-684.58 |
| 2019 | $-685.50 | $-686.57 |
| 2020 | $-647.20 | $-625.35 |
| 2021 | $+1364.77 | $-601.33 |
| 2022 | $+2412.43 | $-649.94 |
| 2023 | $+1118.53 | $+738.75 |
| 2024 | $+3264.70 | $+2340.39 |
| 2025 | $+3861.16 | $-618.98 |
| **Mean annual net** | **$+872.77 (+8.73%)** | **$-203.36 (-2.03%)** |

- AUDJPY: 5/10 profitable calendar years; 5/10 internally halted. Arithmetic yearly mean includes all losing and halted years.
- USDJPY: 2/10 profitable calendar years; 8/10 internally halted. Arithmetic yearly mean includes all losing and halted years.

2026 is partial and excluded from the averages:

| Jan1–Sep4, 2026 | Net |
|---|---:|
| AUDJPY | $+1820.85 |
| USDJPY | $+59.63 |

## Latest 12 complete months: September2025–August2026

The continuous columns use one $10,000 account for the window, with profits/losses and positions carried forward. Fresh columns start each individual month at $10,000; they cannot be summed as a single account's return. A zero with zero trades may reflect a prior permanent halt.

| Month | AUDJPY continuous net (trades) | USDJPY continuous net (trades) | AUDJPY fresh-month net | USDJPY fresh-month net |
|---|---:|---:|---:|---:|
| 2025-09 | $+902.73 (22) | $-26.73 (22) | $+902.73 | $-26.73 |
| 2025-10 | $+315.34 (23) | $-230.76 (23) | $+289.74 | $-233.66 |
| 2025-11 | $-54.87 (20) | $-355.03 (10) | $-51.22 | $+234.01 |
| 2025-12 | $+761.63 (22) | $+0.00 (0) | $+682.64 | $+160.54 |
| 2026-01 | $+508.34 (21) | $+0.00 (0) | $+420.12 | $+34.85 |
| 2026-02 | $+101.41 (19) | $+0.00 (0) | $+89.46 | $+218.05 |
| 2026-03 | $-48.16 (22) | $+0.00 (0) | $-35.22 | $+155.55 |
| 2026-04 | $+693.61 (22) | $+0.00 (0) | $+558.69 | $-265.65 |
| 2026-05 | $-302.35 (21) | $+0.00 (0) | $-230.80 | $-194.35 |
| 2026-06 | $-371.37 (22) | $+0.00 (0) | $-288.49 | $+52.31 |
| 2026-07 | $+640.93 (23) | $+0.00 (0) | $+503.13 | $+13.58 |
| 2026-08 | $+1235.06 (21) | $+0.00 (0) | $+942.29 | $+270.29 |

## January–December2025

The continuous columns use one $10,000 account for the window, with profits/losses and positions carried forward. Fresh columns start each individual month at $10,000; they cannot be summed as a single account's return. A zero with zero trades may reflect a prior permanent halt.

| Month | AUDJPY continuous net (trades) | USDJPY continuous net (trades) | AUDJPY fresh-month net | USDJPY fresh-month net |
|---|---:|---:|---:|---:|
| 2025-01 | $+18.18 (22) | $-618.98 (20) | $+18.18 | $-618.98 |
| 2025-02 | $-247.40 (20) | $+0.00 (0) | $-248.45 | $-601.74 |
| 2025-03 | $+31.19 (21) | $+0.00 (0) | $+30.64 | $-631.27 |
| 2025-04 | $+32.80 (22) | $+0.00 (0) | $+44.38 | $-663.84 |
| 2025-05 | $+228.32 (22) | $+0.00 (0) | $+229.30 | $+1097.83 |
| 2025-06 | $+121.40 (21) | $+0.00 (0) | $+119.36 | $-111.85 |
| 2025-07 | $+710.27 (23) | $+0.00 (0) | $+698.26 | $+1603.22 |
| 2025-08 | $+701.38 (21) | $+0.00 (0) | $+633.91 | $-137.91 |
| 2025-09 | $+1050.34 (22) | $+0.00 (0) | $+902.73 | $-26.73 |
| 2025-10 | $+376.18 (23) | $+0.00 (0) | $+289.74 | $-233.66 |
| 2025-11 | $-54.67 (20) | $+0.00 (0) | $-51.22 | $+234.01 |
| 2025-12 | $+893.18 (22) | $+0.00 (0) | $+682.64 | $+160.54 |

## Limitations and verification

The common history cutoff is September4, 2026 because AUDJPY's available feed stops there; USDJPY's additional week was not used to create an unequal comparison. Older history was fetched for December2015 onward so January2016 has indicator warmup. Finite OHLC, unique chronological timestamps and available FX conversion were checked; history is not certified gap-free. No exchange-rate row more than three hours stale is carried forward.

The model handles stop-before-time-exit priority, adverse opening gaps, spread, fees and the 12-hour timer. Risk guards use closed balance and therefore do not certify floating-equity compliance. Swap and conversion spreads are omitted; rare missing-bar/closed-market delays can create overnight exposure. A monthly or annual terminal exit is an artificial mark. Wider-spread sensitivity from the initial recheck is separate from this requested historical table; these annual numbers are not evidence of stress-tested profitability.

Every run reconciles trade profits to ending balance, and continuous monthly rows reconcile to their window total. Unit checks cover 12-hour exit timing, JPY/USD conversion and commission charging. Raw yearly/monthly trade logs, tables, source/data hashes and both interpretations of 'last year monthwise' are in `logs/jpy-session-history-20260913/`. Reproduce with `.venv\Scripts\python.exe -m research.jpy_session_history`.
