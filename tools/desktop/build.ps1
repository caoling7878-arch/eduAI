# Build Windows install.exe for eduAI desktop (includes admin SPA + Embedding fixes).
# Prerequisites: Windows x64, Python 3.10+, Node.js 18+
#   powershell -ExecutionPolicy Bypass -File tools\desktop\build.ps1

$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

Write-Host "==> Building Windows installer from $Root"

function Need-Cmd($name) {
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
    throw "Missing command: $name"
  }
}

Need-Cmd npm
Need-Cmd python

Write-Host "==> Frontend deps"
npm install --prefix apps/web
npm install --prefix apps/admin

Write-Host "==> Build student web"
Push-Location apps/web
npx vite build
if ($LASTEXITCODE -ne 0) { throw "web vite build failed" }
Pop-Location

Write-Host "==> Build admin (base=/admin/)"
Push-Location apps/admin
$env:EDUAI_ADMIN_BASE = "/admin/"
npx vite build
if ($LASTEXITCODE -ne 0) { throw "admin vite build failed" }
Pop-Location

$SpaWeb = Join-Path $Root "apps\api\app\spa\web"
$SpaAdmin = Join-Path $Root "apps\api\app\spa\admin"
Remove-Item -Recurse -Force $SpaWeb, $SpaAdmin -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $SpaWeb, $SpaAdmin | Out-Null
Copy-Item -Recurse (Join-Path $Root "apps\web\dist\*") $SpaWeb
Copy-Item -Recurse (Join-Path $Root "apps\admin\dist\*") $SpaAdmin

$AdminIndex = Join-Path $SpaAdmin "index.html"
if (-not (Test-Path $AdminIndex)) { throw "missing admin spa index.html" }
$AdminHtml = Get-Content -Raw $AdminIndex
if ($AdminHtml -notmatch '/admin/assets/') {
  throw "admin was not built with base=/admin/ — packaged admin console would 404"
}

$Venv = Join-Path $Root "apps\api\.venv-desktop"
$Py = Join-Path $Venv "Scripts\python.exe"
$PyInstaller = Join-Path $Venv "Scripts\pyinstaller.exe"
if (-not (Test-Path $Py)) {
  python -m venv $Venv
}
& $Py -m pip install -q -U pip wheel
& $Py -m pip install -q -r (Join-Path $Root "apps\api\requirements.txt") "pyinstaller>=6.0"

Write-Host "==> PyInstaller (clean, includes spa_serve + embedding config)"
Push-Location (Join-Path $Root "apps\api")
& $PyInstaller --noconfirm --clean (Join-Path $Root "desktop\eduai-server.spec")
if ($LASTEXITCODE -ne 0) { throw "pyinstaller failed" }
Pop-Location

$ServerOut = Join-Path $Root "desktop\resources\server"
Remove-Item -Recurse -Force $ServerOut -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $ServerOut | Out-Null
Copy-Item -Recurse (Join-Path $Root "apps\api\dist\eduai-server\*") $ServerOut

$ServerExe = Join-Path $ServerOut "eduai-server.exe"
if (-not (Test-Path $ServerExe)) {
  throw "eduai-server.exe missing under desktop\resources\server"
}

Write-Host "==> Electron NSIS -> install.exe"
npm install --prefix desktop
npm run dist:win --prefix desktop
if ($LASTEXITCODE -ne 0) { throw "electron-builder failed" }

$Installer = Join-Path $Root "desktop\dist\install.exe"
if (Test-Path $Installer) {
  Write-Host "✓ Windows installer ready (admin /admin + Embedding fixes included):"
  Get-Item $Installer | Format-List FullName, Length, LastWriteTime
} else {
  Get-ChildItem (Join-Path $Root "desktop\dist") | Format-Table Name, Length
  throw "install.exe not found"
}
