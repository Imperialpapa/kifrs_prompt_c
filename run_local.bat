@echo off
echo =================================================================
echo   K-IFRS 1019 DBO Validation System (Local Mode)
echo =================================================================
echo.

cd backend

if not exist ".env" (
    echo [ERROR] .env file not found in backend directory!
    echo Please copy .env.example to .env and configure it.
    pause
    exit /b 1
)

echo [1/2] Installing/Updating dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

echo.
echo [2/2] Starting Server...
echo Mobile-optimized UI: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server.
echo.

python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
