"""Unit tests for platform process utilities."""

import sys
import pytest
from sansible.platform import proc


class TestProcessExecution:
    """Tests for process execution."""
    
    def test_run_python_version(self):
        result = proc.run([sys.executable, "--version"])
        assert result.success
        assert "Python" in result.stdout or "Python" in result.stderr
    
    def test_run_captures_stdout(self):
        result = proc.run([sys.executable, "-c", "print('hello')"])
        assert result.success
        assert "hello" in result.stdout
    
    def test_run_captures_stderr(self):
        result = proc.run([sys.executable, "-c", "import sys; print('error', file=sys.stderr)"])
        assert "error" in result.stderr
    
    def test_run_returns_exit_code(self):
        result = proc.run([sys.executable, "-c", "import sys; sys.exit(42)"])
        assert result.failed
        assert result.returncode == 42
    
    def test_run_with_check_raises(self):
        with pytest.raises(Exception):  # subprocess.CalledProcessError
            proc.run([sys.executable, "-c", "import sys; sys.exit(1)"], check=True)


class TestQuoting:
    """Tests for argument quoting."""
    
    def test_quote_simple(self):
        result = proc.quote_arg("simple")
        # Simple strings might not need quotes
        assert "simple" in result
    
    def test_quote_with_spaces(self):
        result = proc.quote_arg("hello world")
        # Should be quoted somehow
        assert "hello" in result and "world" in result
    
    def test_quote_command(self):
        result = proc.quote_command(["echo", "hello world"])
        assert "echo" in result
        assert "hello" in result


class TestUtilities:
    """Tests for process utilities."""
    
    def test_which_python(self):
        result = proc.which("python") or proc.which("python3")
        assert result is not None
        assert "python" in result.lower()
    
    def test_get_python_executable(self):
        result = proc.get_python_executable()
        assert result == sys.executable
    
    def test_is_command_available(self):
        # Python should always be available
        assert proc.is_command_available("python") or proc.is_command_available("python3")
