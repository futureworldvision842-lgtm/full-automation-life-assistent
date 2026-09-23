# Start J.A.R.V.I.S. Ecosystem Services
$ROOT = $PSScriptRoot
$PY = if (Test-Path "$ROOT\.venv\Scripts\python.exe") { "$ROOT\.venv\Scripts\python.exe" } else { "python" }

Write-Host "Stopping any running instances..." -ForegroundColor Yellow
Stop-Process -Name "ollama" -ErrorAction SilentlyContinue

if (Test-Path "$ROOT\scratch\ollama\ollama.exe") {
    Write-Host "Starting Ollama Server..." -ForegroundColor Cyan
    Start-Process -FilePath "$ROOT\scratch\ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden -WorkingDirectory "$ROOT\scratch\ollama"
}

if (Test-Path "$ROOT\bots\odysseus\app.py") {
    Write-Host "Starting Odysseus AI Server..." -ForegroundColor Cyan
    Start-Process -FilePath $PY -ArgumentList "-m uvicorn app:app --host 127.0.0.1 --port 7000" -WindowStyle Hidden -WorkingDirectory "$ROOT\bots\odysseus"
}

if (Get-Command "clawdbot" -ErrorAction SilentlyContinue) {
    Write-Host "Starting Moltbot Gateway..." -ForegroundColor Cyan
    Start-Process -FilePath "clawdbot" -ArgumentList "gateway" -WindowStyle Hidden -WorkingDirectory $ROOT
}

if (Test-Path "$ROOT\wa\jarvis_baileys.js") {
    Write-Host "Starting WhatsApp Bridge (Baileys)..." -ForegroundColor Cyan
    Start-Process -FilePath "node" -ArgumentList "jarvis_baileys.js" -WorkingDirectory "$ROOT\wa"
}

if (Test-Path "$ROOT\dashboard.py") {
    Write-Host "Starting Ops Dashboard (port 8770)..." -ForegroundColor Cyan
    Start-Process -FilePath $PY -ArgumentList "dashboard.py" -WorkingDirectory $ROOT
}

if (Test-Path "$ROOT\mobile_control.py") {
    Write-Host "Starting Mobile Remote (port 8765)..." -ForegroundColor Cyan
    Start-Process -FilePath $PY -ArgumentList "mobile_control.py" -WorkingDirectory $ROOT
}

if (Test-Path "$ROOT\main.py") {
    Write-Host "Starting Main Python J.A.R.V.I.S. Assistant GUI..." -ForegroundColor Green
    Start-Process -FilePath $PY -ArgumentList "main.py" -WorkingDirectory $ROOT
}

Write-Host "All services successfully launched!" -ForegroundColor Green
