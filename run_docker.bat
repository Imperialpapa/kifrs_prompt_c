@echo off
echo =================================================================
echo   K-IFRS 1019 DBO Validation System
echo   AI-Powered Data Validation for Defined Benefit Obligations
echo =================================================================
echo.

if not exist "backend\.env" (
    echo [ERROR] backend\.env file not found!
    echo Please copy backend\.env.example to backend\.env and fill in the values.
    exit /b 1
)

echo [1/2] Building and starting Docker containers...
docker-compose up --build -d

echo.
echo [2/2] Success! System is running.
echo - Frontend: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo.
echo To stop the system, run: docker-compose down
pause
