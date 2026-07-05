# 本机构建 Docker 镜像并导出 tar（上传 ECS 用）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host ">>> [1/3] uv lock" -ForegroundColor Cyan
uv lock
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ">>> [2/3] docker build" -ForegroundColor Cyan
docker build -f deploy/Dockerfile -t sheldon-agent:1.0.0 .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ">>> [3/3] docker save" -ForegroundColor Cyan
$tar = Join-Path $Root "sheldon-agent.tar"
if (Test-Path $tar) { Remove-Item $tar -Force }
docker save -o $tar sheldon-agent:1.0.0
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$mb = [math]::Round((Get-Item $tar).Length / 1MB, 1)
Write-Host "[完成] $tar ($mb MB)" -ForegroundColor Green
Write-Host "下一步: Workbench 上传到 ECS /opt/sheldon-agent/ 后执行 deploy/ecs-run.sh" -ForegroundColor Yellow
