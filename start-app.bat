@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
 echo Run install-offline.bat with your approved Python first.
 exit /b 1
)
.venv\Scripts\python.exe -m desk_helper_ui %*
exit /b %ERRORLEVEL%
