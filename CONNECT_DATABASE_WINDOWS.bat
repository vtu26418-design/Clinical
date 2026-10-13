@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run SETUP_WINDOWS.bat first, then run this connector.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" scripts\configure_postgres.py %*
set "CTI_DATABASE_EXIT=%ERRORLEVEL%"
if not "%CTI_DATABASE_EXIT%"=="0" echo Read the message above, correct the local settings, and retry.
pause
exit /b %CTI_DATABASE_EXIT%
