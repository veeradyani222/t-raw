<#
  Make the VM log in to Windows by itself after every reboot, so the bot always starts.
  Run it on YOUR laptop:

    powershell -ExecutionPolicy Bypass -File ops\set_autologon.ps1

  You type veera's Windows password (the one you use for Remote Desktop) into a hidden
  prompt. On the VM the script first checks the password is right, then runs Microsoft's
  Sysinternals Autologon (C:\tools\autologon, Microsoft-signed), which stores it
  encrypted (LSA secret), not in plain text. Nothing is printed or saved here.
#>
param([string]$User = "veera")

$sec = Read-Host "Windows password for $User on the VM (hidden)" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
try { $plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr) }
if (-not $plain) { Write-Host "No password typed - nothing changed."; exit 1 }
$b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($plain))
Remove-Variable plain

$remote = @'
$ProgressPreference = "SilentlyContinue"
$pw = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__B64__'))
Add-Type -AssemblyName System.DirectoryServices.AccountManagement
$ctx = New-Object System.DirectoryServices.AccountManagement.PrincipalContext('Machine')
if (-not $ctx.ValidateCredentials('__USER__', $pw)) { Remove-Variable pw; Write-Host "WRONG PASSWORD for __USER__ - nothing changed. Run it again."; exit 1 }
$exe = "C:\tools\autologon\Autologon64.exe"
if (-not (Test-Path $exe)) {
    New-Item -ItemType Directory -Force C:\tools\autologon | Out-Null
    Invoke-WebRequest "https://download.sysinternals.com/files/AutoLogon.zip" -OutFile C:\tools\autologon\AutoLogon.zip -UseBasicParsing
    Expand-Archive C:\tools\autologon\AutoLogon.zip C:\tools\autologon -Force
}
if ((Get-AuthenticodeSignature $exe).Status -ne 'Valid') { Remove-Variable pw; Write-Host "Autologon64.exe signature not valid - stopped."; exit 1 }
& $exe /accepteula '__USER__' $env:COMPUTERNAME $pw | Out-Null
Remove-Variable pw
Start-Sleep 2
$w = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon'
Write-Host ("Autologon: " + $(if ($w.AutoAdminLogon -eq '1') { "ON" } else { "NOT on" }) + " for user $($w.DefaultUserName) on $($w.DefaultDomainName)")
Write-Host "Password stored in plain text in the registry: $([bool]$w.DefaultPassword) (should be False)"
'@
$remote = $remote.Replace("__B64__", $b64).Replace("__USER__", $User)
$enc = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($remote))
Remove-Variable b64, remote

gcloud compute ssh mt5-bot --zone=us-east1-b --project=mt5-trader-bot-16108 --account=veeradyani16108@gmail.com `
    --tunnel-through-iap --quiet --command="powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand $enc" 2>&1 |
    Where-Object { "$_" -notmatch "^#< CLIXML|<Objs|troubleshoot|Recommendation|recommendations|plink|^\s*$" }
