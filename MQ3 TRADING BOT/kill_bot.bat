@echo off
title Funding Pips AI Bot Emergency Kill Switch
cls
echo ⚠️ EMERGENCY KILL SWITCH - Closing all open positions and stopping bot...
python run.py --kill-switch
pause
