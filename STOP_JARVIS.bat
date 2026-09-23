@echo off
title STOP J.A.R.V.I.S. ECOSYSTEM
color 0c
chcp 65001 >nul
cd /d "%~dp0"

echo ===============================================================================
echo                STOPPING J.A.R.V.I.S. SOVEREIGN ECOSYSTEM
echo ===============================================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command "& {
    Write-Host '[*] Freeing listening ports (8770, 8765, 5050, 7000, 8090)...' -ForegroundColor Yellow
    8770, 8765, 5050, 7000, 8090 | ForEach-Object {
        Get-NetTCPConnection -LocalPort $_ -ErrorAction SilentlyContinue | ForEach-Object {
            Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
    Write-Host '[*] Terminating background Python daemons...' -ForegroundColor Yellow
    Get-Process -Name python -ErrorAction SilentlyContinue | Where-Object {
        $_.CommandLine -like '*supervisor*' -or
        $_.CommandLine -like '*dashboard*' -or
        $_.CommandLine -like '*mobile_control*' -or
        $_.CommandLine -like '*discord_bot*' -or
        $_.CommandLine -like '*autonomous_live_daemon*'
    } | Stop-Process -Force -ErrorAction SilentlyContinue

    Write-Host '[+] All J.A.R.V.I.S. daemons and ports safely stopped.' -ForegroundColor Green
}"

timeout /t 2 /nobreak >nul
