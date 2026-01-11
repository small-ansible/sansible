"""
Sansible setup module (gather_facts)

Collect minimal system facts from target hosts.
"""

from sansible.modules.base import Module, ModuleResult, register_module


@register_module
class SetupModule(Module):
    """
    Gather minimal facts about target hosts.
    
    Collects:
    - ansible_hostname: short hostname
    - ansible_fqdn: fully qualified domain name
    - ansible_os_family: OS family (Debian, RedHat, Windows, etc.)
    - ansible_system: OS type (Linux, Windows, Darwin)
    - ansible_distribution: distribution name
    - ansible_architecture: CPU architecture
    
    This is a minimal implementation for Sansible - not full Ansible facts.
    """
    
    name = "setup"
    required_args = []
    optional_args = {
        "gather_subset": ["all"],  # "all", "min", "network", etc.
        "filter": None,  # Filter facts by pattern
    }
    
    async def run(self) -> ModuleResult:
        """Gather facts about the target system."""
        if not self.connection:
            return ModuleResult(
                failed=True,
                msg="No connection available",
            )
        
        # Detect if Windows based on connection type or host vars
        is_windows = self._is_windows()
        
        if is_windows:
            facts = await self._gather_windows_facts()
        else:
            facts = await self._gather_linux_facts()
        
        return ModuleResult(
            changed=False,  # Facts gathering never changes anything
            msg="Facts gathered successfully",
            results={"ansible_facts": facts},
        )
    
    def _is_windows(self) -> bool:
        """Check if target is Windows based on connection type."""
        conn_type = self.context.host.vars.get("ansible_connection", "ssh")
        return conn_type in ("winrm", "psrp")
    
    async def _gather_linux_facts(self) -> dict:
        """Gather facts from a Linux/Unix system."""
        facts = {}
        
        # Get system type
        result = await self.connection.run("uname -s", shell=True)
        if result.rc == 0:
            facts["ansible_system"] = result.stdout.strip()
        
        # Get hostname
        result = await self.connection.run("hostname -s 2>/dev/null || hostname", shell=True)
        if result.rc == 0:
            facts["ansible_hostname"] = result.stdout.strip()
        
        # Get FQDN
        result = await self.connection.run("hostname -f 2>/dev/null || hostname", shell=True)
        if result.rc == 0:
            facts["ansible_fqdn"] = result.stdout.strip()
        
        # Get architecture
        result = await self.connection.run("uname -m", shell=True)
        if result.rc == 0:
            facts["ansible_architecture"] = result.stdout.strip()
        
        # Get OS distribution info from /etc/os-release
        result = await self.connection.run(
            "cat /etc/os-release 2>/dev/null || cat /etc/redhat-release 2>/dev/null || echo 'ID=unknown'",
            shell=True
        )
        if result.rc == 0:
            os_info = self._parse_os_release(result.stdout)
            facts.update(os_info)
        
        # Derive os_family from distribution
        facts["ansible_os_family"] = self._get_os_family(facts.get("ansible_distribution", ""))
        
        return facts
    
    async def _gather_windows_facts(self) -> dict:
        """Gather facts from a Windows system."""
        facts = {
            "ansible_system": "Win32NT",
            "ansible_os_family": "Windows",
        }
        
        # Get hostname
        result = await self.connection.run("$env:COMPUTERNAME", shell=True)
        if result.rc == 0:
            facts["ansible_hostname"] = result.stdout.strip()
        
        # Get OS version
        result = await self.connection.run(
            "(Get-CimInstance Win32_OperatingSystem).Caption",
            shell=True
        )
        if result.rc == 0:
            caption = result.stdout.strip()
            facts["ansible_distribution"] = caption
            facts["ansible_os_name"] = caption
        
        # Get architecture
        result = await self.connection.run(
            "(Get-CimInstance Win32_OperatingSystem).OSArchitecture",
            shell=True
        )
        if result.rc == 0:
            facts["ansible_architecture"] = result.stdout.strip()
        
        return facts
    
    def _parse_os_release(self, content: str) -> dict:
        """Parse /etc/os-release content."""
        facts = {}
        for line in content.splitlines():
            line = line.strip()
            if "=" in line:
                key, _, value = line.partition("=")
                value = value.strip('"\'')
                if key == "ID":
                    facts["ansible_distribution"] = value.capitalize()
                elif key == "VERSION_ID":
                    facts["ansible_distribution_version"] = value
                elif key == "PRETTY_NAME":
                    facts["ansible_distribution_pretty"] = value
        return facts
    
    def _get_os_family(self, distribution: str) -> str:
        """Map distribution to OS family."""
        dist_lower = distribution.lower()
        
        # Debian family
        if dist_lower in ("ubuntu", "debian", "linuxmint", "pop", "raspbian"):
            return "Debian"
        
        # RedHat family
        if dist_lower in ("redhat", "rhel", "centos", "fedora", "rocky", "alma", "oracle"):
            return "RedHat"
        
        # SUSE family
        if dist_lower in ("suse", "opensuse", "sles"):
            return "Suse"
        
        # Arch family
        if dist_lower in ("arch", "manjaro", "endeavouros"):
            return "Archlinux"
        
        # Alpine
        if dist_lower == "alpine":
            return "Alpine"
        
        # Generic fallback
        return "Linux"
