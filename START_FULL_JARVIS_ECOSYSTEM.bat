@echo off
title J.A.R.V.I.S. Master Ecosystem Launcher (Full Mode)
color 0B
cls
echo ============================================================
echo   🤖 J.A.R.V.I.S. FULL AUTONOMOUS ECOSYSTEM & TRADER LAUNCHER
echo ============================================================
echo.

echo [1/6] Launching MetaTrader 5 Physical Terminal...
start "" "C:\Program Files\MetaTrader 5\terminal64.exe"
timeout /t 2 > nul

echo [2/6] Launching J.A.R.V.I.S. Core Voice Assistant GUI (main.py)...
start "JARVIS_Voice_GUI" cmd /k "cd /d E:\jarvis & set PYTHONUTF8=1 & py -3 main.py"
timeout /t 2 > nul

echo [3/6] Launching J.A.R.V.I.S. Autonomous Prop-Trader & Evolution Daemon...
start "JARVIS_Daemon" cmd /k "cd /d E:\jarvis & py -3 agent\evolution_daemon.py"
timeout /t 2 > nul

echo [4/6] Launching J.A.R.V.I.S. Web Telemetry & 3D HUD Server (Port 8090)...
start "JARVIS_HUD_Server" cmd /k "cd /d E:\jarvis & py -3 web\server.py"
timeout /t 2 > nul

echo [5/6] Launching J.A.R.V.I.S. Official Chrome WhatsApp Bridge (Port 3200)...
start "JARVIS_WhatsApp_Bridge" cmd /k "cd /d E:\jarvis\wa & node jarvis_wweb.js"
timeout /t 2 > nul

echo [6/6] Opening J.A.R.V.I.S. Live Prop-Trading Dashboard...
start "" "E:\jarvis\web\live_trade_terminal.html"

echo.
echo ============================================================
echo   🚀 ALL J.A.R.V.I.S. CORE MODULES ARE NOW FULLY ACTIVE!
echo ============================================================
echo.
pause
