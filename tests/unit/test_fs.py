"""Unit tests for platform filesystem utilities."""

import os
import tempfile
import pytest
from sansible.platform import fs


class TestFileReadWrite:
    """Tests for file read/write operations."""
    
    def test_write_and_read_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        fs.write_file(test_file, "hello world")
        content = fs.read_file(test_file)
        assert content == "hello world"
    
    def test_write_and_read_bytes(self, tmp_path):
        test_file = tmp_path / "test.bin"
        fs.write_bytes(test_file, b"\x00\x01\x02\x03")
        content = fs.read_bytes(test_file)
        assert content == b"\x00\x01\x02\x03"
    
    def test_atomic_write(self, tmp_path):
        test_file = tmp_path / "atomic.txt"
        fs.atomic_write(test_file, "atomic content")
        assert fs.read_file(test_file) == "atomic content"
    
    def test_atomic_write_overwrites(self, tmp_path):
        test_file = tmp_path / "atomic.txt"
        fs.write_file(test_file, "original")
        fs.atomic_write(test_file, "updated")
        assert fs.read_file(test_file) == "updated"


class TestDirectoryOperations:
    """Tests for directory operations."""
    
    def test_makedirs_creates_nested(self, tmp_path):
        nested = tmp_path / "a" / "b" / "c"
        fs.makedirs(nested)
        assert nested.is_dir()
    
    def test_makedirs_exist_ok(self, tmp_path):
        existing = tmp_path / "existing"
        fs.makedirs(existing)
        # Should not raise
        fs.makedirs(existing, exist_ok=True)
    
    def test_listdir(self, tmp_path):
        (tmp_path / "file1.txt").touch()
        (tmp_path / "file2.txt").touch()
        contents = fs.listdir(tmp_path)
        assert "file1.txt" in contents
        assert "file2.txt" in contents


class TestFileCopy:
    """Tests for file copy operations."""
    
    def test_copy_file(self, tmp_path):
        src = tmp_path / "src.txt"
        dst = tmp_path / "dst.txt"
        fs.write_file(src, "copy me")
        fs.copy_file(src, dst)
        assert fs.read_file(dst) == "copy me"


class TestContextManagers:
    """Tests for context managers."""
    
    def test_temp_directory(self):
        with fs.temp_directory() as tmp:
            assert os.path.isdir(tmp)
            test_file = os.path.join(tmp, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")
        # Directory should be cleaned up
        assert not os.path.exists(tmp)
    
    def test_temp_file(self):
        with fs.temp_file(suffix=".txt") as tmp:
            assert os.path.exists(tmp)
            assert tmp.endswith(".txt")
        # File should be cleaned up
        assert not os.path.exists(tmp)
