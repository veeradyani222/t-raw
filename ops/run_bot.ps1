<#
  mt5-trader launcher
  -------------------
  What the scheduled task / Startup entry actually runs. Two jobs:

    1. Make sure the MT5 terminal is up, logged in to the .env account, with
       Algo Trading ON. It is started with a /config ini generated from .env,
       because a terminal launched by the Python bridge alone starts with
       whatever Algo Trading state it had last time - and OFF means every
       order_send is rejected with retcode 10027.
    2. Run run_live.py in a restart loop, so a Python crash comes back in 5s.
       (A signed-out RDP session still kills this loop; ops\watchdog.ps1 covers
       that by rebooting the box.)

  Reads MT5_LOGIN / MT5_PASSWORD / MT5_SERVER / MT5_PATH from .env.
#>
param(
    [string]$ProjectDir = (Split-Path $PSScriptRoot -Parent)
)

$ErrorActionPreference = "Continue"
Set-Location $ProjectDir

$EnvFile = Join-Path $ProjectDir ".env"
$Python  = Join-Path $ProjectDir ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) { $Python = "python" }

function Get-EnvVar($name) {
    if (-not (Test-Path $EnvFile)) { return $null }
    foreach ($line in Get-Content $EnvFile) {
        if ($line -match "^\s*$name\s*=\s*(.+?)\s*$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

function Find-Terminal {
    $fromEnv = Get-EnvVar "MT5_PATH"
    if ($fromEnv -and (Test-Path $fromEnv)) { return $fromEnv }
    $hits = Get-ChildItem "C:\Program Files", "C:\Program Files (x86)" -Filter terminal64.exe -Recurse -Depth 2 -ErrorAction SilentlyContinue
    if ($hits) { return $hits[0].FullName }
    return $null
}

# --- 1. terminal --------------------------------------------------------------
$terminal = Find-Terminal
if (-not $terminal) {
    Write-Host "ERROR: terminal64.exe not found. Install MetaTrader 5 (or set MT5_PATH in .env)." -ForegroundColor Red
} elseif (-not (Get-Process -Name terminal64 -ErrorAction SilentlyContinue)) {
    $login  = Get-EnvVar "MT5_LOGIN"
    $pass   = Get-EnvVar "MT5_PASSWORD"
    $server = Get-EnvVar "MT5_SERVER"
    $ini    = Join-Path $ProjectDir "ops\mt5-start.ini"   # git-ignored: holds the password
    $lines  = @("[Common]")
    if ($login -and $pass -and $server) {
        $lines += "Login=$login"; $lines += "Password=$pass"; $lines += "Server=$server"
    }
    $lines += ""
    $lines += "[Experts]"
    $lines += "AllowLiveTrading=1"   # the Algo Trading button
    $lines += "AllowDllImport=0"
    $lines += "Enabled=1"
    $lines += "Account=0"
    $lines += "Profile=0"
    Set-Content -Path $ini -Value $lines -Encoding ascii
    Write-Host "starting MT5 terminal: $terminal"
    Start-Process -FilePath $terminal -ArgumentList "/config:`"$ini`"" -WorkingDirectory (Split-Path $terminal -Parent)
    Start-Sleep -Seconds 20      # let it log in and stream quotes before the bot attaches
} else {
    Write-Host "MT5 terminal already running"
}

# --- 2. the bot, forever ------------------------------------------------------
while ($true) {
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  starting run_live.py"
    & $Python (Join-Path $ProjectDir "run_live.py")
    Write-Host "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')  run_live.py exited ($LASTEXITCODE); restarting in 5s"
    Start-Sleep -Seconds 5
}
