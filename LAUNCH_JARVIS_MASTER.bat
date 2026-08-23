@echo off
title J.A.R.V.I.S. Master Launcher
color 0A
cls
echo ============================================================
echo   🤖 J.A.R.V.I.S. AUTONOMOUS PROP-TRADER MASTER LAUNCHER
echo ============================================================
echo.
echo [1/4] Launching MetaTrader 5 Terminal...
start "" "C:\Program Files\MetaTrader 5\terminal64.exe"

echo [2/4] Launching J.A.R.V.I.S. Web Telemetry & Control Server (Port 8090)...
start "JARVIS_HUD_SERVER" cmd /k "cd /d E:\jarvis & py -3 web\server.py"

echo [3/4] Launching J.A.R.V.I.S. Chrome WhatsApp Bridge (Port 3200)...
start "JARVIS_WHATSAPP_ENGINE" cmd /k "cd /d E:\jarvis\wa & node jarvis_wweb.js"

echo [4/4] Opening J.A.R.V.I.S. Live Prop-Trading Dashboard...
start "" "E:\jarvis\web\live_trade_terminal.html"

echo.
echo ============================================================
echo   ✅ ALL J.A.R.V.I.S. MODULES LAUNCHED VISIBLY ON YOUR SCREEN!
echo ============================================================
echo.
