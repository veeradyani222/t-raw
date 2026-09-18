# M30 BOS body confirmation verification

The requested rule is that any positive portion of a completed candle's rectangular body beyond the boundary qualifies; a wick alone does not. For the existing bullish-long/bearish-short candles, `close > swing_high` / `close < swing_low` already implements this. Touching the boundary exactly is insufficient. Other filters and the fresh-cross requirement remain unchanged.

No strategy behavior or live configuration was changed. Added long/short tests for wick-only crossings, exact touches, 0.01 body overlap, larger partial overlap, and live/research equivalence with the trend filter. All 96 repository tests passed. Checked every logged entry against its candle body and swing boundary, and reconciled trade profits to final balances.

## M30 results

Broker data: 30,000 XAUUSD M30 candles with tick volume, from 2024-02-21 06:30 through 2026-09-11 21:30 (timestamps as returned by MT5). Use the local `run_live.GOLD`: BOS + CMF20, swing window 2, MA200, structure exits, 2000-bar context, 3R fallback and minimum 1R structure target. Each run starts flat with $10,000 and full historical context. One position, 1% sizing, 3-pip spread ($0.30 price), $300 daily and $600 permanent total-loss limits. Runs use `SimBroker`, `RiskGuard` and production `engine.on_bar`, including opposite-signal exits.

| Test window | Trades | Wins | Win rate | Net P&L | Final balance | Max closed-balance drawdown | Permanent halt |
|---|---:|---:|---:|---:|---:|---:|---|
| 2026-08-12 to 2026-09-11 | 28 | 9 | 32.14% | -$466.60 | $9,533.40 | $730.76 | No |
| 2025-09-12 to 2026-09-11 | 266 | 128 | 48.12% | +$3,104.21 | $13,104.21 | $1,009.44 | No |

Drawdown is measured from the running balance peak including the initial $10,000. It can exceed $600 without breaching the fixed $9,400 floor. The month and year are independent starts, so their trades need not match within their overlapping dates.

The strategy was profitable across the tested year but lost money in the recent month. These are results of the existing body-close rule, not an improvement produced by a new rule.

Limitations: fixed-spread OHLC fills, SL first on same-bar SL/TP ties; no commission, swap, slippage or execution latency. Simulator risk checks use closed balance whereas live checks floating equity. Local configuration was used; remote deployed code was not independently inspected.

Artifacts: `logs/m30-close-baseline-2026-08-12-trades.csv`, `logs/m30-close-baseline-2025-09-12-trades.csv`, corresponding `-summary.json` files, and `data/xauusd-m30-volume-20260912.csv`.
