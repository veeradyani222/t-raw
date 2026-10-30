$p = Read-Host 'IC demo password' -AsSecureString
$s = [Runtime.InteropServices.Marshal]::PtrToStringAuto([Runtime.InteropServices.Marshal]::SecureStringToBSTR($p))
$f = 'C:\Users\veera\Desktop\mt5-trader\.env'
(Get-Content $f) -replace '^MT5_PASSWORD=.*', ('MT5_PASSWORD=' + $s) | Set-Content $f
Write-Host 'saved'
