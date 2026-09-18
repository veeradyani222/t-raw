# Public EA rule replay ? 17 September 2026

## Outcome and status

Three published rule sets were evaluated offline. None was established as reliably profitable. Automatic approval review rejected the attempted download of third-party EA sources into the workspace with a generic blocked-by-policy message and no specific explanation. No source download, native installation, compilation, MT5 startup or trading order was completed. The Python analytical replay reads existing local CSVs only. CHFJPY live configuration was not changed.

## Frozen comparison

EURUSD only: Adjustable MA and RSI on H1, Heiken Ashi Naive on D1. These timeframes were fixed before viewing results. The indicator/rule parameters follow pinned publisher source, including MA MinDiff=3 points, not the webpage value of 30. The H1 selections are local test choices, not claims to reproduce the publisher M5 tests. See [source research](2026-09-17-public-ea-candidates.md) for source links, exact commits and publisher claims.

Each period starts flat with $10,000 and fixed 0.1-lot trades. No protective stop, profit target or risk halt is imposed, matching published default rule behavior; consequently this is not 1% risk sizing and is not directly comparable with guarded CHFJPY results. The $600 static-loss threshold is recorded diagnostically even when an open position later recovers. Base costs: 1-pip spread, $14/lot round-trip commission and 0.1 pip slippage per fill. Stress spread: 2 pips. No parameter optimization or winner-driven substitutions were performed.

| Candidate | Aug 2025?Jul 2026 net | Trades | 2-pip spread net | Profitable years 2018?2025 | Years crossing $600 static loss |
|---|---:|---:|---:|---:|---:|
| Adjustable MA / H1 | $-431.00 | 115 | $-546.00 | 3/8 | 4/8 |
| RSI EA / H1 | $+75.20 | 6 | $+69.20 | 3/8 | 2/8 |
| Heiken Ashi Naive / D1 | $-3.80 | 24 | $-27.80 | 4/8 | 3/8 |

## Latest cached months ? one account from July 1

August is incomplete: cached EURUSD prices stop August 21. Values below are realized P/L allocated by exit date, with any remaining position force-closed on the last available bar. July can carry unrealized P/L into August.

| Candidate | July 2026 | August 1?21 only | Combined |
|---|---:|---:|---:|
| Adjustable MA / H1 | $-290.40 | $+119.70 | $-170.70 |
| RSI EA / H1 | $+0.00 | $-120.00 | $-120.00 |
| Heiken Ashi Naive / D1 | $+164.80 | $-149.30 | $+15.50 |

## Calendar-year net results ? fresh account each year

| Year | Adjustable MA | RSI | Heiken Ashi |
|---|---:|---:|---:|
| 2018 | $-48.40 | $-1,185.60 | $+1,879.80 |
| 2019 | $+250.90 | $+462.40 | $+747.20 |
| 2020 | $+2,037.00 | $-281.00 | $+21.10 |
| 2021 | $-842.20 | $-46.80 | $-148.60 |
| 2022 | $-824.30 | $-327.00 | $-858.60 |
| 2023 | $-288.90 | $+1,219.20 | $-5.40 |
| 2024 | $-1,362.70 | $+1.50 | $-630.70 |
| 2025 | $+752.20 | $-84.00 | $+251.60 |

## Limits and verification

- Research implementations are not certified native EA parity. Indicators use causal completed-bar inputs and next-open fills. The EMA has a first-close seed with at least a year of warmup before reported windows. RSI uses the MT5 sample Wilder seed; HA initialization follows the installed MT5 example. Native retry behavior, rejected orders, indicators refreshing between ticks, multi-position interference and terminal state are not reproduced.
- No downloaded EA or native EA executable was run. There is no claim of a verified live track record. Public source availability makes rules inspectable, not profitable.
- Swap is omitted despite potentially long holding periods, especially RSI. Margin/stop-out, variable spreads, financing, tick ordering and latency are not modeled. Small positive net results can disappear after these costs.
- Drawdown is an OHLC upper bound using favorable then adverse prices within a bar, not an observed tick-path drawdown. Static threshold crossings use adverse floating liquidation equity. There is no synthetic close at $600: eventual full-period P/L can recover after a threshold breach and would not represent an account terminated at breach.
- Three candidates plus timeframes were selected for inspectability and usable cached history, not sampled randomly from all online EAs. These are historical screens, not an untouched validation set and not a search for the highest backtest.
- Tests cover future-data invariance, RSI seed limits, both long/short spread/slippage/commission accounting, next-open timing and floating-loss breach detection. All 60 run ledgers reconcile to final balances.

Reproduce: `.venv/Scripts/python -m research.public_ea_replay`.

[Summary](../logs/public-ea-replay-20260917/summary.csv), [monthly P/L](../logs/public-ea-replay-20260917/monthly.csv), [trade ledgers and data/code hash manifest](../logs/public-ea-replay-20260917/).
