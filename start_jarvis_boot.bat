@echo off
:: ============================================================
::  J.A.R.V.I.S. MASTER BOOT LAUNCHER
::  Launches all 10 Motherbot companion services + Voice HUD GUI
:: ============================================================
title J.A.R.V.I.S. Boot Launcher
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

set PY=C:\Users\HP\AppData\Local\Programs\Python\Python311\python.exe
set JARVIS=E:\jarvis

del /f /q "%JARVIS%\scratch\jarvis.stop" 2>nul

echo Launching Motherbot Core Services...

:: The supervisor owns JARVIS voice, dashboard, mobile bridge, Ollama,
:: MoltBot, GAIGS status bridge and cloud heartbeat with auto-restart.
start "JARVIS Supervisor" /min /D "%JARVIS%" %PY% bootstrap\supervisor.py

start "Odysseus AI Server" /min /D "%JARVIS%\scratch\odysseus" %PY% -m uvicorn app:app --host 127.0.0.1 --port 7000
start "TypeScript Jarvis" /min /D "C:\Users\HP\jarvis_ts" C:\Users\HP\.bun\bin\bun.exe start
start "AI Studio Backend" /min /D "E:\Muhammad's Work VP automation\full bot\vision-point-ai-studio-complete\backend" npm start
start "AI Studio Frontend" /min /D "E:\Muhammad's Work VP automation\full bot\vision-point-ai-studio-complete\frontend" npm run dev
start "WhatsApp Forwarder" /min /D "E:\Muhammad's Work VP automation\full bot\voice-automation my upgradation" node app.js
echo All Motherbot services launched successfully.
