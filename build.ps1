<#
.SYNOPSIS
    Build ASCII Visualizer as a Windows app (.exe), a screensaver (.scr), or both.

.DESCRIPTION
    Both come from the same source through PyInstaller, each as one
    self-contained file dropped in this folder:

      ASCIIVisualizer.exe   the app: main.py, every key and command-line
                            option, webcam/video included when opencv-python
                            is installed. Double-click it, or run it with flags.
      ASCIIVisualizer.scr   the screensaver: screensaver.py, answers Windows'
                            /s /c /p. No webcam support, so it stays smaller
                            and starts faster. Right-click it > Install.

    Both read the same config.json, so settings carry across.

    One-time prerequisite: python -m pip install -r requirements.txt
    PyInstaller is installed for you if it is missing.

.PARAMETER Target
    all (default), app, or screensaver.

.PARAMETER Python
    The Python to build with. Defaults to "python" on PATH; point it at a
    venv's python.exe to build from that venv instead.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File build.ps1
    Builds both.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File build.ps1 app
    Builds just ASCIIVisualizer.exe.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File build.ps1 screensaver
    Builds just ASCIIVisualizer.scr.
#>
param(
    [ValidateSet("all", "app", "screensaver")]
    [string]$Target = "all",
    [string]$Python = "python"
)

# Native tools are checked through $LASTEXITCODE rather than
# $ErrorActionPreference = "Stop": PyInstaller logs to stderr, and Windows
# PowerShell 5.1 (what build.bat runs) can treat any stderr line as a failure.
Set-Location -LiteralPath $PSScriptRoot
$env:PYGAME_HIDE_SUPPORT_PROMPT = "1"

function Fail([string]$Message) {
    Write-Host ""
    Write-Host "BUILD FAILED: $Message" -ForegroundColor Red
    exit 1
}

function Test-Import([string]$Module) {
    & $Python -c "import $Module" *> $null
    return $LASTEXITCODE -eq 0
}

# --------------------------------------------------------------------------
# Prerequisites
# --------------------------------------------------------------------------

if (-not (Get-Command $Python -ErrorAction SilentlyContinue)) {
    Fail "can't find '$Python'. Install Python, or pass -Python <path to python.exe>."
}

$missing = @("pygame", "numpy", "PIL") | Where-Object { -not (Test-Import $_) }
if ($missing) {
    Fail ("missing " + ($missing -join ", ") + ". Run once:  $Python -m pip install -r requirements.txt")
}

if (-not (Test-Import "PyInstaller")) {
    Write-Host "PyInstaller isn't installed; installing it now..."
    & $Python -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) { Fail "couldn't install PyInstaller." }
}

# --------------------------------------------------------------------------
# One build
# --------------------------------------------------------------------------

# Each target gets its own dist\ and build\ subfolders (and keeps its .spec
# in there), so the two builds never overwrite each other's work.
function Build-Target([string]$Kind, [string]$Script, [string]$Output, [string[]]$Extra) {
    $dist = Join-Path $PSScriptRoot "dist\$Kind"
    $work = Join-Path $PSScriptRoot "build\$Kind"
    Write-Host ""
    Write-Host "=== Building $Output from $Script ===" -ForegroundColor Cyan
    $started = Get-Date

    # --onefile            : a single self-contained file
    # --windowed           : no terminal window opens alongside it
    # --collect-submodules : make sure the whole asciiviz package is bundled
    $pyiArgs = @(
        "-m", "PyInstaller", "--noconfirm", "--log-level", "WARN",
        "--onefile", "--windowed", "--name", "ASCIIVisualizer",
        "--collect-submodules", "asciiviz",
        "--distpath", $dist, "--workpath", $work, "--specpath", $work
    ) + $Extra + @((Join-Path $PSScriptRoot $Script))
    & $Python @pyiArgs
    if ($LASTEXITCODE -ne 0) { Fail "PyInstaller couldn't build $Output (exit code $LASTEXITCODE)." }

    try {
        Copy-Item -LiteralPath (Join-Path $dist "ASCIIVisualizer.exe") `
                  -Destination (Join-Path $PSScriptRoot $Output) -Force -ErrorAction Stop
    } catch {
        Fail "built, but couldn't copy it to $Output. Is it running? Close it and build again. ($($_.Exception.Message))"
    }
    $seconds = [int]((Get-Date) - $started).TotalSeconds
    Write-Host "Built $Output in $seconds s."
}

# --------------------------------------------------------------------------
# The targets
# --------------------------------------------------------------------------

$built = @()

if ($Target -in "all", "app") {
    if (Test-Import "cv2") {
        $appExtra = @()
    } else {
        Write-Host ""
        Write-Host "Note: opencv-python isn't installed, so this ASCIIVisualizer.exe will have" -ForegroundColor Yellow
        Write-Host "no webcam/video (the V key, --webcam, --video). The rest works. To include" -ForegroundColor Yellow
        Write-Host "it: $Python -m pip install opencv-python, then build again." -ForegroundColor Yellow
        $appExtra = @("--exclude-module", "cv2")
    }
    Build-Target "app" "main.py" "ASCIIVisualizer.exe" $appExtra
    $built += "ASCIIVisualizer.exe"
}

if ($Target -in "all", "screensaver") {
    # The screensaver never uses the webcam; leaving OpenCV out roughly halves
    # the file and the time Windows waits for it to unpack on every launch.
    Build-Target "screensaver" "screensaver.py" "ASCIIVisualizer.scr" @("--exclude-module", "cv2")
    $built += "ASCIIVisualizer.scr"
}

# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------

Write-Host ""
Write-Host "Done:" -ForegroundColor Green
foreach ($name in $built) {
    $mb = "{0,6:N1} MB" -f ((Get-Item -LiteralPath (Join-Path $PSScriptRoot $name)).Length / 1MB)
    Write-Host "  $name  $mb"
}
Write-Host ""
if ($built -contains "ASCIIVisualizer.exe") {
    Write-Host "App:          double-click ASCIIVisualizer.exe, or run it with options"
    Write-Host "              from a terminal (ASCIIVisualizer.exe --help lists them)."
}
if ($built -contains "ASCIIVisualizer.scr") {
    Write-Host "Screensaver:  right-click ASCIIVisualizer.scr in Explorer > Install."
    Write-Host "              Its Settings button opens config.json; no rebuild needed to retune it."
}
