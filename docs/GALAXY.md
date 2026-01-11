# Galaxy Module Support

Sansible provides support for Ansible Galaxy collections through a hybrid strategy that combines native module implementations with remote Ansible execution.

## Overview

When encountering a module specified with a Fully Qualified Collection Name (FQCN), Sansible uses the following resolution strategy:

1. **Native Fallback (Preferred)**: If a native Sansible module exists, use it
2. **Remote Execution**: For modules without native implementations, execute via Ansible on the target host

This approach provides:
- Fast execution for common modules (native implementation)
- Full Galaxy compatibility for specialized modules (remote execution)
- Windows support via native fallback (Ansible cannot run on Windows as controller)

## Supported FQCNs

### Native Fallback

The following namespaces are automatically mapped to native Sansible modules:

| FQCN Pattern | Native Module | Example |
|--------------|---------------|---------|
| `ansible.builtin.*` | Same name | `ansible.builtin.copy` → `copy` |
| `ansible.windows.*` | Same name | `ansible.windows.win_ping` → `win_ping` |
| `ansible.posix.*` | Same name (if native) | `ansible.posix.authorized_key` → `authorized_key` |

### Remote Execution

Other Galaxy modules are executed via Ansible on the target host:

| Collection | Requirement |
|------------|-------------|
| `community.general.*` | Collection installed + Ansible on target |
| `community.windows.*` | Not supported (no Ansible on Windows) |
| `cyberark.pas.*` | Collection installed + Ansible on target |

## Usage Examples

### Using FQCNs (Recommended)

```yaml
- name: Playbook with FQCNs
  hosts: all
  tasks:
    # Uses native copy module
    - ansible.builtin.copy:
        src: /etc/hosts
        dest: /tmp/hosts.bak

    # Uses native win_ping module on Windows
    - ansible.windows.win_ping:
      when: ansible_os_family == 'Windows'

    # Uses Galaxy execution on Linux
    - ansible.posix.authorized_key:
        user: admin
        key: "ssh-rsa AAAA..."
```

### Mixed Playbook

```yaml
- name: Cross-platform playbook
  hosts: all
  tasks:
    # Native modules work everywhere
    - ansible.builtin.debug:
        msg: "Hello from {{ inventory_hostname }}"

    # Windows-specific (native fallback)
    - ansible.windows.win_stat:
        path: C:\Windows\System32\cmd.exe
      when: ansible_os_family == 'Windows'

    # Linux-specific (Galaxy execution)
    - ansible.posix.sysctl:
        name: net.ipv4.ip_forward
        value: '1'
      when: ansible_os_family != 'Windows'
      become: true
```

## Requirements

### For Native Fallback

No additional requirements - works out of the box.

### For Remote Galaxy Execution (Linux targets)

1. **Python** on target host
2. **ansible-core** installed on target (pip install ansible-core)
3. **Collections** installed on target (`ansible-galaxy collection install namespace.collection`)

### Windows Targets

Galaxy modules that don't have native Sansible implementations cannot run on Windows targets. Use native modules instead:

```yaml
# Instead of community.windows.win_timezone, use native alternatives
- ansible.windows.win_shell: |
    tzutil /s "Pacific Standard Time"
```

## Architecture

### Resolution Flow

```
┌─────────────────────────┐
│    Task: module_name    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│  Is FQCN (3 parts)?     │
│  e.g., ansible.builtin. │
│         copy            │
└───────────┬─────────────┘
            │
     ┌──────┴──────┐
     │             │
     No           Yes
     │             │
     ▼             ▼
┌─────────┐  ┌──────────────┐
│ Native  │  │ Has Native   │
│ Module  │  │ Fallback?    │
│ Lookup  │  └───────┬──────┘
└─────────┘          │
              ┌──────┴──────┐
              │             │
             Yes           No
              │             │
              ▼             ▼
        ┌─────────┐  ┌─────────────┐
        │ Native  │  │ Galaxy Exec │
        │ Module  │  │ (Linux only)│
        └─────────┘  └─────────────┘
```

### Components

- **GalaxyModuleLoader** (`galaxy/loader.py`): Manages Ansible/collection availability
- **GalaxyModuleExecutor** (`galaxy/executor.py`): Executes modules via remote Ansible
- **GalaxyModule** (`galaxy/module.py`): Module wrapper integrating with Sansible

## Configuration

Galaxy module behavior can be configured:

```python
from sansible.galaxy import configure_galaxy

configure_galaxy(
    allowed_namespaces=["community.general", "cyberark.pas"],
    denied_modules=["community.general.dangerous_module"],
    auto_install_ansible=True,  # Install ansible-core if missing
    auto_install_collections=True,  # Install collections if missing
)
```

## Limitations

1. **Windows Galaxy Execution**: Not supported (Ansible doesn't run on Windows as controller)
2. **Python 3.6 Deprecation**: Remote hosts with Python 3.6 show deprecation warnings
3. **Collection Compatibility**: Some collections require specific Ansible versions
4. **Network Dependencies**: Collection installation requires internet access on target

## Error Handling

### Module Not Found

```
FAILED - Unknown module: community.unknown.module
```

Ensure the collection is installed on the target host.

### Windows Galaxy Attempt

```
FAILED - Galaxy module 'community.windows.win_timezone' cannot be executed 
on Windows targets. Ansible control node cannot run on Windows. 
Use native Sansible win_* modules instead.
```

Use native `ansible.windows.*` modules instead.

### Collection Installation Failed

```
FAILED - Failed to install collection for community.general.timezone
```

Check network connectivity and target host permissions.

## Testing

Run Galaxy-specific tests:

```bash
pytest tests/unit/test_galaxy.py -v
```

Live testing (requires inventory with Linux and Windows hosts):

```bash
sansible-playbook -i inventory.ini galaxy_test.yml -v
```
