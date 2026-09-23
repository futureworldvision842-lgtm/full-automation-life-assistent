@echo off
title TRADING BOT + JARVIS - WINDOWS SYSTEM INSTALLER
color 0A
echo.
echo ================================================================
echo   TRADING BOT + JARVIS V7 - REAL SYSTEM INSTALLATION
echo ================================================================
echo   This will:
echo   1. Register Bot + Jarvis in Windows Task Scheduler
echo   2. Add to Windows Startup Registry
echo   3. Create Desktop Shortcuts
echo   4. Run with HIGHEST privileges at every Windows Login
echo ================================================================
echo.
cd /d "p:\TRADING BOT"
echo Running installer with admin privileges...
powershell -Command "Start-Process python -ArgumentList 'install_system.py' -Verb RunAs -WorkingDirectory 'p:\TRADING BOT' -Wait"
echo.
echo Installation complete! Check logs above.
pause
