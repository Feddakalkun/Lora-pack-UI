@echo off
color 0B
setlocal

set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"

echo ==============================================
echo =       UPDATING LORA PACK UI PROJECT        =
echo ==============================================
echo.

where git >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Git is not installed or not on PATH.
  pause
  exit /b 1
)

echo [1/5] Pulling latest code...
cd /d "%ROOT%"
git pull --rebase --autostash
if errorlevel 1 (
  echo [WARN] Git pull had conflicts or failed. Resolve git state, then run update again.
  pause
  exit /b 1
)

echo [2/5] Ensuring Python virtual environment...
if not exist "%PY%" (
  echo Creating .venv...
  python -m venv "%ROOT%.venv"
  if errorlevel 1 (
    echo [ERROR] Failed to create .venv
    pause
    exit /b 1
  )
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
echo Update complete.
echo You can now run run.cmd
pause
