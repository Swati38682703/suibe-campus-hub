param([switch]$Mobile)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (Test-Path -LiteralPath '.env') {
    foreach ($taskLine in Get-Content -LiteralPath '.env') {
        if ($taskLine -match '^(ADMIN_TOKEN|APP_SECRET|DATABASE_URL|LLM_API_KEY|LLM_BASE_URL|LLM_MODEL)=(.+)$') {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim(), 'Process')
        }
    }
}
$taskPython = Join-Path $PSScriptRoot '.venv/Scripts/python.exe'
$taskVite = Join-Path $PSScriptRoot 'frontend/node_modules/vite/bin/vite.js'
if (!(Test-Path -LiteralPath $taskPython) -or !(Test-Path -LiteralPath $taskVite)) { throw 'Install dependencies first; see README.md.' }
foreach ($taskPort in @(8000, 5173)) {
    if (Get-NetTCPConnection -LocalPort $taskPort -State Listen -ErrorAction SilentlyContinue) { throw "Port $taskPort is in use. Reuse the running app or stop it first." }
}
New-Item -ItemType Directory -Path 'tmp' -Force | Out-Null
$taskBackend = Start-Process -FilePath $taskPython -ArgumentList @('-m', 'uvicorn', 'backend.app.main:app', '--host', '127.0.0.1', '--port', '8000') -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'tmp/backend.log') -RedirectStandardError (Join-Path $PSScriptRoot 'tmp/backend-error.log')
$taskNode = (Get-Command node).Source
$taskFrontendHost = if ($Mobile) { '0.0.0.0' } else { '127.0.0.1' }
$taskFrontend = Start-Process -FilePath $taskNode -ArgumentList @(('"'+$taskVite+'"'), '--host', $taskFrontendHost, '--port', '5173', '--strictPort') -WorkingDirectory (Join-Path $PSScriptRoot 'frontend') -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $PSScriptRoot 'tmp/frontend.log') -RedirectStandardError (Join-Path $PSScriptRoot 'tmp/frontend-error.log')
Write-Host "Campus Hub: http://127.0.0.1:5173"
Write-Host "Backend PID: $($taskBackend.Id); frontend PID: $($taskFrontend.Id). Stop these specific processes when finished."

if ($Mobile) {
    $taskAddresses = Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' -and $_.AddressState -eq 'Preferred' }
    foreach ($taskAddress in $taskAddresses) { Write-Host "Phone preview (same Wi-Fi): http://$($taskAddress.IPAddress):5173" }
    Write-Host 'Use your Wi-Fi address on the phone. If prompted, allow Node.js on private networks only. Stop the printed frontend PID when done.'
}
