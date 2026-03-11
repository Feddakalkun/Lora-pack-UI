@echo off
color 0A
setlocal

set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"

echo ==============================================
echo =   STARTING LORA PACK UI (PREMIUM EDITION)  =
echo ==============================================
echo.

if not exist "%PY%" (
  echo [ERROR] Project virtual environment not found at:
  echo         %PY%
  echo Create it with: python -m venv .venv
  pause
  exit /b 1
)

echo Starting FastAPI Backend (project venv)...
start "Backend" cmd /k "cd /d %ROOT%backend && %PY% -m pip install -r requirements.txt && %PY% main.py"

echo Starting Vite React Frontend...
cd /d "%ROOT%frontend"
cmd /c npm run dev