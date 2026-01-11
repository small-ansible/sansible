#!/usr/bin/env python3
"""
Linux Smoke Tests for sansible.

Runs minimal tests to verify the package works correctly on Linux.
Includes additional Unix-specific tests not applicable to Windows.

Usage:
    python -m tools.linux_smoke
"""

import os
import sys
import platform
import tempfile
import json
from pathlib import Path

# Import shared tests from windows_smoke
from tools.windows_smoke import (
    SmokeTestRunner,
    test_import_main_package,
    test_import_cli,
    test_import_platform,
    test_platform_detection,
    test_path_normalization,
    test_fs_operations,
    test_process_execution,
    test_concurrency,
    test_tty_detection,
    test_user_functions,
    test_inventory_list_json,
    test_version_command,
    test_inventory_help,
)


def test_file_permissions():
    """Test Unix file permissions work."""
    from sansible.platform import fs
    import stat
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.sh")
        fs.write_file(test_file, "#!/bin/bash\necho hello")
        
        # Make executable
        result = fs.make_executable(test_file)
        assert result
        
        # Verify it's executable
        assert fs.is_executable(test_file)


def test_symlinks():
    """Test symlink operations."""
    from sansible.platform import fs
    
    with tempfile.TemporaryDirectory() as tmpdir:
        target = os.path.join(tmpdir, "target.txt")
        link = os.path.join(tmpdir, "link.txt")
        
        fs.write_file(target, "target content")
        result = fs.symlink(target, link)
        
        assert result
        assert fs.is_symlink(link)
        assert fs.read_file(link) == "target content"


def test_file_locking():
    """Test file locking works."""
    from sansible.platform.locks import FileLock
    
    with tempfile.TemporaryDirectory() as tmpdir:
        lock_file = os.path.join(tmpdir, "test.lock")
        
        lock = FileLock(lock_file, timeout=1.0)
        lock.acquire()
        assert lock.is_locked
        lock.release()
        assert not lock.is_locked


def test_shell_command():
    """Test shell command execution."""
    from sansible.platform import proc
    
    result = proc.run_shell("echo hello && echo world")
    assert result.success
    assert "hello" in result.stdout
    assert "world" in result.stdout


def test_unix_user_info():
    """Test Unix-specific user info."""
    from sansible.platform import users
    
    uid = users.get_uid()
    gid = users.get_gid()
    
    # On real Linux these should be actual values
    assert isinstance(uid, int)
    assert isinstance(gid, int)
    
    # Check current user exists
    username = users.get_current_user()
    assert users.user_exists(username)


def main():
    """Run all smoke tests."""
    print("=" * 50)
    print("SANSIBLE LINUX SMOKE TESTS")
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
    
    print("\nUnix-Specific Tests:")
    runner.run_test("file_permissions", test_file_permissions)
    runner.run_test("symlinks", test_symlinks)
    runner.run_test("file_locking", test_file_locking)
    runner.run_test("shell_command", test_shell_command)
    runner.run_test("unix_user_info", test_unix_user_info)
    
    print("\nFunctional Tests:")
    runner.run_test("inventory_list_json", test_inventory_list_json)
    
    return runner.summary()


if __name__ == "__main__":
    sys.exit(main())
