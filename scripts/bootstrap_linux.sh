#!/bin/bash
# Bootstrap script for Linux development environment

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=================================="
echo "Sansible Linux Bootstrap"
echo "=================================="
echo ""

cd "$PROJECT_DIR"

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)

echo "Python version: $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 9 ]); then
    echo "ERROR: Python 3.9+ required"
    exit 1
fi

# Create virtual environment
if [ ! -d ".venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source .venv/bin/activate

# Upgrade pip
echo ""
echo "Upgrading pip..."
pip install --upgrade pip wheel

# Install package in development mode
echo ""
echo "Installing sansible in development mode..."
pip install -e ".[dev]"

# Install build tools
echo ""
echo "Installing build tools..."
pip install build

# Build wheel
echo ""
echo "Building wheel..."
python -m build --wheel

# Run dep audit
echo ""
echo "Running pure Python audit..."
python -m tools.dep_audit || {
    echo "WARNING: Dependency audit failed!"
}

# Run smoke tests
echo ""
echo "Running smoke tests..."
python -m tools.linux_smoke

# Check SSH availability
echo ""
echo "Checking SSH client..."
if command -v ssh &> /dev/null; then
    echo "  ✓ SSH client available: $(which ssh)"
else
    echo "  ⚠ SSH client not found (needed for SSH transport)"
fi

echo ""
echo "=================================="
echo "Bootstrap complete!"
echo "=================================="
echo ""
echo "To activate the environment:"
echo "  source .venv/bin/activate"
echo ""
echo "To run sansible:"
echo "  sansible --version"
echo ""
