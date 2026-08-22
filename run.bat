@echo off
title SecureAuth Web Application
echo ========================================================
echo  Starting SecureAuth Python Web Server...
echo ========================================================
echo.

:: Check for python in PATH or direct installation path
where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    python app.py
) else (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" app.py
)

pause
