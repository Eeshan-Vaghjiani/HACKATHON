@echo off
echo ========================================
echo  HabitatCanvas Startup Script
echo ========================================
echo.

echo Checking Docker...
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not running
    echo Please install Docker Desktop and make sure it's running
    pause
    exit /b 1
)

echo Docker found! Starting HabitatCanvas...
echo.

echo Cleaning previous builds...
docker-compose down -v >nul 2>&1

echo Building and starting services...
echo This may take 5-10 minutes on first run...
docker-compose up --build

echo.
echo ========================================
echo  HabitatCanvas should now be running at:
echo  Frontend: http://localhost:3000
echo  Backend:  http://localhost:8000
echo  API Docs: http://localhost:8000/docs
echo ========================================
pause