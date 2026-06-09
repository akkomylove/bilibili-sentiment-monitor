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

echo [5/6] Starting Celery worker in a new window...
REM Kill any stale celery worker first (avoid duplicate registration)
for /f "tokens=1" %%p in ('tasklist /FI "IMAGENAME eq celery.exe" /NH 2^>nul ^| findstr celery') do (
    echo [INFO] Killing stale celery PID %%p
    taskkill /PID %%p /F >nul 2>&1
)
for /f "tokens=2" %%p in ('tasklist /FI "IMAGENAME eq python.exe" /V /NH 2^>nul ^| findstr /I "celery -A app.tasks worker"') do (
    echo [INFO] Killing stale celery worker PID %%p
    taskkill /PID %%p /F >nul 2>&1
)
REM Launch worker in a separate window. cmd /k keeps the window open so
REM the worker keeps running. NO output redirect - celery output goes
REM straight to the window so the user can watch the crawl progress
REM (video titles, comment counts, etc.) live. A rolling log is also
REM captured to logs\celery_worker.log via PowerShell Tee-Object.
if not exist "logs" mkdir logs
start "Celery Worker" powershell -NoProfile -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; $OutputEncoding = [System.Text.Encoding]::UTF8; celery -A app.tasks worker --loglevel=info --concurrency=1 -P solo 2>&1 | Tee-Object -FilePath 'logs\celery_worker.log'"
echo [OK] Celery worker launched. See the "Celery Worker" window for live crawl progress.
echo       logs\celery_worker.log also captures output.
echo.

echo [6/6] Starting FastAPI server on port %PORT%...
echo ==========================================
echo    Server starting on http://localhost:%PORT%
echo    Keep this window open. Press Ctrl+C to stop.
echo ==========================================
echo.

REM Open browser after 2s (non-blocking). Do NOT use Chinese full-width
REM brackets in this script - some shells split them into the uvicorn args.
ping -n 3 127.0.0.1 >nul
start "" "http://localhost:%PORT%"

REM Use python -m uvicorn to avoid PATH/console quirks. %PORT% is resolved
REM here as a normal env-style expansion at execution time.
python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT%

echo.
echo [INFO] uvicorn exited. Press any key to close.
pause >nul
