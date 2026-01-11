"""
Sansible git module

Git repository management.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class GitModule(Module):
    """
    Manage git checkouts of repositories.
    """
    
    name = "git"
    required_args = ["repo", "dest"]
    optional_args = {
        "version": "HEAD",      # Branch, tag, or commit hash
        "clone": True,          # Clone if repo doesn't exist
        "update": True,         # Update if repo exists
        "force": False,         # Force update even with local modifications
        "depth": None,          # Create shallow clone with history depth
        "bare": False,          # Create bare repository
        "single_branch": False,  # Clone only specified branch
        "recursive": True,      # Initialize submodules recursively
        "key_file": None,       # SSH private key file
        "ssh_opts": None,       # SSH options
        "accept_hostkey": False,  # Auto-accept SSH host key
        "refspec": None,        # Refspec to fetch
        "remote": "origin",     # Remote name
        "umask": None,          # Umask to apply
    }
    
    async def run(self) -> ModuleResult:
        """Manage git repository."""
        repo = self.args["repo"]
        dest = self.args["dest"]
        version = self.get_arg("version", "HEAD")
        clone = self.get_arg("clone", True)
        update = self.get_arg("update", True)
        force = self.get_arg("force", False)
        depth = self.get_arg("depth")
        bare = self.get_arg("bare", False)
        recursive = self.get_arg("recursive", True)
        key_file = self.get_arg("key_file")
        
        # Build SSH wrapper command if needed
        ssh_env = ""
        if key_file:
            ssh_env = f"GIT_SSH_COMMAND='ssh -i {key_file} -o StrictHostKeyChecking=no' "
        
        # Check if destination exists
        stat_result = await self.connection.stat(dest)
        repo_exists = stat_result.get("exists", False)
        
        if not repo_exists and not clone:
            return ModuleResult(
                changed=False,
                msg=f"Repository {dest} does not exist and clone=False",
            )
        
        # Clone or update
        if not repo_exists:
            # Clone the repository
            if self.check_mode:
                return ModuleResult(
                    changed=True,
                    msg=f"Would clone {repo} to {dest}",
                )
            
            clone_opts = []
            if depth:
                clone_opts.append(f"--depth {depth}")
            if bare:
                clone_opts.append("--bare")
            if recursive:
                clone_opts.append("--recursive")
            if version != "HEAD":
                clone_opts.append(f"-b {version}")
            
            opts_str = " ".join(clone_opts)
            cmd = f"{ssh_env}git clone {opts_str} {repo} {dest}"
            
            result = await self.connection.run(cmd)
            
            if result.rc != 0:
                return ModuleResult(
                    failed=True,
                    msg=f"git clone failed: {result.stderr}",
                )
            
            # Get current commit
            commit_result = await self.connection.run(
                f"cd {dest} && git rev-parse HEAD")
            
            return ModuleResult(
                changed=True,
                msg=f"Cloned {repo} to {dest}",
                results={
                    "after": commit_result.stdout.strip() if commit_result.rc == 0 else "",
                    "before": None,
                },
            )
        
        # Repository exists - update if requested
        if not update:
            return ModuleResult(
                changed=False,
                msg=f"Repository {dest} exists and update=False",
            )
        
        # Get current commit before update
        before_result = await self.connection.run(
            f"cd {dest} && git rev-parse HEAD")
        before_commit = before_result.stdout.strip() if before_result.rc == 0 else ""
        
        if self.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Would update {dest} to {version}",
            )
        
        # Fetch updates
        fetch_cmd = f"cd {dest} && {ssh_env}git fetch --all"
        await self.connection.run(fetch_cmd)
        
        # Handle local changes
        if force:
            await self.connection.run(f"cd {dest} && git reset --hard")
            await self.connection.run(f"cd {dest} && git clean -fd")
        
        # Checkout requested version
        checkout_cmd = f"cd {dest} && git checkout {version}"
        result = await self.connection.run(checkout_cmd)
        
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"git checkout failed: {result.stderr}",
            )
        
        # Pull if on a branch
        remote = self.get_arg("remote", "origin")
        pull_cmd = f"cd {dest} && {ssh_env}git pull {remote} {version}"
        await self.connection.run(pull_cmd)
        
        # Update submodules
        if recursive:
            await self.connection.run(
                f"cd {dest} && git submodule update --init --recursive")
        
        # Get commit after update
        after_result = await self.connection.run(
            f"cd {dest} && git rev-parse HEAD")
        after_commit = after_result.stdout.strip() if after_result.rc == 0 else ""
        
        changed = before_commit != after_commit
        
        return ModuleResult(
            changed=changed,
            msg=f"Repository updated" if changed else "Repository already up to date",
            results={
                "before": before_commit,
                "after": after_commit,
            },
        )
