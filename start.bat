@echo off
chcp 65001 >nul
title Bilibili Sentiment Monitor
cd /d "%~dp0"

set PORT=8010

echo ==========================================
echo    Bilibili Sentiment Monitor
echo ==========================================
echo.

echo [1/6] Checking Docker...
docker ps >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running. Please start Docker Desktop first.
    pause
    exit /b 1
)
echo [OK] Docker is running
echo.

echo [2/6] Starting MySQL + Redis containers...
docker compose up -d
if %errorlevel% neq 0 (
    echo [ERROR] Failed to start Docker containers
    pause
    exit /b 1
)
echo [OK] Containers started
echo.

echo [3/6] Waiting for database...
timeout /t 3 /nobreak >nul
echo [OK] Database ready
echo.

echo [4/6] Killing process on port %PORT%...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :%PORT% ^| findstr LISTENING') do (
    echo [INFO] Killing PID %%a on port %PORT%
    taskkill /PID %%a /F >nul 2>&1
)
echo [OK] Port %PORT% is free
echo.

echo [5/6] Starting Celery Worker + Beat Scheduler...
start "Celery Worker" cmd /k "cd /d %~dp0 && set OMP_NUM_THREADS=1 && set MKL_NUM_THREADS=1 && set OPENBLAS_NUM_THREADS=1 && celery -A app.tasks worker --loglevel=info --concurrency=1 -P solo"
start "Celery Beat" cmd /k "cd /d %~dp0 && celery -A app.tasks beat --loglevel=info"
echo [OK] Celery Worker and Beat started in new windows
echo.

echo [6/6] Starting FastAPI server on port %PORT%...
echo.
echo ==========================================
echo    Server started!
echo    Opening http://localhost:%PORT%
echo.
echo    NOTE: Keep this window and the Celery
echo    window open while using the app.
echo    Press Ctrl+C to stop.
echo ==========================================
echo.

start http://localhost:%PORT%

uvicorn app.main:app --host 0.0.0.0 --port %PORT%

pause
