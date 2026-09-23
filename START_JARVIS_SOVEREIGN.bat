@echo off
setlocal
cd /d "%~dp0"
title J.A.R.V.I.S. SOVEREIGN MASTER LAUNCHER (SSD F:)
color 0B

set "JARVIS_PY=%~dp0.venv\Scripts\python.exe"
if not exist "%JARVIS_PY%" set "JARVIS_PY=p:\Vision Point Work\jarvis\.venv\Scripts\python.exe"
if not exist "%JARVIS_PY%" set "JARVIS_PY=python.exe"

"%JARVIS_PY%" "%~dp0bootstrap\master_ecosystem_launcher.py" start
exit /b %errorlevel%
