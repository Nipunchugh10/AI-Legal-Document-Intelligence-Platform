@echo off
setlocal
cd /d "%~dp0"

set "BACKEND_PY=%~dp0backend\.venv\Scripts\python.exe"

if "%1"=="space" (
    echo Starting Unified App on http://localhost:7860...
    "%BACKEND_PY%" space_app.py
    exit /b %ERRORLEVEL%
)

echo Starting FastAPI Backend...
start "AI Legal Backend" "%BACKEND_PY%" -m uvicorn app.main:app --reload --port 8000 --app-dir "%~dp0backend"

echo Starting React Frontend on http://localhost:5173...
cd /d "%~dp0frontend"
npm run dev
