$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location -Path $PSScriptRoot

function Fail([string]$msg) {
  Write-Host "`nERROR: $msg`n" -ForegroundColor Red
  exit 1
}

function Remove-IfExists([string]$p) {
  if (Test-Path $p) { Remove-Item -Recurse -Force $p }
}

# ---- CONFIG ----
$AppName = "LineForge_DEV"
$Entry   = ".\main.py"

$StrictCompliance = $true
$LicensesFolderName = "Licenses"
# -----------------

Write-Host "`n== LineForge DEV build ==" -ForegroundColor Cyan
Write-Host "Project root: $PSScriptRoot`n"

if (-not (Test-Path $Entry)) { Fail "Entrypoint not found: $Entry" }

$Root = $PSScriptRoot

$PotracePath = Join-Path $Root "bin\potrace.exe"
$NoticePath  = Join-Path $Root "NOTICE.txt"
$LicensesDir = Join-Path $Root $LicensesFolderName

if (-not (Test-Path $PotracePath)) { Fail "Missing required file: $PotracePath" }

if ($StrictCompliance) {
  if (-not (Test-Path $NoticePath))  { Fail "Missing required file: $NoticePath" }
  if (-not (Test-Path $LicensesDir)) { Fail "Missing required folder: $LicensesDir" }
} else {
  if (-not (Test-Path $NoticePath))  { Write-Host "NOTE: NOTICE.txt not found (will not bundle)." -ForegroundColor Yellow }
  if (-not (Test-Path $LicensesDir)) { Write-Host "NOTE: $LicensesFolderName folder not found (will not bundle)." -ForegroundColor Yellow }
}

$PotraceAbs = (Resolve-Path $PotracePath).Path
$NoticeAbs  = $null
$LicensesAbs = $null
if (Test-Path $NoticePath)  { $NoticeAbs = (Resolve-Path $NoticePath).Path }
if (Test-Path $LicensesDir) { $LicensesAbs = (Resolve-Path $LicensesDir).Path }

Write-Host "Entrypoint: $Entry"
Write-Host "Bundling:  $PotraceAbs"
if ($NoticeAbs)   { Write-Host "Bundling:  $NoticeAbs" }
if ($LicensesAbs) { Write-Host "Bundling:  $LicensesAbs" }
Write-Host ""

Write-Host "Cleaning old DEV build artifacts..." -ForegroundColor Cyan
Remove-IfExists ".\build_dev"
Remove-IfExists ".\dist_dev"
Remove-IfExists ".\$AppName.spec"

Write-Host "`nUpgrading pip + installing build deps..." -ForegroundColor Cyan
python -m pip install --upgrade pip | Out-Host
python -m pip install --upgrade pyinstaller | Out-Host
if (Test-Path ".\requirements.txt") { python -m pip install -r requirements.txt | Out-Host }

$Args = @(
  "-m","PyInstaller",
  "--noconfirm",
  "--onedir",
  "--console",
  "--name",$AppName,
  "--distpath",".\dist_dev",
  "--workpath",".\build_dev",
  "--specpath",".\build_dev",
  "--log-level","WARN"
)

$Args += @("--add-binary", "$PotraceAbs;bin")
if ($NoticeAbs)   { $Args += @("--add-data", "$NoticeAbs;.") }
if ($LicensesAbs) { $Args += @("--add-data", "$LicensesAbs;$LicensesFolderName") }

$Args += $Entry

Write-Host "`nRunning PyInstaller (DEV)..." -ForegroundColor Cyan
python @Args | Out-Host

$Exe = ".\dist_dev\$AppName\$AppName.exe"
if (-not (Test-Path $Exe)) { Fail "DEV build finished but exe not found: $Exe" }

Write-Host "`nDEV Built: $Exe" -ForegroundColor Green
