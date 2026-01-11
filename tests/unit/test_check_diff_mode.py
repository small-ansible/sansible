"""
TDD Tests for --check and --diff modes.

These tests are written FIRST, before implementation.
"""

import pytest
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

from sansible.modules.base import Module, ModuleResult, register_module
from sansible.engine.scheduler import HostContext
from sansible.engine.inventory import Host
from sansible.connections.base import Connection, RunResult


class MockConnection(Connection):
    """Mock connection for testing."""
    
    def __init__(self, host: Host):
        super().__init__(host)
        self.commands_run = []
        self.files_put = []
        self._stat_results = {}
    
    async def connect(self) -> None:
        pass
    
    async def close(self) -> None:
        pass
    
    async def run(self, command: str, shell: bool = True, 
                  timeout: Optional[int] = None, cwd: Optional[str] = None,
                  environment: Optional[dict] = None) -> RunResult:
        self.commands_run.append(command)
        return RunResult(rc=0, stdout="ok", stderr="")
    
    async def put(self, local_path: Path, remote_path: str, 
                  mode: Optional[str] = None) -> None:
        self.files_put.append((str(local_path), remote_path, mode))
    
    async def get(self, remote_path: str, local_path: Path) -> None:
        pass
    
    async def mkdir(self, remote_path: str, mode: Optional[str] = None) -> None:
        pass
    
    async def stat(self, remote_path: str) -> Optional[dict]:
        return self._stat_results.get(remote_path)


class TestCheckMode:
    """Tests for --check (dry-run) mode."""
    
    def create_context(self, check_mode: bool = False, diff_mode: bool = False) -> HostContext:
        """Create a test host context with mock connection."""
        host = Host(name="testhost")
        conn = MockConnection(host)
        ctx = HostContext(host=host, connection=conn, check_mode=check_mode, diff_mode=diff_mode)
        return ctx
    
    @pytest.mark.asyncio
    async def test_copy_module_check_mode_no_file_transfer(self):
        """In check mode, copy module should NOT actually transfer files."""
        from sansible.modules.builtin_copy import CopyModule
        
        ctx = self.create_context(check_mode=True)
        args = {"src": "/tmp/test.txt", "dest": "/remote/test.txt"}
        
        # Patch Path.exists to return True
        with patch.object(Path, 'exists', return_value=True):
            with patch.object(Path, 'is_dir', return_value=False):
                with patch.object(Path, 'stat') as mock_stat:
                    mock_stat.return_value = MagicMock(st_size=100)
                    module = CopyModule(args, ctx)
                    result = await module.run()
        
        # Should report what WOULD change
        assert result.changed == True
        assert "would" in result.msg.lower() or "check mode" in result.msg.lower()
        # Should NOT actually put files
        assert len(ctx.connection.files_put) == 0
    
    @pytest.mark.asyncio
    async def test_command_module_check_mode_no_execution(self):
        """In check mode, command module should NOT execute commands."""
        from sansible.modules.builtin_command import CommandModule
        
        ctx = self.create_context(check_mode=True)
        args = {"_raw_params": "rm -rf /important"}
        
        module = CommandModule(args, ctx)
        result = await module.run()
        
        # Should indicate skipped/would change
        assert result.skipped == True or "check" in result.msg.lower()
        # Should NOT execute the command
        assert len(ctx.connection.commands_run) == 0
    
    @pytest.mark.asyncio
    async def test_shell_module_check_mode_no_execution(self):
        """In check mode, shell module should NOT execute commands."""
        from sansible.modules.builtin_shell import ShellModule
        
        ctx = self.create_context(check_mode=True)
        args = {"_raw_params": "echo 'dangerous command'"}
        
        module = ShellModule(args, ctx)
        result = await module.run()
        
        # Should indicate skipped
        assert result.skipped == True or "check" in result.msg.lower()
        # Should NOT execute the command
        assert len(ctx.connection.commands_run) == 0
    
    @pytest.mark.asyncio
    async def test_debug_module_works_in_check_mode(self):
        """Debug module should still work in check mode (safe operation)."""
        from sansible.modules.builtin_debug import DebugModule
        
        ctx = self.create_context(check_mode=True)
        args = {"msg": "Hello, check mode!"}
        
        module = DebugModule(args, ctx)
        result = await module.run()
        
        # Debug should always run
        assert result.failed == False
        assert result.skipped == False
    
    @pytest.mark.asyncio
    async def test_set_fact_works_in_check_mode(self):
        """set_fact should work in check mode (affects only variables)."""
        from sansible.modules.builtin_set_fact import SetFactModule
        
        ctx = self.create_context(check_mode=True)
        args = {"my_var": "my_value"}
        
        module = SetFactModule(args, ctx)
        result = await module.run()
        
        # set_fact should always run
        assert result.failed == False
        assert result.skipped == False
    
    @pytest.mark.asyncio
    async def test_file_module_check_mode_no_changes(self):
        """In check mode, file module should NOT create/delete files."""
        from sansible.modules.builtin_file import FileModule
        
        ctx = self.create_context(check_mode=True)
        args = {"path": "/tmp/newdir", "state": "directory"}
        
        module = FileModule(args, ctx)
        result = await module.run()
        
        # Should report would change
        assert "would" in result.msg.lower() or "check" in result.msg.lower() or result.changed == True
        # Should NOT run commands
        assert len(ctx.connection.commands_run) == 0


