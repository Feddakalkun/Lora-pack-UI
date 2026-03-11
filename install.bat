@echo off
color 0A
setlocal

set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"

echo ==============================================
echo =      INSTALLING LORA PACK UI PROJECT       =
echo ==============================================
echo.

where python >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python is not installed or not on PATH.
  pause
  exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm is not installed or not on PATH.
  echo Install Node.js LTS, then run install.bat again.
  pause
  exit /b 1
)

echo [1/5] Creating Python virtual environment (if missing)...
if not exist "%PY%" (
  python -m venv "%ROOT%.venv"
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv
    pause
    exit /b 1
  )
)

echo [2/5] Upgrading pip in .venv...
"%PY%" -m pip install --upgrade pip
if errorlevel 1 (
  echo [WARN] pip upgrade failed. Continuing...
)

echo [3/5] Installing backend dependencies...
cd /d "%ROOT%backend"
"%PY%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo [ERROR] Failed to install backend requirements.
  pause
  exit /b 1
)

echo [4/5] Installing frontend dependencies...
cd /d "%ROOT%frontend"
cmd /c npm install
if errorlevel 1 (
  echo [ERROR] Failed to install frontend dependencies.
  pause
  exit /b 1
)

echo [5/5] Installing Playwright Chromium...
cd /d "%ROOT%"
"%PY%" -m playwright install chromium
if errorlevel 1 (
  echo [WARN] Playwright Chromium install failed. VSCO login browser may not work until this succeeds.
)

echo.
echo Install complete.
echo Next step: run run.cmd
pause
