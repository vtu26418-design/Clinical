@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run SETUP_WINDOWS.bat first.
  pause
  exit /b 1
)
.venv\Scripts\python.exe scripts\doctor.py
.venv\Scripts\python.exe -m pip check
pause
