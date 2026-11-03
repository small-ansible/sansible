# Runs on the Windows host (copied there by scripts/test-windows.sh): installs the wheel into a
# fresh venv per Python version and runs the test suite, including winlocal and PSRP to localhost.
param(
    [Parameter(Mandatory)][string]$Wheel,
    [string]$Pythons = "3.13,3.14"  # comma-separated; a plain string survives ssh + powershell quoting
)
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here
$env:PYTHONUTF8 = "1"

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) { throw "uv is required on the Windows host (https://docs.astral.sh/uv/)" }

$collections = Join-Path $here "collections"
$failed = @()
foreach ($py in $Pythons.Split(",")) {
    Write-Host "`n== Python $py" -ForegroundColor Cyan
    $venv = Join-Path $here "venv-$py"
    if (Test-Path $venv) { Remove-Item -Recurse -Force $venv }
    & uv venv -q --python $py $venv
    if ($LASTEXITCODE) { throw "uv venv failed for $py" }
    $env:VIRTUAL_ENV = $venv
    & uv pip install -q (Join-Path $here $Wheel) pytest pexpect
    if ($LASTEXITCODE) { throw "install failed for $py" }
    $bin = Join-Path $venv "Scripts"

    if (-not (Test-Path (Join-Path $collections "ansible_collections\ansible\windows"))) {
        & (Join-Path $bin "ansible-galaxy.exe") collection install ansible.windows -p $collections
    }
    $env:SANSIBLE_TEST_COLLECTIONS_PATH = $collections
    # PSRP to this machine with the current logon's credentials (Negotiate/SSPI, no password)
    if (-not $env:SANSIBLE_TEST_PSRP_HOST) { $env:SANSIBLE_TEST_PSRP_HOST = "localhost" }

    & (Join-Path $bin "sansible.exe") doctor
    if ($LASTEXITCODE) { $failed += "$py doctor" }
    Push-Location (Join-Path $here "tests")
    & (Join-Path $bin "python.exe") -m pytest -v -rs -p no:cacheprovider
    if ($LASTEXITCODE) { $failed += "$py tests" }
    Pop-Location
}

if ($failed) { Write-Host "`nFAILED: $($failed -join ', ')" -ForegroundColor Red; exit 1 }
Write-Host "`nAll Windows checks passed" -ForegroundColor Green
