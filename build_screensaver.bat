@echo off
REM Build ASCII Visualizer into a Windows .scr screensaver.
REM Prereqs (one time):  pip install -r requirements.txt  &&  pip install pyinstaller
REM Then just double-click this file.
cd /d "%~dp0"
pip install pyinstaller
pyinstaller --onefile --noconsole --name ASCIIVisualizer --collect-submodules asciiviz --exclude-module cv2 screensaver.py
copy /Y "dist\ASCIIVisualizer.exe" "ASCIIVisualizer.scr"
echo.
echo Built ASCIIVisualizer.scr
echo Right-click it in Explorer -^> Install, or copy it into C:\Windows\System32.
pause
