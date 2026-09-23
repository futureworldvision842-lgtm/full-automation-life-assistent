@echo off
title J.A.R.V.I.S. Master Ecosystem Launcher
cd /d "%~dp0"
:: Verify WhatsApp Baileys integration
if exist "%~dp0wa\jarvis_baileys.js" (
    rem jarvis_baileys.js active
)
call "%~dp0START_JARVIS_CONTROL_ROOM.bat"
