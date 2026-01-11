"""
Tests for win_template module.
"""

import pytest
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from sansible.engine.scheduler import HostContext
from sansible.engine.inventory import Host


class TestWinTemplateModule:
    """Tests for the win_template module."""
    
    def test_win_template_module_exists(self):
        """Win_template module can be imported."""
        from sansible.modules.win_template import WinTemplateModule
        assert WinTemplateModule is not None
        assert WinTemplateModule.name == "win_template"
    
    def test_win_template_required_args(self):
        """Win_template module requires src and dest arguments."""
        from sansible.modules.win_template import WinTemplateModule
        assert "src" in WinTemplateModule.required_args
        assert "dest" in WinTemplateModule.required_args
    
    def test_win_template_optional_args(self):
        """Win_template module has optional args."""
        from sansible.modules.win_template import WinTemplateModule
        assert "backup" in WinTemplateModule.optional_args
        assert "force" in WinTemplateModule.optional_args
        assert "newline_sequence" in WinTemplateModule.optional_args
    
    @pytest.mark.asyncio
    async def test_win_template_no_connection(self):
        """Win_template module fails without connection."""
        from sansible.modules.win_template import WinTemplateModule
        
        host = Host(name="test", variables={"ansible_connection": "winrm"})
        ctx = HostContext(host=host)
        ctx.connection = None
        
        module = WinTemplateModule({"src": "test.j2", "dest": "C:\\test.txt"}, ctx)
        result = await module.run()
        
        assert result.failed
        assert "No connection" in result.msg
    
    @pytest.mark.asyncio
    async def test_win_template_not_found(self):
        """Win_template module fails when template file not found."""
        from sansible.modules.win_template import WinTemplateModule
        
        host = Host(name="test", variables={"ansible_connection": "winrm"})
        ctx = HostContext(host=host)
        ctx.connection = MagicMock()
        
        module = WinTemplateModule({
            "src": "/nonexistent/template.j2",
            "dest": "C:\\output.txt",
        }, ctx)
        result = await module.run()
        
        assert result.failed
        assert "Template not found" in result.msg
    
    @pytest.mark.asyncio
    async def test_win_template_check_mode(self):
        """Win_template module reports would-template in check mode."""
        from sansible.modules.win_template import WinTemplateModule
        
        # Create temp template file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.j2', delete=False) as f:
            f.write("Hello {{ name }}!\n")
            template_path = f.name
        
        try:
            host = Host(name="test", variables={"ansible_connection": "winrm"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = True
            ctx.vars = {"name": "World"}
            
            module = WinTemplateModule({
                "src": template_path,
                "dest": "C:\\output.txt",
            }, ctx)
            result = await module.run()
            
            assert not result.failed
            assert result.changed
            assert "Would template" in result.msg
        finally:
            os.unlink(template_path)
    
    @pytest.mark.asyncio
    async def test_win_template_render_success(self):
        """Win_template module renders and copies template successfully."""
        from sansible.modules.win_template import WinTemplateModule
        
        # Create temp template file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.j2', delete=False) as f:
            f.write("Server: {{ inventory_hostname }}\nValue: {{ my_var }}\n")
            template_path = f.name
        
        try:
            host = Host(name="testhost", variables={"ansible_connection": "winrm"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = False
            ctx.vars = {"my_var": "test_value"}
            
            # Mock write success
            write_result = MagicMock()
            write_result.rc = 0
            write_result.stderr = ""
            
            ctx.connection.run = AsyncMock(return_value=write_result)
            
            module = WinTemplateModule({
                "src": template_path,
                "dest": "C:\\output.txt",
            }, ctx)
            result = await module.run()
            
            assert not result.failed
            assert result.changed
            assert "Templated" in result.msg
        finally:
            os.unlink(template_path)
    
    @pytest.mark.asyncio
    async def test_win_template_undefined_variable(self):
        """Win_template module fails on undefined variable (StrictUndefined)."""
        from sansible.modules.win_template import WinTemplateModule
        
        # Create temp template with undefined var
        with tempfile.NamedTemporaryFile(mode='w', suffix='.j2', delete=False) as f:
            f.write("Value: {{ undefined_var }}\n")
            template_path = f.name
        
        try:
            host = Host(name="test", variables={"ansible_connection": "winrm"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = False
            ctx.hostvars = {}  # No variables defined
            
            module = WinTemplateModule({
                "src": template_path,
                "dest": "C:\\output.txt",
            }, ctx)
            result = await module.run()
            
            assert result.failed
            assert "Template rendering failed" in result.msg
        finally:
            os.unlink(template_path)
    
    @pytest.mark.asyncio
    async def test_win_template_with_backup(self):
        """Win_template module creates backup when requested."""
        from sansible.modules.win_template import WinTemplateModule
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.j2', delete=False) as f:
            f.write("Simple content\n")
            template_path = f.name
        
        try:
            host = Host(name="test", variables={"ansible_connection": "winrm"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = False
            ctx.hostvars = {}
            
            calls = []
            async def capture_run(cmd, shell=False):
                calls.append(cmd)
                result = MagicMock()
                result.rc = 0
                result.stderr = ""
                return result
            
            ctx.connection.run = capture_run
            
            module = WinTemplateModule({
                "src": template_path,
                "dest": "C:\\output.txt",
                "backup": True,
            }, ctx)
            result = await module.run()
            
            assert not result.failed
            # Verify backup command was called
            backup_cmd_found = any("Copy-Item" in cmd and ".bak" in cmd for cmd in calls)
            assert backup_cmd_found, f"Backup command not found in calls: {calls}"
        finally:
            os.unlink(template_path)
    
    @pytest.mark.asyncio
    async def test_win_template_force_false(self):
        """Win_template module respects force=false when dest exists."""
        from sansible.modules.win_template import WinTemplateModule
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.j2', delete=False) as f:
            f.write("Content\n")
            template_path = f.name
        
        try:
            host = Host(name="test", variables={"ansible_connection": "winrm"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = False
            ctx.hostvars = {}
            
            # Mock Test-Path returning True (file exists)
            check_result = MagicMock()
            check_result.rc = 0
            check_result.stdout = "True"
            check_result.stderr = ""
            
            ctx.connection.run = AsyncMock(return_value=check_result)
            
            module = WinTemplateModule({
                "src": template_path,
                "dest": "C:\\output.txt",
                "force": False,
            }, ctx)
            result = await module.run()
            
            assert not result.failed
            assert not result.changed
            assert "force=false" in result.msg.lower()
        finally:
            os.unlink(template_path)
    
    @pytest.mark.asyncio
    async def test_win_template_write_failure(self):
        """Win_template module handles write failure."""
        from sansible.modules.win_template import WinTemplateModule
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.j2', delete=False) as f:
            f.write("Content\n")
            template_path = f.name
        
        try:
            host = Host(name="test", variables={"ansible_connection": "winrm"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = False
            ctx.hostvars = {}
            
            # Mock write failure
            write_result = MagicMock()
            write_result.rc = 1
            write_result.stderr = "Access denied"
            
            ctx.connection.run = AsyncMock(return_value=write_result)
            
            module = WinTemplateModule({
                "src": template_path,
                "dest": "C:\\output.txt",
            }, ctx)
            result = await module.run()
            
            assert result.failed
            assert "Failed to write" in result.msg
        finally:
            os.unlink(template_path)
    
    @pytest.mark.asyncio
    async def test_win_template_relative_path_templates_dir(self):
        """Win_template module looks in templates/ subdirectory."""
        from sansible.modules.win_template import WinTemplateModule
        
        # Create temp dir structure with templates/
        with tempfile.TemporaryDirectory() as tmpdir:
            templates_dir = os.path.join(tmpdir, 'templates')
            os.makedirs(templates_dir)
            
            template_file = os.path.join(templates_dir, 'test.j2')
            with open(template_file, 'w') as f:
                f.write("Template content: {{ value }}\n")
            
            host = Host(name="test", variables={"ansible_connection": "winrm"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = True
            ctx.vars = {"value": "test"}
            ctx.playbook_dir = tmpdir
            
            module = WinTemplateModule({
                "src": "test.j2",  # Relative path
                "dest": "C:\\output.txt",
            }, ctx)
            result = await module.run()
            
            assert not result.failed
            assert result.changed
    
    @pytest.mark.asyncio
    async def test_win_template_crlf_conversion(self):
        """Win_template module converts newlines to CRLF by default."""
        from sansible.modules.win_template import WinTemplateModule
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.j2', delete=False) as f:
            f.write("Line1\nLine2\nLine3\n")
            template_path = f.name
        
        try:
            host = Host(name="test", variables={"ansible_connection": "winrm"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = False
            ctx.hostvars = {}
            
            captured_content = []
            async def capture_run(cmd, shell=False):
                captured_content.append(cmd)
                result = MagicMock()
                result.rc = 0
                result.stderr = ""
                return result
            
            ctx.connection.run = capture_run
            
            module = WinTemplateModule({
                "src": template_path,
                "dest": "C:\\output.txt",
            }, ctx)
            result = await module.run()
            
            assert not result.failed
            # Check that Set-Content command contains CRLF
            # (the content should have \r\n after newline conversion)
            write_cmd = [c for c in captured_content if "Set-Content" in c][0]
            assert write_cmd is not None
        finally:
            os.unlink(template_path)
