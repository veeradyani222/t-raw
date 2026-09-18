# USDJPY hour-6 long session recheck - 17 September 2026

Offline replay of the former USDJPY session signal: completed H1 bar labelled 06:00, long entry normally near 07:00 broker/data time, ATR14 x2 stop, no TP, exit 12 elapsed hours after entry (normally near 19:00) unless stopped. The elapsed-time replay follows the existing September13 study; timestamps in the ledger are bar labels, not exact fill times. No session-timezone/DST mapping to Tokyo is independently verified.

Every run starts flat with $10,000, 1% balance risk, maximum1 lot and 0.01 lot steps, $300 daily / $600 static closed-balance entry halts. July-August is one continuous account; fresh months and calendar years are separate starts. The model does not liquidate at risk thresholds. A permanent halt explains subsequent months with no trades.

Both profiles assume 1-pip spread and 0.1-pip slippage per market fill. historical-fee7 uses $7/lot round-trip commission to reproduce the prior study; fee14 uses the more cautious $14/lot assumption used in later CHFJPY work. Neither fee is verified against account execution records. USDJPY profit converts using exit price. Swap, conversion spread, margin and tick sequencing are not modeled. Different risk engines prevent treating this as a fully controlled comparison with the guarded CHFJPY replay.

## July-August continuous account

| Commission/lot round trip | July P/L | August P/L | Total P/L | Trades | Wins / losses | Ending balance |
|---|---:|---:|---:|---:|---:|---:|
| $7 | $+13.58 | $+270.29 | $+283.87 | 44 | 19 / 25 | $10283.87 |
| $14 | $-85.92 | $+181.51 | $+95.60 | 44 | 19 / 25 | $10095.60 |

## Calendar years and latest full twelve months

| Window | $7 commission net | $14 commission net |
|---|---:|---:|
| 2016 | $-627.52 | $-652.16 |
| 2017 | $-618.43 | $-687.24 |
| 2018 | $-684.58 | $-623.38 |
| 2019 | $-686.57 | $-635.27 |
| 2020 | $-625.35 | $-649.01 |
| 2021 | $-601.33 | $-671.49 |
| 2022 | $-649.94 | $-670.44 |
| 2023 | $+738.75 | $+50.30 |
| 2024 | $+2340.39 | $+1445.58 |
| 2025 | $-618.98 | $-640.88 |
| latest-12-months | $-612.52 | $-610.01 |
| July-fresh | $+13.58 | $-85.92 |
| August-fresh | $+270.29 | $+197.43 |

Annual averages and halt counts: `{'historical-fee7': {'mean_net': -203.3564038993013, 'profitable_years': 2, 'halted_years': 8}, 'fee14': {'mean_net': -373.3987561938063, 'profitable_years': 2, 'halted_years': 8}}`.

All ten historical-fee7 annual results reproduced the saved September13 counts and net profits. All 28 runs reconcile gross P/L, fees, converted P/L and ending balances. Monthly splits reconcile to their continuous runs. This is a replay of cached research-feed prices, not a statement of actual account earnings.

Reproduce with `.venv/Scripts/python -m research.usdjpy_hour6_recheck`. [Trade ledgers and manifest](../logs/usdjpy-hour6-recheck-20260917/). [Earlier study](2026-09-13-jpy-session-history.md). No live strategy settings or orders were changed.
