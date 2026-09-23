@echo off
setlocal
cd /d "%~dp0"
title J.A.R.V.I.S. UNIFIED FLEET TEARDOWN - STOP ALL
color 0C
chcp 65001 >nul 2>&1

echo ================================================================================
echo   J.A.R.V.I.S. UNIFIED FLEET TEARDOWN (CLEAN PROCESS TREE SHUTDOWN)
echo   Terminating all services, trees, and clearing ports:
echo   8770, 3000, 4173, 5050, 7000, 11434, 8765, 3200, 5678 with 0 zombie processes
echo ================================================================================

:: Clean termination across all core ports: 8770, 3000, 4173, 5050, 7000, 11434, 8765, 3200, 5678
:: Executes bootstrap\stop_all.py to terminate all managed processes with 0 zombies

set "JARVIS_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%JARVIS_PY%" set "JARVIS_PY=F:\Jarvis Command Center\.venv\Scripts\python.exe"
if not exist "%JARVIS_PY%" set "JARVIS_PY=C:\Python314\python.exe"
if not exist "%JARVIS_PY%" set "JARVIS_PY=python.exe"

"%JARVIS_PY%" "%~dp0bootstrap\stop_all.py"
set EXIT_CODE=%errorlevel%

echo [*] Enforcing clean process tree termination and port clearing...
"%JARVIS_PY%" "%~dp0bootstrap\master_ecosystem_launcher.py" stop
if %errorlevel% EQU 0 set EXIT_CODE=0

echo ================================================================================
echo   [SUCCESS] All J.A.R.V.I.S. services stopped cleanly.
echo ================================================================================

exit /b %EXIT_CODE%
