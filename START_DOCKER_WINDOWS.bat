@echo off
setlocal
cd /d "%~dp0"
py -3.12 scripts\initialize_env.py --start
if errorlevel 1 (
  echo Check Python 3.12, Docker Desktop, and the guide troubleshooting section.
  pause
  exit /b 1
)
start http://localhost:8000
echo First owner: copy SETUP_TOKEN from your private .env file.
pause
