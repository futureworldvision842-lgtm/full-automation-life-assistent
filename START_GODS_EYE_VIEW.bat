@echo off
setlocal
title J.A.R.V.I.S. // GOD'S EYE VIEW 3D OPERATIONAL CONSOLE
echo ======================================================================
echo   J.A.R.V.I.S. GOD'S EYE VIEW 3D OPERATIONAL CONSOLE (PORT 4173)
echo ======================================================================
echo.

cd /d "%~dp0gods-eye-view"
if not exist "node_modules" (
    echo [!] Installing dependencies...
    call npm.cmd install --ignore-engines
)

echo [*] Launching God's Eye View 3D Globe on http://127.0.0.1:4173 ...
start "" "http://127.0.0.1:4173"
call npm.cmd run dev -- --port 4173 --host 127.0.0.1

endlocal
