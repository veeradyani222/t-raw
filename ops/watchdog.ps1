<#
  mt5-trader watchdog
  -------------------
  Runs every ~10 min as a SYSTEM scheduled task (see install_watchdog.ps1), so it
  keeps checking even when NO ONE is logged in - which is exactly the gap the
  Startup .bat can't cover: if the RDP session is signed out, the .bat and its
  restart loop die with it, and nothing brings the bot back until a reboot.

  What it does each run:
    - looks for a python process actually running run_live.py AND a fresh
      equity status line in trader.log (the bot writes one every 30 min), so a
      crash-looping bot (e.g. MT5 "Algo Trading is OFF") counts as broken too
    - if it's healthy -> clears the miss counter (and says "back up" if it
                        had alerted), done
    - broken but the process is there (crash loop / stuck) -> Telegram alert
                        with the last error line, no reboot (a reboot can't fix
                        an MT5 setting); repeats at most once an hour
    - process gone and nobody logged in and no autologon -> alert "RDP in",
                        no reboot (a reboot without autologon can't help)
    - if it's gone   -> Telegram-alerts you, and after REBOOT_AFTER consecutive
                        misses reboots the box (auto-login then relaunches the
                        Startup .bat -> bot back up). Reboots are rate-limited to
                        one per hour so a genuinely broken bot can't boot-loop.

  Telegram creds are read from the same .env the bot uses (TELEGRAM_BOT_TOKEN /
  TELEGRAM_CHAT_ID). Nothing here is secret, so it's safe to commit.
#>
param(
    [string]$ProjectDir = (Split-Path $PSScriptRoot -Parent),
    [int]$RebootAfter   = 2,        # consecutive misses (~10 min each) before reboot
    [int]$RebootCooldownMinutes = 60,
    [int]$StaleMinutes  = 50,       # bot writes an equity status line every 30 min; none for this long = stuck
    [int]$RealertMinutes = 60,      # repeat a still-broken alert at most this often
    [switch]$DryRun                 # print what it would do; no Telegram, no reboot
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
    if ($DryRun) { Write-Host "TELEGRAM: $text"; return }
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

# --- is the bot actually running and healthy? -----------------------------
$AlertFile = Join-Path $StateDir "last_alert.txt"
function Alert-Due {
    if (-not (Test-Path $AlertFile)) { return $true }
    try { return ((Get-Date) - [DateTime]::Parse((Get-Content $AlertFile -Raw).Trim())) -ge (New-TimeSpan -Minutes $RealertMinutes) }
    catch { return $true }
}
function Mark-Alert { if (-not $DryRun) { Set-Content -Path $AlertFile -Value (Get-Date -Format o) -Encoding utf8 } }

$alive = $false
$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe' OR Name='pythonw.exe'" -ErrorAction SilentlyContinue
foreach ($p in $procs) {
    if ($p.CommandLine -and $p.CommandLine -match 'run_live\.py') { $alive = $true; break }
}

# newest "ALERT: ... equity" line in trader.log = the bot's own heartbeat
$lastBeat = $null
$TraderLog = Join-Path $ProjectDir "trader.log"
if (Test-Path $TraderLog) {
    $hit = Get-Content $TraderLog -Tail 3000 -ErrorAction SilentlyContinue | Select-String 'ALERT: .*equity' | Select-Object -Last 1
    if ($hit -and $hit.Line -match '^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)') { $lastBeat = [DateTime]::ParseExact($Matches[1], 'yyyy-MM-dd HH:mm:ss', $null) }
}
$fresh = $lastBeat -and (((Get-Date) - $lastBeat) -lt (New-TimeSpan -Minutes $StaleMinutes))

function Last-Error {
    $rb = Join-Path $ProjectDir "ops\run_bot.log"
    if (-not (Test-Path $rb)) { return "" }
    $e = Get-Content $rb -Tail 200 -ErrorAction SilentlyContinue | Select-String 'Error:|Exception' | Select-Object -Last 1
    if ($e) { return $e.Line.Trim().Substring(0, [Math]::Min(300, $e.Line.Trim().Length)) }
    return ""
}

if ($alive -and $fresh) {
    if ((Read-Count $MissFile) -gt 0 -or (Test-Path $AlertFile)) {
        Send-Telegram "WATCHDOG: mt5-trader is back up on $env:COMPUTERNAME (last status $($lastBeat.ToString('HH:mm')))."
        if (-not $DryRun) { Remove-Item $AlertFile -ErrorAction SilentlyContinue }
    }
    if (-not $DryRun) { Set-Content -Path $MissFile -Value 0 -Encoding utf8 }
    Write-Log "ok: run_live.py running, last status $lastBeat"
    if ($DryRun) { Write-Host "OK (last status $lastBeat)" }
    exit 0
}

if ($alive) {
    # process exists but no fresh status: crash loop (restarting every few seconds) or stuck.
    # A reboot does not fix an MT5 setting, so alert only.
    $since = if ($lastBeat) { $lastBeat.ToString('yyyy-MM-dd HH:mm') } else { "unknown" }
    Write-Log "BROKEN: run_live.py present but no status line since $since"
    if (Alert-Due) {
        Send-Telegram ("WATCHDOG: mt5-trader is NOT trading on $env:COMPUTERNAME - no status since $since (crash loop or stuck). Last error: " + (Last-Error))
        Mark-Alert
    }
    exit 0
}

# --- process gone ---------------------------------------------------------
$sessionUp = [bool](Get-CimInstance Win32_Process -Filter "Name='explorer.exe'" -ErrorAction SilentlyContinue | Where-Object { $_.SessionId -gt 0 })   # someone has a desktop session
$autoLogon = (Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon' -ErrorAction SilentlyContinue).AutoAdminLogon -eq '1'
if (-not $sessionUp -and -not $autoLogon) {
    Write-Log "DOWN: nobody logged in and no autologon; a reboot cannot help"
    if (Alert-Due) {
        Send-Telegram "WATCHDOG: mt5-trader is DOWN on $env:COMPUTERNAME - nobody is logged in to Windows, so the bot can't start. RDP in (log in as veera, close with X). Setting up Autologon stops this."
        Mark-Alert
    }
    exit 0
}

$misses = (Read-Count $MissFile) + 1
if (-not $DryRun) { Set-Content -Path $MissFile -Value $misses -Encoding utf8 }
Write-Log "DOWN: run_live.py not found (miss $misses/$RebootAfter)"
Send-Telegram "WATCHDOG: mt5-trader is DOWN on $env:COMPUTERNAME (miss $misses/$RebootAfter). run_live.py process not found."
Mark-Alert

if ($misses -lt $RebootAfter) { exit 0 }
if ($DryRun) { Write-Host "would reboot now"; exit 0 }

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
    Send-Telegram "WATCHDOG: auto-rebooting $env:COMPUTERNAME to recover mt5-trader. It should come back within a few minutes."
    Set-Content -Path $RebootFile -Value (Get-Date -Format o) -Encoding utf8
    Set-Content -Path $MissFile   -Value 0 -Encoding utf8
    shutdown /r /t 5 /c "mt5-watchdog auto-recover"
} else {
    Write-Log "still down but rebooted within the last $RebootCooldownMinutes min; NOT rebooting again"
    Send-Telegram "WATCHDOG: mt5-trader still DOWN, but a reboot happened under $RebootCooldownMinutes min ago. Not rebooting again - this needs a manual look (RDP in and check trader.log)."
}
