@echo off
title Push MangaVerse to GitHub
cd /d "%~dp0"

echo ========================================================
echo   🚀 Pushing MangaVerse to GitHub (@parvejshaikhg)
echo ========================================================
echo.

git remote remove origin 2>nul
git remote add origin https://github.com/parvejshaikhg/mangaverse.git

echo Linking to https://github.com/parvejshaikhg/mangaverse.git...
echo Pushing branch 'main'...
echo.

git push -u origin main

if %errorlevel% neq 0 (
    echo.
    echo ========================================================
    echo   Notice:
    echo   1. Make sure you have created the repository at:
    echo      https://github.com/new named 'mangaverse'
    echo   2. When Windows asks you to authenticate, sign in
    echo      with your GitHub account: parvejshaikhg
    echo ========================================================
) else (
    echo.
    echo ✨ Successfully published to GitHub!
    echo Check it live at: https://github.com/parvejshaikhg/mangaverse
)
echo.
pause
