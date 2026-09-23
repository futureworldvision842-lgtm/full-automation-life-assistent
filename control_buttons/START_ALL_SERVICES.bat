@echo off
setlocal
title J.A.R.V.I.S. - START ALL
color 0B
"F:\Jarvis Command Center\.venv\Scripts\python.exe" "F:\Jarvis Command Center\bootstrap\master_ecosystem_launcher.py" start all
echo.
echo Process complete.
timeout /t 3
exit /b
