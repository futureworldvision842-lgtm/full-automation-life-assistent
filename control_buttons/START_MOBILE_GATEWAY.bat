@echo off
setlocal
title J.A.R.V.I.S. - START MOBILE
color 0A
"F:\Jarvis Command Center\.venv\Scripts\python.exe" "F:\Jarvis Command Center\bootstrap\master_ecosystem_launcher.py" start mobile
echo.
echo Process complete.
timeout /t 3
exit /b
