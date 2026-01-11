# Sansible End-to-End Testing

> **Purpose**: Production validation of all sansible modules against real Linux and Windows targets.

## Quick Start

```bash
# 1. Create inventory from template
cp test_inventory.ini.template live_inventory.ini

# 2. Edit with your credentials (NEVER commit this file!)
vim live_inventory.ini

# 3. Run tests
sansible-playbook -i live_inventory.ini test_all_linux_modules.yml -v
sansible-playbook -i live_inventory.ini test_all_windows_modules.yml -v
```

## Test Files

| File | Description |
|------|-------------|
| `test_all_linux_modules.yml` | Comprehensive Linux module tests (45 modules) |
| `test_all_windows_modules.yml` | Comprehensive Windows module tests (16 modules) |
| `test_linux_core.yml` | Quick Linux connectivity test |
| `test_windows_core.yml` | Quick Windows connectivity test |
| `quick_test.yml` | Fastest sanity check (ping only) |

## Inventory Setup

### Template Structure

```ini
[linux]
linux_target ansible_host=YOUR_LINUX_IP ansible_user=USERNAME ansible_password=PASSWORD ansible_connection=ssh

[windows]
win_target ansible_host=YOUR_WINDOWS_IP ansible_user=USERNAME ansible_password=PASSWORD ansible_connection=winrm ansible_winrm_transport=ntlm ansible_winrm_server_cert_validation=ignore

[linux:vars]
ansible_ssh_common_args='-o StrictHostKeyChecking=no'

[windows:vars]
ansible_winrm_port=5985
```

### Requirements

**Linux Target:**
- SSH server running
- Python 3 installed
- User with sudo access (for become tests)

**Windows Target:**
- WinRM enabled (HTTP on port 5985)
- NTLM authentication configured
- PowerShell execution policy: RemoteSigned

## Expected Results

### Linux Tests

```
PLAY RECAP ************************************************************
linux_target                             : ok=35  changed=25  failed=2  skipped=2
```

- `failed=2` is expected (intentional failures for assert/block testing)
- `skipped=2` is expected (conditional tests)

### Windows Tests

```
PLAY RECAP ************************************************************
win_target                               : ok=28  changed=17  failed=1
```

- `failed=1` is expected (intentional failure for block testing)

## Troubleshooting

### SSH Connection Issues

```bash
# Test SSH manually
ssh administrator@YOUR_IP

# Check key
ssh -o StrictHostKeyChecking=no administrator@YOUR_IP
```

### WinRM Connection Issues

```powershell
# On Windows target - Enable WinRM
winrm quickconfig

# Set Basic auth (for testing)
Set-Item WSMan:\localhost\Service\Auth\Basic -Value true
Set-Item WSMan:\localhost\Service\AllowUnencrypted -Value true

# Check listener
winrm enumerate winrm/config/listener
```

### Module Failures

1. Check the error message in verbose output
2. Verify target OS has required capabilities
3. Check user permissions (sudo/Administrator)
4. Review module source in `src/sansible/modules/`
