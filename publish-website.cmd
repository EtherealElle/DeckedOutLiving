@echo off
REM ===========================================================
REM  Decked Out Living - put the website online.
REM
REM  Sends everything in this folder up to GitHub, which then
REM  publishes it. Takes about a minute for changes to appear.
REM ===========================================================
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo   Decked Out Living - publishing the website
echo   =========================================
echo.

where git >nul 2>nul
if errorlevel 1 goto nogit

REM --- first time? set the repository up ------------------------
if not exist ".git" (
    echo   This folder is not connected to GitHub yet.
    echo.
    echo   Follow GO-LIVE-GUIDE.md from the beginning - it walks you
    echo   through creating the GitHub account and repository first.
    echo.
    pause
    exit /b 1
)

git remote get-url origin >nul 2>nul
if errorlevel 1 goto noremote

REM --- what changed? -------------------------------------------
git add -A

git diff --cached --quiet
if not errorlevel 1 (
    echo   Nothing has changed since the last time you published.
    echo   The site online is already up to date.
    echo.
    pause
    exit /b 0
)

echo   About to publish these changes:
echo.
git diff --cached --name-status
echo.

set "MSG=%~1"
if "%MSG%"=="" set "MSG=Site update"

git commit -m "%MSG%" >nul
if errorlevel 1 goto commitfail

echo   Uploading to GitHub...
git push
if errorlevel 1 goto pushfail

echo.
echo   ===========================================================
echo    Done. GitHub is building the site now.
echo    Give it about a minute, then refresh your website.
echo   ===========================================================
echo.
pause
exit /b 0

:nogit
echo   Git is not installed on this computer.
echo.
echo   1. Go to   https://git-scm.com/download/win
echo   2. Download and run the installer. The default options are fine.
echo   3. Restart the computer, then double-click this file again.
echo.
pause
exit /b 1

:noremote
echo   This folder has no GitHub address saved yet.
echo.
echo   Open GO-LIVE-GUIDE.md and work through Step 4.
echo.
pause
exit /b 1

:commitfail
echo.
echo   Git could not save the changes.
echo   If it is asking for your name and email, run these two lines
echo   once, putting your own details in the quotes:
echo.
echo       git config --global user.name "Your Name"
echo       git config --global user.email "you@example.com"
echo.
pause
exit /b 1

:pushfail
echo.
echo   The upload did not go through.
echo.
echo   Most common reasons:
echo     - No internet connection.
echo     - GitHub asked you to sign in and the window was closed.
echo     - You are signed in as the wrong account.
echo.
echo   Try running this file again. If GitHub opens a sign-in window,
echo   complete it and let this finish.
echo.
pause
exit /b 1
