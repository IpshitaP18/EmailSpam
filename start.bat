@echo off
REM Email Spam Classifier - Quick Start Script for Windows

echo.
echo ===============================================
echo   Email Spam Classifier - Quick Start
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7+ from https://www.python.org/
    pause
    exit /b 1
)

echo [1/3] Installing backend dependencies...
cd backend
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error: Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [2/3] Starting backend server...
echo Backend will start on http://localhost:5000
echo.
echo Waiting for server to initialize...
timeout /t 2 /nobreak

start python app.py

echo.
echo [3/3] Backend server started!
echo.
echo ===============================================
echo   Opening Frontend...
echo ===============================================
echo.

cd ..
cd frontend

REM Try to open index.html in default browser
start index.html

echo.
echo Application is ready!
echo Frontend: http://localhost:8000 (or open frontend/index.html directly)
echo Backend: http://localhost:5000
echo.
echo Press CTRL+C in this window to stop the backend server.
echo.

REM Start a simple HTTP server for the frontend
python -m http.server 8000

pause
