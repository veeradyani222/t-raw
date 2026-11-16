<#
  Turn on phone alerts (Telegram) for the VM bot + watchdog. Run it on YOUR laptop:

    powershell -ExecutionPolicy Bypass -File ops\set_telegram.ps1

  Before running:
    1. In Telegram, open @BotFather, send /newbot, pick any name -> it gives you a token.
    2. Open your new bot's chat and send it any message (e.g. "hi"), so it knows your chat.

  You paste the token into a hidden prompt. This script finds your chat id, sends a
  test message, writes TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID into the VM's .env
  (never to the screen or a file here), then restarts only the Python bot (MT5 keeps
  running; the bot re-adopts open trades) so its own alerts start too.
#>
$sec = Read-Host "Telegram bot token from @BotFather (hidden)" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
try { $token = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
$token = "$token".Trim()
if (-not $token) { Write-Host "No token typed - nothing changed."; exit 1 }

try { $me = Invoke-RestMethod "https://api.telegram.org/bot$token/getMe" -TimeoutSec 15 }
catch { Write-Host "Telegram rejected that token. Copy it again from @BotFather."; exit 1 }
$upd = Invoke-RestMethod "https://api.telegram.org/bot$token/getUpdates" -TimeoutSec 15
$chat = $upd.result | ForEach-Object { $_.message.chat.id } | Where-Object { $_ } | Select-Object -Last 1
if (-not $chat) {
    Write-Host "Bot @$($me.result.username) found, but it has no messages yet. Send it 'hi' in Telegram, then run this again."
    exit 1
}
Invoke-RestMethod -Method Post "https://api.telegram.org/bot$token/sendMessage" -Body @{ chat_id = $chat; text = "mt5-trader alerts connected. You'll get a message here if the bot stops trading." } -TimeoutSec 15 | Out-Null
Write-Host "Test message sent to your Telegram (bot @$($me.result.username))."

$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($token))
Remove-Variable token
$remote = @'
$ProgressPreference = "SilentlyContinue"
cd C:\mt5-trader
$tok = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__B64__'))
$keep = @(Get-Content .env | Where-Object { $_ -notmatch '^\s*TELEGRAM_(BOT_TOKEN|CHAT_ID)\s*=' })
$keep += "TELEGRAM_BOT_TOKEN=" + $tok
$keep += "TELEGRAM_CHAT_ID=__CHAT__"
Set-Content .env $keep -Encoding ascii
Remove-Variable tok
Write-Host ".env updated with Telegram settings"
# restart only the Python bot; run_bot.ps1's loop brings it back in ~5s with the new settings
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "run_live" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
Write-Host "bot restarting (about 1 minute); you should get its startup message on Telegram"
'@
$remote = $remote.Replace("__B64__", $b64).Replace("__CHAT__", "$chat")
$enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($remote))
Remove-Variable b64, remote

gcloud compute ssh mt5-bot --zone=us-east1-b --project=mt5-trader-bot-16108 --account=veeradyani16108@gmail.com `
    --tunnel-through-iap --quiet --command="powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand $enc" 2>&1 |
    Where-Object { "$_" -notmatch "^#< CLIXML|<Objs|troubleshoot|Recommendation|recommendations|plink|^\s*$" }
