@echo off
setlocal

rem make venv if not exist
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo Error: Failed to create venv. Make sure Python is installed.
        exit /b 1
    )
)

rem upgrade pip
.venv\Scripts\python.exe -m pip install --upgrade pip

rem install requirements
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 (
    echo Error: Failed to install dependencies.
    exit /b 1
)

echo Setup complete. Run ".venv\Scripts\activate" to enter the virtual environment.
