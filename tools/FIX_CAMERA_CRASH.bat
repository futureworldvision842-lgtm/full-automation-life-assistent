@echo off
title J.A.R.V.I.S. Camera Driver Fix & System Stabilizer
color 0b

:: Check for administrative rights
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges to repair camera driver...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

echo ========================================================
echo   J.A.R.V.I.S. CAMERA CRASH REPAIR & DRIVER FIX
echo ========================================================
echo.
echo Running driver remediation...
powershell -NoProfile -ExecutionPolicy Bypass -File "F:\Jarvis Command Center\tools\fix_camera_driver.ps1"

echo.
echo ========================================================
echo Done! Check the log above. Press any key to exit.
echo ========================================================
pause
