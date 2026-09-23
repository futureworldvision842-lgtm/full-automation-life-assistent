@echo off
title MQ3 + JARVIS - MANAGED STOP
color 0C
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "P:\MQ3 TRADING BOT\scripts\mq3_stack.ps1" -Action Stop
echo.
pause

