<#
  mt5-trader watchdog
  -------------------
  Runs every ~10 min as a SYSTEM scheduled task (see install_watchdog.ps1), so it
  keeps checking even when NO ONE is logged in — which is exactly the gap the
  Startup .bat can't cover: if the RDP session is signed out, the .bat and its
  restart loop die with it, and nothing brings the bot back until a reboot.

  What it does each run:
    - looks for a python process actually running run_live.py
    - if it's alive  -> clears the miss counter, done
    - if it's gone   -> Telegram-alerts you, and after REBOOT_AFTER consecutive
                        misses reboots the box (auto-login then relaunches the
                        Startup .bat -> bot back up). Reboots are rate-limited to
                        one per hour so a genuinely broken bot can't boot-loop.

  Telegram creds are read from the same .env the bot uses (TELEGRAM_BOT_TOKEN /
  TELEGRAM_CHAT_ID). Nothing here is secret, so it's safe to commit.
#>
param(
    [string]$ProjectDir = "C:\Users\Administrator\Desktop\mt5-trader",
    [int]$RebootAfter   = 2,        # consecutive misses (~10 min each) before reboot
    [int]$RebootCooldownMinutes = 60
)

$ErrorActionPreference = "Stop"

$EnvFile   = Join-Path $ProjectDir ".env"
$StateDir  = Join-Path $env:ProgramData "mt5-watchdog"
$MissFile  = Join-Path $StateDir "misses.txt"
$RebootFile= Join-Path $StateDir "last_reboot.txt"
$LogFile   = Join-Path $StateDir "watchdog.log"
if (-not (Test-Path $StateDir)) { New-Item -ItemType Directory -Path $StateDir -Force | Out-Null }

function Write-Log($msg) {
    "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  $msg" | Add-Content -Path $LogFile -Encoding utf8
}

function Get-EnvVar($name) {
    if (-not (Test-Path $EnvFile)) { return $null }
    foreach ($line in Get-Content $EnvFile) {
        if ($line -match "^\s*$name\s*=\s*(.+?)\s*$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

function Send-Telegram($text) {
    $token = Get-EnvVar "TELEGRAM_BOT_TOKEN"
    $chat  = Get-EnvVar "TELEGRAM_CHAT_ID"
    if (-not $token -or -not $chat) { Write-Log "no telegram creds; skipping alert"; return }
    try {
        Invoke-RestMethod -Method Post -TimeoutSec 15 `
            -Uri "https://api.telegram.org/bot$token/sendMessage" `
            -Body @{ chat_id = $chat; text = $text } | Out-Null
    } catch {
        Write-Log "telegram send failed: $($_.Exception.Message)"
    }
}

function Read-Count($path) {
    if (Test-Path $path) {
        $v = 0
        if ([int]::TryParse((Get-Content $path -Raw).Trim(), [ref]$v)) { return $v }
    }
    return 0
}

# --- is the bot actually running? -----------------------------------------
$alive = $false
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue
foreach ($p in $procs) {
    if ($p.CommandLine -and $p.CommandLine -match 'run_live\.py') { $alive = $true; break }
}

if ($alive) {
    Set-Content -Path $MissFile -Value 0 -Encoding utf8
    Write-Log "ok: run_live.py is running"
    exit 0
}

# --- bot is down ----------------------------------------------------------
$misses = (Read-Count $MissFile) + 1
Set-Content -Path $MissFile -Value $misses -Encoding utf8
Write-Log "DOWN: run_live.py not found (miss $misses/$RebootAfter)"
Send-Telegram "WATCHDOG: mt5-trader is DOWN on tradingSuccess (miss $misses/$RebootAfter). run_live.py process not found."

if ($misses -lt $RebootAfter) { exit 0 }

# threshold reached -> reboot, unless we already rebooted recently
$canReboot = $true
if (Test-Path $RebootFile) {
    try {
        $last = [DateTime]::Parse((Get-Content $RebootFile -Raw).Trim())
        if (((Get-Date) - $last) -lt (New-TimeSpan -Minutes $RebootCooldownMinutes)) { $canReboot = $false }
    } catch { $canReboot = $true }
}

if ($canReboot) {
    Write-Log "rebooting to recover (miss $misses)"
    Send-Telegram "WATCHDOG: auto-rebooting tradingSuccess to recover mt5-trader. It should come back within a few minutes."
    Set-Content -Path $RebootFile -Value (Get-Date -Format o) -Encoding utf8
    Set-Content -Path $MissFile   -Value 0 -Encoding utf8
    shutdown /r /t 5 /c "mt5-watchdog auto-recover"
} else {
    Write-Log "still down but rebooted within the last $RebootCooldownMinutes min; NOT rebooting again"
    Send-Telegram "WATCHDOG: mt5-trader still DOWN, but a reboot happened under $RebootCooldownMinutes min ago. Not rebooting again - this needs a manual look (RDP in and check trader.log)."
}
