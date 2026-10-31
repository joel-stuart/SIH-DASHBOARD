@echo off
title Mine Subsidence Monitoring Dashboard

echo ==========================================
echo   Mine Subsidence Monitoring Dashboard
echo ==========================================
echo.

cd /d "%~dp0"

echo Checking Python...
python --version
if errorlevel 1 (
    echo.
    echo ERROR: Python is not installed.
    echo Please install Python first.
    pause
    exit /b
)

echo.
echo Creating virtual environment if needed...

if not exist "venv\Scripts\python.exe" (
    python -m venv venv
)

echo.
echo Installing required packages...
venv\Scripts\python.exe -m pip install -r requirements.txt

echo.
echo Starting dashboard...
echo.

venv\Scripts\python.exe -m streamlit run app.py

pause