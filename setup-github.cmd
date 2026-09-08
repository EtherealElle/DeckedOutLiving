@echo off
REM ===========================================================
REM  Decked Out Living - ONE-TIME setup.
REM
REM  Connects this folder to GitHub. You only ever run this once.
REM  After this, use publish-website.cmd to push changes.
REM
REM  Work through GO-LIVE-GUIDE.md Steps 1-3 before running this:
REM  you need Git installed and an empty GitHub repository created.
REM ===========================================================
REM enabledelayedexpansion is needed because the name and email are read
REM and used inside the same if-block below (the !VAR! syntax).
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo.
echo   ===========================================================
echo    DECKED OUT LIVING - one-time GitHub setup
echo   ===========================================================
echo.

where git >nul 2>nul
if errorlevel 1 (
    echo   Git is not installed yet.
    echo.
    echo   Go to https://git-scm.com/download/win , run the installer
    echo   with the default options, restart the computer, then run
    echo   this file again.
    echo.
    pause
    exit /b 1
)

if exist ".git" (
    echo   This folder is ALREADY connected to GitHub.
    echo.
    git remote -v
    echo.
    echo   You do not need this file again. To publish changes from
    echo   now on, use publish-website.cmd instead.
    echo.
    pause
    exit /b 0
)

REM --- who is committing ---------------------------------------
for /f "delims=" %%N in ('git config --global user.name 2^>nul') do set "GITNAME=%%N"
if not defined GITNAME (
    echo   Git needs to know who you are. This is only asked once.
    echo.
    set /p GITNAME="   Your name: "
    set /p GITMAIL="   Your email: "
    git config --global user.name "!GITNAME!"
    git config --global user.email "!GITMAIL!"
    echo.
)

echo   Now paste the address of the EMPTY repository you created
echo   on GitHub. It looks like this:
echo.
echo       https://github.com/yourname/deckedoutliving-website.git
echo.
set /p REPOURL="   Repository address: "

if "%REPOURL%"=="" (
    echo.
    echo   Nothing entered. Stopping - nothing has been changed.
    echo.
    pause
    exit /b 1
)

echo.
echo   Setting up...

git init >nul
if errorlevel 1 goto failed

git branch -M main >nul 2>nul
git add -A
if errorlevel 1 goto failed

git commit -m "Decked Out Living website" >nul
if errorlevel 1 goto failed

git remote add origin "%REPOURL%"
if errorlevel 1 goto failed

echo   Uploading to GitHub. A sign-in window may appear - complete it.
echo.
git push -u origin main
if errorlevel 1 goto pushfailed

echo.
echo   ===========================================================
echo    Uploaded.
echo.
echo    NEXT: turn the website on. In your browser, go to your
echo    repository on GitHub, then:
echo.
echo       Settings  ^>  Pages
echo       Source:   Deploy from a branch
echo       Branch:   main      Folder:  /docs
echo       Save
echo.
echo    Wait about a minute, then your site is live. GitHub shows
echo    you the address at the top of that same Pages screen.
echo.
echo    See GO-LIVE-GUIDE.md Step 5 if you get stuck.
echo   ===========================================================
echo.
pause
exit /b 0

:failed
echo.
echo   Something went wrong during setup. The messages above say what.
echo   Nothing has been uploaded.
echo.
pause
exit /b 1

:pushfailed
echo.
echo   The upload did not finish.
echo.
echo   Most likely causes:
echo     - The sign-in window was closed or cancelled.
echo     - The repository address was typed incorrectly.
echo     - The repository you created was not empty. It must have
echo       NO readme, NO licence and NO .gitignore.
echo.
echo   To try the address again, run these two lines in this folder:
echo       git remote remove origin
echo   then run this setup file again.
echo.
pause
exit /b 1
