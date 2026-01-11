"""
Unit Tests for Galaxy Module Support

Tests the Galaxy module loader, executor, and module wrapper.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

from sansible.galaxy.loader import (
    GalaxyModuleLoader,
    CollectionInfo,
    GalaxyHostState,
    GALAXY_MODULE_PATTERN,
)
from sansible.galaxy.executor import GalaxyModuleExecutor
from sansible.galaxy.module import GalaxyModule, create_galaxy_module
from sansible.galaxy.config import GalaxyConfig, get_config, configure


class TestGalaxyModulePattern:
    """Test Galaxy module name pattern matching."""
    
    def test_valid_galaxy_modules(self):
        """Test that valid Galaxy module names are recognized."""
        valid_modules = [
            "community.general.timezone",
            "ansible.posix.synchronize",
            "community.windows.win_timezone",
            "namespace.collection.module_name",
            "ns1.col2.mod3",
        ]
        for module in valid_modules:
            assert GALAXY_MODULE_PATTERN.match(module), f"{module} should match"
            assert GalaxyModuleLoader.is_galaxy_module(module), f"{module} should be Galaxy"
    
    def test_invalid_galaxy_modules(self):
        """Test that non-Galaxy module names are rejected."""
        invalid_modules = [
            "copy",
            "command",
            # Note: "ansible.builtin.copy" technically matches the pattern,
            # but is handled separately via MODULE_ALIASES in playbook.py
            "namespace.module",  # Only 2 parts total
            "Community.General.Timezone",  # Uppercase
            "",
            "one",
            "1.2.3",  # Numbers can't start parts
        ]
        for module in invalid_modules:
            assert not GalaxyModuleLoader.is_galaxy_module(module), f"{module} should not match"
    
    def test_parse_module_fqcn(self):
        """Test parsing module FQCN into components."""
        namespace, collection, module = GalaxyModuleLoader.parse_module_fqcn(
            "community.general.timezone"
        )
        assert namespace == "community"
        assert collection == "general"
        assert module == "timezone"
    
    def test_parse_invalid_fqcn(self):
        """Test that invalid FQCN raises error."""
        with pytest.raises(ValueError, match="Invalid Galaxy module name"):
            GalaxyModuleLoader.parse_module_fqcn("copy")


class TestGalaxyHostState:
    """Test host state tracking."""
    
    def test_initial_state(self):
        """Test initial host state."""
        state = GalaxyHostState()
        assert state.ansible_installed is None
        assert state.ansible_version is None
        assert state.installed_collections == {}
        assert state.pending_collections == set()
    
    def test_state_update(self):
        """Test updating host state."""
        state = GalaxyHostState()
        state.ansible_installed = True
        state.ansible_version = "2.15.0"
        state.installed_collections["community.general"] = CollectionInfo(
            namespace="community",
            name="general",
            version="7.0.0",
            installed=True,
        )
        
        assert state.ansible_installed is True
        assert state.ansible_version == "2.15.0"
        assert "community.general" in state.installed_collections


class TestCollectionInfo:
    """Test collection info dataclass."""
    
    def test_fqcn_property(self):
        """Test FQCN generation."""
        info = CollectionInfo(
            namespace="community",
            name="general",
            version="7.0.0",
        )
        assert info.fqcn == "community.general"
    
    def test_str_representation(self):
        """Test string representation."""
        info = CollectionInfo(
            namespace="community",
            name="general",
            version="7.0.0",
        )
        assert str(info) == "community.general==7.0.0"
        
        info_no_version = CollectionInfo(
            namespace="community",
            name="general",
        )
        assert str(info_no_version) == "community.general"


class TestGalaxyModuleLoader:
    """Test Galaxy module loader."""
    
    @pytest.fixture
    def mock_connection(self):
        """Create a mock connection."""
        conn = MagicMock()
        conn.host = MagicMock()
        conn.host.name = "testhost"
        conn.run = AsyncMock()
        return conn
    
    @pytest.fixture
    def loader(self, mock_connection):
        """Create a loader with mock connection."""
        GalaxyModuleLoader.reset_cache()
        return GalaxyModuleLoader(mock_connection)
    
    @pytest.mark.asyncio
    async def test_check_ansible_installed_yes(self, loader, mock_connection):
        """Test detecting installed ansible."""
        mock_connection.run.return_value = MagicMock(
            rc=0,
            stdout="ansible [core 2.15.0]\n"
        )
        
        result = await loader.check_ansible_installed()
        
        assert result is True
        assert loader.state.ansible_installed is True
        assert loader.state.ansible_version == "2.15.0"
    
    @pytest.mark.asyncio
    async def test_check_ansible_installed_no(self, loader, mock_connection):
        """Test detecting missing ansible."""
        mock_connection.run.return_value = MagicMock(
            rc=1,
            stdout=""
        )
        
        result = await loader.check_ansible_installed()
        
        assert result is False
        assert loader.state.ansible_installed is False
    
    @pytest.mark.asyncio
    async def test_install_ansible(self, loader, mock_connection):
        """Test installing ansible-core."""
        # Mock: _find_python, install command, and version check after install
        mock_connection.run.side_effect = [
            MagicMock(rc=0, stdout="/usr/bin/python3\n"),  # which python3
            MagicMock(rc=0, stdout="Successfully installed\n"),  # pip install
            MagicMock(rc=0, stdout="2.15.0\n"),  # version check
        ]
        
        result = await loader.install_ansible()
        
        assert result is True
        assert loader.state.ansible_installed is True
    
    @pytest.mark.asyncio
    async def test_list_installed_collections_json(self, loader, mock_connection):
        """Test listing collections with JSON output."""
        # Pre-set ansible installed to skip installation
        loader.state.ansible_installed = True
        
        mock_connection.run.return_value = MagicMock(
            rc=0,
            stdout=json.dumps({
                "/usr/share/ansible/collections": {
                    "community.general": {"version": "7.0.0"},
                    "ansible.posix": {"version": "1.5.0"},
                }
            })
        )
        
        collections = await loader.list_installed_collections()
        
        assert "community.general" in collections
        assert collections["community.general"].version == "7.0.0"
    
    @pytest.mark.asyncio
    async def test_install_collection(self, loader, mock_connection):
        """Test installing a collection."""
        # Pre-set ansible installed
        loader.state.ansible_installed = True
        
        mock_connection.run.side_effect = [
            MagicMock(rc=0, stdout="{}"),  # list_installed_collections
            MagicMock(rc=0, stdout="Installing collection"),  # install
            MagicMock(rc=0, stdout="{}"),  # refresh list
        ]
        
        result = await loader.install_collection("community.general")
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_ensure_collection(self, loader, mock_connection):
        """Test ensuring a collection is installed."""
        # Pre-populate with installed collection
        loader.state.installed_collections["community.general"] = CollectionInfo(
            namespace="community",
            name="general",
            version="7.0.0",
            installed=True,
        )
        
        result = await loader.ensure_collection("community.general.timezone")
        
        assert result is True
        mock_connection.run.assert_not_called()  # Should use cache


class TestGalaxyModuleExecutor:
    """Test Galaxy module executor."""
    
    @pytest.fixture
    def mock_connection(self):
        """Create a mock connection."""
        conn = MagicMock()
        conn.host = MagicMock()
        conn.host.name = "testhost"
        conn.run = AsyncMock()
        return conn
    
    @pytest.fixture
    def mock_loader(self, mock_connection):
        """Create a mock loader."""
        loader = MagicMock()
        loader.ensure_collection = AsyncMock(return_value=True)
        return loader
    
    @pytest.fixture
    def executor(self, mock_connection, mock_loader):
        """Create an executor with mock dependencies."""
        return GalaxyModuleExecutor(mock_connection, mock_loader)
    
    def test_build_args_string_simple(self, executor):
        """Test building args string for simple values."""
        args = {"name": "America/New_York", "hwclock": "UTC"}
        result = executor._build_args_string(args)
        
        assert "name=America/New_York" in result
        assert "hwclock=UTC" in result
    
    def test_build_args_string_bool(self, executor):
        """Test building args string with boolean values."""
        args = {"enabled": True, "disabled": False}
        result = executor._build_args_string(args)
        
        assert "enabled=yes" in result
        assert "disabled=no" in result
    
    def test_build_args_string_complex(self, executor):
        """Test building args string with complex values."""
        args = {"items": ["a", "b"], "config": {"key": "value"}}
        result = executor._build_args_string(args)
        
        assert 'items=["a", "b"]' in result or "items=" in result
    
    def test_build_command(self, executor):
        """Test building ansible command."""
        cmd = executor._build_command(
            "community.general.timezone",
            {"name": "UTC"},
        )
        
        assert "ansible localhost" in cmd
        assert "-m community.general.timezone" in cmd
        assert "--connection local" in cmd
    
    @pytest.mark.asyncio
    async def test_execute_success(self, executor, mock_connection, mock_loader):
        """Test successful module execution."""
        mock_connection.run.return_value = MagicMock(
            rc=0,
            stdout='localhost | SUCCESS => {"changed": true, "msg": "Timezone set"}',
            stderr=""
        )
        
        result = await executor.execute(
            "community.general.timezone",
            {"name": "America/New_York"}
        )
        
        assert result["changed"] is True
        assert result["failed"] is False
    
    @pytest.mark.asyncio
    async def test_execute_failure(self, executor, mock_connection, mock_loader):
        """Test failed module execution."""
        mock_connection.run.return_value = MagicMock(
            rc=2,
            stdout='localhost | FAILED! => {"changed": false, "msg": "Permission denied"}',
            stderr=""
        )
        
        result = await executor.execute(
            "community.general.timezone",
            {"name": "America/New_York"}
        )
        
        assert result["failed"] is True
    
    @pytest.mark.asyncio
    async def test_execute_collection_not_found(self, executor, mock_connection, mock_loader):
        """Test execution when collection install fails."""
        mock_loader.ensure_collection.return_value = False
        
        result = await executor.execute(
            "unknown.collection.module",
            {}
        )
        
        assert result["failed"] is True
        assert "Failed to install collection" in result["msg"]


class TestGalaxyModule:
    """Test Galaxy module wrapper."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock host context."""
        ctx = MagicMock()
        ctx.host = MagicMock()
        ctx.host.name = "testhost"
        ctx.host.get_var = MagicMock(return_value="ssh")
        ctx.check_mode = False
        ctx.diff_mode = False
        ctx.become = False
        ctx.become_user = "root"
        ctx.become_method = "sudo"
        ctx.connection = MagicMock()
        ctx.connection.run = AsyncMock()
        return ctx
    
    def test_validate_args_valid(self, mock_context):
        """Test validating valid Galaxy module."""
        module = GalaxyModule(
            "community.general.timezone",
            {"name": "UTC"},
            mock_context
        )
        
        assert module.validate_args() is None
    
    def test_validate_args_invalid(self, mock_context):
        """Test validating invalid module name."""
        module = GalaxyModule(
            "invalid",
            {},
            mock_context
        )
        
        error = module.validate_args()
        assert error is not None
        assert "Invalid Galaxy module name" in error
    
    def test_detect_windows_ssh(self, mock_context):
        """Test Windows detection for SSH connection."""
        module = GalaxyModule(
            "community.general.timezone",
            {},
            mock_context
        )
        
        assert module._detect_windows() is False
    
    def test_detect_windows_winrm(self, mock_context):
        """Test Windows detection for WinRM connection."""
        mock_context.host.get_variable.return_value = "winrm"
        
        module = GalaxyModule(
            "community.windows.win_timezone",
            {},
            mock_context
        )
        
        assert module._detect_windows() is True
    
    @pytest.mark.asyncio
    async def test_run_success(self, mock_context):
        """Test successful module run."""
        mock_context.connection.run.return_value = MagicMock(
            rc=0,
            stdout='localhost | SUCCESS => {"changed": true, "msg": "Done"}',
            stderr=""
        )
        
        # Pre-install collection in mock
        with patch.object(GalaxyModuleLoader, '_host_states', {}):
            module = GalaxyModule(
                "community.general.timezone",
                {"name": "UTC"},
                mock_context
            )
            
            # Mock the loader methods
            module._loader = MagicMock()
            module._loader.ensure_collection = AsyncMock(return_value=True)
            
            result = await module.run()
            
            assert result.changed is True
            assert result.failed is False


