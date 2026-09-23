@echo off
title J.A.R.V.I.S. QUANTUM MASTER CONTROL ROOM
color 0b
chcp 65001 >nul
cd /d "%~dp0"

echo ===============================================================================
echo                J.A.R.V.I.S. QUANTUM SOVEREIGN CONTROL ROOM
echo            [ AI Core • MQ3 Trading • World Radar • Neural Voice ]
echo ===============================================================================
echo.

:: 1. Clean extraneous duplicate zombie popups
powershell -Command "Get-Process -Name cmd -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*Launcher*' -or $_.MainWindowTitle -like '*Voice_GUI*' -or $_.MainWindowTitle -like '*HUD_Server*' } | Stop-Process -Force -ErrorAction SilentlyContinue" >nul 2>&1

:: 2. Start Background 24/7 Supervisor silently (No extra black popup windows)
echo [*] Initializing Background Sovereign Daemons (Dashboard, Trading, World Monitor, Odysseus)...
start /b "" ".venv\Scripts\python.exe" bootstrap\supervisor.py >nul 2>&1

:: 3. Wait 2 seconds for daemons to initialize
timeout /t 2 /nobreak >nul

:: 4. Open Professional Master Dashboard in default browser
echo [*] Opening Master War Room Dashboard (http://localhost:8770)...
start "" "http://localhost:8770"

:: 5. Launch Single Master Interactive Neural REPL
echo [*] Launching Master Interactive Neural REPL...
echo.
".venv\Scripts\python.exe" terminal.py

pause
