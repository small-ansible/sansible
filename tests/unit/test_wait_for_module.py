"""
Tests for wait_for module.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sansible.engine.scheduler import HostContext
from sansible.engine.inventory import Host
from sansible.connections.base import RunResult


class TestWaitForModule:
    """Tests for the wait_for module."""
    
    def test_wait_for_module_exists(self):
        """Wait_for module can be imported."""
        from sansible.modules.builtin_wait_for import WaitForModule
        assert WaitForModule is not None
        assert WaitForModule.name == "wait_for"
    
    @pytest.mark.asyncio
    async def test_wait_for_port_open(self):
        """Wait_for succeeds when port opens."""
        from sansible.modules.builtin_wait_for import WaitForModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        
        ctx.connection = MagicMock()
        # Port check succeeds (nc returns 0)
        ctx.connection.run = AsyncMock(return_value=RunResult(rc=0, stdout="", stderr=""))
        
        module = WaitForModule({
            "host": "localhost",
            "port": 8080,
            "timeout": 5,
        }, ctx)
        result = await module.run()
        
        assert not result.failed
        assert result.msg == "Port 8080 is reachable"
    
    @pytest.mark.asyncio
    async def test_wait_for_port_timeout(self):
        """Wait_for fails on timeout."""
        from sansible.modules.builtin_wait_for import WaitForModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        
        ctx.connection = MagicMock()
        # Port check always fails
        ctx.connection.run = AsyncMock(return_value=RunResult(rc=1, stdout="", stderr="Connection refused"))
        
        module = WaitForModule({
            "host": "localhost",
            "port": 9999,
            "timeout": 1,
            "delay": 0,
            "sleep": 0.1,
        }, ctx)
        result = await module.run()
        
        assert result.failed
        assert "timed out" in result.msg.lower()
    
    @pytest.mark.asyncio
    async def test_wait_for_file_exists(self):
        """Wait_for succeeds when file appears."""
        from sansible.modules.builtin_wait_for import WaitForModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        
        ctx.connection = MagicMock()
        # test -e returns 0 (file exists)
        ctx.connection.run = AsyncMock(return_value=RunResult(rc=0, stdout="", stderr=""))
        
        module = WaitForModule({
            "path": "/tmp/ready.flag",
            "state": "present",
            "timeout": 5,
        }, ctx)
        result = await module.run()
        
        assert not result.failed
    
    @pytest.mark.asyncio
    async def test_wait_for_file_absent(self):
        """Wait_for succeeds when file is removed."""
        from sansible.modules.builtin_wait_for import WaitForModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        
        ctx.connection = MagicMock()
        # test -e returns 1 (file doesn't exist)
        ctx.connection.run = AsyncMock(return_value=RunResult(rc=1, stdout="", stderr=""))
        
        module = WaitForModule({
            "path": "/tmp/lockfile",
            "state": "absent",
            "timeout": 5,
        }, ctx)
        result = await module.run()
        
        assert not result.failed
    
    @pytest.mark.asyncio
    async def test_wait_for_delay(self):
        """Wait_for respects delay before first check."""
        from sansible.modules.builtin_wait_for import WaitForModule
        import time
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        
        ctx.connection = MagicMock()
        ctx.connection.run = AsyncMock(return_value=RunResult(rc=0, stdout="", stderr=""))
        
        start = time.time()
        module = WaitForModule({
            "host": "localhost",
            "port": 22,
            "delay": 0.2,
            "timeout": 5,
        }, ctx)
        result = await module.run()
        elapsed = time.time() - start
        
        # Should have waited at least the delay
        assert elapsed >= 0.2


class TestWinWaitForModule:
    """Tests for win_wait_for module."""
    
    def test_win_wait_for_module_exists(self):
        """Win_wait_for module can be imported."""
        from sansible.modules.win_wait_for import WinWaitForModule
        assert WinWaitForModule is not None
        assert WinWaitForModule.name == "win_wait_for"
