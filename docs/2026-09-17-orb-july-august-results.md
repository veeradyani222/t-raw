# ORB, BOS and CHFJPY: July-August 2026 replay

Each strategy runs on a separate account starting flat at $10,000 on July 1, with 1% balance risk, maximum 1 lot and no withdrawals. The main monthly rows carry capital and positions forward into August; profits are assigned by exit date. The end boundary is September 1 exclusive. These are offline backtests, not actual account fills.

ORB exactly recovers the former deployed gold H1 signal from commit `665430a`, verified identical to the last pre-BOS version. Three-bar opening box from broker hour 1, structure filter on, volume filter off, box-boundary stop, structure target at least 1R away or 3R fallback, opposite-signal exits, no time exit. It is isolated from the USDJPY strategy that once shared its account. BOS uses the current retained GOLD M30 configuration with MA200.

## Continuous $10,000 accounts

| Strategy | July realized P/L | August realized P/L | Total | Ending balance | Trades | Wins / losses |
|---|---:|---:|---:|---:|---:|---:|
| ORB | $+135.47 | $-110.55 | $+24.92 | $10,024.92 | 20 | 8 / 12 |
| BOS | $+131.28 | $-264.04 | $-132.76 | $9,867.24 | 52 | 23 / 29 |
| CHFJPY | $+120.94 | $+352.40 | $+473.34 | $10,473.34 | 44 | 23 / 21 |

## Model differences and limits

- ORB and BOS use the same archived gold execution convention: $0.30 price spread, no commission, swap or slippage, exact-price stop fills even across gaps, and closed-balance entry halts ($300 daily / $600 static). These are spread-adjusted results, not all-in execution estimates. Sizing uses signal-close stop distance before spread. Short spread is modeled on entry rather than through an ask series.
- CHFJPY uses the existing guarded JPY research replay: 2.5-pip spread, $14/lot round-trip commission, 0.1-pip slippage per fill, historical USDJPY conversion, and floating-liquidation/headroom guards. No guards fired or entries were blocked in this particular two-month base run, but the engines still differ. Neither model includes swap or verifies broker-session mapping. This is not a controlled comparison of identical execution assumptions.
- Both gold profiles preserve archived signal/engine quirks; no parameters were optimized on July-August. Current BOS parameters and choice of CHFJPY were already influenced by historical testing, so this is not an untouched out-of-sample validation.
- Gold trade timestamps are candle opening labels: a signal at 05:00 executes at the completed H1 close, normally around 06:00. Intrabar SL/TP timestamps identify the bar containing the fill, not an exact fill time. CHFJPY ledger labels likewise are bar timestamps.
- OHLC cannot establish order of intrabar touches; the gold simulator takes the stop first if both SL and TP occur within one candle. Period-end marks are artificial closes. Monthly realized P/L does not mark a held trade at month-end.

## Wider-spread sensitivity

Gold spread doubles to $0.60; CHFJPY doubles to 5 pips. Other assumptions remain unchanged.

| Strategy | Base two-month P/L | Wide two-month P/L |
|---|---:|---:|
| ORB | $+24.92 | $+11.72 |
| BOS | $-132.76 | $-184.06 |
| CHFJPY | $+473.34 | $+218.28 |

## ORB: every trade in the continuous base run

