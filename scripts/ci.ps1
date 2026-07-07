# Sheldon Agent CI：pytest + Web build（本地或流水线均可运行）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host ">>> [1/3] pytest" -ForegroundColor Cyan
uv run pytest tests/ -q --ignore=tests/test_docker_health.py
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ">>> [2/3] Web build" -ForegroundColor Cyan
Push-Location apps/web
npm run build
if ($LASTEXITCODE -ne 0) { Pop-Location; exit $LASTEXITCODE }
Pop-Location

Write-Host ">>> [3/3] Docker health（可选，需 Docker）" -ForegroundColor Cyan
if (Get-Command docker -ErrorAction SilentlyContinue) {
    uv run pytest tests/test_docker_health.py -v
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} else {
    Write-Host "    跳过：未检测到 docker" -ForegroundColor Yellow
}

Write-Host "[CI 通过]" -ForegroundColor Green
