# Deploying and keeping the live bot alive (ops)

## The multi-strategy demo forward test (branch `multi-strategy-bot`)

`run_live.py` now runs the 66-strategy portfolio from
`docs/board/portfolio-lp300-66.json` (`trader/multi.py` + `trader/multi_live.py`):
every strategy is the same `build_*` research function the backtest used, fed a
rolling window of 6,000 broker bars, one MT5 magic number per strategy
(500000 + its index in the mix), sized with the harness formula (risk x $10,000
at the stop, $14/lot commission reserved, rounded down to the lot step).
Account-wide rails, checked every 10 s on floating equity: **-$300 on the server
day closes everything and blocks entries until the next server day; equity at
$9,300 closes everything and halts for good** (state in `logs/multi_state.json`;
delete it to clear a halt). The demo-only guard is unchanged.

**Start it (laptop or VM):**

```powershell
cd <Desktop>\mt5-trader
git fetch; git checkout multi-strategy-bot; git pull
.venv\Scripts\python run_live.py --preflight      # symbol table; must say every symbol is ok
.venv\Scripts\python run_live.py                 # or let the MT5Trader task / ops
un_bot.ps1 do it
```

The pre-flight refuses to run if a symbol is missing, not tradable, or has a
different contract size / point / lot step / profit currency from what the
research assumed. On **MetaQuotes-Demo the index CFDs (DE40, US500, US30, USTEC)
are quote-only ("Trade disabled")**, which takes 15 of the 66 strategies out; to
run the other 51 anyway set `MULTI_SKIP_UNTRADABLE=1` (the startup Telegram
message then lists exactly which strategies are off and why). On a broker that
names symbols differently (FundedNext: `GER40` for `DE40`), edit
`config/symbols.json` (`map` for every broker, `servers.<prefix of the MT5
server name>` for one broker).

**Bot environment variables** (`.env` in the repo root, read at start):

| Variable | Meaning |
|---|---|
| `MT5_LOGIN` / `MT5_PASSWORD` / `MT5_SERVER` | the demo account; blank = attach to the terminal's logged-in account |
| `MT5_PATH` | `terminal64.exe` to start/attach to; blank = auto-detect |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | alerts and commands; blank = log only |
| `MULTI_MIX_PATH` | the mix JSON to run, absolute or relative to the repo root. Default `docs/board/portfolio-lp300-66.json`. Round 3: `docs/board/portfolio-round3-2y.json`, `-3y.json` or `-5y.json` (readiness per strategy: `docs/2026-10-31-round3-live-readiness.md`). `compare_demo.py` reads the same variable. |
| `MULTI_BASE_MAGIC` | magic number base (default 500000). Use a new range when switching mixes on an account that still holds the old mix's trades, e.g. 510000 for round 3; the old trades keep their broker stops and are left alone. |
| `MULTI_MAX_RISK` | per-trade risk cap as a fraction of the $10k baseline, e.g. `0.0275`. FundedNext funded accounts forbid any single trade risking more than 3%; on the round-3 2y mix this trims only the two 3% strategies. Unset = no cap. |
| `MULTI_SKIP_UNTRADABLE` | `1` = start anyway when the pre-flight rejects a symbol (missing, trade disabled, contract/point/lot-step/currency differ from the research) and switch off just those strategies, each named in the log and in the startup Telegram message. Unset = refuse to start. |

