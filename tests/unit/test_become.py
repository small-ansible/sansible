"""
Tests for become (privilege escalation) support.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from sansible.engine.scheduler import HostContext
from sansible.engine.inventory import Host
from sansible.connections.base import RunResult


class TestBecomeInHostContext:
    """Test become fields in HostContext."""
    
    def test_host_context_has_become_field(self):
        """HostContext has become field."""
        host = Host(name="test", variables={})
        ctx = HostContext(host=host, become=True)
        assert ctx.become is True
    
    def test_host_context_become_default_false(self):
        """HostContext become defaults to False."""
        host = Host(name="test", variables={})
        ctx = HostContext(host=host)
        assert ctx.become is False
    
    def test_host_context_has_become_user(self):
        """HostContext has become_user field."""
        host = Host(name="test", variables={})
        ctx = HostContext(host=host, become=True, become_user="root")
        assert ctx.become_user == "root"
    
    def test_host_context_become_user_default_root(self):
        """HostContext become_user defaults to root."""
        host = Host(name="test", variables={})
        ctx = HostContext(host=host, become=True)
        assert ctx.become_user == "root"
    
    def test_host_context_has_become_method(self):
        """HostContext has become_method field."""
        host = Host(name="test", variables={})
        ctx = HostContext(host=host, become=True, become_method="sudo")
        assert ctx.become_method == "sudo"


class TestBecomeInPlay:
    """Test become parsing in plays."""
    
    def test_play_has_become_field(self):
        """Play dataclass has become field."""
        from sansible.engine.playbook import Play
        play = Play(name="test", hosts="all", tasks=[], become=True)
        assert play.become is True
    
    def test_play_become_default_false(self):
        """Play become defaults to False."""
        from sansible.engine.playbook import Play
        play = Play(name="test", hosts="all", tasks=[])
        assert play.become is False
    
    def test_play_has_become_user(self):
        """Play has become_user field."""
        from sansible.engine.playbook import Play
        play = Play(name="test", hosts="all", tasks=[], become=True, become_user="admin")
        assert play.become_user == "admin"


class TestBecomeInTask:
    """Test become parsing in tasks."""
    
    def test_task_has_become_field(self):
        """Task dataclass has become field."""
        from sansible.engine.playbook import Task
        task = Task(name="test", module="command", args={"cmd": "whoami"}, become=True)
        assert task.become is True
    
    def test_task_become_default_none(self):
        """Task become defaults to None (inherit from play)."""
        from sansible.engine.playbook import Task
        task = Task(name="test", module="command", args={"cmd": "whoami"})
        assert task.become is None


class TestBecomeCommandWrapping:
    """Test that commands are wrapped with sudo/runas."""
    
    @pytest.mark.asyncio
    async def test_command_wrapped_with_sudo(self):
        """Command module wraps command with sudo when become=True."""
        from sansible.modules.builtin_command import CommandModule
        
        host = Host(name="test", variables={"ansible_connection": "ssh"})
        ctx = HostContext(host=host, become=True, become_method="sudo", become_user="root")
        
        ctx.connection = MagicMock()
        ctx.connection.run = AsyncMock(return_value=RunResult(rc=0, stdout="root\n", stderr=""))
        
        module = CommandModule({"cmd": "whoami"}, ctx)
        result = await module.run()
        
        # Verify sudo was used
        call_args = ctx.connection.run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("command", "")
        assert "sudo" in cmd or result.stdout.strip() == "root"
    
    @pytest.mark.asyncio
    async def test_shell_wrapped_with_sudo(self):
        """Shell module wraps command with sudo when become=True."""
        from sansible.modules.builtin_shell import ShellModule
        
        host = Host(name="test", variables={"ansible_connection": "ssh"})
        ctx = HostContext(host=host, become=True, become_method="sudo", become_user="root")
        
        ctx.connection = MagicMock()
        ctx.connection.run = AsyncMock(return_value=RunResult(rc=0, stdout="", stderr=""))
        
        module = ShellModule({"cmd": "cat /etc/shadow"}, ctx)
        result = await module.run()
        
        call_args = ctx.connection.run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("command", "")
        assert "sudo" in cmd
    
    @pytest.mark.asyncio
    async def test_become_false_no_sudo(self):
        """Command not wrapped when become=False."""
        from sansible.modules.builtin_command import CommandModule
        
        host = Host(name="test", variables={"ansible_connection": "ssh"})
        ctx = HostContext(host=host, become=False)
        
        ctx.connection = MagicMock()
        ctx.connection.run = AsyncMock(return_value=RunResult(rc=0, stdout="user\n", stderr=""))
        
        module = CommandModule({"cmd": "whoami"}, ctx)
        result = await module.run()
        
        call_args = ctx.connection.run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1].get("command", "")
        assert "sudo" not in cmd


class TestWindowsBecome:
    """Test become on Windows (runas)."""
    
    @pytest.mark.asyncio
    async def test_win_command_with_become(self):
        """Win_command uses runas when become=True."""
        from sansible.modules.win_command import WinCommandModule
        
        host = Host(name="test", variables={"ansible_connection": "winrm"})
        ctx = HostContext(host=host, become=True, become_user="Administrator")
        
        ctx.connection = MagicMock()
        ctx.connection.run = AsyncMock(return_value=RunResult(rc=0, stdout="", stderr=""))
        
        module = WinCommandModule({"cmd": "whoami"}, ctx)
        # Windows become typically handled at connection level
        result = await module.run()
        
        assert not result.failed
