@echo off
title J.A.R.V.I.S. PowerShell & Command Controller
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" terminal.py
) else (
    python terminal.py
)
pause
