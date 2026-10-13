@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Install Python 3.12 from python.org, including the Python launcher, then retry.
  pause
  exit /b 1
)
py -3.12 scripts\setup.py
if errorlevel 1 (
  echo Setup did not finish. Read the error above.
  pause
  exit /b 1
)
pause
