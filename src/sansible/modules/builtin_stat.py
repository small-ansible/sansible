"""
Sansible stat module

Retrieve file or directory status.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class StatModule(Module):
    """
    Retrieve file or directory status.
    
    Returns facts about the specified path including:
    - exists: whether the path exists
    - isdir: whether it's a directory
    - isreg: whether it's a regular file
    - mode: permissions mode
    - size: file size in bytes
    - uid/gid: owner/group IDs
    """
    
    name = "stat"
    required_args = ["path"]
    optional_args = {
        "follow": True,  # Follow symlinks
        "get_checksum": True,  # Calculate checksum
        "checksum_algorithm": "sha1",  # Checksum algorithm
    }
    
    async def run(self) -> ModuleResult:
        """Get file/directory status."""
        path = self.args["path"]
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        try:
            stat_info = await self.connection.stat(path)
            
            # connection.stat returns a dict or None
            if stat_info is None:
                # File doesn't exist
                stat_result = {
                    "exists": False,
                    "path": path,
                }
            else:
                stat_result = {
                    "exists": stat_info.get("exists", True),
                    "path": path,
                    "isdir": stat_info.get("isdir", False),
                    "isreg": stat_info.get("isfile", stat_info.get("isreg", False)),
                    "mode": stat_info.get("mode", ""),
                    "size": stat_info.get("size", 0),
                    "uid": stat_info.get("uid", 0),
                    "gid": stat_info.get("gid", 0),
                }
            
            return ModuleResult(
                changed=False,  # stat never changes anything
                msg="File stat retrieved",
                results={"stat": stat_result},
            )
        except Exception as e:
            return ModuleResult(
                failed=True,
                msg=f"Failed to stat {path}: {e}",
            )
