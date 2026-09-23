@echo off
setlocal
cd /d "%~dp0"
title J.A.R.V.I.S. UNIFIED FLEET TEARDOWN - STOP ALL
color 0C
chcp 65001 >nul 2>&1

:: Clean termination across all core ports: 8770, 3000, 4173, 5050, 7000, 11434, 8765, 3200, 5678
:: Executes bootstrap\stop_all.py to terminate all managed processes with 0 zombies

set "JARVIS_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%JARVIS_PY%" set "JARVIS_PY=F:\Jarvis Command Center\.venv\Scripts\python.exe"
if not exist "%JARVIS_PY%" set "JARVIS_PY=C:\Python314\python.exe"
if not exist "%JARVIS_PY%" set "JARVIS_PY=python.exe"

"%JARVIS_PY%" "%~dp0bootstrap\stop_all.py"
set EXIT_CODE=%errorlevel%

exit /b %EXIT_CODE%
