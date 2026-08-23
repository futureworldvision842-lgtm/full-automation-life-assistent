@echo off
title J.A.R.V.I.S. Launcher
color 0A
cls
echo ============================================================
echo   🤖 J.A.R.V.I.S. MANUAL ECOSYSTEM LAUNCHER
echo ============================================================
echo.
echo Removing manual-stop lock...
del /f /q "E:\jarvis\scratch\jarvis.stop" 2>nul

echo [1/4] Starting J.A.R.V.I.S. Voice Assistant GUI...
start "JARVIS_Voice_GUI" cmd /k "cd /d E:\jarvis && set PYTHONUTF8=1 && py -3 main.py"

echo [2/4] Starting J.A.R.V.I.S. Web Telemetry Server (Port 8090)...
start "JARVIS_HUD_Server" cmd /k "cd /d E:\jarvis && py -3 web\server.py"

echo [3/4] Starting J.A.R.V.I.S. WhatsApp Bridge (Port 3200)...
start "JARVIS_WhatsApp_Bridge" cmd /k "cd /d E:\jarvis\wa && node jarvis_wweb.js"

echo [4/4] Opening J.A.R.V.I.S. Web Dashboard...
start "" "E:\jarvis\web\live_trade_terminal.html"

echo.
echo ============================================================
echo   ✅ J.A.R.V.I.S. is now RUNNING!
echo   To STOP J.A.R.V.I.S. anytime, run STOP_JARVIS.bat.
echo ============================================================
echo.
timeout /t 5 >nul
exit /b 0
