# AI Agent Prompt: Sansible Linux Testing

## Context
You are testing sansible, a pure-Python Ansible runner. Your task is to validate all Linux modules work correctly against a real target.

## Prerequisites
- Python 3.10+
- Target: Linux server with SSH access
- Inventory file at `tests/e2e/live_inventory.ini`

## Testing Workflow

### Step 1: Build and Install
```bash
cd /path/to/sansible
python -m build --wheel
pip install dist/sansible-*.whl --force-reinstall
```

### Step 2: Run Unit Tests
```bash
pytest tests/unit/ -q --tb=no
```
**Expected**: `307 passed` (or similar count, all green)

### Step 3: Run Linux Module Tests
```bash
sansible-playbook -i tests/e2e/live_inventory.ini tests/e2e/test_all_linux_modules.yml -v
```

### Expected Results
```
PLAY RECAP ************************************************************
linux_target                             : ok=35  changed=25  failed=2  skipped=2
```

- `failed=2` is **expected** (intentional failures for assert/block testing)
- `skipped=2` is **expected** (conditional tests)

## Troubleshooting

### If unit tests fail:
1. Read the error message
2. Check `src/sansible/modules/` for the failing module
3. Fix and re-run

### If integration tests fail unexpectedly:
1. Check SSH connectivity: `ssh user@host`
2. Verify inventory file has correct credentials
3. Check module output in verbose mode
4. Fix module source and re-test

### Common Issues

| Symptom | Cause | Fix |
|---------|-------|-----|
| Connection refused | SSH not running | Start sshd on target |
| Authentication failed | Wrong password | Update inventory |
| Module not found | Import error | Check `modules/base.py` imports |
| Permission denied | sudo needed | Add `become: true` to play |

## Success Criteria

1. All 307 unit tests pass
2. Integration tests: `ok=35 changed=25 failed=2 skipped=2`
3. No unexpected failures

## Files to Modify if Fixing Issues

| File | Purpose |
|------|---------|
| `src/sansible/modules/builtin_*.py` | Linux modules |
| `src/sansible/engine/runner.py` | Execution engine |
| `src/sansible/connections/ssh_asyncssh.py` | SSH connection |
| `tests/e2e/test_all_linux_modules.yml` | Test playbook |