| Entry bar | Exit bar | Side | Lots | Entry | Exit | P/L | Exit reason |
|---|---|---|---:|---:|---:|---:|---|
| 2026-07-02 05:00 | 2026-07-02 15:00 | long | 0.01 | 4057.46 | 4115.79 | $+58.33 | tp |
| 2026-07-07 15:00 | 2026-07-07 17:00 | long | 0.03 | 4172.57 | 4145.22 | $-82.05 | sl |
| 2026-07-09 05:00 | 2026-07-09 09:00 | short | 0.04 | 4064.72 | 4089.74 | $-100.08 | sl |
| 2026-07-09 09:00 | 2026-07-10 09:00 | long | 0.02 | 4108.23 | 4111.74 | $+7.02 | signal |
| 2026-07-10 09:00 | 2026-07-10 16:00 | short | 0.06 | 4111.44 | 4093.69 | $+106.50 | tp |
| 2026-07-13 06:00 | 2026-07-17 09:00 | short | 0.02 | 4060.15 | 3999.23 | $+121.84 | signal |
| 2026-07-17 09:00 | 2026-07-17 15:00 | long | 0.03 | 3999.53 | 3971.79 | $-83.22 | sl |
| 2026-07-17 15:00 | 2026-07-17 16:00 | short | 0.03 | 3965.79 | 3991.95 | $-78.48 | sl |
| 2026-07-20 05:00 | 2026-07-21 09:00 | long | 0.01 | 4022.11 | 4081.45 | $+59.34 | tp |
| 2026-07-23 14:00 | 2026-07-29 17:00 | short | 0.02 | 4085.34 | 3999.70 | $+171.28 | tp |
| 2026-07-30 16:00 | 2026-07-31 10:00 | long | 0.01 | 4112.51 | 4067.50 | $-45.01 | signal |
| 2026-07-31 10:00 | 2026-08-04 14:00 | short | 0.02 | 4067.20 | 4074.97 | $-15.54 | signal |
| 2026-08-04 14:00 | 2026-08-05 18:00 | long | 0.01 | 4075.27 | 4248.40 | $+173.13 | tp |
| 2026-08-06 18:00 | 2026-08-07 11:00 | short | 0.01 | 4233.39 | 4300.17 | $-66.78 | sl |
| 2026-08-10 09:00 | 2026-08-13 20:00 | long | 0.02 | 4358.25 | 4355.91 | $-4.68 | signal |
| 2026-08-13 20:00 | 2026-08-14 14:00 | short | 0.01 | 4355.61 | 4369.20 | $-13.59 | signal |
| 2026-08-14 14:00 | 2026-08-17 01:00 | long | 0.02 | 4369.50 | 4329.09 | $-80.82 | sl |
| 2026-08-24 05:00 | 2026-08-26 12:00 | long | 0.02 | 4643.89 | 4623.23 | $-41.32 | signal |
| 2026-08-26 12:00 | 2026-08-28 09:00 | short | 0.02 | 4622.93 | 4612.53 | $+20.80 | signal |
| 2026-08-28 09:00 | 2026-08-28 17:00 | long | 0.03 | 4612.83 | 4585.58 | $-81.75 | sl |

`tp` = target, `sl` = stop, `signal` = opposite qualified signal. One trade entered July 31 and exited August 4; its full -$15.54 belongs to August realized P/L.

## Independent fresh-month alternatives

These reset to $10,000 and start flat at each month boundary. July ends by marking any remaining position. They must not be added to the continuous-account monthly rows above.

| Strategy | Fresh July | Fresh August |
|---|---:|---:|
| ORB | $+168.33 | $-193.55 |
| BOS | $+131.28 | $-233.04 |
| CHFJPY | $+120.94 | $+351.10 |

## Interpretation

CHFJPY was the best of these three historical July-August replays under the stated models. ORB was nearly flat across both months and lost in August, so this sample does not establish ORB as a profitable replacement for recent BOS losses. BOS itself made money in July in this calendar test.

The broader CHFJPY $10,000 account study had four profitable independent calendar years out of ten (2016-2025), six losing/headroom-limited years, and an arithmetic annual mean of +$157.05. Its recent +$5,294.44 year is therefore not enough to establish a dependable edge. Treat the switch as a demo hypothesis needing forward evidence, not a proven improvement. [Earlier account study](2026-09-13-jpy-account-comparison.md). Past performance cannot predict a strategy’s future performance. [SEC performance-claims bulletin](https://www.investor.gov/introduction-investing/general-resources/news-alerts/alerts-bulletins/investor-bulletins-47).

The earlier August CHFJPY figure +$523.00 came from a year-long account that entered August at $14,771.43. This report starts July at $10,000; its August figure is +$352.40. The differing capital paths explain why the amounts differ.

## Reproduction and artifacts

Run `.venv/Scripts/python -m research.orb_recent_recheck`. The script recovers archived source from git without restoring ORB in the live registry. It saves 18 trade ledgers, gold event logs, summary.csv, monthly.csv, source hashes and input audits in [the results folder](../logs/orb-recent-recheck-20260917/). Every run reconciles profits to its ending balance and every continuous monthly split to its run total. [Archive audit](2026-09-17-orb-archived-rules.md). No MT5 account connection, order or live configuration change is part of this replay.
