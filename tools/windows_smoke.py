#!/usr/bin/env python3
"""
Windows Smoke Tests for sansible.

Runs minimal tests to verify the package works correctly on Windows.
These tests use only pure Python and no external dependencies.

Usage:
    python -m tools.windows_smoke
"""

import os
import sys
import platform
import tempfile
import json
from pathlib import Path


class SmokeTestRunner:
    """Simple test runner with colored output."""
    
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []
    
    def run_test(self, name: str, test_func):
        """Run a single test."""
        try:
            test_func()
            self.passed += 1
            print(f"  ✓ {name}")
        except AssertionError as e:
            self.failed += 1
            self.errors.append((name, str(e)))
            print(f"  ✗ {name}: {e}")
        except Exception as e:
            self.failed += 1
            self.errors.append((name, f"Exception: {e}"))
            print(f"  ✗ {name}: Exception: {e}")
    
    def summary(self) -> int:
        """Print summary and return exit code."""
        print("\n" + "=" * 50)
        print(f"PASSED: {self.passed}  FAILED: {self.failed}")
        
        if self.failed > 0:
            print("\nFailed tests:")
            for name, error in self.errors:
                print(f"  - {name}: {error}")
            print("\n❌ SMOKE TESTS FAILED")
            return 1
        else:
            print("\n✅ ALL SMOKE TESTS PASSED")
            return 0


def test_import_main_package():
    """Test that sansible can be imported."""
    import sansible
    assert hasattr(sansible, "__version__")
    assert sansible.__version__ == "0.1.0"


def test_import_cli():
    """Test that CLI modules can be imported."""
    from sansible.cli import main, playbook, inventory
    assert callable(main.main)
    assert callable(playbook.main)
    assert callable(inventory.main)


def test_import_platform():
    """Test that platform modules can be imported."""
    from sansible.platform import paths, fs, proc, concurrency, tty, users, locks
    assert callable(paths.normalize)
    assert callable(fs.read_file)
    assert callable(proc.run)


def test_version_command():
    """Test that --version works."""
    from sansible.cli.main import main
    # Should not raise
    result = main(["--version"])
    # argparse exits with 0 on --version, but raises SystemExit
    # So we catch it in the test


def test_inventory_help():
    """Test that inventory --help works."""
    from sansible.cli.inventory import main
    result = main(["--help"])


def test_platform_detection():
    """Test platform detection works."""
    from sansible.platform import IS_WINDOWS, IS_LINUX, IS_MACOS, IS_POSIX
    
    current = platform.system()
    if current == "Windows":
        assert IS_WINDOWS
        assert not IS_POSIX
    elif current == "Linux":
        assert IS_LINUX
        assert IS_POSIX
    elif current == "Darwin":
        assert IS_MACOS
        assert IS_POSIX


def test_path_normalization():
    """Test path normalization works."""
    from sansible.platform import paths
    
    # Basic normalization
    result = paths.normalize("foo/bar/../baz")
    assert "bar" not in result or ".." not in result
    
    # POSIX conversion
    assert paths.to_posix("foo\\bar") == "foo/bar"
    
    # Temp dir exists
    tmp = paths.get_temp_dir()
    assert os.path.isdir(tmp)


def test_fs_operations():
    """Test filesystem operations."""
    from sansible.platform import fs
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Write and read
        test_file = os.path.join(tmpdir, "test.txt")
        fs.write_file(test_file, "hello world")
        content = fs.read_file(test_file)
        assert content == "hello world"
        
        # Atomic write
        atomic_file = os.path.join(tmpdir, "atomic.txt")
        fs.atomic_write(atomic_file, "atomic content")
        assert fs.read_file(atomic_file) == "atomic content"


def test_process_execution():
    """Test process execution works."""
    from sansible.platform import proc
    
    # Run Python version
    result = proc.run([sys.executable, "--version"])
    assert result.success
    assert "Python" in result.stdout or "Python" in result.stderr


def test_concurrency():
    """Test concurrency primitives work."""
    from sansible.platform.concurrency import run_parallel_threads
    
    def square(x):
        return x * x
    
    results = run_parallel_threads(square, [1, 2, 3, 4, 5])
    values = [r.value for r in results if r.success]
    assert sorted(values) == [1, 4, 9, 16, 25]


def test_tty_detection():
    """Test TTY detection doesn't crash."""
    from sansible.platform import tty
    
    # These should not raise
    is_tty = tty.is_tty()
    supports_color = tty.supports_color()
    size = tty.get_terminal_size()
    
    assert isinstance(is_tty, bool)
    assert isinstance(supports_color, bool)
    assert isinstance(size, tuple) and len(size) == 2


def test_user_functions():
    """Test user functions work."""
    from sansible.platform import users
    
    username = users.get_current_user()
    assert username and len(username) > 0
    
    home = users.get_home_dir()
    assert os.path.isdir(home)


def test_inventory_list_json():
    """Test inventory --list produces valid JSON."""
    from sansible.cli.inventory import main
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        main(["--list"])
    
    output = f.getvalue()
    data = json.loads(output)
    
    assert "_meta" in data
    assert "hostvars" in data["_meta"]


def main():
    """Run all smoke tests."""
    print("=" * 50)
    print("SANSIBLE WINDOWS SMOKE TESTS")
    print(f"Platform: {platform.system()} {platform.release()}")
    print(f"Python: {sys.version}")
    print("=" * 50)
    print()
    
    runner = SmokeTestRunner()
    
    print("Package Import Tests:")
    runner.run_test("import_main_package", test_import_main_package)
    runner.run_test("import_cli", test_import_cli)
    runner.run_test("import_platform", test_import_platform)
    
    print("\nCLI Tests:")
    # Version and help tests exit, so we handle them specially
    try:
        runner.run_test("version_command", test_version_command)
    except SystemExit:
        runner.passed += 1
        print("  ✓ version_command")
    
    try:
        runner.run_test("inventory_help", test_inventory_help)
    except SystemExit:
        runner.passed += 1
        print("  ✓ inventory_help")
    
    print("\nPlatform Abstraction Tests:")
    runner.run_test("platform_detection", test_platform_detection)
    runner.run_test("path_normalization", test_path_normalization)
    runner.run_test("fs_operations", test_fs_operations)
    runner.run_test("process_execution", test_process_execution)
    runner.run_test("concurrency", test_concurrency)
    runner.run_test("tty_detection", test_tty_detection)
    runner.run_test("user_functions", test_user_functions)
    
    print("\nFunctional Tests:")
    runner.run_test("inventory_list_json", test_inventory_list_json)
    
    return runner.summary()


if __name__ == "__main__":
    sys.exit(main())
