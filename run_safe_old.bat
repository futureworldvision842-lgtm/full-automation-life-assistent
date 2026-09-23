@echo off
echo ==========================================
echo      Jarvis Safe Launcher
echo ==========================================

cd /d "%~dp0\ai assistant"

if not exist venv (
    echo [INFO] Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate

echo [INFO] Installing minimal dependencies...
pip install -r requirements_safe.txt

echo [INFO] Attempting to install System Control (might fail on Py3.14)...
pip install pyautogui

echo [INFO] Attempting to install Browser Control...
pip install playwright
python -m playwright install chromium

echo [INFO] Starting Jarvis...
python main.py

pause
