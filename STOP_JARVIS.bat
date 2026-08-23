@echo off
title J.A.R.V.I.S. Stop
color 0C
cls
echo ============================================================
echo   🛑 STOPPING ALL J.A.R.V.I.S. SERVICES...
echo ============================================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "E:\jarvis\scratch\jarvis_stop.ps1"
echo.
echo ============================================================
echo   ✅ J.A.R.V.I.S. is completely STOPPED.
echo ============================================================
echo.
timeout /t 3 >nul
exit /b 0
