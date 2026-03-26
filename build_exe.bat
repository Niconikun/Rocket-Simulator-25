@echo off
REM Build script for Rocket Simulator Pro executable
REM This script compiles the PyQt6 application to a Windows .exe file

setlocal enabledelayedexpansion

echo.
echo ========================================================
echo    ROCKET SIMULATOR PRO - BUILD EXECUTABLE
echo ========================================================
echo.

REM Check if PyInstaller is installed
python -m pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [!] PyInstaller not found. Installing...
    python -m pip install pyinstaller>=6.0.0
    if errorlevel 1 (
        echo [X] Failed to install PyInstaller
        exit /b 1
    )
)

echo [✓] PyInstaller is ready
echo.

REM Clean previous builds
echo [*] Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "*.spec" del /q "*.spec" >nul 2>&1
echo [✓] Cleaned old builds
echo.

REM Build with spec file
echo [*] Building executable from build_exe.spec...
echo.
pyinstaller build_exe.spec --noconfirm

if errorlevel 1 (
    echo.
    echo [X] Build failed!
    exit /b 1
)

echo.
echo ========================================================
echo    BUILD SUCCESSFUL!
echo ========================================================
echo.
echo Location: dist\RocketSimulator\RocketSimulator.exe
echo.
echo [*] Running final checks...
if exist "dist\RocketSimulator\RocketSimulator.exe" (
    echo [✓] Executable created successfully
    echo.
    echo FILE SIZE:
    for %%A in (dist\RocketSimulator\RocketSimulator.exe) do (
        echo   %%~sA bytes
    )
) else (
    echo [X] Executable not found
    exit /b 1
)

echo.
echo ========================================================
echo    WHAT'S NEXT?
echo ========================================================
echo.
echo 1. Test the executable:
echo    dist\RocketSimulator\RocketSimulator.exe
echo.
echo 2. Create installer (optional - requires NSIS):
echo    makensis rocket_installer.nsi
echo.
echo 3. For single-file executable, edit build_exe.spec:
echo    - Comment out COLLECT section
echo    - Set upx=False if single-file doesn't work
echo.
echo ========================================================
echo.

endlocal