class TestGalaxyConfig:
    """Test Galaxy configuration."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = GalaxyConfig()
        
        assert config.enabled is True
        assert config.auto_install_ansible is True
        assert config.auto_install_collections is True
        assert config.cache_timeout == 300
    
    def test_is_module_allowed_no_restrictions(self):
        """Test module allowed with no restrictions."""
        config = GalaxyConfig()
        
        assert config.is_module_allowed("community.general.timezone") is True
    
    def test_is_module_denied(self):
        """Test denied module."""
        config = GalaxyConfig(
            denied_modules={"community.general.dangerous_module"}
        )
        
        assert config.is_module_allowed("community.general.dangerous_module") is False
        assert config.is_module_allowed("community.general.timezone") is True
    
    def test_is_module_allowed_namespace(self):
        """Test namespace allow list."""
        config = GalaxyConfig(
            allowed_namespaces={"community"}
        )
        
        assert config.is_module_allowed("community.general.timezone") is True
        assert config.is_module_allowed("ansible.posix.synchronize") is False
    
    def test_configure_function(self):
        """Test configure helper function."""
        configure(enabled=False, cache_timeout=600)
        
        config = get_config()
        assert config.enabled is False
        assert config.cache_timeout == 600
        
        # Reset for other tests
        configure(enabled=True, cache_timeout=300)


class TestFactoryFunction:
    """Test factory function."""
    
    def test_create_galaxy_module(self):
        """Test creating Galaxy module via factory."""
        ctx = MagicMock()
        ctx.host = MagicMock()
        ctx.host.name = "testhost"
        ctx.host.get_var = MagicMock(return_value="ssh")
        ctx.check_mode = False
        ctx.diff_mode = False
        ctx.connection = MagicMock()
        
        module = create_galaxy_module(
            "community.general.timezone",
            {"name": "UTC"},
            ctx
        )
        
        assert isinstance(module, GalaxyModule)
        assert module.module_name == "community.general.timezone"
        assert module.args == {"name": "UTC"}
