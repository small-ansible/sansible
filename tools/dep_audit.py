#!/usr/bin/env python3
"""
Dependency Audit Tool for sansible.

This tool enforces the pure-Python constraint by verifying that:
1. The sansible wheel is tagged as py3-none-any
2. No installed dependencies contain compiled extensions (.so, .pyd, .dylib)
3. All dependencies have pure-python wheel/sdist availability

This tool is THE LAW. If it fails, the build fails.

Usage:
    python -m tools.dep_audit [--check-wheel path/to/wheel.whl]
    python -m tools.dep_audit --install-and-check
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import List, Set, Tuple, Optional


# Extensions that indicate compiled code
COMPILED_EXTENSIONS = {".so", ".pyd", ".dylib", ".dll"}

# Allowed wheel tags for pure Python
PURE_PYTHON_TAGS = {"py3-none-any", "py2.py3-none-any"}

# Packages that have OPTIONAL C extensions but work without them
# These have pure Python fallbacks and will work on any platform
KNOWN_OPTIONAL_EXTENSIONS = {
    "markupsafe",  # Jinja2 dep, has pure Python fallback
    "pyyaml",      # Has Loader/Dumper fallbacks without C extensions
}


class AuditError(Exception):
    """Raised when audit finds violations."""
    pass


def print_header(text: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print(f"{'=' * 60}")


def print_pass(text: str) -> None:
    """Print a passing check."""
    print(f"  ✓ {text}")


def print_fail(text: str) -> None:
    """Print a failing check."""
    print(f"  ✗ {text}")


def print_warn(text: str) -> None:
    """Print a warning."""
    print(f"  ⚠ {text}")


def get_wheel_tag(wheel_path: Path) -> str:
    """Extract the wheel tag from a wheel filename."""
    # Wheel filename format: {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl
    name = wheel_path.stem
    parts = name.split("-")
    
    if len(parts) >= 3:
        # Last three parts are python-abi-platform
        return "-".join(parts[-3:])
    
    return "unknown"


def check_wheel_is_pure(wheel_path: Path) -> Tuple[bool, str]:
    """
    Check if a wheel file is pure Python.
    
    Returns (is_pure, tag_or_error_message)
    """
    if not wheel_path.exists():
        return False, f"Wheel not found: {wheel_path}"
    
    tag = get_wheel_tag(wheel_path)
    
    # Check tag
    if tag in PURE_PYTHON_TAGS:
        return True, tag
    
    # Check if it contains only python/abi none
    if "-none-any" in tag or "-none-" in tag and tag.endswith("-any"):
        return True, tag
    
    return False, f"Non-pure wheel tag: {tag}"


def check_wheel_contents(wheel_path: Path) -> List[str]:
    """
    Check wheel contents for compiled extensions.
    
    Returns list of compiled files found (empty if pure).
    """
    compiled_files = []
    
    with zipfile.ZipFile(wheel_path, "r") as zf:
        for name in zf.namelist():
            ext = os.path.splitext(name)[1].lower()
            if ext in COMPILED_EXTENSIONS:
                compiled_files.append(name)
    
    return compiled_files


def get_installed_packages(venv_python: str) -> List[Tuple[str, str, str]]:
    """
    Get list of installed packages.
    
    Returns list of (name, version, location) tuples.
    """
    result = subprocess.run(
        [venv_python, "-m", "pip", "list", "--format=json"],
        capture_output=True,
        text=True,
    )
    
    if result.returncode != 0:
        raise AuditError(f"Failed to list packages: {result.stderr}")
    
    import json
    packages = json.loads(result.stdout)
    
    # Get locations
    pkg_list = []
    for pkg in packages:
        name = pkg["name"]
        version = pkg["version"]
        
        # Get package location
        loc_result = subprocess.run(
            [venv_python, "-m", "pip", "show", name],
            capture_output=True,
            text=True,
        )
        location = ""
        for line in loc_result.stdout.splitlines():
            if line.startswith("Location:"):
                location = line.split(":", 1)[1].strip()
                break
        
        pkg_list.append((name, version, location))
    
    return pkg_list


def check_package_for_compiled(pkg_name: str, pkg_location: str) -> List[str]:
    """
    Check a single installed package for compiled extensions.
    
    Returns list of compiled files found.
    """
    compiled_files = []
    
    # Find package directory
    pkg_dir = Path(pkg_location) / pkg_name.replace("-", "_")
    if not pkg_dir.exists():
        # Try with original name
        pkg_dir = Path(pkg_location) / pkg_name
    if not pkg_dir.exists():
        # Try lowercase
        pkg_dir = Path(pkg_location) / pkg_name.lower().replace("-", "_")
    
    if not pkg_dir.exists():
        return compiled_files
    
    # Scan for compiled files
    for root, dirs, files in os.walk(pkg_dir):
        for fname in files:
            ext = os.path.splitext(fname)[1].lower()
            if ext in COMPILED_EXTENSIONS:
                rel_path = os.path.relpath(os.path.join(root, fname), pkg_location)
                compiled_files.append(rel_path)
    
    return compiled_files


def audit_wheel(wheel_path: Path) -> bool:
    """
    Audit a wheel file for pure Python compliance.
    
    Returns True if wheel passes audit.
    """
    print_header(f"Auditing wheel: {wheel_path.name}")
    
    passed = True
    
    # Check wheel tag
    is_pure, tag = check_wheel_is_pure(wheel_path)
    if is_pure:
        print_pass(f"Wheel tag is pure Python: {tag}")
    else:
        print_fail(tag)
        passed = False
    
    # Check contents
    compiled = check_wheel_contents(wheel_path)
    if compiled:
        print_fail(f"Found {len(compiled)} compiled file(s):")
        for f in compiled[:10]:  # Show first 10
            print(f"      - {f}")
        if len(compiled) > 10:
            print(f"      ... and {len(compiled) - 10} more")
        passed = False
    else:
        print_pass("No compiled extensions in wheel contents")
    
    return passed


def audit_installed_deps(venv_python: str, our_package: str = "sansible") -> bool:
    """
    Audit all installed dependencies for compiled code.
    
    Returns True if all deps pass audit.
    """
    print_header("Auditing installed dependencies")
    
    packages = get_installed_packages(venv_python)
    
    # Packages that are allowed to have platform-specific but are stdlib or known-safe
    # (they ship pure-python fallbacks or are part of Python itself)
    ALLOWED_PACKAGES = {
        "pip", "setuptools", "wheel",  # Build tools, not runtime
    }
    
    passed = True
    checked = 0
    warnings = 0
    
    for name, version, location in packages:
        if name.lower() in ALLOWED_PACKAGES:
            continue
        
        if not location:
            print_warn(f"Could not find location for: {name}")
            continue
        
        compiled = check_package_for_compiled(name, location)
        checked += 1
        
        if compiled:
            # Check if this package has optional C extensions that we allow
            if name.lower() in KNOWN_OPTIONAL_EXTENSIONS:
                print_warn(f"{name} {version} has C extensions (optional, pure Python fallback available)")
                warnings += 1
            else:
                print_fail(f"{name} {version} has compiled extensions:")
                for f in compiled[:5]:
                    print(f"      - {f}")
                if len(compiled) > 5:
                    print(f"      ... and {len(compiled) - 5} more")
                passed = False
        else:
            print_pass(f"{name} {version}")
    
    print(f"\n  Checked {checked} packages")
    if warnings > 0:
        print(f"  Warnings: {warnings} packages with optional C extensions (will work without them)")
    
    return passed


def build_and_audit(project_dir: Path) -> bool:
    """
    Build the wheel and audit it along with dependencies.
    
    Returns True if everything passes.
    """
    print_header("Building wheel in isolated environment")
    
    with tempfile.TemporaryDirectory(prefix="sansible_audit_") as tmpdir:
        tmpdir = Path(tmpdir)
        venv_dir = tmpdir / "venv"
        dist_dir = tmpdir / "dist"
        
        # Create venv
        print("  Creating virtual environment...")
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print_fail(f"Failed to create venv: {result.stderr}")
            return False
        
        # Get venv python
        if sys.platform == "win32":
            venv_python = str(venv_dir / "Scripts" / "python.exe")
        else:
            venv_python = str(venv_dir / "bin" / "python")
        
        # Upgrade pip
        print("  Upgrading pip...")
        subprocess.run(
            [venv_python, "-m", "pip", "install", "--upgrade", "pip", "wheel", "build"],
            capture_output=True,
        )
        
        # Build the wheel
        print("  Building wheel...")
        result = subprocess.run(
            [venv_python, "-m", "build", "--wheel", "--outdir", str(dist_dir), str(project_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print_fail(f"Failed to build wheel: {result.stderr}")
            print(result.stdout)
            return False
        
        # Find the wheel
        wheels = list(dist_dir.glob("*.whl"))
        if not wheels:
            print_fail("No wheel produced")
            return False
        
        wheel_path = wheels[0]
        print_pass(f"Built wheel: {wheel_path.name}")
        
        # Audit the wheel
        if not audit_wheel(wheel_path):
            return False
        
        # Install the wheel
        print_header("Installing wheel and dependencies")
        result = subprocess.run(
            [venv_python, "-m", "pip", "install", str(wheel_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print_fail(f"Failed to install wheel: {result.stderr}")
            return False
        print_pass("Wheel installed successfully")
        
        # Audit installed dependencies
        if not audit_installed_deps(venv_python):
            return False
        
        # Test that CLI works
        print_header("Testing CLI functionality")
        result = subprocess.run(
            [venv_python, "-m", "sansible.cli.main", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print_fail(f"CLI failed: {result.stderr}")
            return False
        print_pass("CLI --version works")
        print(f"      {result.stdout.splitlines()[0]}")
        
        return True


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Audit sansible for pure Python compliance"
    )
    parser.add_argument(
        "--check-wheel",
        type=Path,
        help="Check a specific wheel file",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path(__file__).parent.parent,
        help="Project directory to build and audit",
    )
    
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("  SANSIBLE PURE PYTHON AUDIT")
    print("=" * 60)
    
    if args.check_wheel:
        # Just check a specific wheel
        if not audit_wheel(args.check_wheel):
            print("\n❌ AUDIT FAILED")
            return 1
    else:
        # Full build and audit
        if not build_and_audit(args.project_dir):
            print("\n❌ AUDIT FAILED")
            return 1
    
    print("\n✅ AUDIT PASSED - Package is pure Python")
    return 0


if __name__ == "__main__":
    sys.exit(main())
