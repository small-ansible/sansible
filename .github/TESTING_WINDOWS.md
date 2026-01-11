# AI Agent Prompt: Sansible Windows Testing

## Context
You are testing sansible, a pure-Python Ansible runner. Your task is to validate all Windows modules work correctly against a real Windows Server target.

## Prerequisites
- Python 3.10+
- pypsrp installed: `pip install "sansible[winrm]"`
- Target: Windows Server with WinRM enabled
- Inventory file at `tests/e2e/live_inventory.ini`

## Testing Workflow

### Step 1: Verify Environment
```bash
cd /path/to/sansible
pip install ".[winrm]"  # Install with WinRM support
```

### Step 2: Verify Unit Tests Pass
```bash
pytest tests/unit/ -q --tb=no
```
**Expected**: All tests pass

### Step 3: Run Windows Module Tests
```bash
sansible-playbook -i tests/e2e/live_inventory.ini tests/e2e/test_all_windows_modules.yml -v
```

### Expected Results
```
PLAY RECAP ************************************************************
win_target                               : ok=28  changed=17  failed=1
```

- `failed=1` is **expected** (intentional failure for block testing)

## Windows Target Setup

### Enable WinRM (Run as Administrator on Windows target)
```powershell
# Quick setup
winrm quickconfig -force

# Enable NTLM auth
Set-Item WSMan:\localhost\Service\Auth\Basic -Value true
Set-Item WSMan:\localhost\Service\AllowUnencrypted -Value true

# Configure HTTP listener
winrm set winrm/config/service '@{AllowUnencrypted="true"}'
winrm set winrm/config/service/auth '@{Basic="true"}'

# Verify
winrm enumerate winrm/config/listener
```

### Firewall (if needed)
```powershell
New-NetFirewallRule -Name "WinRM-HTTP" -DisplayName "WinRM HTTP" -Protocol TCP -LocalPort 5985 -Action Allow
```

## Troubleshooting

### Connection Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Connection refused | WinRM not running | Run `winrm quickconfig` |
| 401 Unauthorized | Auth not configured | Enable Basic/NTLM auth |
| SSL error | HTTPS required | Use port 5986 or disable SSL |
| Timeout | Firewall blocking | Open port 5985 |

### Module Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| PowerShell error | Script syntax | Check module's PowerShell code |
| Access denied | Not administrator | Use Administrator account |
| Path not found | Wrong drive | Verify path format `C:\path` |

## Success Criteria

1. Connection to Windows target succeeds
2. Integration tests: `ok=28 changed=17 failed=1`
3. No unexpected failures

## Files to Modify if Fixing Issues

| File | Purpose |
|------|---------|
| `src/sansible/modules/win_*.py` | Windows modules |
| `src/sansible/connections/winrm_psrp.py` | WinRM connection |
| `tests/e2e/test_all_windows_modules.yml` | Test playbook |

## Quick Test Commands

```bash
# Quick connectivity test
sansible-playbook -i tests/e2e/live_inventory.ini tests/e2e/test_windows_core.yml -v

# Full module test
sansible-playbook -i tests/e2e/live_inventory.ini tests/e2e/test_all_windows_modules.yml -v
```
