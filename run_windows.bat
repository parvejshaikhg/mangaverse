@echo off
title MangaVerse Downloader
cd /d "%~dp0"

echo ========================================================
echo   Starting MangaVerse (Windows Launcher)
echo ========================================================
echo.

python main.py %*
if %errorlevel% neq 0 (
    echo.
    echo If Python failed to launch, please verify Python is installed:
    echo https://www.python.org/downloads/
    echo.
    pause
)
