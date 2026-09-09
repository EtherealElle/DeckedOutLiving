@echo off
REM ===========================================================
REM  Decked Out Living - fetch job photos from Discord.
REM
REM  1. Post your job photos to Discord as you always do.
REM  2. Double-click this file. It downloads them into
REM     photo-inbox and opens a page to name each job.
REM  3. Run publish-photos.cmd to put them on the website.
REM
REM  First time only: this walks you through connecting Discord.
REM ===========================================================
setlocal
cd /d "%~dp0"

echo.
echo   Decked Out Living - photos from Discord
echo   ======================================
echo.

where python >nul 2>nul
if errorlevel 1 goto nopython

REM  Nothing to install. This tool uses only what Python ships with.

REM  If the user asked for setup themselves, do not also run it below.
echo %* | findstr /C:"--setup" >nul
if not errorlevel 1 goto run

if not exist "discord-bot.secret.json" (
    python tools\import_photos.py --setup
    if errorlevel 1 (
        set RESULT=1
        goto finish
    )
    echo.
)

:run
python tools\import_photos.py %*
set RESULT=%ERRORLEVEL%

:finish
echo.
if not "%RESULT%"=="0" (
    echo   ===========================================================
    echo    SOMETHING NEEDS YOUR ATTENTION - read the messages above.
    echo    Nothing has been downloaded.
    echo   ===========================================================
)
echo.
pause
exit /b %RESULT%

:nopython
echo.
echo   Python is not installed on this computer.
echo.
echo   1. Go to   https://www.python.org/downloads/
echo   2. Download Python for Windows and run the installer.
echo   3. IMPORTANT: tick "Add python.exe to PATH" on the first screen.
echo   4. Restart the computer, then double-click this file again.
echo.
pause
exit /b 1
