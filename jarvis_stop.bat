@echo off
title J.A.R.V.I.S. Shutdown
color 0C
cls
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scratch\jarvis_stop.ps1"
exit /b 0
