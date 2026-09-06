# Daily state export from the trading box

**Date:** 2026-09-07
**Status:** approved, implemented

## Problem

Reconciling the live bot against a backtest required an RDP session into the EC2
box to read `trader.log` by hand. RDP is the weakest link in this setup — the
security group pins 3389 to a single home IP that rotates, so getting in is
itself an errand, and signing out (rather than disconnecting) has killed the bot
before. The box should publish what it did without anyone logging in.

A second, sharper need surfaced while diagnosing the 31 Aug – 4 Sep mismatch:
`trader.log` records what the bot **decided**, but not what the broker actually
**filled**. Stop-loss and take-profit fills happen broker-side and never reach
the log as decisions. Without the filled deals, a strategy problem and an
execution problem look identical.

## What it does

A SYSTEM scheduled task, `MT5DailyExport`, runs `ops/daily_export.ps1` daily at
23:45 box time — after the Friday close and before the Sunday open.

1. `ops/export_state.py` writes broker ground truth:
   - `ops/state/deals-YYYY-MM-DD.csv` — every filled deal in the trailing 30 days
   - `ops/state/status.json` — account login/server/balance/equity, open
     positions, and the commit the box is running
2. Copies `trader.log` and `%ProgramData%\mt5-watchdog\watchdog.log` into
   `ops/state/`.
3. `git add ops/state` → commit → `git pull --rebase` → `git push origin main`.

`status.json` carries the running commit deliberately: "is the box on the code I
think it is?" was an open question for two weeks and should be answerable at a
glance.

## Decisions

**Public repo, main branch.** Veer chose both, having been shown that `t-raw` is
public and that `trader.log` was deliberately gitignored. What becomes public:
every trade, every skipped signal, the account number, broker and balance. No
passwords are logged, and a login number alone cannot trade. Mitigation
available but not taken: strip the `connected:` line before committing.

**Rebase, then abort on conflict.** The box now writes to the branch it deploys
from, so collisions are possible. On a conflicted rebase the script aborts,
leaves the tree clean, alerts on Telegram, and does not push. A wedged repo means
the next code deploy silently doesn't pull — a worse failure than a missed
export.

**Copies, not un-ignoring.** Root `trader.log` and `logs/` stay ignored; only
`ops/state/` copies are tracked, via three `!` negations in `.gitignore`. Local
workflow is unchanged.

## Testing

`tests/test_export_state.py` covers the shaping logic — deal decoding, UTC
timestamps, field completeness, empty history, status payload, CSV round trip —
against namedtuple fakes, so it runs with no MT5 terminal. The MT5 and git I/O
sit in `main()` and are verified by a real run on the box.

## Setup, once, on the box

Push rights are new; the box has only ever pulled. Veer creates a fine-grained
GitHub PAT scoped to `t-raw` with contents:write and stores it directly on the
server — it never passes through chat.

```
git config --global credential.helper store
git push origin main          # paste the PAT as the password, once
powershell -ExecutionPolicy Bypass -File ops\install_daily_export.ps1
```
