@echo off
setlocal

rem require .venv (run setup.bat first)
if not exist .venv (
    echo Error: .venv not found. Run setup.bat first.
    exit /b 1
)

rem check PyInstaller is installed
.venv\Scripts\python.exe -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo Error: PyInstaller is not installed. Check requirements.txt.
    exit /b 1
)

rem build launcher.py as a single exe (does not bundle torch etc, calls .venv at runtime)
rem output goes directly to the repo root: wdv3_timm.exe must stay next to .venv and wdv3_timm.py
.venv\Scripts\pyinstaller.exe --noconfirm --onefile --name wdv3_timm --distpath . launcher.py
if errorlevel 1 (
    echo Error: Build failed.
    exit /b 1
)

rem remove intermediate build artifacts (keep only wdv3_timm.exe)
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q wdv3_timm.spec 2>nul

echo Build complete. wdv3_timm.exe is in the repo root (keep it next to .venv and wdv3_timm.py).
