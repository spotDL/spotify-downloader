@echo off
title SpotDL Web Interface
echo.
echo ===============================================
echo    🎵 SpotDL Web Interface Launcher 🎵
echo ===============================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python from https://python.org
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Show Python version
echo ✅ Python found:
python --version

REM Check if pip is available
pip --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ pip is not available
    echo Please ensure Python was installed correctly with pip
    pause
    exit /b 1
)

echo ✅ pip found
echo.

REM Install/update required packages (with compatible versions)
echo 📦 Installing/updating required packages...
pip install "fastapi>=0.103.0,<0.104" "uvicorn>=0.23.2,<0.24" "websockets~=14.1" requests beautifulsoup4 spotipy python-multipart

REM Check if spotdl is installed, if not install it
spotdl --version >nul 2>&1
if %errorlevel% neq 0 (
    echo 📥 Installing SpotDL...
    pip install spotdl
) else (
    echo ✅ SpotDL found:
    spotdl --version
)

echo.
echo 🚀 Starting SpotDL Web Interface...
echo.
echo Once started, the web interface will be available at:
echo 🌐 http://localhost:8807 (or next available port)
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run the web interface
python custom_web_interface.py

REM If the script exits, pause to show any error messages
if %errorlevel% neq 0 (
    echo.
    echo ❌ SpotDL Web Interface exited with an error
    pause
)