$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $ProjectRoot "frontend")

if (-not (Test-Path "node_modules")) {
  npm.cmd install
}

npm.cmd run dev
