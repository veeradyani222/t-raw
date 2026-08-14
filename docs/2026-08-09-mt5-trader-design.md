# mt5-trader — design

**Date:** 2026-08-09 · **Status:** v1 built and backtested

## Goal
Automation infrastructure for forex trading on MT5, proven end-to-end with a
placeholder strategy before any real strategy work. Demo account only; a hard
guard in code refuses non-demo accounts.

## Decisions
- **Route:** Python + official `MetaTrader5` package driving the MT5 terminal
  (chosen over an MQL5 EA for iteration speed and testability).
- **Architecture:** one strategy definition, two runners. `engine.on_bar()` is
  the single decision step; the backtester (`sim.SimBroker`) and live loop
  (`broker_mt5.MT5Broker`) both implement the same `Broker` protocol, so
  tested logic and traded logic cannot diverge.
- **Placeholder strategy:** SMA 20/50 crossover, EURUSD H1, SL 30 / TP 60 pips.
  Exists to exercise the pipeline, not to make money.
- **Risk rails (always on):** 1% equity risk per trade via position sizing,
  max 1 open position, daily −3% equity halt, lot caps [0.01, 1.0].
- **Alerts:** Telegram if `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` set in
  `.env`, otherwise log-only. All decisions logged to `trader.log`.
- **Backtester model (deliberately simple):** entry at signal-bar close ±1 pip
  spread; SL/TP filled against later bars' high/low, SL wins ties
  (pessimistic). Not research-grade — good enough for pipeline validation.

## Module map
| File | Role | Touches MT5? |
|---|---|---|
| `trader/strategy.py` | candles → LONG/SHORT/FLAT (pure) | no |
| `trader/risk.py` | sizing + RiskGuard rails (pure) | no |
| `trader/engine.py` | per-bar decision step | via Broker protocol only |
| `trader/broker.py` | Broker protocol + Position | no |
| `trader/sim.py` | SimBroker + backtest runner | no |
| `trader/broker_mt5.py` | real broker impl, demo-only guard | **only this file** |
| `trader/live.py` | poll loop, alert on open/close/halt/error | via broker_mt5 |
| `trader/alerts.py` | Telegram / log alerts | no |
| `trader/config.py` | all knobs + .env secrets | no |

## Verification so far
- 13 unit/integration tests pass without MT5 (pure logic + synthetic backtest).
- Real-data backtest: 5,000 EURUSD H1 bars pulled from the live terminal,
  105 trades simulated. (Any profit figure from one sample is noise, not a
  validated edge.)
- MT5 terminal build 6104 installed; MetaQuotes-Demo account auto-created
  (login 110810899, $3,000 virtual). Demo-only guard verified against it.
- **Not yet verified:** live order placement — market closed (Saturday).
  First live-loop session must happen during market hours.

## Out of scope for v1
Dashboard, multi-symbol, ML/strategy research, VPS deployment.
