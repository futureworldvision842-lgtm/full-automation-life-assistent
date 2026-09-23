@echo off
setlocal
title J.A.R.V.I.S. - STATUS ALL
color 0E
"F:\Jarvis Command Center\.venv\Scripts\python.exe" "F:\Jarvis Command Center\bootstrap\master_ecosystem_launcher.py" status all
echo.
echo Process complete.
timeout /t 3
exit /b
