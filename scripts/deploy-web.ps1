# 构建 Web 前端并打包为 web-dist.tar（上传 ECS 用）
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Web = Join-Path $Root "apps\web"
$Deploy = Join-Path $Root "deploy"
Set-Location $Web

Write-Host ">>> npm run build (同域 /api，无需 VITE_API_BASE)" -ForegroundColor Cyan
npm run build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$dist = Join-Path $Web "dist"
$tar = Join-Path $Deploy "web-dist.tar"
$staging = Join-Path $env:TEMP "sheldon-web-dist"

if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging | Out-Null
Copy-Item -Path (Join-Path $dist "*") -Destination $staging -Recurse

if (Test-Path $tar) { Remove-Item $tar -Force }
Set-Location $staging
tar -cf $tar .
Set-Location $Root

$mb = [math]::Round((Get-Item $tar).Length / 1MB, 1)
Write-Host ("[完成] {0} ({1} MB)" -f $tar, $mb) -ForegroundColor Green
Write-Host "上传到 ECS /opt/sheldon-agent/:" -ForegroundColor Yellow
Write-Host "  - web-dist.tar"
Write-Host "  - nginx-sheldon.conf"
Write-Host "  - setup-nginx.sh"
Write-Host "ECS 执行: sed -i 's/\r$//' setup-nginx.sh && chmod +x setup-nginx.sh && ./setup-nginx.sh"
