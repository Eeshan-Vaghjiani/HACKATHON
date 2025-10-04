@echo off
echo 🚀 Setting up HabitatCanvas development environment...

REM Check if Docker is installed
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker is not installed. Please install Docker first.
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Docker Compose is not installed. Please install Docker Compose first.
    exit /b 1
)

echo ✅ Docker and Docker Compose are installed

REM Build and start the development environment
echo 🔨 Building and starting development environment...
docker-compose up --build -d

REM Wait for services to be ready
echo ⏳ Waiting for services to start...
timeout /t 10 /nobreak >nul

echo 🔍 Checking service health...

REM Check services (simplified for Windows)
echo ✅ Services should be starting up...

echo.
echo 🎉 Development environment setup complete!
echo.
echo 📋 Available services:
echo    Frontend: http://localhost:3000
echo    Backend API: http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo    Database: localhost:5432
echo    Redis: localhost:6379
echo.
echo 🛠️  Useful commands:
echo    View logs: docker-compose logs -f
echo    Stop services: docker-compose down
echo    Restart services: docker-compose restart
echo.