# Sheldon Agent Android APK build
# Output: apps/web/android/app/build/outputs/apk/debug/app-debug.apk
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Web = Join-Path $Root "apps\web"
$Android = Join-Path $Web "android"
$OutApk = Join-Path $Android "app\build\outputs\apk\debug\app-debug.apk"
$DeployApk = Join-Path $Root "deploy\sheldon-agent-debug.apk"

Set-Location $Web

Write-Host ">>> npm run build:android (API -> ECS)" -ForegroundColor Cyan
npm run build:android
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ">>> cap sync android" -ForegroundColor Cyan
npx cap sync android
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $env:ANDROID_HOME -or -not (Test-Path $env:ANDROID_HOME)) {
    if (Test-Path "D:\Android\SDK") {
        $env:ANDROID_HOME = "D:\Android\SDK"
    } elseif (Test-Path "$env:LOCALAPPDATA\Android\Sdk") {
        $env:ANDROID_HOME = "$env:LOCALAPPDATA\Android\Sdk"
    }
}
if (-not $env:ANDROID_HOME -or -not (Test-Path $env:ANDROID_HOME)) {
    Write-Host "Android SDK not found. Set ANDROID_HOME or install SDK to D:\Android\SDK" -ForegroundColor Red
    exit 1
}
$sdkDir = $env:ANDROID_HOME -replace '\\', '/'
Set-Content -Path (Join-Path $Android "local.properties") -Value "sdk.dir=$sdkDir" -Encoding ASCII
Write-Host ">>> ANDROID_HOME=$env:ANDROID_HOME" -ForegroundColor DarkGray

Set-Location $Android
Write-Host ">>> gradlew assembleDebug" -ForegroundColor Cyan
.\gradlew.bat assembleDebug
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not (Test-Path $OutApk)) {
    Write-Host "APK not found: $OutApk" -ForegroundColor Red
    exit 1
}

$deployDir = Split-Path $DeployApk -Parent
if (-not (Test-Path $deployDir)) { New-Item -ItemType Directory -Path $deployDir | Out-Null }
Copy-Item $OutApk $DeployApk -Force
$sizeMb = [math]::Round((Get-Item $DeployApk).Length / 1MB, 1)
Write-Host ('[OK] {0} ({1} megabytes)' -f $DeployApk, $sizeMb) -ForegroundColor Green
Write-Host 'Share deploy\sheldon-agent-debug.apk with testers (enable unknown sources on phone).' -ForegroundColor Yellow
