@echo off
title YouTube Traffic & Marketing Bot v1.0
cd /d "%~dp0"
echo ====================================================
echo     Launching YouTube Traffic & Marketing Bot
echo ====================================================
py main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo If 'py' failed, trying with 'python'...
    python main.py
)
pause
