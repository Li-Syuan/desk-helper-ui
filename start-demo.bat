@echo off
call "%~dp0start-app.bat" --temporary %*
exit /b %ERRORLEVEL%
