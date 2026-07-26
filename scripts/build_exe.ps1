$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$BackendRoot = Join-Path $ProjectRoot "backend"
$OutputsRoot = Resolve-Path (Join-Path $ProjectRoot "..\..\outputs")
$AppName = "FOSIM"
$ExeZip = Join-Path $OutputsRoot "$AppName-exe.zip"

Set-Location $FrontendRoot
npm.cmd install
npm.cmd test
npm.cmd run build

Set-Location $BackendRoot
python -m pytest -q

$DistPath = Join-Path $ProjectRoot "frontend\dist"
$SamplePath = Join-Path $ProjectRoot "sample-data"
$DocsPath = Join-Path $ProjectRoot "docs"

if (Test-Path "dist") { Remove-Item -LiteralPath "dist" -Recurse -Force }
if (Test-Path "build") { Remove-Item -LiteralPath "build" -Recurse -Force }

python -m PyInstaller `
  --noconfirm `
  --clean `
  --name $AppName `
  --add-data "$DistPath;frontend/dist" `
  --add-data "$SamplePath;sample-data" `
  --add-data "$DocsPath;docs" `
  desktop_launcher.py

$ReadmePath = Join-Path $BackendRoot "dist\$AppName\README_RUN.txt"
@"
FOSIM.exe Run Guide

FOSIM = Fastening Optimization & Simulation Manager

1. Extract the whole zip file to a folder.
2. Run FOSIM.exe.
3. The browser opens automatically.
4. Close the console window to stop the app.

Notes:
- This MVP uses CSV/sample data only.
- Actual SH-2 communication and device write are not included.
- If Windows shows a security warning, choose More info, then Run anyway.
"@ | Set-Content -Path $ReadmePath -Encoding UTF8

if (Test-Path $ExeZip) { Remove-Item -LiteralPath $ExeZip -Force }
Compress-Archive -Path (Join-Path $BackendRoot "dist\$AppName") -DestinationPath $ExeZip -Force

Write-Host "Created $ExeZip"
