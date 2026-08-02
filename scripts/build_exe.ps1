$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$BackendRoot = Join-Path $ProjectRoot "backend"
$ReleasesRoot = Join-Path $ProjectRoot "releases"
$AppName = "FOSIM"

# 빌드 시각은 여기서 한 번만 잡는다. VERSION.txt와 프론트엔드 번들이 같은 값을 쓴다.
$Now = Get-Date
$Version = $Now.ToString("yyyyMMdd_HHmmss")
$env:FOSIM_BUILD_ISO = $Now.ToString("o")

# 매 빌드마다 releases/를 비운다. 버전별 zip을 쌓지 않고 항상 최신 하나만 둔다.
if (Test-Path $ReleasesRoot) { Remove-Item -LiteralPath $ReleasesRoot -Recurse -Force }
New-Item -ItemType Directory -Path $ReleasesRoot | Out-Null

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

$BuildSource = Join-Path $BackendRoot "dist\$AppName"
$ReleaseApp = Join-Path $ReleasesRoot $AppName
$ExeZip = Join-Path $ReleasesRoot "$AppName-exe.zip"
$VersionFile = Join-Path $ReleasesRoot "VERSION.txt"

Copy-Item -LiteralPath $BuildSource -Destination $ReleaseApp -Recurse

$ReadmePath = Join-Path $ReleaseApp "README_RUN.txt"
@"
FOSIM.exe Run Guide

FOSIM = Fastening Optimization & Simulation Manager
Version: $Version

1. Extract the whole zip file to a folder.
2. Run FOSIM.exe.
3. The browser opens automatically.
4. Close the console window to stop the app.

Notes:
- This MVP uses CSV/sample data only.
- Actual SH-2 communication and device write are not included.
- If Windows shows a security warning, choose More info, then Run anyway.
"@ | Set-Content -Path $ReadmePath -Encoding UTF8

Compress-Archive -Path $ReleaseApp -DestinationPath $ExeZip -Force

@"
$AppName
Version: $Version
Format: YYYYMMDD_HHmmss
Build source: $BuildSource
Package: $ExeZip
Created: $($Now.ToString("yyyy-MM-dd HH:mm:ss"))
"@ | Set-Content -Path $VersionFile -Encoding UTF8

Write-Host "Created $ExeZip (version $Version)"
