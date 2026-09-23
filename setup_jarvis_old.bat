@echo off
echo ==========================================
echo      Jarvis Auto-Fix & Setup Script
echo ==========================================

cd /d "%~dp0\ai assistant"

if not exist venv (
    echo [INFO] Creating virtual environment...
    python -m venv venv
) else (
    echo [INFO] Virtual environment found.
)

echo [INFO] Activating virtual environment...
call venv\Scripts\activate

echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

echo [INFO] Installing dependencies from requirements.txt...
pip install -r requirements.txt

echo [INFO] Installing Playwright browsers...
playwright install

echo ==========================================
echo      Setup Complete!
echo ==========================================
exit /b 0
