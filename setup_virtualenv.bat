@echo off

:: Navigate to the project directory
cd /d "%~dp0"
echo Current directory: %cd%

:: Create a virtual environment named 'venv'
echo Creating virtual environment...
python -m venv venv
if %errorlevel% neq 0 (
    echo Failed to create virtual environment.
    exit /b %errorlevel%
)

:: Activate the virtual environment
echo Activating virtual environment...
call venv\Scripts\activate
if %errorlevel% neq 0 (
    echo Failed to activate virtual environment.
    exit /b %errorlevel%
)

:: Install required packages
echo Installing required packages...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Failed to install required packages.
    exit /b %errorlevel%
)

echo Virtual environment setup complete.