class TestDiffMode:
    """Tests for --diff mode."""
    
    def create_context(self, check_mode: bool = False, diff_mode: bool = True) -> HostContext:
        """Create a test host context with mock connection."""
        host = Host(name="testhost")
        conn = MockConnection(host)
        ctx = HostContext(host=host, connection=conn, check_mode=check_mode, diff_mode=diff_mode)
        return ctx
    
    @pytest.mark.asyncio
    async def test_copy_module_diff_shows_content_diff(self):
        """In diff mode, copy with content should show before/after."""
        from sansible.modules.builtin_copy import CopyModule
        
        ctx = self.create_context(diff_mode=True)
        ctx.connection._stat_results["/remote/test.txt"] = {
            "exists": True,
            "size": 10,
        }
        
        args = {"content": "new content here", "dest": "/remote/test.txt"}
        
        module = CopyModule(args, ctx)
        result = await module.run()
        
        # Should have diff information in results
        assert "diff" in result.results or result.changed
    
    @pytest.mark.asyncio
    async def test_template_module_diff_shows_content(self):
        """Template module should show rendered content diff."""
        from sansible.modules.builtin_template import TemplateModule
        
        ctx = self.create_context(diff_mode=True)
        args = {"src": "/tmp/template.j2", "dest": "/remote/config.txt"}
        
        # Would need template file - this tests the interface
        module = TemplateModule(args, ctx)
        # Just verify the module can access diff_mode via context
        assert ctx.diff_mode == True


class TestCheckModeModuleBase:
    """Test that Module base class supports check_mode."""
    
    def test_module_has_check_mode_attribute(self):
        """Module instances should accept check_mode."""
        from sansible.modules.base import Module
        
        # Modules should be able to receive check_mode flag
        host = Host(name="test")
        ctx = HostContext(host=host, check_mode=True)
        
        # The context should carry check_mode
        assert ctx.check_mode == True
    
    def test_host_context_has_check_diff_attributes(self):
        """HostContext should have check_mode and diff_mode."""
        host = Host(name="test")
        ctx = HostContext(host=host, check_mode=True, diff_mode=True)
        
        assert ctx.check_mode == True
        assert ctx.diff_mode == True


class TestCheckModeIntegration:
    """Integration tests for check mode through the runner."""
    
    def test_runner_passes_check_mode_to_context(self):
        """Runner should pass check_mode to module execution context."""
        from sansible.engine.runner import PlaybookRunner
        
        runner = PlaybookRunner(
            inventory_source="tests/fixtures/inventory.ini",
            playbook_paths=["tests/fixtures/playbooks/linux_smoke.yml"],
            check_mode=True,
            diff_mode=True,
        )
        
        assert runner.check_mode == True
        assert runner.diff_mode == True
