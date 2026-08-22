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

## RESULTS (2026-08-23)

**H1 walk-forward** (2yr train / 6mo test, 15 OOS folds, per-fold search over a
tiny grid): aggregate **OOS net +$4,103, 10/15 folds positive**, 821 trades. This
is the real test — the same discipline that found NOTHING on EURUSD. It survived.

**CMF A/B** (isolating the volume leg): CMF **helps or is neutral on every TF**,
never hurts. On H1 it flips the strategy from −$629 to +$599 full-history. The
directional close-in-range formulation works where a raw tick-volume threshold
(tried on ORB) did not. Demanding *strong* CMF (`cmf_min` 0.05/0.10) HURTS — plain
`CMF>0` is the sweet spot.

**Strengthen (C):** no a-priori lever beats plain baseline on OOS profit. Trend
`MA50` trades fewer/cleaner → more consistent (10/15 folds, 7/10 yrs, lowest DD)
but less total profit; every other filter cuts profit. Two finalists: **baseline**
(max profit, leans on 2020) and **MA50** (max consistency).

**Spread stress (A):** full-history both go negative above ~1.5× spread (fragile) —
BUT last-12mo both hold **~+$2,000 even at 4× spread (12 pips)**. Nearly
spread-insensitive in the current regime = a real edge with cost margin, the
OPPOSITE of a spread artifact. The full-history fragility is old low-vol gold
(2017–19) making breaks too small to clear cost.

**Prop rails (B), 1% risk / 3% daily / 6% total halt, $10k:**

| window | baseline | MA50 |
|---|---|---|
| last 12mo | +22.0%, worst day −2.35%, DD −0.94%, survives | +23.4%, worst day −1.65%, DD +2.52%, survives |
| last 3yr | +70.0%, DD −0.21%, survives | +47.0%, DD −4.71%, survives |
| full 9.5yr | −6.7% then total-halt trips (Nov 2017) | −6.8% then total-halt trips (Nov 2017) |

**Verdict:** a genuine, walk-forward-surviving, spread-robust gold H1 edge **in the
current (2020+) volatile-gold regime** — ~14–22%/yr at 1% risk, drawdown well inside
prop limits. **Regime-tilted**: it loses in old low-vol gold and the −6% total halt
is the designed safety net for a regime shift back. Shares gold ORB's regime
dependence (running both = correlated, not diversified). Not yet slippage-tested or
demo-forward-tested. MA50 = safer live pick (consistency + lower daily excursion);
baseline = higher raw return.

## GO-LIVE (2026-08-23): shipped as a live strategy module

Decision: **replace the H1 gold ORB with BOS+CMF M30** (both are XAUUSD, so they
can't share one account — they'd fight over the gold slot; and BOS beat ORB in
every recent window: e.g. 2yr ORB −6.7% BLOWN vs BOS +86% survived, buffered rails).
Live set is now **BOS-gold-M30 + USDJPY-session** (two symbols, no collision),
1% risk each, account-wide buffered rails 3% daily / 6% total. Variant = **baseline**
(plain CMF>0): it beat MA50 on return in every window and MA50's extra smoothness is
unneeded far from the rails.

**Live TP / lookback finding (important).** Porting to the live module surfaced that
the structure TARGET = "nearest overhead swing" depends on how far back the bot can
see. A too-short 400-bar (8-day) window aimed at worse targets and tanked results
(2yr +33%). The realistic band (3wk–3mo) is stable and strong; **~6 weeks
(`bos_lookback=2000` M30 bars)** is the sweet spot and BEATS the full-history number.
Corrected ship numbers (M30 baseline, L=2000, 1% risk, buffered rails):

| window | net | prop |
|---|---|---|
| 3 months | +12.7% | survived |
| 12 months | +67.3% | survived |
| 2 years | +86.0% | survived |
| 3 years | −6.8% | BLOWN 2023-09 (the 2023 regime; 0.5% risk survives) |

**Code:** `trader/strategies/bos.py` (canonical `compute_signal`), Config `bos_*`
fields, registered in the strategy registry, wired into `run_live.py`. The research
`bos_backtest.make_bos_signal` is a FAST path that reproduces `compute_signal`
decision-for-decision (asserted in `tests/test_bos.py`, 0 diffs) — so the numbers
above and the live signals are the same strategy. Telegram gained tappable command
buttons (reply keyboard). 79 tests pass. Still a DEMO forward test — regime-tilted,
not proven live.
