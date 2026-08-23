@echo off
:: ============================================================
::  J.A.R.V.I.S.  —  ON / OFF TOGGLE  (desktop button)
::  If Jarvis is running  -> shut it down.
::  If Jarvis is stopped  -> boot the full ecosystem.
:: ============================================================
title J.A.R.V.I.S. On/Off
set "JARVIS=%~dp0"

:: Count running voice-GUI instances (python main.py).
for /f %%i in ('powershell -NoProfile -Command "@(Get-CimInstance Win32_Process -Filter \"Name='python.exe' OR Name='pythonw.exe'\" | Where-Object { $_.CommandLine -like '*main.py*' }).Count"') do set "RUNNING=%%i"
if not defined RUNNING set "RUNNING=0"

if "%RUNNING%"=="0" (
    echo J.A.R.V.I.S. is OFF  ^-^->  starting it up...
    start "" "%JARVIS%start_jarvis_boot.bat"
) else (
    echo J.A.R.V.I.S. is ON  ^-^->  shutting it down...
    call "%JARVIS%jarvis_stop.bat"
)
ping -n 2 127.0.0.1 >nul
