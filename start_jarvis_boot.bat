@echo off
:: ============================================================
::  J.A.R.V.I.S. BOOT LAUNCHER  (auto-start on logon)
::  Launches the full ecosystem + voice GUI on boot and keeps
::  them all alive using the portable supervisor.
:: ============================================================
title J.A.R.V.I.S. Boot Launcher
cd /d "%~dp0"
chcp 65001 > nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
set PYTHONUNBUFFERED=1

if exist ".venv\Scripts\python.exe" (
    start "" /b ".venv\Scripts\python.exe" bootstrap\supervisor.py
) else (
    start "" /b python bootstrap\supervisor.py
)
