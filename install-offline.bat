@echo off
setlocal
cd /d "%~dp0"
if "%~1"=="" (
 echo Usage: install-offline.bat "C:\approved\Python\python.exe"
 exit /b 2
)
"%~1" scripts\install_offline.py
exit /b %ERRORLEVEL%
