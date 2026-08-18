<#
  Registers the mt5-trader watchdog as a scheduled task.
  RUN THIS ONCE, on the server, in an ELEVATED PowerShell (Run as administrator).

    cd C:\Users\Administrator\Desktop\mt5-trader
    powershell -ExecutionPolicy Bypass -File ops\install_watchdog.ps1

  The task:
    - runs as SYSTEM  -> works whether or not anyone is logged in (survives sign-out)
    - fires at startup AND every 10 minutes  -> catches a dead bot fast
    - runs with highest privileges  -> allowed to reboot the box to self-heal

  Re-running it is safe: it overwrites the existing task (-Force).
#>
param(
    [string]$ProjectDir = "C:\Users\Administrator\Desktop\mt5-trader",
    [string]$TaskName   = "MT5Watchdog"
)

$ErrorActionPreference = "Stop"

# must be elevated
$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin = ([Security.Principal.WindowsPrincipal]$id).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: run this in an ELEVATED PowerShell (Run as administrator)." -ForegroundColor Red
    exit 1
}

$script = Join-Path $ProjectDir "ops\watchdog.ps1"
if (-not (Test-Path $script)) {
    Write-Host "ERROR: cannot find $script - did you git pull?" -ForegroundColor Red
    exit 1
}

$argline = '-NoProfile -ExecutionPolicy Bypass -File "{0}" -ProjectDir "{1}"' -f $script, $ProjectDir
$action  = New-ScheduledTaskAction -Execute "powershell.exe" -Argument $argline

$atStartup = New-ScheduledTaskTrigger -AtStartup
$every10   = New-ScheduledTaskTrigger -Once -At ((Get-Date).AddMinutes(1)) -RepetitionInterval (New-TimeSpan -Minutes 10) -RepetitionDuration (New-TimeSpan -Days 3650)

$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $atStartup, $every10 -Principal $principal -Settings $settings -Force | Out-Null

Write-Host "Installed scheduled task '$TaskName' (SYSTEM, at startup + every 10 min)." -ForegroundColor Green
Write-Host "Running it once now to confirm it works..."
Start-ScheduledTask -TaskName $TaskName
Start-Sleep 5

$logFile = Join-Path $env:ProgramData "mt5-watchdog\watchdog.log"
Write-Host ""
Write-Host "Watchdog log (should say 'ok: run_live.py is running'):"
if (Test-Path $logFile) { Get-Content $logFile -Tail 3 } else { Write-Host "(no log yet - give it a few seconds and check $logFile)" }
Write-Host ""
Write-Host "Manage later with:"
Write-Host "  Get-ScheduledTaskInfo $TaskName                       # status / last run"
Write-Host ('  Unregister-ScheduledTask {0} -Confirm:$false          # remove' -f $TaskName)
