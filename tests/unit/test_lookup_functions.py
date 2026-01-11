"""
Unit tests for lookup functions in templating.
"""

import os
import tempfile
import pytest

from sansible.engine.templating import lookup, TemplateError


def test_lookup_env_present(monkeypatch):
    monkeypatch.setenv("FOO", "bar")
    assert lookup("env", "FOO") == "bar"


def test_lookup_env_default(monkeypatch):
    monkeypatch.delenv("FOO", raising=False)
    assert lookup("env", "FOO", default="baz") == "baz"


def test_lookup_file_reads_content():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("hello world\n")
        path = f.name
    try:
        assert lookup("file", path) == "hello world"
    finally:
        os.unlink(path)


def test_lookup_file_not_found():
    with pytest.raises(TemplateError):
        lookup("file", "/nonexistent/path.txt")


def test_lookup_lines():
    with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
        f.write("a\nB\nc\n")
        path = f.name
    try:
        assert lookup("lines", path) == ["a", "B", "c"]
    finally:
        os.unlink(path)


def test_lookup_pipe():
    out = lookup("pipe", "echo 123")
    assert out.strip() == "123"


def test_lookup_fileglob():
    with tempfile.TemporaryDirectory() as d:
        f1 = os.path.join(d, "a.txt")
        f2 = os.path.join(d, "b.txt")
        open(f1, "w").close()
        open(f2, "w").close()
        files = lookup("fileglob", os.path.join(d, "*.txt"))
        assert f1 in files and f2 in files


def test_lookup_first_found():
    with tempfile.TemporaryDirectory() as d:
        f1 = os.path.join(d, "a.txt")
        f2 = os.path.join(d, "b.txt")
        open(f2, "w").close()
        found = lookup("first_found", [f1, f2])
        assert found == f2


def test_lookup_dict():
    data = {"a": 1, "b": 2}
    res = lookup("dict", data)
    assert {"key": "a", "value": 1} in res and {"key": "b", "value": 2} in res


def test_lookup_items():
    res = lookup("items", "x", "y")
    assert res == ["x", "y"]


def test_lookup_unknown():
    with pytest.raises(TemplateError):
        lookup("unknown_plugin", "x")