Strategies that must never trade whatever the mix (today: the two round-3
strategies that need a second symbol's bars) are listed with reasons in
`config/live_skip.json`; the bot logs one `SKIPPED` line per strategy and shows
them as OFF in the startup message.

**Fresh GCP Windows VM from this branch:** same one-liner as below, with the
branch's bootstrap and `MT5_TRADER_BRANCH`:

```powershell
$env:MT5_TRADER_BRANCH='multi-strategy-bot'; $env:MULTI_SKIP_UNTRADABLE='1'; $env:MT5_LOGIN='...'; $env:MT5_PASSWORD='...'; $env:MT5_SERVER='MetaQuotes-Demo'; $env:TELEGRAM_BOT_TOKEN='...'; $env:TELEGRAM_CHAT_ID='...'; iex (irm https://raw.githubusercontent.com/veeradyani222/t-raw/multi-strategy-bot/ops/bootstrap.ps1)
```

(`MULTI_SKIP_UNTRADABLE` and `MULTI_MIX_PATH`, when set in the shell, are written
into `.env` by the bootstrap, so the launcher picks them up on every restart; on
an existing box add the lines to `.env` by hand and restart the bot.)

**Daily check routine (5 minutes, from the phone):**

1. The morning Telegram report `📊 demo vs backtest — server day …` (sent
   automatically at the first poll after server midnight, or on demand with the
   `report` button / `report 2026-10-21`). Per strategy it lists trades taken live
   vs in the backtest, entry/exit price differences and the P&L difference, then
   the account totals. What you want to see: the same trades on both sides,
   entry differences of a spread or so, P&L differences of a few dollars.
   A backtest trade with no live twin on the first day (position opened before
   the bot started) is expected; after that, every mismatch needs an explanation.
   Full text + JSON is in `logs/compare/<date>.{txt,json}` on the box.
2. `status` on Telegram: equity, today's P&L vs the -$300 stop, open positions.
3. Once a day the `✅ alive` ping; if it stops, the bot is down (see the watchdog
   section below).
4. From a shell on the box: `python compare_demo.py --date YYYY-MM-DD` prints the
   same report for any past server day.

Telegram buttons: `status`, `risk`, `report`, `close all` (closes everything,
keeps trading), `halt` (closes everything and stops until the state file is
deleted), `help`.


## Fresh box in one command

Open PowerShell **as administrator** on the new box and paste, with your values:

```powershell
$env:MT5_LOGIN='12345678'; $env:MT5_PASSWORD='xxxx'; $env:MT5_SERVER='FundedNext-Server'; $env:TELEGRAM_BOT_TOKEN='123:abc'; $env:TELEGRAM_CHAT_ID='999'; iex (irm https://raw.githubusercontent.com/veeradyani222/t-raw/main/ops/bootstrap.ps1)
```

Optional, set before the same line:

| Variable | Why |
|---|---|
| `$env:WINDOWS_AUTOLOGON_PASSWORD='...'` | Windows password of this user. The box then logs itself in after a reboot, so the watchdog's reboot actually brings the bot back. Stored in the registry in plain text. |
| `$env:MT5_SETUP_URL='https://...'` | Your broker's own MT5 installer, if the generic MetaQuotes one cannot find your server. |
| `$env:MT5_TRADER_DIR='D:\bot'` | Somewhere other than `<Desktop>\mt5-trader`. |

What runs afterwards:

| Piece | Runs as | What |
|---|---|---|
| `MT5Trader` task -> `ops\mt5-trader.bat` -> `ops\run_bot.ps1` | you, at logon | starts `terminal64.exe` with a `/config` ini built from `.env` (login + **Algo Trading on**), then loops `run_live.py`, restarting it 5s after any crash |
| `MT5Watchdog` task -> `ops\watchdog.ps1` | SYSTEM, every 10 min | Telegram-alerts if `run_live.py` is gone; reboots after 2 misses |
| `MT5DailyExport` task -> `ops\daily_export.ps1` | SYSTEM, 23:45 | pushes fills + logs to `ops/state/` (needs a stored GitHub PAT, see below) |

First thing to do once it is up, so you never again wait until 01:00 to find
out that orders are rejected:

```powershell
cd <Desktop>\mt5-trader
Get-Content trader.log -Tail 20            # want: "connected:" then "preflight ok"
.venv\Scripts\python manual_trade.py buy   # 0.01 lot CHFJPY market order
.venv\Scripts\python manual_trade.py close
```

## Why no trade ever fired on the AWS box

`session_entry_lots()` required the last quote to be within 60s of the
**machine** clock (`time.time() - tick.time`). MT5 hands Python broker-local
seconds labelled as UTC, and the broker runs GMT+3 / GMT+2, so that difference
was always about -10800s: every entry was judged stale, skipped as
"session entry ineligible", and nothing said why. Freshness is now judged on
the broker clock alone, every skip logs its reason, and startup pre-flight
fails loudly if Algo Trading is off or the symbol is not tradable.

The daily-export scripts also never parsed under Windows PowerShell 5.1
(em-dashes in a BOM-less UTF-8 file read as a stray quote), which is why
`ops/state/` stayed empty. They are plain ASCII now.

## What happened the time before (2026-08-15)

The bot ran from `mt5-trader.bat` in the Windows **Startup** folder (now the
`MT5Trader` logon task, same idea). That `.bat` has a restart loop, so it survives a Python crash, and auto-login means it comes
back after a reboot. But the whole loop lives **inside your logged-in session** —
so when the RDP session got **signed out**, the loop was killed too, and nothing
restarted it. On top of that, a home-IP change locked RDP out, so no one could get
in to restart it by hand. Result: dead for days, no trades, and no warning.

## The three layers that now protect it

1. **Restart loop (already there).** Python crashes -> relaunches in 5s. Reboot ->
   auto-login re-runs the Startup `.bat`.
2. **Watchdog (`watchdog.ps1`, installed by `install_watchdog.ps1`).** Runs as
   SYSTEM every 10 min, so it keeps working even with nobody logged in. If it sees
   the bot process is gone, it Telegram-alerts you and, after ~20 min down,
   **reboots the box** — which auto-logs-in and relaunches the bot. This is what
   covers the sign-out case the restart loop can't.
3. **Daily heartbeat (in `trader/live.py`).** Once a day the bot sends a Telegram
   `✅ alive` ping, even when it's flat. If that ping stops arriving, you *know*
   it's down — silence is no longer ambiguous.

## Deploying a code change to the server

Push from the laptop, then on the server (RDP in, PowerShell as administrator):

```powershell
cd <Desktop>\mt5-trader
git pull
# kill the running bot; the launcher loop restarts it on the new code in 5s
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object CommandLine -match run_live | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Or re-run the one-command bootstrap: it pulls, re-registers the tasks and restarts.

## The one golden rule

When you finish an RDP session, **Disconnect** (just close the RDP window, or
Start → the person icon → Disconnect). **Never "Sign out."** Signing out kills the
bot. (Even if you forget, the watchdog will now reboot and recover — but don't rely
on it.)

## If you get locked out of RDP again

The bot does **not** need you logged in to keep trading — RDP is only your window
in. If RDP won't connect, it's almost always your home IP changed:
AWS: EC2 → Security Groups → the RDP (3389) inbound rule → Source = **My IP**.
Google Cloud: VPC network → Firewall → the rule allowing tcp:3389 → Source IPv4
ranges = your current IP followed by `/32`.

## Quick health checks (on the server)

```powershell
# bot process alive?
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object CommandLine -match run_live | Select-Object ProcessId
# watchdog task status + log
Get-ScheduledTaskInfo MT5Watchdog
Get-Content "$env:ProgramData\mt5-watchdog\watchdog.log" -Tail 5
# newest bot log lines
Get-Content <Desktop>\mt5-trader\trader.log -Tail 10
```

And on your phone: you should see one `✅ alive` Telegram message per day.

---

## Daily state export (`MT5DailyExport`)

The box publishes its own state to git every day at 23:45, so reading what the
bot did never needs an RDP session.

**Files it writes** (committed to `ops/state/`):

| File | What it is |
|---|---|
| `deals-<date>.csv` | Every filled deal, last 30 days — broker ground truth |
| `status.json` | Account, equity, open positions, **the commit this box runs** |
| `trader.log` | Copy of the bot's decision log |
| `watchdog.log` | Copy of the watchdog's uptime log |

`trader.log` says what the bot **decided**; `deals-<date>.csv` says what the
broker actually **filled**. SL/TP fills never appear as decisions, so you need
both to tell a strategy problem from an execution problem.

**One-time setup** (the box has only ever pulled, never pushed):

```
git config --global credential.helper store
git push origin main          # paste a GitHub PAT (fine-grained, t-raw, contents:write)
```
(The task itself is registered by the bootstrap; until the PAT is stored it
just fails with a Telegram "push FAILED" alert each night.)

**Run it now / check it:**

```
Start-ScheduledTask -TaskName MT5DailyExport
Get-Content $env:ProgramData\mt5-watchdog\daily_export.log -Tail 20
```

On a rebase conflict the script aborts and Telegram-alerts rather than forcing —
a wedged repo would silently break the next code deploy.
