<#
  mt5-trader fresh-box bootstrap
  ------------------------------
  Turns an EMPTY Windows box (Google Cloud / AWS RDP, nothing installed) into a
  running bot. Idempotent: re-running it upgrades/repairs instead of breaking.

  Run in an ELEVATED PowerShell (Start > type "powershell" > Run as administrator),
  with the account details in environment variables, then ONE line:

    $env:MT5_LOGIN='12345678'; $env:MT5_PASSWORD='xxxx'; $env:MT5_SERVER='FundedNext-Server'
    $env:TELEGRAM_BOT_TOKEN='123:abc'; $env:TELEGRAM_CHAT_ID='999'
    iex (irm https://raw.githubusercontent.com/veeradyani222/t-raw/main/ops/bootstrap.ps1)

  Optional env vars:
    MT5_TRADER_DIR              where to put the repo   (default: <Desktop>\mt5-trader)
    MT5_TRADER_REPO             git URL                 (default: the public t-raw repo)
    MT5_SETUP_URL               broker-branded MT5 installer URL (default: MetaQuotes generic)
    WINDOWS_AUTOLOGON_PASSWORD  this Windows user's password. If set, the box auto-logs-in
                                after a reboot so the watchdog's reboot actually revives the
                                bot. Stored in the registry in plain text (Microsoft's own
                                AutoAdminLogon mechanism) - your call.

  What it does, in order:
    1. Git, Python 3.14, MetaTrader 5   (skips anything already installed)
    2. clone/pull the repo, build .venv, pip install
    3. write .env from the env vars above (never overwrites an existing .env)
    4. scheduled tasks: MT5Trader (at logon), MT5Watchdog (SYSTEM, 10 min),
       MT5DailyExport (SYSTEM, 23:45)
    5. start the bot now and show the first log lines
#>
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

# ---------------------------------------------------------------------------
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
if (-not ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    throw "Run this in an ELEVATED PowerShell (Run as administrator)."
}

$Repo   = if ($env:MT5_TRADER_REPO) { $env:MT5_TRADER_REPO } else { "https://github.com/veeradyani222/t-raw.git" }
$Dir    = if ($env:MT5_TRADER_DIR)  { $env:MT5_TRADER_DIR }  else { Join-Path ([Environment]::GetFolderPath("Desktop")) "mt5-trader" }
$PyVer  = "3.14.3"
$PyUrl  = "https://www.python.org/ftp/python/$PyVer/python-$PyVer-amd64.exe"
$Mt5Url = if ($env:MT5_SETUP_URL) { $env:MT5_SETUP_URL } else { "https://download.mql5.com/cdn/web/metaquotes.software.corp/mt5/mt5setup.exe" }
$Tmp    = Join-Path $env:TEMP "mt5-trader-bootstrap"
New-Item -ItemType Directory -Force -Path $Tmp | Out-Null

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function Refresh-Path {
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
}
function Download($url, $out) {
    Write-Host "    downloading $url"
    Invoke-WebRequest -Uri $url -OutFile $out -UseBasicParsing
}

# --- 1a. Git ---------------------------------------------------------------
Step "Git"
Refresh-Path
if (Get-Command git -ErrorAction SilentlyContinue) {
    Write-Host "    already installed: $(git --version)"
} else {
    $rel = Invoke-RestMethod -Uri "https://api.github.com/repos/git-for-windows/git/releases/latest" -UseBasicParsing
    $asset = $rel.assets | Where-Object { $_.name -like "Git-*-64-bit.exe" } | Select-Object -First 1
    $exe = Join-Path $Tmp $asset.name
    Download $asset.browser_download_url $exe
    Start-Process -FilePath $exe -ArgumentList "/VERYSILENT /NORESTART /NOCANCEL /SP- /CLOSEAPPLICATIONS" -Wait
    Refresh-Path
    Write-Host "    installed: $(git --version)"
}

# --- 1b. Python -------------------------------------------------------------
Step "Python $PyVer"
$PyExe = "C:\Program Files\Python$($PyVer.Split('.')[0])$($PyVer.Split('.')[1])\python.exe"
if (Test-Path $PyExe) {
    Write-Host "    already installed: $(& $PyExe --version)"
} else {
    $exe = Join-Path $Tmp "python-$PyVer-amd64.exe"
    Download $PyUrl $exe
    Start-Process -FilePath $exe -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_launcher=1" -Wait
    Refresh-Path
    if (-not (Test-Path $PyExe)) { throw "Python install failed - $PyExe not found" }
    Write-Host "    installed: $(& $PyExe --version)"
}

# --- 1c. MetaTrader 5 -------------------------------------------------------
Step "MetaTrader 5"
function Find-Terminal {
    $hits = Get-ChildItem "C:\Program Files", "C:\Program Files (x86)" -Filter terminal64.exe -Recurse -Depth 2 -ErrorAction SilentlyContinue
    if ($hits) { return $hits[0].FullName }
    return $null
}
$Terminal = Find-Terminal
if ($Terminal) {
    Write-Host "    already installed: $Terminal"
} else {
    $exe = Join-Path $Tmp "mt5setup.exe"
    Download $Mt5Url $exe
    Start-Process -FilePath $exe -ArgumentList "/auto" -Wait
    Start-Sleep -Seconds 5
    $Terminal = Find-Terminal
    if (-not $Terminal) { throw "MT5 install finished but terminal64.exe was not found" }
    Write-Host "    installed: $Terminal"
    # the installer launches the terminal; close it, the launcher starts it its own way
    Get-Process -Name terminal64 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
}

# --- 2. repo + venv ---------------------------------------------------------
Step "repo -> $Dir"
if (Test-Path (Join-Path $Dir ".git")) {
    git -C $Dir pull --ff-only
} else {
    git clone $Repo $Dir
}
Set-Location $Dir
$Venv = Join-Path $Dir ".venv\Scripts\python.exe"
if (-not (Test-Path $Venv)) { & $PyExe -m venv (Join-Path $Dir ".venv") }
& $Venv -m pip install --quiet --upgrade pip
& $Venv -m pip install --quiet -r (Join-Path $Dir "requirements.txt")
Write-Host "    venv ready: $(& $Venv --version)"

# --- 3. .env ----------------------------------------------------------------
Step ".env"
$EnvFile = Join-Path $Dir ".env"
if (Test-Path $EnvFile) {
    Write-Host "    keeping the existing .env (delete it and re-run to regenerate)"
} else {
    if (-not $env:MT5_LOGIN -or -not $env:MT5_PASSWORD -or -not $env:MT5_SERVER) {
        throw "Set `$env:MT5_LOGIN, `$env:MT5_PASSWORD and `$env:MT5_SERVER before running (see the header of this script)."
    }
    @(
        "MT5_LOGIN=$($env:MT5_LOGIN)",
        "MT5_PASSWORD=$($env:MT5_PASSWORD)",
        "MT5_SERVER=$($env:MT5_SERVER)",
        "MT5_PATH=$Terminal",
        "TELEGRAM_BOT_TOKEN=$($env:TELEGRAM_BOT_TOKEN)",
        "TELEGRAM_CHAT_ID=$($env:TELEGRAM_CHAT_ID)"
    ) | Set-Content -Path $EnvFile -Encoding ascii
    Write-Host "    written (login $($env:MT5_LOGIN) @ $($env:MT5_SERVER))"
}

# --- 4. scheduled tasks -----------------------------------------------------
Step "scheduled tasks"
$User = "$env:USERDOMAIN\$env:USERNAME"
$Bat  = Join-Path $Dir "ops\mt5-trader.bat"
$action    = New-ScheduledTaskAction -Execute $Bat -WorkingDirectory $Dir
$trigger   = New-ScheduledTaskTrigger -AtLogOn -User $User
$principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName "MT5Trader" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Write-Host "    MT5Trader      : runs ops\mt5-trader.bat when $User logs on"

& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Dir "ops\install_watchdog.ps1") -ProjectDir $Dir | Out-Null
Write-Host "    MT5Watchdog    : SYSTEM, every 10 min, reboots the box if the bot is gone"
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $Dir "ops\install_daily_export.ps1") -ProjectDir $Dir -Python $Venv | Out-Null
Write-Host "    MT5DailyExport : SYSTEM, 23:45, pushes logs + fills to git (needs a stored PAT, see ops\README.md)"

