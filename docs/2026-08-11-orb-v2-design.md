# ORB v2 — confirmations, price-action exits, backtest CLI, trade logs

Date: 2026-08-11. Requested by Veera: strengthen the ORB entry with volume and
market-structure confirmation, keep SL/TP fully price-action-derived (single
TP for now), replace one-off backtest scripts with a parameterized CLI, and
produce a per-trade CSV log for every run.

## 1. Strategy confirmations (all configurable, individually toggleable)

The raw ORB breakout stays exactly as it is. Two new confirmation filters run
after a breakout is detected; each can veto it. Both default ON for the new
work but can be switched off to reproduce the v1 results.

### Volume confirmation
Forex has no centralized buyer/seller volume; MT5 supplies **tick volume**
(number of price updates per bar), the standard proxy. A breakout bar on thin
volume is more likely a fake-out.

- Rule: breakout bar's `tick_volume` ≥ `orb_vol_mult` (default 1.2) × the
  mean tick volume of the previous `orb_vol_lookback` (default 20) bars.
- If the data has no `tick_volume` column (old caches), the filter
  auto-passes and the trade log notes `vol_ratio=NaN` — it never silently
  changes results.
- Config: `orb_vol_filter: bool = True`, `orb_vol_mult: float = 1.2`,
  `orb_vol_lookback: int = 20`.

### Structure confirmation (higher highs / higher lows)
Fractal swing detection over an extended lookback (~3 trading days of bars):
a swing high is a bar whose high exceeds the `orb_swing_window` (default 2)
bars on each side; swing lows mirrored.

- Long allowed only if the two most recent completed swing **lows are
  rising** (market making higher lows into the breakout). Short requires the
  two most recent swing **highs to be falling**.
- Fewer than two swings on the relevant side → filter passes (no evidence is
  not a veto).
- Config: `orb_structure_filter: bool = True`, `orb_swing_window: int = 2`.

### Blocked signals are first-class
When a breakout exists but a filter vetoes it, `compute_signal` returns a
`Blocked(side, reason, meta)` record instead of a bare FLAT. The engine
treats it as no-trade but reports it, so the trade log shows *why* the
strategy stayed out — essential for judging whether the filters help.

## 2. Stop loss / take profit — price action only

- **SL (unchanged):** far side of the opening-range box — the level that
  invalidates the breakout. Position size derives from this distance, so
  every trade risks the same equity fraction.
- **TP (new mode):** `orb_tp_mode`:
  - `"structure"` (new default for v2 runs): TP = the most recent swing high
    above entry (long) / swing low below entry (short), reusing the swing
    detection. Guard: the level must be at least `orb_tp_min_r` (default
    1.0) × stop distance away; if there is no qualifying swing level, fall
    back to the R-multiple target.
  - `"r_multiple"` (v1 behavior): TP = `orb_tp_r` × stop distance.
- Single TP per trade. Partial exits / multiple targets are explicitly out of
  scope for now (testing accuracy first, profits later).

## 3. Parameterized backtest CLI — `backtest.py`

```
python backtest.py XAUUSD H1 --from 2026-05-01 --to 2026-08-11
                  [--strategy orb] [--tp-mode structure|r_multiple]
                  [--tp-r 3] [--no-vol-filter] [--no-structure-filter]
                  [--equity 10000] [--spread-pips 3]
```

- **Symbol presets:** a small table maps symbol → pip_size,
  pip_value_per_lot, default spread (XAUUSD, EURUSD, GBPUSD, USDJPY to
  start); flags override.
- **Data layer:** one cache per symbol+timeframe (`data/<symbol>-<tf>.csv`)
  that now includes `tick_volume`. If the cache covers the requested range,
  use it; otherwise fetch from MT5 (chunked `copy_rates_range`, generalized
  from run_orb_sweep) and merge into the cache. MT5 is imported lazily —
  cache-served runs and the test suite never touch it. Old volume-less
  caches are used as-is when the volume filter is off; with it on, refetch.
