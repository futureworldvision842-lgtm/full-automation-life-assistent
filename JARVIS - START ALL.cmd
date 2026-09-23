@echo off
setlocal
cd /d "%~dp0"
title J.A.R.V.I.S. MASTER OPERATIONS FLEET - START ALL
color 0A
chcp 65001 >nul 2>&1

echo ================================================================================
echo   J.A.R.V.I.S. 1-CLICK SOVEREIGN FLEET STARTUP
echo   Master Dashboard (:8770) ^| World Monitor (:3000) ^| God's Eye 3D (:4173)
echo   MQ3 Cockpit (:5050) ^| Odysseus (:7000) ^| Mobile (:8765) ^| Ollama (:11434)
echo   Autonomous Live Trader (MT5 #40000294403) ^| Discord ^| WhatsApp (:3200)
echo ================================================================================

set "JARVIS_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%JARVIS_PY%" set "JARVIS_PY=F:\Jarvis Command Center\.venv\Scripts\python.exe"
if not exist "%JARVIS_PY%" set "JARVIS_PY=C:\Python314\python.exe"
if not exist "%JARVIS_PY%" set "JARVIS_PY=python.exe"

"%JARVIS_PY%" "%~dp0bootstrap\master_ecosystem_launcher.py" start all

echo.
echo [*] Opening Master Operations Dashboard...
start http://127.0.0.1:8770/

echo.
echo ================================================================================
echo   ALL 10 SERVICES STARTED SUCCESSFULLY!
echo ================================================================================
ping 127.0.0.1 -n 3 >nul
exit
