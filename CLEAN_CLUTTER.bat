@echo off
title J.A.R.V.I.S. Clutter Cleaner
color 0c
echo ============================================================
echo   J.A.R.V.I.S. WINDOW CLUTTER CLEANER
echo ============================================================
echo.
echo [*] Cleaning visible duplicate launcher windows...
powershell -Command "Get-Process -Name cmd -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like '*Master Launcher*' -or $_.MainWindowTitle -like '*Voice_GUI*' -or $_.MainWindowTitle -like '*HUD_Server*' -or $_.MainWindowTitle -like '*JARVIS_Daemon*' } | Stop-Process -Force -ErrorAction SilentlyContinue"
echo [*] Done. All duplicate windows closed cleanly.
