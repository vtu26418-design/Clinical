@echo off
setlocal
cd /d "%~dp0"
py -3.12 scripts\docker_model_report.py %*
set "REPORT_EXIT=%ERRORLEVEL%"
if not "%REPORT_EXIT%"=="0" (
  echo.
  echo Start Docker Desktop and the workbench first. Python 3.12 is required for this launcher.
  pause
)
exit /b %REPORT_EXIT%
