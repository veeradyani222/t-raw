<#
  Point the VM's MT5 + bot at a trading account. Run it on YOUR laptop:

    powershell -ExecutionPolicy Bypass -File ops\set_mt5_login.ps1 [-Login 12118056] [-Server FundedNext-Server]

  You type the password into a hidden prompt; it goes straight to the VM's .env
  (MT5_LOGIN / MT5_PASSWORD / MT5_SERVER), never to the screen or to a file here.
  Then it restarts MT5 and the bot so both come up on that account, and prints
  only the account number, server, balance and the bot's startup line.
#>
param([string]$Login = "12118056", [string]$Server = "FundedNext-Server")

$sec = Read-Host "MT5 password for account $Login on $Server (hidden)" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
try { $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
if (-not $plain) { Write-Host "No password typed - nothing changed."; exit 1 }
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($plain))
Remove-Variable plain

$remote = @'
$ProgressPreference = "SilentlyContinue"
cd C:\mt5-trader
$pw = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__B64__'))
$keep = @(Get-Content .env | Where-Object { $_ -notmatch '^\s*MT5_(LOGIN|PASSWORD|SERVER)\s*=' })
$keep += "MT5_LOGIN=__LOGIN__"
$keep += "MT5_PASSWORD='" + $pw + "'"
$keep += "MT5_SERVER=__SERVER__"
Set-Content .env $keep -Encoding ascii
Remove-Variable pw
Write-Host ".env updated (login __LOGIN__, server __SERVER__)"
Stop-ScheduledTask -TaskName MT5Trader -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "run_live" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Get-Process terminal64 -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep 5
Start-ScheduledTask -TaskName MT5Trader
Write-Host "restarting MT5 and the bot on the new account (about 2 minutes)..."
Start-Sleep 110
.venv\Scripts\python.exe -c "import MetaTrader5 as m; ok=m.initialize(); a=m.account_info(); print('MT5:', 'LOGGED IN' if a else 'NOT logged in', (a.login, a.server, 'balance', a.balance, 'mode', ['demo','contest','real'][a.trade_mode]) if a else m.last_error())"
Get-Content trader.log -Tail 150 | Select-String "bot started|NOT running|NOT a demo|ERROR|Invalid|authoriz" | Select-Object -Last 4 | ForEach-Object { $_.Line.Substring(0, [Math]::Min(260, $_.Line.Length)) }
'@
$remote = $remote.Replace("__B64__", $b64).Replace("__LOGIN__", $Login).Replace("__SERVER__", $Server)
$enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($remote))
Remove-Variable b64, remote

gcloud compute ssh mt5-bot --zone=us-east1-b --project=mt5-trader-bot-16108 --account=veeradyani16108@gmail.com `
    --tunnel-through-iap --quiet --command="powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand $enc" 2>&1 |
    Where-Object { "$_" -notmatch "^#< CLIXML|<Objs|troubleshoot|Recommendation|recommendations|plink|^\s*$" }
