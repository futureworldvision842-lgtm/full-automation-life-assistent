@echo off
:: ============================================================
::   JARVIS  -  START EVERYTHING
::   Launches the supervisor, which brings up the voice GUI,
::   dashboard, phone remote and WhatsApp bridge, and keeps
::   them all alive (auto-restarts anything that dies).
:: ============================================================
title JARVIS
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" set "PY=C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe"
if not exist "%PY%" (
  echo [X] Python 3.11 is required.
  pause & exit /b 1
)

if not exist "config\api_keys.json" (
  echo [X] config\api_keys.json missing. Run install.bat, then add your Gemini key.
  pause & exit /b 1
)

:: Real user-initiated start — clear any manual-stop flag so auto-heal resumes.
del /f /q "scratch\jarvis.stop" 2>nul

echo Starting JARVIS ecosystem ...
"%PY%" bootstrap\supervisor.py
