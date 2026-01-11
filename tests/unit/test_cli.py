"""Unit tests for CLI modules."""

import pytest
from sansible import __version__
from sansible.cli import main, playbook, inventory


class TestMainCLI:
    """Tests for main CLI."""
    
    def test_create_parser(self):
        parser = main.create_parser()
        assert parser.prog == "sansible"
    
    def test_version_string(self):
        version = main.get_version_string()
        assert __version__ in version
        assert "pure-python" in version.lower()
    
    def test_main_no_args_shows_help(self, capsys):
        result = main.main([])
        assert result == 0


class TestPlaybookCLI:
    """Tests for playbook CLI."""
    
    def test_create_parser(self):
        parser = playbook.create_parser()
        assert parser.prog == "sansible-playbook"
    
    def test_version_string(self):
        version = playbook.get_version_string()
        assert __version__ in version


class TestInventoryCLI:
    """Tests for inventory CLI."""
    
    def test_create_parser(self):
        parser = inventory.create_parser()
        assert parser.prog == "sansible-inventory"
    
    def test_list_returns_json(self, capsys):
        result = inventory.main(["--list"])
        assert result == 0
        captured = capsys.readouterr()
        assert "_meta" in captured.out
    
    def test_host_returns_json(self, capsys):
        result = inventory.main(["--host", "testhost"])
        assert result == 0
        captured = capsys.readouterr()
        assert "{" in captured.out
