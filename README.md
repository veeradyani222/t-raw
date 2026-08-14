# mt5-trader

Automated forex trading pipeline on MetaTrader 5. Python drives the MT5
terminal via the official `MetaTrader5` package. **Demo accounts only** — the
code refuses to trade anything else.

## Run it

```powershell
# tests (no MT5 needed)
.venv\Scripts\python -m pytest tests -q

# backtest any symbol/timeframe/date range — serves from data/ cache, else
# fetches from MT5; writes a per-trade CSV log to logs/ every run
.venv\Scripts\python backtest.py XAUUSD H1 --from 2025-08-11 --to 2026-08-11

# v1-exact behavior for comparison runs:
.venv\Scripts\python backtest.py XAUUSD H1 --from 2026-05-11 --to 2026-08-11 `
    --tp-mode r_multiple --no-structure-filter

# live loop on the demo account (market hours only)
.venv\Scripts\python run_live.py
```

`backtest.py` defaults to ORB v2: structure filter on (longs need rising
swing lows, shorts falling swing highs), stop at the far side of the box,
target at the most recent swing level beyond entry (R-multiple fallback).
The tick-volume filter is opt-in (`--vol-filter`) — it backtested worse at
every threshold tried. Design + evidence:
`docs/2026-08-11-orb-v2-design.md`. Older scripts `run_backtest.py` /
`run_orb_sweep.py` still work but `backtest.py` supersedes them.

## Configure

Copy `.env.example` to `.env`. Everything is optional: leave `MT5_*` empty to
use the terminal's logged-in account, leave `TELEGRAM_*` empty for log-only
alerts. Strategy/risk knobs live in `trader/config.py`.

## Strategies

The engine runs whichever strategy `Config.strategy` names, from the registry
in `trader/strategies/`:

| Name | Idea | Ported from | Authored for |
|---|---|---|---|
| `sma_cross` | SMA 20/50 crossover (pipeline proof) | — | EURUSD H1 |
| `orb` | Opening-range breakout (first 3 bars set the box) | `ea-library/GOLD_ORB` | XAUUSD H1 |

(A BBRSI port was removed 2026-08-11: its source repo admits the raw signal
is unprofitable without the grid module, which we will never run.)

Every strategy is a pure module — `lookback(cfg)` plus
`compute_signal(candles, cfg) -> Signal` — so backtest and live run identical
code, and the ports deliberately EXCLUDE the source EAs' grid/martingale and
custom stops: sizing, SL/TP, and halts always come from `trader/risk.py`.
When switching strategy, switch `symbol`/`timeframe`/pip settings in
`trader/config.py` to match. To add a strategy: new module in
`trader/strategies/`, register it in `STRATEGIES`, add tests. See
`docs/2026-08-09-mt5-trader-design.md` for the architecture.

## ea-library/

Open-source MQL5 EAs pulled for evaluation (source only, shipped binaries
deleted) — candidate strategies to port into `compute_signal()` or to run
directly in MT5 after compiling from source ourselves. Claimed results are
unverified until re-backtested here; demo account only, always. Details and
rules: `ea-library/README.md`.
