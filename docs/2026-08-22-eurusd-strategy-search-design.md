# EURUSD strategy search — walk-forward design (2026-08-22)

## Goal

Find a EURUSD strategy that is profitable **out-of-sample**, or report honestly
that no robust edge was found. The ORB battery showed EURUSD loses in every ORB
configuration (v1 −7% to −55%, v2 −20% to −40%, and it also lost in 2024
out-of-sample), so we are searching new strategy families, not re-tuning ORB.

The overriding risk is **overfitting**: "iterate until the backtest is green" on
one slice of data produces a curve fit that dies live — exactly the gold trap
(15/15 in-sample winners in 2025–26, then −15% to −22% in 2024). The method
below exists to prevent that.

## Data

- **EURUSD H1 from the local MT5 terminal**, cached to `data/eurusd-h1.csv`.
- Verified real, not backfilled filler: 2017-01-02 → 2026-08-21, 59,898 bars,
  ~6,200 bars every full year (a complete year of hourly forex), per-year
  volatility that matches known regimes (2022 loudest at 18.9 pips/hr, 2019/2024
  calmest ~10), thousands of distinct closes per year, and only ~3-day weekend
  gaps. ~9.5 years spanning covid vol, the 2022 USD trend, and 2023–24 range.
- H1 is the anchor because it has the deepest clean history. Intraday is capped
  by the broker (M5 only ~1.3 yr) — too shallow for walk-forward, so out of scope.

## Method — walk-forward

Roll a train → test window across the ~9.5 years:

- **Train window:** ~2 years. Only the train slice is used to pick/tune a
  strategy's parameters.
- **Test window:** the next ~6 months, which the strategy never saw during tuning.
- **Step:** ~6 months, giving ~12 non-overlapping out-of-sample test folds.

A strategy is judged **only on its stitched-together test folds.** Train-slice
performance is never a success criterion — it only selects parameters.

## Candidates (in priority order)

Grounded in what both our own data and outside research (fxstreet time-of-day
study, academic home-timezone effect, mean-reversion literature) point to for
EURUSD — fade and time-of-day, not breakout.

1. **Session time-of-day** — long/short by hour-of-day block (the home-timezone
   depreciation effect), flat during the London/NY overlap. ~1–2 parameters.
2. **Mean-reversion fade** — enter when price stretches N z-scores / RSI-2 hits
   an extreme; stop *beyond* the extreme; target back at the moving mean.
   ~2–3 parameters.
3. **ORB breakout** — the **control**. We expect it to keep losing; a green
   result here would mean the harness is broken.

Iteration is evidence-driven: read each candidate's per-fold results and trade
logs, form the next tweak from what the data shows, re-run. No blind parameter
grids — a grid overfits even under walk-forward.

## Acceptance bar

A strategy is only reported as "working" if **all** hold; otherwise the result
is "no robust edge found":

- Positive on a **majority of the OOS test folds** (not just the aggregate).
- Positive **aggregate** OOS net after realistic costs.
- **Robust:** nearby parameter values do not flip it to a loss.
- **Enough trades:** folds with <~20 trades are treated as noise, not evidence
  (a lesson from the gold scale-out work).

## Harness & safety

- **Isolated research harness** (`wf_search.py` in the repo root), in the same
  spirit as `scaleout_backtest.py` / `trailing_backtest.py`: it does **not**
  touch `engine.py`, `sim.py`, or anything the live bot runs.
- It **reuses the real cost/risk model**: entry at the signal bar's close ±
  spread (~1 pip EURUSD), SL/TP filled against subsequent bars' high/low with
  **SL winning ties** (pessimistic), and position sizing from
  `trader.risk.position_size_lots` at 1% risk. It adds a time-based exit, which
  the live engine lacks, for the session strategy.
- **Validated before use:** the harness reproduces a known ORB backtest number
  (net + trade count) from `trader.sim.run_backtest` on the same range, the same
  way the scale-out/trailing scripts were validated. Only then are its new-strategy
  numbers trusted.
- If a candidate clears the acceptance bar, *then* it graduates to a real
  `trader/strategies/` module with tests — not before.

## Explicitly out of scope

- Intraday timeframes (data too shallow).
- Any live deployment. This is research; nothing here goes near the live bot.
- Second-broker data validation (Dukascopy etc.) — optional final robustness
  check only if a candidate survives.
