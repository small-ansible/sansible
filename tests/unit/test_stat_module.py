"""
Tests for stat module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from sansible.engine.scheduler import HostContext
from sansible.engine.inventory import Host


def mock_stat_dict(*, exists=True, isfile=True, isdir=False, mode="0644", size=100, uid=1000, gid=1000):
    """Create a mock stat result dict (matching what connections actually return)."""
    if not exists:
        return None  # Non-existent files return None
    return {
        "exists": exists,
        "isfile": isfile,
        "isdir": isdir,
        "mode": mode,
        "size": size,
        "uid": uid,
        "gid": gid,
    }


class TestStatModule:
    """Tests for the stat module."""
    
    def test_stat_module_exists(self):
        """Stat module can be imported."""
        from sansible.modules.builtin_stat import StatModule
        assert StatModule is not None
        assert StatModule.name == "stat"
    
    def test_stat_path_required(self):
        """Stat module requires path argument."""
        from sansible.modules.builtin_stat import StatModule
        assert "path" in StatModule.required_args
    
    @pytest.mark.asyncio
    async def test_stat_file_exists(self):
        """Stat module returns exists=True for existing file."""
        from sansible.modules.builtin_stat import StatModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        
        # Mock connection with stat - returns dict
        ctx.connection = MagicMock()
        ctx.connection.stat = AsyncMock(return_value=mock_stat_dict(exists=True, isfile=True))
        
        module = StatModule({"path": "/etc/passwd"}, ctx)
        result = await module.run()
        
        assert not result.failed
        stat = result.results.get("stat", {})
        assert stat.get("exists") is True
        assert stat.get("isreg") is True
    
    @pytest.mark.asyncio
    async def test_stat_file_not_exists(self):
        """Stat module returns exists=False for non-existent file."""
        from sansible.modules.builtin_stat import StatModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)

        ctx.connection = MagicMock()
        ctx.connection.stat = AsyncMock(return_value=None)  # Non-existent = None
        
        module = StatModule({"path": "/nonexistent"}, ctx)
        result = await module.run()
        
        assert not result.failed
        stat = result.results.get("stat", {})
        assert stat.get("exists") is False
    
    @pytest.mark.asyncio
    async def test_stat_directory(self):
        """Stat module returns isdir=True for directories."""
        from sansible.modules.builtin_stat import StatModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        
        ctx.connection = MagicMock()
        ctx.connection.stat = AsyncMock(return_value=mock_stat_dict(exists=True, isfile=False, isdir=True))
        
        module = StatModule({"path": "/etc"}, ctx)
        result = await module.run()
        
        assert not result.failed
        stat = result.results.get("stat", {})
        assert stat.get("exists") is True
        assert stat.get("isdir") is True
    
    @pytest.mark.asyncio
    async def test_stat_returns_mode(self):
        """Stat module returns file mode."""
        from sansible.modules.builtin_stat import StatModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        
        ctx.connection = MagicMock()
        ctx.connection.stat = AsyncMock(return_value=mock_stat_dict(exists=True, mode="0755"))
        
        module = StatModule({"path": "/usr/bin/python"}, ctx)
        result = await module.run()
        
        assert not result.failed
        stat = result.results.get("stat", {})
        assert stat.get("mode") == "0755"
    
    @pytest.mark.asyncio
    async def test_stat_returns_size(self):
        """Stat module returns file size."""
        from sansible.modules.builtin_stat import StatModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        
        ctx.connection = MagicMock()
        ctx.connection.stat = AsyncMock(return_value=mock_stat_dict(exists=True, size=1024))
        
        module = StatModule({"path": "/etc/hosts"}, ctx)
        result = await module.run()
        
        assert not result.failed
        stat = result.results.get("stat", {})
        assert stat.get("size") == 1024


class TestWinStatModule:
    """Tests for win_stat module."""
    
    def test_win_stat_module_exists(self):
        """Win_stat module can be imported."""
        from sansible.modules.win_stat import WinStatModule
        assert WinStatModule is not None
        assert WinStatModule.name == "win_stat"
    
    @pytest.mark.asyncio
    async def test_win_stat_file_exists(self):
        """Win_stat returns exists=True for existing file."""
        from sansible.modules.win_stat import WinStatModule
        from sansible.connections.base import RunResult
        
        host = Host(name="test", variables={"ansible_connection": "winrm"})
        ctx = HostContext(host=host)
        
        ctx.connection = MagicMock()
        # Return valid JSON from PowerShell
        ps_output = '{"Exists":true,"IsDirectory":false,"Length":1024,"Mode":"Archive"}'
        ctx.connection.run = AsyncMock(return_value=RunResult(rc=0, stdout=ps_output, stderr=""))
        
        module = WinStatModule({"path": "C:\\Windows\\System32\\cmd.exe"}, ctx)
        result = await module.run()
        
        assert not result.failed
        stat = result.results.get("stat", {})
        assert stat.get("exists") is True
