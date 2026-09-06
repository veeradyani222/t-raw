<#
  mt5-trader daily state export
  -----------------------------
  Runs once a day as a SYSTEM scheduled task (see install_daily_export.ps1) so
  the box publishes its own ground truth and you never have to RDP in just to
  read a log.

  Each run:
    - runs ops\export_state.py  -> ops\state\deals-<date>.csv + status.json
    - copies trader.log and the watchdog log into ops\state\
    - git pull --rebase, commit, push to origin main

  On a rebase conflict it ABORTS and alerts rather than forcing: a wedged repo
  on this box means the next code deploy silently doesn't pull, which is a worse
  failure than a missed export.

  Telegram creds come from the same .env the bot uses. Nothing here is secret.
#>
param(
    [string]$ProjectDir = "C:\Users\Administrator\Desktop\mt5-trader",
    [string]$Python     = "python",
    [int]$Days          = 30
)

$ErrorActionPreference = "Stop"

$EnvFile  = Join-Path $ProjectDir ".env"
$StateDir = Join-Path $ProjectDir "ops\state"
$LogFile  = Join-Path $env:ProgramData "mt5-watchdog\daily_export.log"
New-Item -ItemType Directory -Path (Split-Path $LogFile) -Force | Out-Null
New-Item -ItemType Directory -Path $StateDir -Force | Out-Null

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

Set-Location $ProjectDir

# --- 1. broker ground truth ------------------------------------------------
Write-Log "exporting MT5 state ..."
& $Python (Join-Path $ProjectDir "ops\export_state.py") --days $Days 2>&1 | ForEach-Object { Write-Log $_ }
if ($LASTEXITCODE -ne 0) {
    Write-Log "export_state.py failed (exit $LASTEXITCODE) — committing logs anyway"
    Send-Telegram "daily export: MT5 snapshot FAILED (exit $LASTEXITCODE). Logs still committed."
}

# --- 2. the logs -----------------------------------------------------------
Copy-Item (Join-Path $ProjectDir "trader.log") (Join-Path $StateDir "trader.log") -Force -ErrorAction SilentlyContinue
Copy-Item (Join-Path $env:ProgramData "mt5-watchdog\watchdog.log") (Join-Path $StateDir "watchdog.log") -Force -ErrorAction SilentlyContinue

# --- 3. publish ------------------------------------------------------------
git add -- ops/state
$staged = git diff --cached --name-only
if (-not $staged) { Write-Log "nothing changed; done"; exit 0 }

git -c user.name="mt5-trader box" -c user.email="bot@localhost" commit -q -m "chore: daily state export $(Get-Date -Format 'yyyy-MM-dd')"
if ($LASTEXITCODE -ne 0) { Write-Log "commit failed"; Send-Telegram "daily export: git commit FAILED"; exit 1 }

git pull --rebase --quiet origin main
if ($LASTEXITCODE -ne 0) {
    git rebase --abort 2>$null
    Write-Log "rebase conflicted — aborted, NOT pushing"
    Send-Telegram "daily export: git pull --rebase conflicted. Aborted so deploys keep working. Needs a look."
    exit 1
}

git push --quiet origin main
if ($LASTEXITCODE -ne 0) {
    Write-Log "push failed (credentials?)"
    Send-Telegram "daily export: git push FAILED — check the stored GitHub token on the box."
    exit 1
}

Write-Log "pushed daily state export"
exit 0
