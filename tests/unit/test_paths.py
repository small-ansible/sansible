"""Unit tests for platform path utilities."""

import os
import pytest
from sansible.platform import paths


class TestPathNormalization:
    """Tests for path normalization functions."""
    
    def test_normalize_removes_parent_refs(self):
        result = paths.normalize("foo/bar/../baz")
        # Result should be foo/baz or foo\baz depending on platform
        assert "bar" not in result or ".." not in result
    
    def test_normalize_handles_current_dir(self):
        result = paths.normalize("./foo")
        assert result == "foo"
    
    def test_to_posix_converts_backslashes(self):
        assert paths.to_posix("foo\\bar\\baz") == "foo/bar/baz"
    
    def test_to_posix_preserves_forward_slashes(self):
        assert paths.to_posix("foo/bar/baz") == "foo/bar/baz"


class TestPathJoining:
    """Tests for path joining functions."""
    
    def test_join_basic(self):
        result = paths.join("foo", "bar")
        assert "foo" in result
        assert "bar" in result
    
    def test_safe_join_allows_subpath(self):
        result = paths.safe_join("/base", "sub", "file.txt")
        assert result.startswith("/base")
    
    def test_safe_join_blocks_traversal(self):
        with pytest.raises(ValueError, match="traversal"):
            paths.safe_join("/base", "..", "etc", "passwd")


class TestPathUtilities:
    """Tests for path utility functions."""
    
    def test_get_temp_dir_exists(self):
        tmp = paths.get_temp_dir()
        assert os.path.isdir(tmp)
    
    def test_expand_user_home(self):
        result = paths.expand_user("~")
        assert result != "~"
        assert os.path.isdir(result)
    
    def test_basename(self):
        assert paths.basename("/foo/bar/baz.txt") == "baz.txt"
    
    def test_dirname(self):
        result = paths.dirname("/foo/bar/baz.txt")
        assert "baz.txt" not in result
    
    def test_splitext(self):
        root, ext = paths.splitext("file.tar.gz")
        assert ext == ".gz"
        assert root == "file.tar"
