@echo off
echo STARTING JARVIS IN TEXT MODE (Voice libraries missing)
echo ---------------------------------------------------
cd /d "%~dp0\ai assistant"
if exist ..\venv\Scripts\activate (
    call ..\venv\Scripts\activate
)
python main.py
pause
