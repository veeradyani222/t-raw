# CHFJPY midnight-opening recheck ? 17 September 2026

Deployment note (2026-09-19): the user confirmed keeping the current 01:00 MT5-time entry for main. The midnight variant described below is a historical research experiment, not the selected live configuration.

CHFJPY is the sole selected strategy in run_live.py. This experiment targets the first fresh quote/poll at 00:00 in the MT5 data clock; the loop polls every 10 seconds and skips entries more than 60 seconds late. It uses ATR14 from completed candles and the preceding close minus 2?ATR for the stop. The long position exits 12 elapsed hours after actual entry unless stopped. This is normally near 12:00, not a guaranteed exact-second fill. Weekend entries use the last available completed candles. No forming-bar values enter the signal.

Local process inspection found no run_live.py bot and no MT5 terminal process. The runner is configured, but not actively trading here. It still refuses non-demo accounts. No process was started, terminal connected or order sent.

## Comparable backtests

Each window starts a separate $10,000 account, with 1% balance risk, maximum 1 lot, $14/lot round-trip commission, 0.1-pip slippage per market fill and JPY-to-USD conversion. Base spread is 2.5 pips; stress spread is 5 pips. July and August share one continuous account started July 1. The 12-month window is September 1, 2025 through August 31, 2026. No parameters were optimized.

| Period | Old completed-00:00 candle | New 00:00 opening |
|---|---:|---:|
| July 2026 | $+120.94 | $+510.81 |
| August 2026 | $+352.40 | $+86.49 |
| July?August total | $+473.34 | $+597.30 |
| Last full 12 months | $+5,294.44 | $+3,986.34 |

## Calendar years ? separate $10,000 starts

| Year | Old timing, base | New timing, base | New timing, 5-pip spread |
|---|---:|---:|---:|
| 2016 | $-525.77 | $-516.69 | $-516.16 |
| 2017 | $-521.19 | $+650.06 | $-579.07 |
| 2018 | $-516.75 | $-567.85 | $-595.14 |
| 2019 | $-541.62 | $-595.42 | $-597.28 |
| 2020 | $-526.74 | $+659.73 | $-568.33 |
| 2021 | $+690.37 | $+1,367.23 | $-557.56 |
| 2022 | $+2,070.40 | $+7,258.90 | $+4,369.57 |
| 2023 | $+1,057.56 | $+5,609.98 | $+3,289.29 |
| 2024 | $+917.20 | $-589.19 | $-590.13 |
| 2025 | $-532.96 | $+7,104.14 | $+4,757.18 |

New timing: 6/10 profitable calendar years; mean annual net $+2,038.09. These selected historical years are not untouched out-of-sample evidence.

## Execution and modeling limits

- Opening replay buys at the 00:00 open plus spread/slippage, using only the previous ATR/close and previous USDJPY close for sizing. Stops are checked within the entry candle. Timed exits use the opening quote at or after 12 elapsed hours, before the exit candle low. Gap-through stops execute at the opening quote.
- Old replay preserves its original close-fill and bar-label timestamp convention, normally corresponding to 01:00 entry and 13:00 exit. The old base yearly results reproduce the earlier study, including $5,294.44 for the recent year and $473.34 for July?August.
- Both variants retain the same guarded research engine: floating-equity liquidation floors and planned-risk headroom checks. Live has floating-equity entry halts and a server-side ATR stop, but does not implement these synthetic guard liquidations/headroom checks. Consequently this comparison isolates timing within the research model; it is not an exact prediction of live account P/L.
- Broker/feed timezone and daylight-saving alignment remain unverified. Fixed spreads do not capture midnight rollover widening or market breaks. Commission is assumed; swap, conversion spread, tick sequencing, broker stop-level constraints and outages are not modeled. A trade can therefore be skipped or filled differently live.
- A first static headroom block need not be permanent: headroom can suffice for a later smaller planned loss. Historical profits do not establish a durable edge.

## Artifacts and verification

[Summary](../logs/chfjpy-midnight-recheck-20260917/summary.csv), [monthly results](../logs/chfjpy-midnight-recheck-20260917/monthly.csv), [all trade ledgers and source manifest](../logs/chfjpy-midnight-recheck-20260917/).

Reproduce: `.venv/Scripts/python -m research.chfjpy_midnight_recheck`. All 48 runs reconcile ledger net P/L to final balance. Regression coverage checks prior-candle ATR, midnight date handling, weekend entries, stale entry rejection, entry-candle stops and noon exit ordering.
