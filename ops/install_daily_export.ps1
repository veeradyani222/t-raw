<#
  Registers the mt5-trader daily state export as a scheduled task.
  RUN THIS ONCE, on the server, in an ELEVATED PowerShell (Run as administrator).

    cd C:\Users\Administrator\Desktop\mt5-trader
    powershell -ExecutionPolicy Bypass -File ops\install_daily_export.ps1

  The task:
    - runs as SYSTEM  -> works whether or not anyone is logged in
    - fires daily at 23:45 box time (after the Friday close, before Sunday open)
    - is safe to re-run: it overwrites the existing task (-Force)

  BEFORE the first run, give the box push rights ONCE (see ops/README.md):
    git config --global credential.helper store
    git push origin main      # paste a GitHub PAT as the password, once
#>
param(
    [string]$ProjectDir = "C:\Users\Administrator\Desktop\mt5-trader",
    [string]$TaskName   = "MT5DailyExport",
    [string]$At         = "23:45",
    [string]$Python     = "python"
)

$ErrorActionPreference = "Stop"

$id = [Security.Principal.WindowsIdentity]::GetCurrent()
$isAdmin = ([Security.Principal.WindowsPrincipal]$id).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: run this in an ELEVATED PowerShell (Run as administrator)." -ForegroundColor Red
    exit 1
}

$script = Join-Path $ProjectDir "ops\daily_export.ps1"
if (-not (Test-Path $script)) {
    Write-Host "ERROR: $script not found — git pull first." -ForegroundColor Red
    exit 1
}

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$script`" -ProjectDir `"$ProjectDir`" -Python `"$Python`""
$trigger = New-ScheduledTaskTrigger -Daily -At $At
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Minutes 15)

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null

Write-Host "Registered '$TaskName' — runs daily at $At as SYSTEM." -ForegroundColor Green
Write-Host "Test it now with:  Start-ScheduledTask -TaskName $TaskName" -ForegroundColor Cyan
Write-Host "Log:  $env:ProgramData\mt5-watchdog\daily_export.log" -ForegroundColor Cyan
