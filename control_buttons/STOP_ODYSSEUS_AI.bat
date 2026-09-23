@echo off
setlocal
title J.A.R.V.I.S. - STOP ODYSSEUS
color 0C
"F:\Jarvis Command Center\.venv\Scripts\python.exe" "F:\Jarvis Command Center\bootstrap\master_ecosystem_launcher.py" stop odysseus
echo.
echo Process complete.
timeout /t 3
exit /b
