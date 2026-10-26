@echo off
REM Build ASCII Visualizer: the app (ASCIIVisualizer.exe), the screensaver
REM (ASCIIVisualizer.scr), or both. Double-click this file to build both, or
REM from a command prompt:
REM
REM     build.bat               both
REM     build.bat app           just ASCIIVisualizer.exe
REM     build.bat screensaver   just ASCIIVisualizer.scr
REM
REM One-time prerequisite:  python -m pip install -r requirements.txt
REM (PyInstaller is installed for you if it is missing.) The real work is in
REM build.ps1; see the top of that file for the details.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
set RC=%ERRORLEVEL%
echo.
pause
exit /b %RC%
