# ORB backtest sweep — XAUUSD, all timeframes (2026-08-11)

## Setup

- **Strategy:** `orb` (trader/strategies/orb.py) — first 3 bars after server-hour 1
  define a high/low box; the first bar closing beyond the box in its own
  direction enters. **Stop at the far side of the box** (the invalidation
  level), **target = `orb_tp_r` × stop distance.** Position sized off the
  actual stop distance → every trade risks 1% of equity.
- **Data:** real XAUUSD candles pulled from the demo terminal
  (cached in `data/xauusd-<tf>-1yr.csv`). $10,000 start.
- **Engine:** `trader/sim.py` — entry at signal-bar close + 3-pip ($0.30)
  spread; SL/TP filled against subsequent bars' high/low, **SL wins ties**
  (pessimistic). Risk rails on: 1%/trade, max 1 position, −3% daily halt.
- **Runner:** `python run_orb_sweep.py <TFs>` → appends to
  `backtest-orb-1yr-results.csv`.

## Results — one year (2025-08-11 → 2026-08-11)

| TF | TP | Trades | Win % | Net P/L | Max DD | Final equity |
|---|---|---:|---:|---:|---:|---:|
| M5 | 2R | 405 | 42.0% | +$9,315 | −$2,926 | $19,315 |
| M5 | **3R** | 392 | 34.7% | **+$11,054** | −$2,309 | $21,054 |
| M5 | 4R | 387 | 30.5% | +$9,256 | −$3,199 | $19,256 |
| M15 | 2R | 378 | 38.9% | +$2,975 | −$1,795 | $12,975 |
| M15 | 3R | 363 | 32.5% | +$2,220 | −$2,886 | $12,220 |
| M15 | 4R | 357 | 30.5% | +$4,231 | −$3,833 | $14,231 |
| M30 | 2R | 326 | 39.9% | +$3,122 | −$1,632 | $13,122 |
| M30 | 3R | 308 | 35.1% | +$4,517 | −$2,264 | $14,517 |
| M30 | 4R | 295 | 33.6% | +$4,259 | −$2,200 | $14,259 |
| H1 | 2R | 237 | 41.8% | +$2,761 | −$2,042 | $12,761 |
| H1 | 3R | 226 | 38.9% | +$2,500 | −$1,776 | $12,500 |
| H1 | 4R | 220 | 36.8% | +$4,194 | −$1,856 | $14,194 |
| H4 | any | 0 | — | — | — | bars never land on session hour |
| D1 | any | 0 | — | — | — | same — ORB is intraday-only |

## M1 — broker history caps at ~100k bars (3.5 months only, Apr 27 → Aug 10)

| TF | TP | Trades | Win % | Net P/L | Max DD |
|---|---|---:|---:|---:|---:|
| M1 | 2R | 120 | 40.0% | +$1,508 | −$1,013 |
| M1 | 3R | 117 | 34.2% | +$2,365 | −$828 |
| M1 | 4R | 113 | 26.5% | +$468 | −$1,144 |

## Context: fixed stops vs box stops (H1, 3 months, same data)

| Exits | Trades | Win % | Net | Max DD |
|---|---:|---:|---:|---:|
| Fixed SL $4 / TP $12 (EA defaults) | 79 | 25.3% | −$546 | −$903 |
| Box SL, 2R target | 63 | 52.4% | +$2,427 | −$360 |

The fixed stop sat inside the box and got clipped by range noise; moving the
stop to the invalidation level flipped the strategy from losing to winning on
identical signals. Full trade logs: `backtest-orb-3mo*.csv`.

## Read of the results

1. **15 of 15 intraday runs profitable** across four timeframes × three TP
   multiples (plus M1's three on its shorter window). The edge does not
   depend on parameter choice — the strongest robustness signal available
   from a single year.
2. **M5 is the standout** (+93–110%/yr): the 15-minute box catches the
   session-open volatility burst most precisely.
3. **Caveats, in order of importance:**
   - Fill realism: fixed $0.30 spread, no slippage. Session-open gold on M1/M5
     is exactly where real spreads widen. Live results WILL be worse; the
     sim's SL-wins-ties pessimism offsets only part of that.
   - One market, one year, and 2025–26 was a strong gold-trend regime.
   - Session hour 1 is broker-server-specific — re-verify on any new broker.
   - M1 span ≠ the others; do not compare its totals directly.

## Out-of-sample: 2024, H1 (added same day — CHANGES THE CONCLUSION)

Broker M5 history starts 2025-03-05, so 2024 could only be tested on H1
(`data/xauusd-h1-2024.csv`, 5,938 bars).

| TP | Trades | Win % | Net P/L | Max DD |
|---|---:|---:|---:|---:|
| 2R | 329 | 35.0% | −$2,160 | −$3,578 |
| 3R | 322 | 30.1% | −$2,159 | −$3,661 |
| 4R | 315 | 28.9% | −$1,473 | −$3,188 |

**Every configuration lost in 2024.** The same H1 settings that made +25–42%
in 2025–26 lost 15–22% the year before. The edge is REGIME-DEPENDENT: it
harvests clean session-open breakouts in strong trend years and bleeds in
choppy ones. The 2025–26 sweep was fifteen views of one favorable year, not
fifteen independent confirmations.

## Revised verdict

NOT deployable as-is — a strategy that needs the right year is a bet on the
regime, not an edge you control. Paths that could change this, in order:

1. **Regime filter** — only trade when a trend/volatility condition holds
   (e.g. price above a long MA, ATR expanding). Test: does it sit out most of
   2024 while keeping most of 2025–26?
2. Session-hour sweep (0–23) — confirm hour 1 wasn't lucky in-sample.
3. Spread stress (2–3×) on any surviving config.
4. Only then a demo forward test via `run_live.py`.
