# mt5-trader

The live runner selects **CHFJPY H1 session trading only**. It buys after the
hour-0 candle closes, uses a 2 x simple ATR14 stop from completed history, no take-profit, and closes
after 12 elapsed hours from actual entry. BOS remains available for research.
The MT5 broker adapter accepts demo accounts only.

## Deploy to a fresh Windows box (one command)

On a brand-new RDP box with nothing installed, open PowerShell **as
administrator** and paste (with your own values):

```powershell
$env:MT5_LOGIN='12345678'; $env:MT5_PASSWORD='xxxx'; $env:MT5_SERVER='FundedNext-Server'; $env:TELEGRAM_BOT_TOKEN='123:abc'; $env:TELEGRAM_CHAT_ID='999'; iex (irm https://raw.githubusercontent.com/veeradyani222/t-raw/main/ops/bootstrap.ps1)
```

`ops/bootstrap.ps1` installs Git, Python and MetaTrader 5, clones this repo,
builds `.venv`, writes `.env`, registers the bot / watchdog / daily-export
scheduled tasks, starts the bot and prints the first log lines. Re-running it
is safe. See [ops/README.md](ops/README.md) for what each piece does and how
to check it.

## Run

```powershell
# Offline tests
.venv\Scripts\python -m pytest tests -q

# BOS backtest; CSV cache or MT5 history, with a per-trade log in logs/
.venv\Scripts\python backtest.py XAUUSD M30 --from 2026-08-12 --to 2026-09-11 --quiet --monthly

# Explicit CSV input (must include tick_volume for CMF)
.venv\Scripts\python backtest.py XAUUSD M30 --from 2026-08-12 --to 2026-09-11 --data data/xauusd-m30-volume-20260912.csv --quiet

# Historical GOLD BOS backtest (not the CHFJPY live configuration)
.venv\Scripts\python run_backtest.py 5000

# Live loop against the demo account (by hand; the MT5Trader task normally does this)
.venv\Scripts\python run_live.py

# Prove the order path on the live symbol, then flatten
.venv\Scripts\python manual_trade.py buy
.venv\Scripts\python manual_trade.py close
```

`backtest.py` exposes BOS controls: `--swing-window`, `--cmf-n`, `--cmf-min`,
`--trend-ma`, `--lookback`, `--tp-mode`, `--tp-r`, and `--tp-min-r`. Its defaults
match the retained GOLD research settings. For fixed baseline loss limits,
add `--loss-baseline 10000 --total-loss-halt 0.06`; the CLI retains its existing
daily-halt default and optional total/trailing-loss controls. `--help` lists the sizing,
spread, account-limit and data options. The CLI starts flat at the beginning of
the selected history; early candles build indicator/structure context.

The simulator uses fixed-spread OHLC fills and closed-balance risk checks;
live trading uses executable quotes and floating equity. Commission, swap,
slippage and latency are not modeled. Historical results are not live fills.

## CHFJPY live behavior

`run_live.py` selects only `CHFJPY`; `GOLD` is retained for research imports.
Risk is 1% equity, at most one lot and one account position, with existing
$300 daily / $600 total entry halts against a fixed $10,000 baseline.
The hour is the MT5 data clock, not India local time; the entry targets 01:00
on the first fresh quote/poll after the hour-0 candle closes, with exit around 13:00.
Mapping to the research feed's market session remains unverified.
Entries more than 60 seconds after that candle closes are skipped; freshness
is judged on the broker clock only (MT5 reports broker-local time labelled as
UTC, so it must never be compared with the machine clock). Every skipped entry
is logged with its reason.
The forming candle never supplies ATR. The midnight-opening option remains available
for research but is not selected by the live runner.
MT5 deal history prevents another entry on the same date after a restart or stop.

Sizing uses executable ask, broker lot steps and MT5 account-currency stop
valuation, reserving $14/lot round-trip commission and 0.1 pip slippage per
fill. These are configurable assumptions, not measured fees or guaranteed
execution bounds. The fixed dollar rails assume a USD account.
[MT5 valuation API](https://www.mql5.com/en/docs/python_metatrader5/mt5ordercalcprofit_py).

Timed exits run every poll, including while entries are halted. They recover
opening times from MT5 positions and retry failed closes. The loop and market
must be available; a stopped loop leaves only the server-side SL active.
The existing loss rails block entries; they do not liquidate floating positions
or persist the daily anchor across process restarts. These semantics differ
from the guarded research simulation. Do not run multiple bot instances.

For CHFJPY historical replay use `research.jpy_account_comparison` and the
[research report](docs/2026-09-13-jpy-account-comparison.md). The generic BOS
simulator's fixed pip value cannot replay this live FX sizing path.

## BOS research strategy

BOS enters on a fresh close through the most recent confirmed fractal swing,
with a bullish body for a long or a bearish body for a short. Any positive
portion of the body beyond the boundary counts; a wick alone does not.
CMF must agree, and the trend SMA filters the direction. Stops use the opposing
swing, with a structure target or an R-multiple fallback.

- `trader/strategies/session.py`: live CHFJPY session signal.
- `trader/strategies/bos.py`: retained BOS signal and confirmation logic.
- `trader/strategies/structure.py`: confirmed fractal swing calculation.
- `trader/engine.py`, `trader/risk.py`, `trader/sim.py`: execution, sizing, limits and simulation.
- `run_live.py`: deployed-strategy configuration and risk rationale.
- `bos_backtest.py`, `bos_variants.py`: BOS research and variant comparisons.
- `wf_search.py`: shared simulation and walk-forward utilities used by BOS research.
- `ops/`: watchdog and daily state export.

BOS research scripts retain their explicit experiment configurations; they do
not inherit the CHFJPY live settings. `run_backtest.py` and the BOS CLI
remain gold research tools. See
[body-confirmation results](docs/2026-09-12-m30-body-confirmation-results.md).

## Startup pre-flight

`broker_mt5.connect()` refuses to start unless the terminal is connected,
**Algo Trading is on**, the account allows expert trading and the symbol is
fully tradable, and it logs the broker clock offset from UTC. Each failure
names the exact fix. `ops/run_bot.ps1` starts the terminal with Algo Trading
forced on, so the check normally passes without touching the terminal.

## Configure

Copy `.env.example` to `.env`. Leave MT5 credentials empty to attach to the
terminal's logged-in account, and Telegram credentials empty for log-only
alerts. Shared settings live in `trader/config.py`; active live values are in
`run_live.py`. BOS, broker history and existing research artifacts are retained.
