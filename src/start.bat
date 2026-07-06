@echo off
chcp 65001 >nul 2>&1
title SNMP MIB to Zabbix Template Tool

echo ==========================================
echo   SNMP MIB to Zabbix Template Tool
echo ==========================================
echo.

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"

REM === Check Python ===
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

REM === Check Node ===
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js not found. Please install Node.js 16+
    pause
    exit /b 1
)

echo [1/4] Installing backend dependencies...
cd /d "%BACKEND%"
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo [ERROR] Backend dependencies install failed
    pause
    exit /b 1
)

echo [2/4] Starting backend (port 8000)...
start "Backend" cmd /k "cd /d "%BACKEND%" && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

echo [3/4] Installing frontend dependencies...
cd /d "%FRONTEND%"
if not exist "node_modules" (
    call npm install
) else (
    echo        node_modules already exists, skipping
)

echo [4/4] Starting frontend (port 5173)...
start "Frontend" cmd /k "cd /d "%FRONTEND%" && npm run dev"

echo.
echo ==========================================
echo   All services started!
echo.
echo   Frontend:  http://localhost:5173
echo   Backend:   http://localhost:8000
echo   API Docs:  http://localhost:8000/docs
echo ==========================================
echo.
echo Press any key to close this window (services keep running)
pause >nul
