"""
Sansible unarchive module

Extract compressed archives on remote machines.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class UnarchiveModule(Module):
    """
    Unpack an archive on a remote machine.
    
    Supports .tar, .tar.gz, .tar.bz2, .zip, etc.
    """
    
    name = "unarchive"
    required_args = ["src", "dest"]
    optional_args = {
        "remote_src": False,  # If true, src is on remote machine
        "creates": None,  # Skip if this path exists
        "list_files": False,
        "exclude": [],
        "include": [],
        "keep_newer": False,
        "extra_opts": [],
        "copy": True,  # Deprecated alias for remote_src=false
    }
    
    async def run(self) -> ModuleResult:
        """Extract archive to destination."""
        src = self.args["src"]
        dest = self.args["dest"]
        remote_src = self.get_arg("remote_src", False)
        creates = self.get_arg("creates")
        list_files = self.get_arg("list_files", False)
        exclude = self.get_arg("exclude", [])
        extra_opts = self.get_arg("extra_opts", [])
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Check creates condition
        if creates:
            stat_result = await self.connection.stat(creates)
            if stat_result and stat_result.get("exists", False):
                return ModuleResult(
                    changed=False,
                    msg=f"Skipped - {creates} already exists",
                )
        
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Would extract {src} to {dest}",
            )
        
        # If src is local, copy it to remote first
        if not remote_src:
            import os
            import base64
            
            if not os.path.exists(src):
                return ModuleResult(
                    failed=True,
                    msg=f"Source file not found: {src}",
                )
            
            # Create temp file on remote
            result = await self.connection.run("mktemp", shell=True)
            if result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to create temp file: {result.stderr}",
                )
            
            remote_archive = result.stdout.strip()
            
            # Copy file to remote
            try:
                await self.connection.put(src, remote_archive)
            except Exception as e:
                return ModuleResult(
                    failed=True,
                    msg=f"Failed to copy archive to remote: {e}",
                )
            
            archive_path = remote_archive
        else:
            archive_path = src
        
        # Ensure destination exists
        result = await self.connection.run(f"mkdir -p '{dest}'", shell=True)
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to create destination directory: {result.stderr}",
            )
        
        # Detect archive type and build extraction command
        archive_lower = src.lower()
        
        if archive_lower.endswith('.zip'):
            extract_cmd = f"unzip -o '{archive_path}' -d '{dest}'"
            if exclude:
                for ex in exclude:
                    extract_cmd += f" -x '{ex}'"
        elif archive_lower.endswith('.tar.gz') or archive_lower.endswith('.tgz'):
            extract_cmd = f"tar -xzf '{archive_path}' -C '{dest}'"
            if exclude:
                for ex in exclude:
                    extract_cmd += f" --exclude='{ex}'"
        elif archive_lower.endswith('.tar.bz2') or archive_lower.endswith('.tbz2'):
            extract_cmd = f"tar -xjf '{archive_path}' -C '{dest}'"
            if exclude:
                for ex in exclude:
                    extract_cmd += f" --exclude='{ex}'"
        elif archive_lower.endswith('.tar.xz') or archive_lower.endswith('.txz'):
            extract_cmd = f"tar -xJf '{archive_path}' -C '{dest}'"
            if exclude:
                for ex in exclude:
                    extract_cmd += f" --exclude='{ex}'"
        elif archive_lower.endswith('.tar'):
            extract_cmd = f"tar -xf '{archive_path}' -C '{dest}'"
            if exclude:
                for ex in exclude:
                    extract_cmd += f" --exclude='{ex}'"
        else:
            # Try to auto-detect with file command
            extract_cmd = f"tar -xf '{archive_path}' -C '{dest}'"
        
        # Add extra options
        if extra_opts:
            extract_cmd += " " + " ".join(extra_opts)
        
        # Extract
        result = await self.connection.run(extract_cmd, shell=True)
        
        # Cleanup temp file if we copied it
        if not remote_src:
            await self.connection.run(f"rm -f '{archive_path}'", shell=True)
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to extract archive: {result.stderr}",
            )
        
        return ModuleResult(
            changed=True,
            msg=f"Extracted {src} to {dest}",
            results={
                "src": src,
                "dest": dest,
            },
        )