if ($env:WINDOWS_AUTOLOGON_PASSWORD) {
    $wl = "HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon"
    Set-ItemProperty $wl AutoAdminLogon "1"
    Set-ItemProperty $wl DefaultUserName $env:USERNAME
    Set-ItemProperty $wl DefaultDomainName $env:USERDOMAIN
    Set-ItemProperty $wl DefaultPassword $env:WINDOWS_AUTOLOGON_PASSWORD
    Write-Host "    auto-logon     : ON for $User (a watchdog reboot now relaunches the bot)"
} else {
    Write-Host "    auto-logon     : not set. After a reboot the bot waits until someone logs in." -ForegroundColor Yellow
    Write-Host "                     (set `$env:WINDOWS_AUTOLOGON_PASSWORD and re-run to enable)" -ForegroundColor Yellow
}

# --- 5. go ------------------------------------------------------------------
Step "starting the bot"
Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -match 'run_live\.py' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Start-ScheduledTask -TaskName "MT5Trader"
$LogFile = Join-Path $Dir "trader.log"
Write-Host "    waiting 45s for the terminal to log in and the bot to connect ..."
Start-Sleep -Seconds 45
if (Test-Path $LogFile) {
    Write-Host ""
    Get-Content $LogFile -Tail 12
} else {
    Write-Host "    no trader.log yet - check the MT5Trader task: Get-ScheduledTaskInfo MT5Trader" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Look for 'connected:' then 'preflight ok' above. An ERROR line names exactly what to fix." -ForegroundColor Green
Write-Host "Prove the order path now:   .venv\Scripts\python manual_trade.py buy   then   ... close"
Write-Host "Watch it live:              Get-Content trader.log -Wait -Tail 20"
Write-Host "The entry fires at 01:00 on the BROKER clock (GMT+3 in summer, GMT+2 in winter)."
