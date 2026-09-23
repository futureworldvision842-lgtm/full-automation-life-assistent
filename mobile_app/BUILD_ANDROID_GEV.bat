@echo off
setlocal
title J.A.R.V.I.S. // ANDROID GOD'S EYE VIEW APK BUILDER
echo ======================================================================
echo   J.A.R.V.I.S. ANDROID GOD'S EYE VIEW APK & ASSETS BUILDER
echo ======================================================================
echo.

set "GEV_ROOT=%~dp0..\apps\android-gods-eye-view"
set "DIST_DIR=%~dp0dist"
if not exist "%DIST_DIR%" mkdir "%DIST_DIR%"

cd /d "%GEV_ROOT%"
if not exist "node_modules" (
    echo [*] Installing Android God's Eye View dependencies...
    call npm.cmd install --ignore-engines
)

echo.
echo [*] Step 1: Compiling 3D Web Bundle & Syncing Android Assets...
call node.exe "Android\scripts\build-apk-assets.mjs"

echo.
echo [*] Step 2: Checking Android Compilation Toolchain...
where javac >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [+] Java JDK detected. Running Gradle APK build...
    cd /d "%GEV_ROOT%\Android"
    call gradlew.bat assembleDebug
    if exist "app\build\outputs\apk\debug\app-debug.apk" (
        copy /y "app\build\outputs\apk\debug\app-debug.apk" "%DIST_DIR%\gods-eye-view-debug.apk"
        echo [OK] APK successfully copied to %DIST_DIR%\gods-eye-view-debug.apk
    )
) else (
    echo [-] Java JDK not found in PATH for direct Gradle compilation.
    echo [*] Packaging standalone Android APK bundle using Python engine...
    python "%~dp0package_gev_apk.py"
    echo [+] You can also open "%GEV_ROOT%\Android" in Android Studio to build signed APKs.
)

echo.
echo ======================================================================
echo   BUILD & ASSETS PIPELINE COMPLETED!
echo ======================================================================
pause
endlocal
