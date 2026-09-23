@echo off
title J.A.R.V.I.S. Master Launcher
cd /d "%~dp0"
chcp 65001 >nul

if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" "%~dp0launch_all.py"
) else (
    python "%~dp0launch_all.py"
)
pause
