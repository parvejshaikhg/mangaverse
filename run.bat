@echo off
title MangaVerse Downloader
cd /d "%~dp0"
python main.py
if %errorlevel% neq 0 (
    echo.
    echo If Python failed to launch, please make sure Python is installed and added to PATH.
    pause
)
