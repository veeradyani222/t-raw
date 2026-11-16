<#
  Remote desktop into the bot VM through Google's IAP tunnel, so it works from ANY
  internet connection (no "allowed IP" to keep updating). Run on your laptop, or
  double-click the "MT5 Bot VM (tunnel)" shortcut on the desktop.

  It opens the tunnel on localhost:13389, starts Remote Desktop to it, and closes
  the tunnel when you close Remote Desktop. Log in as veera; close with the X,
  never Sign out (signing out stops the bot).
#>
$port = 13389
$args_ = "compute start-iap-tunnel mt5-bot 3389 --local-host-port=localhost:$port --zone=us-east1-b --project=mt5-trader-bot-16108 --account=veeradyani16108@gmail.com"
$gc = (Get-Command gcloud.cmd -ErrorAction SilentlyContinue).Source
if (-not $gc) { $gc = (Get-Command gcloud -ErrorAction Stop).Source }
Write-Host "Opening the secure tunnel to the VM..."
$tunnel = Start-Process -FilePath $gc -ArgumentList $args_ -WindowStyle Hidden -PassThru
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep 1
    try { $c = New-Object Net.Sockets.TcpClient; $c.Connect("127.0.0.1", $port); $c.Close(); $ok = $true; break } catch {}
}
if (-not $ok) {
    Write-Host "Tunnel did not open. Check you're signed in to gcloud (gcloud auth login) and try again."
    if (-not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id -Force }
    Read-Host "Press Enter to close"; exit 1
}
Write-Host "Connected. Starting Remote Desktop (log in as veera, close with X, never Sign out)."
Start-Process mstsc -ArgumentList "/v:localhost:$port" -Wait
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "start-iap-tunnel" -and $_.CommandLine -match "$port" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
if (-not $tunnel.HasExited) { Stop-Process -Id $tunnel.Id -Force -ErrorAction SilentlyContinue }
