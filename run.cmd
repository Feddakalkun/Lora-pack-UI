@echo off
color 0A
setlocal

set "ROOT=%~dp0"
set "PY=%ROOT%.venv\Scripts\python.exe"
set "BACKEND_PORT=%~1"
set "FRONTEND_PORT=%~2"
if "%BACKEND_PORT%"=="" set "BACKEND_PORT=8000"
if "%FRONTEND_PORT%"=="" set "FRONTEND_PORT=5173"

echo ==============================================
echo =   STARTING LORA PACK UI (PREMIUM EDITION)  =
echo ==============================================
echo.
echo Backend:  http://127.0.0.1:%BACKEND_PORT%
echo Frontend: http://127.0.0.1:%FRONTEND_PORT%
echo.

if not exist "%PY%" (
  echo [ERROR] Project virtual environment not found at:
  echo         %PY%
  echo Create it with: python -m venv .venv
  pause
  exit /b 1
)

echo Starting FastAPI Backend (project venv)...
start "Backend" cmd /k "cd /d %ROOT%backend && set BACKEND_PORT=%BACKEND_PORT% && %PY% -m pip install -r requirements.txt && %PY% main.py"

echo Starting Vite React Frontend...
cd /d "%ROOT%frontend"
set "VITE_API_BASE_URL=http://127.0.0.1:%BACKEND_PORT%"
cmd /c npm run dev -- --port %FRONTEND_PORT%
