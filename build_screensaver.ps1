# Build ASCII Visualizer into a Windows .scr screensaver.
#
# Prerequisites (one time):
#     pip install -r requirements.txt
#     pip install pyinstaller
#
# Run from this folder:
#     powershell -ExecutionPolicy Bypass -File build_screensaver.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

pip install pyinstaller | Out-Host

# --onefile            : a single self-contained .exe
# --noconsole          : no terminal window appears when it runs
# --collect-submodules : make sure the whole asciiviz package is bundled
# --exclude-module cv2 : the screensaver doesn't use the webcam; keeps it small
pyinstaller --onefile --noconsole --name ASCIIVisualizer `
    --collect-submodules asciiviz --exclude-module cv2 screensaver.py

Copy-Item -Force "dist\ASCIIVisualizer.exe" "ASCIIVisualizer.scr"

Write-Host ""
Write-Host "Built ASCIIVisualizer.scr"
Write-Host "Install it: right-click ASCIIVisualizer.scr in Explorer -> Install"
Write-Host "(or copy it into C:\Windows\System32 to pick it in Settings > Lock screen > Screen saver)."
