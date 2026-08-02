$ErrorActionPreference = "Stop"

# $ErrorActionPreference = "Stop"는 네이티브 실행 파일의 0이 아닌 종료 코드를 잡지 못한다.
# 예를 들어 npm run build가 TypeScript 오류로 실패해도 스크립트는 계속 진행하고,
# frontend/dist에는 이전 빌드 결과물이 그대로 남는다. 각 네이티브 명령 뒤에는
# 반드시 이 함수로 $LASTEXITCODE를 확인해서 실패를 명시적으로 막는다.
function Invoke-Step {
    param(
        [Parameter(Mandatory)] [string] $Name,
        [Parameter(Mandatory)] [scriptblock] $Command
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "Build step failed: $Name (exit code $LASTEXITCODE)"
    }
}

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendRoot = Join-Path $ProjectRoot "frontend"
$BackendRoot = Join-Path $ProjectRoot "backend"
$ReleasesRoot = Join-Path $ProjectRoot "releases"
$AppName = "FOSIM"

# 빌드 시각은 여기서 한 번만 잡는다. VERSION.txt와 프론트엔드 번들이 같은 값을 쓴다.
# Vite가 설정을 로드할 때 이 환경 변수를 한 번만 읽으므로, 프론트엔드 빌드보다 반드시 앞서야 한다.
$Now = Get-Date
$Version = $Now.ToString("yyyyMMdd_HHmmss")
$env:FOSIM_BUILD_ISO = $Now.ToString("yyyy-MM-ddTHH:mm:ss.fffK")

Set-Location $FrontendRoot
Invoke-Step "npm install" { npm.cmd install }
Invoke-Step "npm test" { npm.cmd test }
Invoke-Step "npm run build" { npm.cmd run build }

Set-Location $BackendRoot
Invoke-Step "pytest" { python -m pytest -q }

$DistPath = Join-Path $ProjectRoot "frontend\dist"
$SamplePath = Join-Path $ProjectRoot "sample-data"
$DocsPath = Join-Path $ProjectRoot "docs"

if (Test-Path "dist") { Remove-Item -LiteralPath "dist" -Recurse -Force }
if (Test-Path "build") { Remove-Item -LiteralPath "build" -Recurse -Force }

Invoke-Step "PyInstaller" {
    python -m PyInstaller `
      --noconfirm `
      --clean `
      --name $AppName `
      --add-data "$DistPath;frontend/dist" `
      --add-data "$SamplePath;sample-data" `
      --add-data "$DocsPath;docs" `
      desktop_launcher.py
}

$BuildSource = Join-Path $BackendRoot "dist\$AppName"
$ReleaseApp = Join-Path $ReleasesRoot $AppName
$ExeZip = Join-Path $ReleasesRoot "$AppName-exe.zip"
$VersionFile = Join-Path $ReleasesRoot "VERSION.txt"

# 빌드가 실제로 결과물을 만들어낸 뒤에만 releases/를 비운다. 그 전에 지우면 npm/pytest
# 실패 시 어제 결과물마저 사라진 빈 폴더만 남는다. 성공한 빌드 뒤에는 releases/에
# 이 세 가지 고정된 이름의 결과물만 남는다는 보장은 그대로 유지된다.
if (Test-Path $ReleasesRoot) { Remove-Item -LiteralPath $ReleasesRoot -Recurse -Force }
New-Item -ItemType Directory -Path $ReleasesRoot | Out-Null

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
