"""
TDD Tests for win_service module.

These tests are written FIRST, before implementation.
"""

import pytest
from pathlib import Path
from typing import Optional

from sansible.engine.scheduler import HostContext
from sansible.engine.inventory import Host
from sansible.connections.base import Connection, RunResult


class MockWinRMConnection(Connection):
    """Mock WinRM connection for testing Windows modules."""
    
    def __init__(self, host: Host):
        super().__init__(host)
        self.commands_run = []
        self._service_states = {}  # name -> {state, start_mode, exists}
    
    def set_service_state(self, name: str, state: str = "stopped", 
                          start_mode: str = "auto", exists: bool = True):
        """Set mock service state for testing."""
        self._service_states[name] = {
            "state": state,
            "start_mode": start_mode,
            "exists": exists,
        }
    
    async def connect(self) -> None:
        pass
    
    async def close(self) -> None:
        pass
    
    async def run(self, command: str, shell: bool = True,
                  timeout: Optional[int] = None, cwd: Optional[str] = None,
                  environment: Optional[dict] = None) -> RunResult:
        self.commands_run.append(command)
        # Simulate PowerShell responses
        if "Get-Service" in command:
            # Extract service name from command
            for name, info in self._service_states.items():
                if name in command:
                    if info["exists"]:
                        # Return state in format expected by module
                        state = info["state"].capitalize()
                        return RunResult(rc=0, stdout=state, stderr="")
                    else:
                        return RunResult(rc=1, stdout="", stderr="Service not found")
            return RunResult(rc=1, stdout="", stderr="Service not found")
        return RunResult(rc=0, stdout="", stderr="")
    
    async def put(self, local_path: Path, remote_path: str,
                  mode: Optional[str] = None) -> None:
        pass
    
    async def get(self, remote_path: str, local_path: Path) -> None:
        pass
    
    async def mkdir(self, remote_path: str, mode: Optional[str] = None) -> None:
        pass
    
    async def stat(self, remote_path: str) -> Optional[dict]:
        return None


class TestWinServiceModule:
    """Tests for win_service module."""
    
    def create_context(self, check_mode: bool = False) -> HostContext:
        """Create a test host context with mock WinRM connection."""
        host = Host(name="winhost", variables={"ansible_connection": "winrm"})
        conn = MockWinRMConnection(host)
        ctx = HostContext(host=host, connection=conn, check_mode=check_mode)
        return ctx
    
    @pytest.mark.asyncio
    async def test_win_service_module_exists(self):
        """win_service module should be registered."""
        from sansible.modules.base import get_module
        
        module_class = get_module("win_service")
        assert module_class is not None
        assert module_class.name == "win_service"
    
    @pytest.mark.asyncio
    async def test_win_service_name_required(self):
        """win_service requires name parameter."""
        from sansible.modules.win_service import WinServiceModule
        
        ctx = self.create_context()
        args = {"state": "started"}  # Missing name
        
        module = WinServiceModule(args, ctx)
        error = module.validate_args()
        
        assert error is not None
        assert "name" in error.lower()
    
    @pytest.mark.asyncio
    async def test_win_service_start_service(self):
        """win_service can start a stopped service."""
        from sansible.modules.win_service import WinServiceModule
        
        ctx = self.create_context()
        ctx.connection.set_service_state("spooler", state="stopped", exists=True)
        
        args = {"name": "spooler", "state": "started"}
        module = WinServiceModule(args, ctx)
        result = await module.run()
        
        assert result.failed == False
        assert result.changed == True
        # Should have run Start-Service command
        assert any("Start-Service" in cmd for cmd in ctx.connection.commands_run)
    
    @pytest.mark.asyncio
    async def test_win_service_stop_service(self):
        """win_service can stop a running service."""
        from sansible.modules.win_service import WinServiceModule
        
        ctx = self.create_context()
        ctx.connection.set_service_state("spooler", state="running", exists=True)
        
        args = {"name": "spooler", "state": "stopped"}
        module = WinServiceModule(args, ctx)
        result = await module.run()
        
        assert result.failed == False
        assert result.changed == True
        # Should have run Stop-Service command
        assert any("Stop-Service" in cmd for cmd in ctx.connection.commands_run)
    
    @pytest.mark.asyncio
    async def test_win_service_restart_service(self):
        """win_service can restart a service."""
        from sansible.modules.win_service import WinServiceModule
        
        ctx = self.create_context()
        ctx.connection.set_service_state("spooler", state="running", exists=True)
        
        args = {"name": "spooler", "state": "restarted"}
        module = WinServiceModule(args, ctx)
        result = await module.run()
        
        assert result.failed == False
        assert result.changed == True
        # Should have run Restart-Service command
        assert any("Restart-Service" in cmd for cmd in ctx.connection.commands_run)
    
    @pytest.mark.asyncio
    async def test_win_service_set_start_mode(self):
        """win_service can set service start mode."""
        from sansible.modules.win_service import WinServiceModule
        
        ctx = self.create_context()
        ctx.connection.set_service_state("spooler", start_mode="manual", exists=True)
        
        args = {"name": "spooler", "start_mode": "auto"}
        module = WinServiceModule(args, ctx)
        result = await module.run()
        
        assert result.failed == False
        # Should have run Set-Service command
        assert any("Set-Service" in cmd for cmd in ctx.connection.commands_run)
    
    @pytest.mark.asyncio
    async def test_win_service_check_mode(self):
        """win_service respects check mode."""
        from sansible.modules.win_service import WinServiceModule
        
        ctx = self.create_context(check_mode=True)
        ctx.connection.set_service_state("spooler", state="stopped", exists=True)
        
        args = {"name": "spooler", "state": "started"}
        module = WinServiceModule(args, ctx)
        result = await module.run()
        
        assert result.failed == False
        assert "check" in result.msg.lower() or "would" in result.msg.lower()
        # Should NOT have run any Start/Stop commands
        assert not any("Start-Service" in cmd for cmd in ctx.connection.commands_run)
    
    @pytest.mark.asyncio
    async def test_win_service_idempotent_already_started(self):
        """win_service is idempotent - no change if already started."""
        from sansible.modules.win_service import WinServiceModule
        
        ctx = self.create_context()
        ctx.connection.set_service_state("spooler", state="running", exists=True)
        
        args = {"name": "spooler", "state": "started"}
        module = WinServiceModule(args, ctx)
        result = await module.run()
        
        assert result.failed == False
        assert result.changed == False  # No change needed
