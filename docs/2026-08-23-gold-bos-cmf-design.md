# Gold Break-of-Structure + CMF strategy — design & backtest spec

**Date:** 2026-08-23
**Market:** XAUUSD (gold)
**Status:** research / backtest only — does NOT touch engine/sim/live

## Idea (in plain language)

Trade a **break of structure (BOS)** on gold, confirmed by a candle close and by
buy/sell pressure:

1. **Mark structure** — the most recent confirmed fractal **swing high** (last
   higher high) and **swing low** (last lower low).
2. **Candle-confirmed break** — a candle **closes** past that swing level (a real
   close beyond it, not just a wick). Long on a close above the last swing high,
   short on a close below the last swing low. The break must be a fresh *cross*
   (prior bar was on the other side of the level) so we fire once, not every bar.
3. **CMF agrees** — Chaikin Money Flow confirms the side: take the long only if
   **CMF > 0** (buyers in control), the short only if **CMF < 0** (sellers). If
   the break happens but CMF disagrees, skip.

### Why CMF (not "real" buy/sell volume)
The MT5 retail gold feed has no true buyer-vs-seller volume — only `tick_volume`
(activity count). CMF is the honest proxy: it weights each bar's volume by where
price **closed within the bar's range** (close near high = buyers, near low =
sellers), summed over N bars. `CMF = sum(MFM*vol) / sum(vol)`, where
`MFM = ((close-low) - (high-close)) / (high-low)`, range −1..+1. No lookahead:
value at bar i uses only bars ≤ i.

Prior note: a naive tick-volume *threshold* filter was tested on the ORB strategy
and made results worse. CMF is a different, directional formulation (close-in-range,
not raw count), which is why it's worth a fresh test — but the null result is fully
acceptable.

## Exit (reuse the proven gold exit)

- **Stop:** far side of the broken structure. For a long that breaks the swing
  high, the stop sits at the most recent confirmed swing **low** below entry (the
  level that invalidates the break). Mirror for shorts.
- **Take-profit:** the next confirmed swing level beyond entry (≥ `tp_min_r` × risk
  away), with an **R-multiple fallback** if there's no clean structure ahead.
- **Sizing:** from the actual stop distance so every trade risks the same fraction
  of equity (1%; 0.5% at the $10k prop config).

Rationale: the project already tested scale-out (lost 3/4 TFs) and tight
structure-trailing (lost 4/4). The single structure target was the sweet spot, so
we start there and only revisit if the numbers demand it.

## Timeframes & validation

- **H1** — 9.5 yr real history (2017→2026). **Walk-forward** (2yr train / 6mo test,
  rolling 6mo). This is the only trustworthy test.
- **M5 / M15 / M30** — broker caps history at ~1 year. Single-period backtest only,
  reported as **weak evidence, no out-of-sample** — never trusted on its own.

Non-negotiable discipline (EURUSD-hunt lesson): a green full-history number whose
params were chosen after seeing the whole series proves nothing. Params are picked
on train folds and scored only on unseen test folds. Honest-negative is acceptable.

## Implementation

`bos_backtest.py` — isolated research script (like `scaleout_backtest.py` /
`trailing_backtest.py`). Imports the **validated** `wf_search.simulate` cost/risk
model, `swing_points`, `folds`, `walk_forward`, `per_year`, and `load_tf`. Adds:
- `cmf(df, n)` indicator (no lookahead)
- `make_bos_signal(df, *, swing_window, cmf_n, tp_mode, tp_r, tp_min_r, use_cmf)`
- commands: `fixed` (a-priori per-year across TFs), `wf` (walk-forward H1),
  `cmf_ab` (A/B: same BOS with CMF on vs off, to isolate the filter's effect).

Cost model reused as-is: entry at close ± spread (gold spread 3 pips = $0.30),
SL wins ties, 1% sizing via `trader.risk.position_size_lots`. Prop rails available
but off for the pure edge test.

## Success criteria

- H1 walk-forward aggregate net > 0 with a majority of OOS folds positive AND the
  train-only search re-finding stable params → candidate worth a demo forward test.
- CMF A/B shows CMF **helps** (better OOS net / win-rate) — else drop it and the
  strategy is just candle-confirmed BOS.
- Anything less = honest negative, logged, no live deployment.
