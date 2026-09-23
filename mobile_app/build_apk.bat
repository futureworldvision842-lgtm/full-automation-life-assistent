@echo off
setlocal
echo ======================================================================
echo   J.A.R.V.I.S. ANDROID COMPANION APK BUILDER
echo ======================================================================
echo.

cd /d "%~dp0"
python build_apk.py --mode all %*

if %ERRORLEVEL% equ 0 (
    echo [OK] Build pipeline completed.
) else (
    echo [ERROR] Build pipeline failed with code %ERRORLEVEL%.
)

endlocal
