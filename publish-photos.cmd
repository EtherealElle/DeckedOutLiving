@echo off
REM ===========================================================
REM  Decked Out Living - put job photos on the website.
REM
REM  1. Drop photos into the photo-inbox folders.
REM  2. Double-click this file.
REM  3. Run publish-website.cmd to push them live.
REM ===========================================================
setlocal
cd /d "%~dp0"

echo.
echo   Decked Out Living - photo publisher
echo   ==================================
echo.

where python >nul 2>nul
if errorlevel 1 goto nopython

REM --- make sure the image libraries are there -------------------
python -c "import PIL" >nul 2>nul
if errorlevel 1 (
    echo   First run - installing the image tools. This takes a minute.
    echo.
    python -m pip install --quiet --upgrade pip
    python -m pip install --quiet Pillow pillow-heif
    echo   Installed.
    echo.
)

REM --- iPhone HEIC support is optional but worth having ---------
python -c "import pillow_heif" >nul 2>nul
if errorlevel 1 (
    echo   Adding iPhone .heic photo support...
    python -m pip install --quiet pillow-heif
    echo.
)

python tools\publish_photos.py %*
set RESULT=%ERRORLEVEL%

echo.
if not "%RESULT%"=="0" (
    echo   ===========================================================
    echo    SOMETHING NEEDS YOUR ATTENTION - read the messages above.
    echo    Nothing has been published.
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