- Prints the summary (trades, win rate, net, max DD, final equity) and always
  writes the trade log CSV.
- `run_backtest.py` / `run_orb_sweep.py` stay but become thin wrappers or are
  retired once the CLI covers them (sweep = shell loop over the CLI).

## 4. Per-trade CSV log

Every backtest writes `logs/<symbol>-<tf>-<from>-<to>-<runid>.csv`, one row
per event:

| column | meaning |
|---|---|
| kind | `trade` \| `blocked` (filter veto) \| `skipped` (risk rails) |
| date, weekday, time | signal bar timestamp |
| side, entry, sl, tp, lots | order as placed |
| box_high, box_low, box_size | the day's opening range |
| vol_ratio | breakout tick_volume ÷ average (NaN if no volume data) |
| structure | `HH/HL` / `LH/LL` / `mixed` / `n/a` at signal time |
| exit_time, exit_price, exit_reason | `tp` \| `sl` \| `end`; empty for non-trades |
| bars_held, profit, r_multiple, equity_after | outcome |
| note | veto/skip reason, fallback notices |

Plumbing: `Setup` gains a `meta` dict (box levels, vol_ratio, structure,
tp_source); `on_bar` returns an event dict instead of only logging;
`sim.py` collects events and exit fills into the log. `live.py` logs the
same events, so live and backtest stay one code path.

## 5. Testing & verification

- All new logic pure and offline-testable (synthetic candles, tmp dirs):
  volume filter pass/block/absent-column, structure filter both directions,
  Blocked records, structure-TP selection + fallback, CLI on a CSV fixture,
  trade-log columns.
- **Regression gate:** CLI with `--tp-mode r_multiple --no-vol-filter
  --no-structure-filter` on the 3-month XAUUSD H1 file must reproduce the
  existing `backtest-orb-3mo-box-3R.csv` results exactly.
- Then A/B: filters off vs on, r_multiple vs structure TP, on 3-month and
  1-year data; results + logs reported side by side.

## 6. Results (2026-08-11, XAUUSD H1, $10k start, 1%/trade)

Regression gate: v1 flags reproduced `backtest-orb-3mo-box-3R.csv`
trade-for-trade (57 trades, +1639.74). ✓

One year 2025-08-11 → 2026-08-11 (fresh MT5 pull incl. tick volume,
`data/xauusd-h1.csv`, 5833 bars):

| config | trades | win % | net | max DD |
|---|---|---|---|---|
| v1 baseline (r_multiple, no filters) | 226 | 38.9% | +2500 | −1776 |
| + structure TP only | 239 | 43.9% | +3744 | −1443 |
| + structure filter only (r_mult TP) | 133 | 42.1% | +3985 | −1408 |
| **v2: structure filter + structure TP** | **137** | **48.2%** | **+4146** | **−1037** |
| v2 + volume 1.2× | 52 | 38.5% | +942 | −471 |
| v2 + volume 1.0× | 90 | 35.6% | +916 | −679 |
| v2 + volume 0.8× | 119 | 47.1% | +3202 | −969 |

**Decision:** structure filter ON, structure TP ON, volume filter OFF by
default (`orb_vol_filter=False`; opt back in with `backtest.py --vol-filter`).
Tick volume on the breakout bar was anti-predictive at every threshold tried
— high-volume breakout bars on XAUUSD H1 lost more often, plausibly
exhaustion moves. Revisit with a different formulation (e.g. volume of the
box vs prior days) rather than a different threshold.

3-month check (2026-05-11 → 2026-08-11, old volume-less cache): v2
structure-only config: 35 trades, 54.3% win, +884, DD −361 vs v1's 57
trades, 49.1% win, +1640, DD −414. Fewer trades and less absolute profit on
this short window but better quality per trade; the 1-year picture is the
one that counts.
