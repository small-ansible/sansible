"""
Tests for lineinfile module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from sansible.engine.scheduler import HostContext
from sansible.engine.inventory import Host
from sansible.connections.base import RunResult


class TestLineinfileModule:
    """Tests for the lineinfile module."""
    
    def test_lineinfile_module_exists(self):
        """Lineinfile module can be imported."""
        from sansible.modules.builtin_lineinfile import LineinfileModule
        assert LineinfileModule is not None
        assert LineinfileModule.name == "lineinfile"
    
    def test_lineinfile_path_required(self):
        """Lineinfile module requires path argument."""
        from sansible.modules.builtin_lineinfile import LineinfileModule
        assert "path" in LineinfileModule.required_args
    
    @pytest.mark.asyncio
    async def test_lineinfile_add_line(self):
        """Lineinfile adds line when not present."""
        from sansible.modules.builtin_lineinfile import LineinfileModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        
        ctx.connection = MagicMock()
        # File exists, line not present
        ctx.connection.run = AsyncMock(side_effect=[
            RunResult(rc=0, stdout="line1\nline2\n", stderr=""),  # cat file
            RunResult(rc=0, stdout="", stderr=""),  # write file
        ])
        
        module = LineinfileModule({
            "path": "/etc/test.conf",
            "line": "new_line",
            "state": "present",
        }, ctx)
        result = await module.run()
        
        assert not result.failed
        assert result.changed is True
    
    @pytest.mark.asyncio
    async def test_lineinfile_line_already_present(self):
        """Lineinfile reports no change when line already present."""
        from sansible.modules.builtin_lineinfile import LineinfileModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        
        ctx.connection = MagicMock()
        # File exists with line already present
        ctx.connection.run = AsyncMock(return_value=RunResult(
            rc=0, stdout="line1\nnew_line\nline3\n", stderr=""
        ))
        
        module = LineinfileModule({
            "path": "/etc/test.conf",
            "line": "new_line",
            "state": "present",
        }, ctx)
        result = await module.run()
        
        assert not result.failed
        assert result.changed is False
    
    @pytest.mark.asyncio
    async def test_lineinfile_remove_line(self):
        """Lineinfile removes line when state=absent."""
        from sansible.modules.builtin_lineinfile import LineinfileModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        
        ctx.connection = MagicMock()
        ctx.connection.run = AsyncMock(side_effect=[
            RunResult(rc=0, stdout="line1\nremove_me\nline3\n", stderr=""),
            RunResult(rc=0, stdout="", stderr=""),
        ])
        
        module = LineinfileModule({
            "path": "/etc/test.conf",
            "line": "remove_me",
            "state": "absent",
        }, ctx)
        result = await module.run()
        
        assert not result.failed
        assert result.changed is True
    
    @pytest.mark.asyncio
    async def test_lineinfile_regexp_match(self):
        """Lineinfile replaces line matching regexp."""
        from sansible.modules.builtin_lineinfile import LineinfileModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        
        ctx.connection = MagicMock()
        ctx.connection.run = AsyncMock(side_effect=[
            RunResult(rc=0, stdout="option=old_value\nother=foo\n", stderr=""),
            RunResult(rc=0, stdout="", stderr=""),
        ])
        
        module = LineinfileModule({
            "path": "/etc/test.conf",
            "regexp": "^option=",
            "line": "option=new_value",
            "state": "present",
        }, ctx)
        result = await module.run()
        
        assert not result.failed
        assert result.changed is True
    
    @pytest.mark.asyncio
    async def test_lineinfile_check_mode(self):
        """Lineinfile respects check mode."""
        from sansible.modules.builtin_lineinfile import LineinfileModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host, check_mode=True)
        
        ctx.connection = MagicMock()
        ctx.connection.run = AsyncMock(return_value=RunResult(
            rc=0, stdout="existing\n", stderr=""
        ))
        
        module = LineinfileModule({
            "path": "/etc/test.conf",
            "line": "new_line",
        }, ctx)
        result = await module.run()
        
        assert not result.failed
        # Check mode should indicate it would change
        assert result.changed is True
        # But not actually write
        assert ctx.connection.run.call_count == 1  # Only read, no write


class TestWinLineinfileModule:
    """Tests for win_lineinfile module."""
    
    def test_win_lineinfile_module_exists(self):
        """Win_lineinfile module can be imported."""
        from sansible.modules.win_lineinfile import WinLineinfileModule
        assert WinLineinfileModule is not None
        assert WinLineinfileModule.name == "win_lineinfile"
