@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run py -3.12 scripts\setup.py --dev first, and configure TEST_DATABASE_URL.
  exit /b 1
)
".venv\Scripts\python.exe" scripts\run_tests.py %*
set "TEST_EXIT=%ERRORLEVEL%"
exit /b %TEST_EXIT%
