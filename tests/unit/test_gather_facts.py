"""
TDD Tests for gather_facts (basic fact collection).

Implements minimal fact gathering: ansible_os_family, ansible_hostname, 
ansible_distribution, ansible_system.
"""

import pytest
from pathlib import Path
from typing import Optional

from sansible.engine.scheduler import HostContext
from sansible.engine.inventory import Host
from sansible.connections.base import Connection, RunResult


class MockConnectionForFacts(Connection):
    """Mock connection that returns realistic fact-gathering responses."""
    
    def __init__(self, host: Host, os_type: str = "linux"):
        super().__init__(host)
        self.os_type = os_type  # "linux" or "windows"
        self.commands_run = []
    
    async def connect(self) -> None:
        pass
    
    async def close(self) -> None:
        pass
    
    async def run(self, command: str, shell: bool = True,
                  timeout: Optional[int] = None, cwd: Optional[str] = None,
                  environment: Optional[dict] = None) -> RunResult:
        self.commands_run.append(command)
        
        if self.os_type == "linux":
            if "uname -s" in command:
                return RunResult(rc=0, stdout="Linux\n", stderr="")
            if "uname -n" in command or "hostname" in command:
                return RunResult(rc=0, stdout="testserver\n", stderr="")
            if "/etc/os-release" in command:
                return RunResult(rc=0, stdout='ID=ubuntu\nVERSION_ID="22.04"\n', stderr="")
            if "uname -m" in command:
                return RunResult(rc=0, stdout="x86_64\n", stderr="")
        elif self.os_type == "windows":
            if "$env:COMPUTERNAME" in command:
                return RunResult(rc=0, stdout="WINSERVER01\n", stderr="")
            if "Get-CimInstance" in command or "Win32_OperatingSystem" in command:
                return RunResult(rc=0, stdout="Microsoft Windows Server 2019\n", stderr="")
        
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


class TestSetupModule:
    """Tests for the setup (fact gathering) module."""
    
    def create_context(self, os_type: str = "linux") -> HostContext:
        """Create a test host context."""
        host = Host(name="testhost")
        conn = MockConnectionForFacts(host, os_type=os_type)
        ctx = HostContext(host=host, connection=conn)
        return ctx
    
    @pytest.mark.asyncio
    async def test_setup_module_exists(self):
        """setup module should be registered."""
        from sansible.modules.base import get_module
        
        module_class = get_module("setup")
        assert module_class is not None
        assert module_class.name == "setup"
    
    @pytest.mark.asyncio
    async def test_setup_gathers_linux_facts(self):
        """setup module gathers basic facts on Linux."""
        from sansible.modules.builtin_setup import SetupModule
        
        ctx = self.create_context(os_type="linux")
        args = {}
        
        module = SetupModule(args, ctx)
        result = await module.run()
        
        assert result.failed == False
        # Should have ansible_facts in results
        facts = result.results.get("ansible_facts", {})
        assert "ansible_system" in facts or "ansible_os_family" in facts
    
    @pytest.mark.asyncio
    async def test_setup_returns_hostname(self):
        """setup module returns ansible_hostname."""
        from sansible.modules.builtin_setup import SetupModule
        
        ctx = self.create_context(os_type="linux")
        args = {}
        
        module = SetupModule(args, ctx)
        result = await module.run()
        
        facts = result.results.get("ansible_facts", {})
        assert "ansible_hostname" in facts
        assert facts["ansible_hostname"] == "testserver"
    
    @pytest.mark.asyncio
    async def test_setup_returns_os_family(self):
        """setup module returns ansible_os_family."""
        from sansible.modules.builtin_setup import SetupModule
        
        ctx = self.create_context(os_type="linux")
        args = {}
        
        module = SetupModule(args, ctx)
        result = await module.run()
        
        facts = result.results.get("ansible_facts", {})
        assert "ansible_os_family" in facts
        # Debian for Ubuntu
        assert facts["ansible_os_family"] in ["Debian", "RedHat", "Linux"]
    
    @pytest.mark.asyncio
    async def test_setup_windows_facts(self):
        """setup module gathers facts on Windows."""
        from sansible.modules.builtin_setup import SetupModule
        
        ctx = self.create_context(os_type="windows")
        # Simulate Windows connection type
        ctx.host.vars["ansible_connection"] = "winrm"
        args = {}
        
        module = SetupModule(args, ctx)
        result = await module.run()
        
        facts = result.results.get("ansible_facts", {})
        assert "ansible_os_family" in facts
        assert facts["ansible_os_family"] == "Windows"
    
    @pytest.mark.asyncio
    async def test_setup_filter_facts(self):
        """setup module can filter which facts to gather."""
        from sansible.modules.builtin_setup import SetupModule
        
        ctx = self.create_context(os_type="linux")
        args = {"gather_subset": ["min"]}
        
        module = SetupModule(args, ctx)
        result = await module.run()
        
        # Should still have minimal facts
        facts = result.results.get("ansible_facts", {})
        assert "ansible_hostname" in facts


class TestGatherFactsIntegration:
    """Integration tests for gather_facts in plays."""
    
    def test_play_has_gather_facts_field(self):
        """Play dataclass should have gather_facts field."""
        from sansible.engine.playbook import Play
        
        play = Play(name="test", hosts="all", gather_facts=True)
        assert play.gather_facts == True
    
    def test_play_gather_facts_default_false(self):
        """Play gather_facts should default to False in Sansible."""
        from sansible.engine.playbook import Play
        
        play = Play(name="test", hosts="all")
        assert play.gather_facts == False


class TestFactsAvailableInTasks:
    """Test that gathered facts are available in tasks."""
    
    def create_context(self) -> HostContext:
        """Create a test host context with pre-populated facts."""
        host = Host(name="testhost")
        ctx = HostContext(host=host)
        # Simulate facts having been gathered
        ctx.vars["ansible_facts"] = {
            "ansible_hostname": "testserver",
            "ansible_os_family": "Debian",
            "ansible_system": "Linux",
        }
        # Facts should also be available at top level
        ctx.vars["ansible_hostname"] = "testserver"
        ctx.vars["ansible_os_family"] = "Debian"
        return ctx
    
    def test_facts_in_context_vars(self):
        """Facts should be accessible in context vars."""
        ctx = self.create_context()
        
        assert ctx.vars["ansible_hostname"] == "testserver"
        assert ctx.vars["ansible_os_family"] == "Debian"
    
    def test_facts_in_ansible_facts_dict(self):
        """Facts should be in ansible_facts dict."""
        ctx = self.create_context()
        
        facts = ctx.vars.get("ansible_facts", {})
        assert facts["ansible_hostname"] == "testserver"
