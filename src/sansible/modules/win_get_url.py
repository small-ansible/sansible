"""
Sansible win_get_url module

Download files on Windows hosts.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class WinGetUrlModule(Module):
    """
    Download files from HTTP/HTTPS/FTP to Windows hosts.
    """
    
    name = "win_get_url"
    required_args = ["url", "dest"]
    optional_args = {
        "force": False,
        "checksum": None,
        "checksum_algorithm": "sha256",
        "headers": {},
        "url_username": None,
        "url_password": None,
        "use_proxy": True,
        "proxy_url": None,
        "proxy_username": None,
        "proxy_password": None,
        "timeout": 10,
    }
    
    async def run(self) -> ModuleResult:
        """Download file from URL to Windows host."""
        url = self.args["url"]
        dest = self.args["dest"]
        force = self.get_arg("force", False)
        checksum = self.get_arg("checksum")
        checksum_algorithm = self.get_arg("checksum_algorithm", "sha256")
        headers = self.get_arg("headers", {})
        url_username = self.get_arg("url_username")
        url_password = self.get_arg("url_password")
        timeout = int(self.get_arg("timeout", 10))
        
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Check if destination already exists
        if not force:
            check_cmd = f"Test-Path -Path '{dest}' -PathType Leaf"
            result = await self.connection.run(check_cmd, shell=True)
            if 'True' in result.stdout:
                # Verify checksum if provided
                if checksum:
                    verify_cmd = f"(Get-FileHash -Path '{dest}' -Algorithm {checksum_algorithm}).Hash"
                    result = await self.connection.run(verify_cmd, shell=True)
                    current_hash = result.stdout.strip().lower()
                    if current_hash == checksum.lower():
                        return ModuleResult(
                            changed=False,
                            msg=f"File already exists with correct checksum",
                        )
                else:
                    return ModuleResult(
                        changed=False,
                        msg=f"File already exists at {dest}",
                    )
        
        if self.context.check_mode:
            return ModuleResult(
                changed=True,
                msg=f"Would download {url} to {dest}",
            )
        
        # Build download command
        download_cmd = f"""
$ProgressPreference = 'SilentlyContinue'
$params = @{{
    Uri = '{url}'
    OutFile = '{dest}'
    TimeoutSec = {timeout}
    UseBasicParsing = $true
}}
"""
        
        # Add headers
        if headers:
            headers_str = "; ".join([f"'{k}'='{v}'" for k, v in headers.items()])
            download_cmd += f"\n$params['Headers'] = @{{ {headers_str} }}"
        
        # Add credentials
        if url_username and url_password:
            download_cmd += f"""
$secpasswd = ConvertTo-SecureString '{url_password}' -AsPlainText -Force
$credential = New-Object System.Management.Automation.PSCredential('{url_username}', $secpasswd)
$params['Credential'] = $credential
"""
        
        download_cmd += "\nInvoke-WebRequest @params"
        
        result = await self.connection.run(download_cmd, shell=True)
        if result.rc != 0:
            return ModuleResult(
                failed=True,
                msg=f"Failed to download file: {result.stderr}",
            )
        
        # Verify checksum if provided
        if checksum:
            verify_cmd = f"(Get-FileHash -Path '{dest}' -Algorithm {checksum_algorithm}).Hash"
            result = await self.connection.run(verify_cmd, shell=True)
            downloaded_hash = result.stdout.strip().lower()
            if downloaded_hash != checksum.lower():
                return ModuleResult(
                    failed=True,
                    msg=f"Checksum mismatch: expected {checksum}, got {downloaded_hash}",
                )
        
        return ModuleResult(
            changed=True,
            msg=f"Downloaded {url} to {dest}",
            results={"url": url, "dest": dest},
        )
