@echo off
:: ============================================================
::   JARVIS  -  ONE-CLICK INSTALLER
::   Downloads deps, sets up config, and prepares JARVIS to run.
::   Just double-click this file after cloning the repo.
:: ============================================================
title JARVIS Installer
chcp 65001 >nul
setlocal enableextensions
cd /d "%~dp0"

echo.
echo   ============================================================
echo      M U H A M M A D ' S   J A R V I S   -   I N S T A L L E R
echo   ============================================================
echo.

:: ---- 1. Find Python 3.11+ ----
set "PYCMD="
py -3.11 --version >nul 2>&1 && set "PYCMD=py -3.11"
if not defined PYCMD ( py -3 --version >nul 2>&1 && set "PYCMD=py -3" )
if not defined PYCMD ( python --version >nul 2>&1 && set "PYCMD=python" )
if not defined PYCMD (
  echo [X] Python not found. Install Python 3.11+ from https://python.org
  echo     ^(tick "Add python.exe to PATH" during install^), then re-run this.
  pause & exit /b 1
)
echo [1/6] Using Python: %PYCMD%

:: ---- 2. Create virtual environment ----
echo [2/6] Creating virtual environment (.venv) ...
if not exist ".venv\Scripts\python.exe" (
  %PYCMD% -m venv .venv || ( echo [X] venv failed & pause & exit /b 1 )
)
set "VPY=.venv\Scripts\python.exe"

:: ---- 3. Install Python dependencies ----
echo [3/6] Installing Python packages (this can take a few minutes) ...
"%VPY%" -m pip install --no-cache-dir --upgrade pip >nul
"%VPY%" -m pip install --no-cache-dir -r requirements.txt || ( echo [X] pip install failed & pause & exit /b 1 )

:: ---- 4. Install Playwright browser (for web control) ----
echo [4/6] Installing Playwright browser ...
"%VPY%" -m playwright install chromium >nul 2>&1

:: ---- 5. Install WhatsApp bridge (Node/Baileys) ----
echo [5/6] Setting up WhatsApp bridge ...
where node >nul 2>&1
if %errorlevel%==0 (
  if exist "wa\package.json" ( pushd wa & call npm install --silent & popd )
) else (
  echo     [!] Node.js not found - WhatsApp bridge skipped.
  echo         Install Node 18+ from https://nodejs.org and run: cd wa ^&^& npm install
)

:: ---- 6. Create config from templates (never overwrites yours) ----
echo [6/6] Preparing config ...
if not exist "config\api_keys.json" (
  copy /y "config\api_keys.example.json" "config\api_keys.json" >nul
  echo     -^> Created config\api_keys.json  ^(ADD YOUR GEMINI KEY^)
)
if not exist "config\gold_config.json" (
  copy /y "config\gold_config.example.json" "config\gold_config.json" >nul
)

echo.
echo   ============================================================
echo     INSTALL COMPLETE!
echo   ------------------------------------------------------------
echo     1. Open  config\api_keys.json  and paste your Google
echo        Gemini API key  (get one free: https://aistudio.google.com/apikey)
echo     2. Double-click  run.bat  to start JARVIS.
echo   ============================================================
echo.
pause
