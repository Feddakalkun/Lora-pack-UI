@echo off
setlocal enabledelayedexpansion

:: Check for virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found. 
    echo Please run: python -m venv .venv
    pause
    exit /b 1
)

:: Check for node_modules in frontend
if not exist "frontend\node_modules" (
    echo [INFO] Installing frontend dependencies...
    cd frontend && npm install && cd ..
)

echo.
echo ==============================================
echo =   LORA PACK STUDIO: UNIFIED SESSION        =
echo ==============================================
echo.

:: Start the backend in the background but keep logs visible? 
:: On Windows, the best way to do "one terminal" without extra tools is a small Python orchestrator.

".venv\Scripts\python.exe" start_studio.py

pause
