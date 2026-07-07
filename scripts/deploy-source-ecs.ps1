# Pack source for ECS docker build (no local Docker required)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Deploy = Join-Path $Root "deploy"
$Tar = Join-Path $Deploy "source.tar"
Set-Location $Root

Write-Host ">>> tar source.tar" -ForegroundColor Cyan
if (Test-Path $Tar) { Remove-Item $Tar -Force }
tar -cf $Tar `
  --exclude=node_modules `
  --exclude=.venv `
  --exclude=runtime `
  --exclude=apps/web/node_modules `
  --exclude=apps/web/dist `
  --exclude=apps/web/android `
  --exclude=*.tar `
  --exclude=.git `
  --exclude=__pycache__ `
  .

$mb = [math]::Round((Get-Item $Tar).Length / 1MB, 1)
Write-Host "OK: $Tar ${mb}MB" -ForegroundColor Green
