# Offline setup of the RCGP environment on Windows x64.
# Usage (from the offline-RCGP folder):
#   powershell -ExecutionPolicy Bypass -File .\scripts\install_offline.ps1
# Needs: python\python-3.10.11-amd64.exe (or an installed Python 3.10),
#        wheels\*.whl including tensorflow_intel-2.13.0 (see README).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$tf = Get-ChildItem -Path "$Root\wheels" -Filter "tensorflow_intel-2.13.0-*.whl" -ErrorAction SilentlyContinue
if (-not $tf) {
    Write-Error "wheels\tensorflow_intel-2.13.0-cp310-cp310-win_amd64.whl is missing. Download it once with: python scripts\fetch_url_files.py offline-RCGP\wheels"
}

# VC++ 2015-2022 x64 runtime (TensorFlow needs it)
$vc = Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" -ErrorAction SilentlyContinue
if (-not ($vc -and $vc.Installed -eq 1)) {
    $redist = "$Root\python\vc_redist.x64.exe"
    if (Test-Path $redist) {
        Write-Host "Installing VC++ runtime ..."
        Start-Process -FilePath $redist -ArgumentList "/install", "/quiet", "/norestart" -Wait
    } else {
        Write-Warning "VC++ x64 runtime not found. Get python\vc_redist.x64.exe via its .url file and run it once."
    }
}

# Python 3.10.11 (per-user install into python\py310, no PATH change)
$py = "$Root\python\py310\python.exe"
if (-not (Test-Path $py)) {
    $installer = "$Root\python\python-3.10.11-amd64.exe"
    if (-not (Test-Path $installer)) { Write-Error "Missing $installer" }
    Write-Host "Installing Python 3.10.11 into $Root\python\py310 ..."
    $instArgs = @("/quiet", "InstallAllUsers=0", "TargetDir=`"$Root\python\py310`"", "PrependPath=0",
                  "Include_launcher=0", "Include_test=0", "Include_doc=0", "Shortcuts=0", "AssociateFiles=0")
    Start-Process -FilePath $installer -ArgumentList $instArgs -Wait
    if (-not (Test-Path $py)) { Write-Error "Python install failed: $py not found" }
}
& $py --version

# Virtual environment and wheels (no index, hashes enforced)
if (-not (Test-Path "$Root\.venv\Scripts\python.exe")) { & $py -m venv "$Root\.venv" }
$vpy = "$Root\.venv\Scripts\python.exe"
& $vpy -m pip install --no-index --find-links "$Root\wheels" --require-hashes -r "$Root\requirements\freeze-py310.txt"
if ($LASTEXITCODE -ne 0) { Write-Error "pip install failed" }

& $vpy "$Root\scripts\prepare_data.py"
& $vpy "$Root\scripts\test_offline.py"
Write-Host "Done. Activate with: $Root\.venv\Scripts\Activate.ps1"
