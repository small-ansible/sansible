# Sansible Full Test Suite - AI Agent Prompt (Linux Control Node)

> **Purpose**: Download latest sansible, install with uv, test all modules against Linux and Windows targets.
> **Control Node**: Linux with Python 3.10+
> **Package Manager**: uv (Astral)

## Target Credentials

| Target | Host | User | Password | Connection |
|--------|------|------|----------|------------|
| Linux | 192.168.10.181 | administrator | Cyberark01! | SSH |
| Windows | 192.168.100.3 | administrator | Cyberark01! | WinRM (NTLM) |

---

## Step 1: Setup Environment

```bash
# Install uv if not present
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.cargo/env

# Create project directory
mkdir -p ~/sansible-test && cd ~/sansible-test

# Clone latest from GitHub
git clone https://github.com/small-ansible/sansible.git .
# OR if already cloned:
# git pull origin main

# Create venv with uv and install
uv venv
source .venv/bin/activate
uv pip install -e ".[dev,ssh,winrm]"
```

## Step 2: Create Inventory File

```bash
cat > tests/e2e/live_inventory.ini << 'EOF'
[linux]
linux_target ansible_host=192.168.10.181 ansible_user=administrator ansible_password=Cyberark01! ansible_connection=ssh

[windows]
win_target ansible_host=192.168.100.3 ansible_user=administrator ansible_password=Cyberark01! ansible_connection=winrm ansible_winrm_transport=ntlm ansible_winrm_server_cert_validation=ignore

[linux:vars]
ansible_ssh_common_args='-o StrictHostKeyChecking=no'

[windows:vars]
ansible_winrm_port=5985
EOF
```

## Step 3: Run Unit Tests

```bash
pytest tests/unit/ -q --tb=no
```

**Expected**: `307 passed` (approximately)

## Step 4: Run Linux Integration Tests

```bash
sansible-playbook -i tests/e2e/live_inventory.ini tests/e2e/test_all_linux_modules.yml -v
```

**Expected Result**:
```
PLAY RECAP ************************************************************
linux_target                             : ok=35  changed=25  failed=2  skipped=2
```

- `failed=2` is **expected** (intentional test failures)
- `skipped=2` is **expected** (conditional tests)

## Step 5: Run Windows Integration Tests

```bash
sansible-playbook -i tests/e2e/live_inventory.ini tests/e2e/test_all_windows_modules.yml -v
```

**Expected Result**:
```
PLAY RECAP ************************************************************
win_target                               : ok=28  changed=17  failed=1
```

- `failed=1` is **expected** (intentional test failure)

---

## Success Criteria

| Test | Expected | Status |
|------|----------|--------|
| Unit tests | ~307 passed | ⬜ |
| Linux integration | ok=35 changed=25 failed=2 skipped=2 | ⬜ |
| Windows integration | ok=28 changed=17 failed=1 | ⬜ |

## Troubleshooting

### SSH Connection Failed
```bash
# Test SSH manually
ssh administrator@192.168.10.181
# Accept host key if prompted
```

### WinRM Connection Failed
```bash
# Test WinRM port
nc -zv 192.168.100.3 5985

# If pypsrp missing
uv pip install pypsrp
```

### Module Import Error
```bash
# Reinstall
uv pip install -e ".[dev,ssh,winrm]" --force-reinstall
```

---

## Quick One-Liner (After Setup)

```bash
cd ~/sansible-test && source .venv/bin/activate && pytest tests/unit/ -q --tb=no && sansible-playbook -i tests/e2e/live_inventory.ini tests/e2e/test_all_linux_modules.yml -v && sansible-playbook -i tests/e2e/live_inventory.ini tests/e2e/test_all_windows_modules.yml -v
```

---

## Files Modified on Failure

If tests fail unexpectedly, investigate and fix:

| Issue | File to Check |
|-------|---------------|
| Linux module failure | `src/sansible/modules/builtin_*.py` |
| Windows module failure | `src/sansible/modules/win_*.py` |
| SSH connection | `src/sansible/connections/ssh_asyncssh.py` |
| WinRM connection | `src/sansible/connections/winrm_psrp.py` |
| Execution engine | `src/sansible/engine/runner.py` |
| Test playbook | `tests/e2e/test_all_*.yml` |

After fixing, re-run tests until all pass with expected results.
