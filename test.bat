@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Run install-offline.bat first.
 exit /b 1
)
.venv\Scripts\python.exe scripts\check.py %*
exit /b %ERRORLEVEL%
