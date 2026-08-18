# Keeping the live bot alive (ops)

Plain-language notes on why the bot stopped on 2026-08-15 and what now keeps it running.

## What happened that time

The bot runs from `mt5-trader.bat` in the Windows **Startup** folder. That `.bat`
has a restart loop, so it survives a Python crash, and auto-login means it comes
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

## Deploying this to the server (one time)

On your laptop it's already pushed. On the server (RDP in):

```powershell
cd C:\Users\Administrator\Desktop\mt5-trader
git pull
# restart the bot so the new heartbeat code is running:
#   close the old bot's console window (the looping cmd), then double-click
#   mt5-trader.bat in the Startup folder — or just reboot the box.
# install the watchdog (elevated PowerShell — Run as administrator):
powershell -ExecutionPolicy Bypass -File ops\install_watchdog.ps1
```

That's it. The installer registers the task and runs it once to confirm.

## The one golden rule

When you finish an RDP session, **Disconnect** (just close the RDP window, or
Start → the person icon → Disconnect). **Never "Sign out."** Signing out kills the
bot. (Even if you forget, the watchdog will now reboot and recover — but don't rely
on it.)

## If you get locked out of RDP again

The bot does **not** need you logged in to keep trading — RDP is only your window
in. If RDP won't connect, it's almost always your home IP changed:
AWS Console → EC2 → Security Groups → `launch-wizard-1` → Inbound rules →
the RDP (3389) rule → Source = **My IP** → Save.

## Quick health checks (on the server)

```powershell
# bot process alive?
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object CommandLine -match run_live | Select-Object ProcessId
# watchdog task status + log
Get-ScheduledTaskInfo MT5Watchdog
Get-Content "$env:ProgramData\mt5-watchdog\watchdog.log" -Tail 5
# newest bot log lines
Get-Content C:\Users\Administrator\Desktop\mt5-trader\trader.log -Tail 10
```

And on your phone: you should see one `✅ alive` Telegram message per day.
