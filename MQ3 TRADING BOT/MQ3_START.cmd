@echo off
title MQ3 + JARVIS - BROKER DEMO TELEMETRY START
color 0A
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "P:\MQ3 TRADING BOT\scripts\mq3_stack.ps1" -Action Start -OpenDashboard
echo.
echo This launcher enables broker-demo telemetry but never bypasses real-money funded-account gates.
pause
