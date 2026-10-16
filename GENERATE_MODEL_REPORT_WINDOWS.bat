@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" scripts\generate_model_report.py %*
) else (
  py -3.12 scripts\generate_model_report.py %*
)
set "REPORT_EXIT=%ERRORLEVEL%"
if not "%REPORT_EXIT%"=="0" (
  echo.
  echo Report generation failed. Run SETUP_WINDOWS.bat first and review the error above.
  pause
)
exit /b %REPORT_EXIT%
