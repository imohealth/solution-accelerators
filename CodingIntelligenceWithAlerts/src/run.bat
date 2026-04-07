@echo off
REM Ambient AI Solution Launcher for Windows

echo ==========================================
echo   Ambient AI Solution Launcher
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo X Python is not installed. Please install Python 3.8 or higher.
    echo Visit: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Get Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo √ Python version: %PYTHON_VERSION%
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo Installing virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo X Failed to create virtual environment
        pause
        exit /b 1
    )
    echo √ Virtual environment created
)

REM Activate virtual environment
echo Activating virtual environment...
call venv\Scripts\activate.bat

REM Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip >nul 2>&1

REM Install requirements
if exist "requirements.txt" (
    echo Installing dependencies...
    pip install -r requirements.txt >nul 2>&1
    if %errorlevel% neq 0 (
        echo X Failed to install dependencies
        echo Run 'pip install -r requirements.txt' manually to see errors
        pause
        exit /b 1
    )
    echo √ Dependencies installed
) else (
    echo ! requirements.txt not found. Installing basic dependencies...
    pip install flask boto3 requests >nul 2>&1
)

echo.
echo ==========================================
echo Starting Ambient AI Solution...
echo ==========================================
echo.
echo The application will open in your browser at:
echo http://127.0.0.1:5000
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run the Flask app
python app.py

pause
