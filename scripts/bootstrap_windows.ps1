# Bootstrap script for Windows development environment

$ErrorActionPreference = "Stop"

Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Sansible Windows Bootstrap" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectDir = Split-Path -Parent $ScriptDir

Set-Location $ProjectDir

# Check Python version
$PythonVersion = (python --version 2>&1) -replace 'Python ', ''
$VersionParts = $PythonVersion.Split('.')
$Major = [int]$VersionParts[0]
$Minor = [int]$VersionParts[1]

Write-Host "Python version: $PythonVersion"

if ($Major -lt 3 -or ($Major -eq 3 -and $Minor -lt 9)) {
    Write-Host "ERROR: Python 3.9+ required" -ForegroundColor Red
    exit 1
}

# Create virtual environment
if (-not (Test-Path ".venv")) {
    Write-Host ""
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

# Activate virtual environment
Write-Host ""
Write-Host "Activating virtual environment..."
& .\.venv\Scripts\Activate.ps1

# Upgrade pip
Write-Host ""
Write-Host "Upgrading pip..."
pip install --upgrade pip wheel

# Install package in development mode
Write-Host ""
Write-Host "Installing sansible in development mode..."
pip install -e ".[dev]"

# Install build tools
Write-Host ""
Write-Host "Installing build tools..."
pip install build

# Build wheel
Write-Host ""
Write-Host "Building wheel..."
python -m build --wheel

# Run dep audit
Write-Host ""
Write-Host "Running pure Python audit..."
try {
    python -m tools.dep_audit
} catch {
    Write-Host "WARNING: Dependency audit failed!" -ForegroundColor Yellow
}

# Run smoke tests
Write-Host ""
Write-Host "Running smoke tests..."
python -m tools.windows_smoke

# Check SSH availability
Write-Host ""
Write-Host "Checking SSH client..."
$SshPath = Get-Command ssh -ErrorAction SilentlyContinue
if ($SshPath) {
    Write-Host "  ✓ SSH client available: $($SshPath.Source)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ SSH client not found" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To install OpenSSH Client (as Administrator):" -ForegroundColor Yellow
    Write-Host "  Add-WindowsCapability -Online -Name OpenSSH.Client~~~~0.0.1.0"
}

Write-Host ""
Write-Host "==================================" -ForegroundColor Cyan
Write-Host "Bootstrap complete!" -ForegroundColor Cyan
Write-Host "==================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "To activate the environment:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host ""
Write-Host "To run sansible:"
Write-Host "  sansible --version"
Write-Host ""
