@echo off
setlocal
title J.A.R.V.I.S. - STOP MQ3
color 0C
"F:\Jarvis Command Center\.venv\Scripts\python.exe" "F:\Jarvis Command Center\bootstrap\master_ecosystem_launcher.py" stop mq3
echo.
echo Process complete.
timeout /t 3
exit /b
