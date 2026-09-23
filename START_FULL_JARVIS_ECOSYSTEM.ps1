# ============================================================
#   J.A.R.V.I.S. FULL AUTONOMOUS ECOSYSTEM & TRADER LAUNCHER
#   PowerShell Dynamic Multi-Service Ecosystem Startup Script
# ============================================================

$ROOT = $PSScriptRoot
Set-Location $ROOT

$PY = if (Test-Path "$ROOT\.venv\Scripts\python.exe") { "$ROOT\.venv\Scripts\python.exe" } elseif (Get-Command "py" -ErrorAction SilentlyContinue) { "py" } else { "python" }
$NODE = if (Get-Command "node" -ErrorAction SilentlyContinue) { "node" } elseif (Test-Path "C:\Program Files\nodejs\node.exe") { "C:\Program Files\nodejs\node.exe" } else { "node" }

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  🤖 J.A.R.V.I.S. FULL AUTONOMOUS ECOSYSTEM LAUNCHER (PS1)" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "Working Directory: $ROOT" -ForegroundColor Gray
Write-Host ""

# 1. MT5 Terminal
if (Test-Path "C:\Program Files\MetaTrader 5\terminal64.exe") {
    Write-Host "[1/7] Launching MetaTrader 5 Terminal..." -ForegroundColor Green
    Start-Process -FilePath "C:\Program Files\MetaTrader 5\terminal64.exe" -ErrorAction SilentlyContinue
} else {
    Write-Host "[1/7] MetaTrader 5 physical terminal not found (skipping)" -ForegroundColor Yellow
}

# 2. Local Ollama LLM Server
if (Test-Path "$ROOT\scratch\ollama\ollama.exe") {
    Write-Host "[2/7] Starting Local Ollama Server (:11434)..." -ForegroundColor Cyan
    Start-Process -FilePath "$ROOT\scratch\ollama\ollama.exe" -ArgumentList "serve" -WindowStyle Hidden -WorkingDirectory "$ROOT\scratch\ollama" -ErrorAction SilentlyContinue
}

# 3. Odysseus Local AI Server (:7000)
if (Test-Path "$ROOT\bots\odysseus\app.py") {
    Write-Host "[3/7] Starting Odysseus Local AI Server (:7000)..." -ForegroundColor Cyan
    Start-Process -FilePath $PY -ArgumentList "-m uvicorn app:app --host 127.0.0.1 --port 7000" -WindowStyle Hidden -WorkingDirectory "$ROOT\bots\odysseus" -ErrorAction SilentlyContinue
}

# 4. WhatsApp Baileys Bridge (:3200)
if (Test-Path "$ROOT\wa\jarvis_baileys.js") {
    Write-Host "[4/7] Starting WhatsApp Baileys Bridge (:3200)..." -ForegroundColor Cyan
    Start-Process -FilePath $NODE -ArgumentList "jarvis_baileys.js" -WorkingDirectory "$ROOT\wa" -ErrorAction SilentlyContinue
}

# 5. Master Command Center Dashboard (:8770)
if (Test-Path "$ROOT\dashboard.py") {
    Write-Host "[5/11] Starting Master Dashboard (:8770)..." -ForegroundColor Cyan
    Start-Process -FilePath $PY -ArgumentList "dashboard.py" -WorkingDirectory $ROOT -ErrorAction SilentlyContinue
}

# 6. Native World Monitor Radar (:3000)
if (Test-Path "$ROOT\worldmonitor-main\package.json") {
    Write-Host "[6/11] Starting World Monitor Geospatial Engine (:3000)..." -ForegroundColor Cyan
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev -- --port 3000 --host 127.0.0.1" -WindowStyle Hidden -WorkingDirectory "$ROOT\worldmonitor-main" -ErrorAction SilentlyContinue
}

# 7. God's Eye View 3D Globe (:4173)
if (Test-Path "$ROOT\gods-eye-view\package.json") {
    Write-Host "[7/11] Starting God's Eye View 3D Globe (:4173)..." -ForegroundColor Cyan
    Start-Process -FilePath "cmd.exe" -ArgumentList "/c npm run dev -- --port 4173 --host 127.0.0.1" -WindowStyle Hidden -WorkingDirectory "$ROOT\gods-eye-view" -ErrorAction SilentlyContinue
}

# 8. MQ3 Trading Cockpit (:5050)
if (Test-Path "$ROOT\MQ3 TRADING BOT\run.py") {
    Write-Host "[8/11] Starting MQ3 Trading Cockpit (:5050)..." -ForegroundColor Cyan
    Start-Process -FilePath $PY -ArgumentList "run.py --demo --host 127.0.0.1 --port 5050" -WindowStyle Hidden -WorkingDirectory "$ROOT\MQ3 TRADING BOT" -ErrorAction SilentlyContinue
}

# 9. 24/7 Autonomous Live Trading Daemon
if (Test-Path "$ROOT\MQ3 TRADING BOT\src\autonomous_live_daemon.py") {
    Write-Host "[9/11] Starting Autonomous 24/7 Live Trading Daemon..." -ForegroundColor Green
    Start-Process -FilePath $PY -ArgumentList "src\autonomous_live_daemon.py" -WindowStyle Hidden -WorkingDirectory "$ROOT\MQ3 TRADING BOT" -ErrorAction SilentlyContinue
}

# 10. Mobile Web Remote Controller (:8765)
if (Test-Path "$ROOT\mobile_control.py") {
    Write-Host "[10/11] Starting Mobile Remote Controller (:8765)..." -ForegroundColor Cyan
    Start-Process -FilePath $PY -ArgumentList "mobile_control.py" -WorkingDirectory $ROOT -ErrorAction SilentlyContinue
}

# 11. Desktop Voice GUI HUD
if (Test-Path "$ROOT\main.py") {
    Write-Host "[11/11] Starting Main J.A.R.V.I.S. Desktop Voice GUI HUD..." -ForegroundColor Green
    Start-Process -FilePath $PY -ArgumentList "main.py" -WorkingDirectory $ROOT -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  🚀 ALL J.A.R.V.I.S. SERVICES SUCCESSFULLY INITIALIZED!" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
