@echo off
title MQ3 + JARVIS - STATUS
color 0B
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "P:\MQ3 TRADING BOT\scripts\mq3_stack.ps1" -Action Status
echo.
pause

