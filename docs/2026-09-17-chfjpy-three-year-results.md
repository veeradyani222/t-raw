# CHFJPY continuous three-year timing comparison

Window: September 1, 2023 through August 31, 2026. Each account starts flat at
$10,000 once, carries capital forward without withdrawals, risks 1% of balance
per trade, and is capped at 1 lot. This is a fresh replay using the same guarded
research engine as the earlier timing comparison. No live configuration changed.

| Period | Approx. 01:00–13:00 | Approx. 00:00–12:00 |
|---|---:|---:|
| Sep 2023–Aug 2024 | +$1,222.55 | +$709.65 |
| Sep 2024–Aug 2025 | +$6,274.59 | +$2,807.42 |
| Sep 2025–Aug 2026 | +$9,353.95 | +$5,448.90 |
| Total net | +$16,851.08 | +$8,965.97 |
| Ending balance | $26,851.08 | $18,965.97 |
| Trades | 777 | 768 |
| Maximum closed-balance drawdown | $1,670.46 | $2,054.15 |

Base costs: 2.5-pip spread, $14/lot round-trip commission and 0.1 pip slippage per
fill, with JPY-to-USD conversion. Last-year profits differ from fresh-$10,000
one-year tests because the final year starts with accumulated capital.

## Spread sensitivity

At a 5-pip spread, with other assumptions unchanged, the 01:00 version loses
$555.88 (ending $9,444.12, 112 trades), and the midnight version loses $579.74
(ending $9,420.26, 136 trades). Losses leave too little headroom above the fixed
$9,400 floor for most subsequent planned trade risks. This is a headroom block,
not necessarily a triggered permanent floating-equity halt. The midnight version
does take one later trade in the final year. The strong base-case result does not
survive this cost stress under the chosen account constraints.

## Limits and artifacts

The research engine enforces floating-equity liquidation floors and planned-risk
headroom checks beyond the live engine's entry halts. It is not exact live execution
parity. Broker/feed time alignment and actual spread/commission remain unverified;
swap, margin, conversion spread, tick sequencing and outages are not modeled.
Closed-balance drawdown excludes intratrade floating excursions.

All four ledgers reconcile net P/L and cumulative balance; the three annual
segments reconcile to each continuous result. No settings were optimized.

Reproduce: `.venv/Scripts/python -m research.chfjpy_three_year_recheck`.

[Summary](../logs/chfjpy-three-year-20260917/summary.csv),
[annual segments](../logs/chfjpy-three-year-20260917/annual-periods.csv),
[ledgers and source/code hashes](../logs/chfjpy-three-year-20260917/).
