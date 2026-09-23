@echo off
setlocal EnableExtensions
title GAIGS / OneJourney

cd /d "%~dp0"

where npm.cmd >nul 2>nul
if errorlevel 1 (
  echo.
  echo Node.js is required to run GAIGS / OneJourney.
  echo Install the current LTS version from https://nodejs.org/ and run this file again.
  echo.
  pause
  exit /b 1
)

if not exist "node_modules\" (
  echo Installing GAIGS dependencies for the first run...
  call npm.cmd install
  if errorlevel 1 (
    echo.
    echo Dependency installation failed. Check your internet connection, then run this file again.
    pause
    exit /b 1
  )
)

echo.
echo Starting GAIGS / OneJourney...
echo Your browser will open automatically at http://127.0.0.1:4173
echo Keep this window open while using the app. Press Ctrl+C to stop it.
echo.
call npm.cmd run dev:open

endlocal
