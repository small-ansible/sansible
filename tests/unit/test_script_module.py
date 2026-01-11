"""
Tests for script module.
"""

import pytest
import os
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch

from sansible.engine.scheduler import HostContext
from sansible.engine.inventory import Host


class TestScriptModule:
    """Tests for the script module."""
    
    def test_script_module_exists(self):
        """Script module can be imported."""
        from sansible.modules.builtin_script import ScriptModule
        assert ScriptModule is not None
        assert ScriptModule.name == "script"
    
    def test_script_required_args(self):
        """Script module requires _raw_params argument."""
        from sansible.modules.builtin_script import ScriptModule
        assert "_raw_params" in ScriptModule.required_args
    
    def test_script_optional_args(self):
        """Script module has optional args."""
        from sansible.modules.builtin_script import ScriptModule
        assert "chdir" in ScriptModule.optional_args
        assert "creates" in ScriptModule.optional_args
        assert "removes" in ScriptModule.optional_args
        assert "executable" in ScriptModule.optional_args
    
    @pytest.mark.asyncio
    async def test_script_no_connection(self):
        """Script module fails without connection."""
        from sansible.modules.builtin_script import ScriptModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        ctx.connection = None
        
        module = ScriptModule({"_raw_params": "/path/to/script.sh"}, ctx)
        result = await module.run()
        
        assert result.failed
        assert "No connection" in result.msg
    
    @pytest.mark.asyncio
    async def test_script_no_script_specified(self):
        """Script module fails with empty params."""
        from sansible.modules.builtin_script import ScriptModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        ctx.connection = MagicMock()
        
        module = ScriptModule({"_raw_params": ""}, ctx)
        result = await module.run()
        
        assert result.failed
        assert "No script specified" in result.msg
    
    @pytest.mark.asyncio
    async def test_script_not_found(self):
        """Script module fails when script file not found."""
        from sansible.modules.builtin_script import ScriptModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        ctx.connection = MagicMock()
        
        module = ScriptModule({"_raw_params": "/nonexistent/script.sh"}, ctx)
        result = await module.run()
        
        assert result.failed
        assert "Script not found" in result.msg
    
    @pytest.mark.asyncio
    async def test_script_creates_skip(self):
        """Script module skips when creates file exists."""
        from sansible.modules.builtin_script import ScriptModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        ctx.connection = MagicMock()
        ctx.connection.stat = AsyncMock(return_value={"exists": True})
        
        module = ScriptModule({
            "_raw_params": "/path/to/script.sh",
            "creates": "/tmp/marker_file",
        }, ctx)
        result = await module.run()
        
        assert not result.failed
        assert not result.changed
        assert "Skipped" in result.msg
    
    @pytest.mark.asyncio
    async def test_script_removes_skip(self):
        """Script module skips when removes file doesn't exist."""
        from sansible.modules.builtin_script import ScriptModule
        
        host = Host(name="test", variables={"ansible_connection": "local"})
        ctx = HostContext(host=host)
        ctx.connection = MagicMock()
        ctx.connection.stat = AsyncMock(return_value=None)
        
        module = ScriptModule({
            "_raw_params": "/path/to/script.sh",
            "removes": "/tmp/should_exist",
        }, ctx)
        result = await module.run()
        
        assert not result.failed
        assert not result.changed
        assert "Skipped" in result.msg
    
    @pytest.mark.asyncio
    async def test_script_check_mode(self):
        """Script module reports would-run in check mode."""
        from sansible.modules.builtin_script import ScriptModule
        
        # Create temp script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("#!/bin/bash\necho 'test'\n")
            script_path = f.name
        
        try:
            host = Host(name="test", variables={"ansible_connection": "local"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = True
            
            module = ScriptModule({"_raw_params": script_path}, ctx)
            result = await module.run()
            
            assert not result.failed
            assert result.changed
            assert "Would run script" in result.msg
        finally:
            os.unlink(script_path)
    
    @pytest.mark.asyncio
    async def test_script_execution_success(self):
        """Script module executes script successfully."""
        from sansible.modules.builtin_script import ScriptModule
        
        # Create temp script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("#!/bin/bash\necho 'hello world'\n")
            script_path = f.name
        
        try:
            host = Host(name="test", variables={"ansible_connection": "local"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = False
            
            # Mock mktemp
            mktemp_result = MagicMock()
            mktemp_result.rc = 0
            mktemp_result.stdout = "/tmp/script_xyz123\n"
            
            # Mock transfer
            transfer_result = MagicMock()
            transfer_result.rc = 0
            
            # Mock chmod
            chmod_result = MagicMock()
            chmod_result.rc = 0
            
            # Mock execution
            exec_result = MagicMock()
            exec_result.rc = 0
            exec_result.stdout = "hello world\n"
            exec_result.stderr = ""
            
            # Mock cleanup
            cleanup_result = MagicMock()
            cleanup_result.rc = 0
            
            ctx.connection.run = AsyncMock(side_effect=[
                mktemp_result,
                transfer_result,
                chmod_result,
                exec_result,
                cleanup_result,
            ])
            
            module = ScriptModule({"_raw_params": script_path}, ctx)
            result = await module.run()
            
            assert not result.failed
            assert result.changed
            assert result.results.get("stdout") == "hello world\n"
            assert result.results.get("rc") == 0
        finally:
            os.unlink(script_path)
    
    @pytest.mark.asyncio
    async def test_script_with_args(self):
        """Script module passes args to script."""
        from sansible.modules.builtin_script import ScriptModule
        
        # Create temp script file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("#!/bin/bash\necho $1 $2\n")
            script_path = f.name
        
        try:
            host = Host(name="test", variables={"ansible_connection": "local"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = False
            
            mktemp_result = MagicMock(rc=0, stdout="/tmp/script_xyz\n")
            transfer_result = MagicMock(rc=0)
            chmod_result = MagicMock(rc=0)
            exec_result = MagicMock(rc=0, stdout="arg1 arg2\n", stderr="")
            cleanup_result = MagicMock(rc=0)
            
            ctx.connection.run = AsyncMock(side_effect=[
                mktemp_result, transfer_result, chmod_result, exec_result, cleanup_result
            ])
            
            module = ScriptModule({"_raw_params": f"{script_path} arg1 arg2"}, ctx)
            result = await module.run()
            
            assert not result.failed
            assert result.changed
        finally:
            os.unlink(script_path)
    
    @pytest.mark.asyncio
    async def test_script_with_chdir(self):
        """Script module uses chdir option."""
        from sansible.modules.builtin_script import ScriptModule
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("#!/bin/bash\npwd\n")
            script_path = f.name
        
        try:
            host = Host(name="test", variables={"ansible_connection": "local"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = False
            
            mktemp_result = MagicMock(rc=0, stdout="/tmp/script_xyz\n")
            transfer_result = MagicMock(rc=0)
            chmod_result = MagicMock(rc=0)
            exec_result = MagicMock(rc=0, stdout="/var/log\n", stderr="")
            cleanup_result = MagicMock(rc=0)
            
            calls = []
            async def capture_run(cmd, shell=False):
                calls.append(cmd)
                results = [mktemp_result, transfer_result, chmod_result, exec_result, cleanup_result]
                return results[len(calls) - 1]
            
            ctx.connection.run = capture_run
            
            module = ScriptModule({
                "_raw_params": script_path,
                "chdir": "/var/log",
            }, ctx)
            result = await module.run()
            
            assert not result.failed
            # Verify chdir was in the execution command
            exec_cmd = calls[3]  # 4th call is execution
            assert "cd '/var/log'" in exec_cmd
        finally:
            os.unlink(script_path)
    
    @pytest.mark.asyncio
    async def test_script_execution_failure(self):
        """Script module handles execution failure."""
        from sansible.modules.builtin_script import ScriptModule
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False) as f:
            f.write("#!/bin/bash\nexit 1\n")
            script_path = f.name
        
        try:
            host = Host(name="test", variables={"ansible_connection": "local"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = False
            
            mktemp_result = MagicMock(rc=0, stdout="/tmp/script_xyz\n")
            transfer_result = MagicMock(rc=0)
            chmod_result = MagicMock(rc=0)
            exec_result = MagicMock(rc=1, stdout="", stderr="error occurred")
            cleanup_result = MagicMock(rc=0)
            
            ctx.connection.run = AsyncMock(side_effect=[
                mktemp_result, transfer_result, chmod_result, exec_result, cleanup_result
            ])
            
            module = ScriptModule({"_raw_params": script_path}, ctx)
            result = await module.run()
            
            assert result.failed
            assert result.results.get("rc") == 1
        finally:
            os.unlink(script_path)
    
    @pytest.mark.asyncio
    async def test_script_with_executable(self):
        """Script module uses custom executable."""
        from sansible.modules.builtin_script import ScriptModule
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write("print('hello from python')\n")
            script_path = f.name
        
        try:
            host = Host(name="test", variables={"ansible_connection": "local"})
            ctx = HostContext(host=host)
            ctx.connection = MagicMock()
            ctx.check_mode = False
            
            mktemp_result = MagicMock(rc=0, stdout="/tmp/script_xyz\n")
            transfer_result = MagicMock(rc=0)
            chmod_result = MagicMock(rc=0)
            exec_result = MagicMock(rc=0, stdout="hello from python\n", stderr="")
            cleanup_result = MagicMock(rc=0)
            
            calls = []
            async def capture_run(cmd, shell=False):
                calls.append(cmd)
                results = [mktemp_result, transfer_result, chmod_result, exec_result, cleanup_result]
                return results[len(calls) - 1]
            
            ctx.connection.run = capture_run
            
            module = ScriptModule({
                "_raw_params": script_path,
                "executable": "/usr/bin/python3",
            }, ctx)
            result = await module.run()
            
            assert not result.failed
            exec_cmd = calls[3]
            assert "/usr/bin/python3" in exec_cmd
        finally:
            os.unlink(script_path)
