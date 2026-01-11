# AI Tasks — Next Actions for Sansible

> **Purpose:** Curated backlog of tasks for AI agents or developers
> **Last Updated:** 2025-01-11
> **Difficulty:** 🟢 Easy | 🟡 Medium | 🔴 Hard

---

## Immediate Priority (M3 — SSH Integration)

### Task 1: Docker SSH Integration Test 🟡
**Status:** Not Started
**Estimate:** 2-3 hours

Create a Docker-based integration test that:
1. Builds a minimal SSH container (Alpine + OpenSSH)
2. Starts container with known SSH credentials
3. Runs `linux_smoke.yml` against the container via SSH
4. Asserts all tasks succeed

**Files to create:**
- `tests/integration/test_ssh.py`
- `tests/integration/docker/Dockerfile.ssh`
- `tests/integration/docker/docker-compose.yml`

**Acceptance Criteria:**
- `pytest tests/integration/test_ssh.py` passes
- Test is skipped if Docker not available
- Works in GitHub Actions CI

---

### Task 2: SSH Connection Debugging 🟢
**Status:** Not Started  
**Estimate:** 1 hour

Manually test SSH connection with a real host or Docker:

```bash
# Start SSH container
docker run -d -p 2222:22 --name ssh-test \
  -e SSH_USER=testuser -e SSH_PASSWORD=testpass \
  linuxserver/openssh-server

# Test with san
san run -i inventory_docker.ini linux_smoke.yml -vvv
```

Document any issues found.

---

## Second Priority (M4 — WinRM Integration)

### Task 3: WinRM Integration Test (Local) 🟡
**Status:** Not Started
**Estimate:** 2-3 hours

Create integration test for Windows:
1. Configure WinRM listener on localhost (requires admin)
2. Run `windows_smoke.yml` against localhost
3. Assert all tasks succeed

**Files to create:**
- `tests/integration/test_winrm.py`
- `tests/fixtures/playbooks/windows_smoke.yml`
- `scripts/setup_winrm_local.ps1`

**Acceptance Criteria:**
- `pytest tests/integration/test_winrm.py -m windows` passes on Windows
- Test is skipped on Linux
- Works in GitHub Actions Windows runner

---

### Task 4: Windows GitHub Actions CI 🔴
**Status:** Not Started
**Estimate:** 3-4 hours

Add Windows CI workflow:
1. Enable WinRM on Windows runner
2. Run unit tests
3. Run WinRM integration test against localhost
4. Report results

**Files to create/modify:**
- `.github/workflows/ci.yml` (add Windows job)

---

## Third Priority (Features)

### Task 5: JSON Output Mode 🟢
**Status:** Not Started
**Estimate:** 1-2 hours

Implement `--json` flag for machine-readable output:

```bash
san run -i inventory.ini playbook.yml --json > results.json
```

Output format:
```json
{
  "playbook": "playbook.yml",
  "plays": [
    {
      "name": "Play Name",
      "hosts": ["host1", "host2"],
      "tasks": [
        {
          "name": "Task Name",
          "results": {
            "host1": {"status": "ok", "changed": false, ...},
            "host2": {"status": "failed", "msg": "...", ...}
          }
        }
      ]
    }
  ],
  "stats": {
    "host1": {"ok": 5, "changed": 2, "failed": 0, "skipped": 1},
    "host2": {"ok": 3, "changed": 1, "failed": 1, "skipped": 0}
  }
}
```

**Files to modify:**
- `src/sansible/engine/runner.py` (add JSON output option)
- `src/sansible/cli/playbook.py` (add --json flag)

---

### Task 6: Golden Test Framework 🟡
**Status:** Not Started
**Estimate:** 2-3 hours

Create test framework that compares Sansible vs Ansible:

1. Run same playbook with `ansible-playbook` and `san run`
2. Compare:
   - Exit codes match
   - Both succeed or both fail
   - Side effects (file exists, content matches)
3. Report any discrepancies

**Files to create:**
- `tests/golden/test_vs_ansible.py`
- `tests/golden/conftest.py` (fixtures for running both)

**Acceptance Criteria:**
- `pytest tests/golden/` runs both engines
- Clear output showing pass/fail per playbook
- Skips if `ansible-playbook` not installed

---

### Task 7: Verbose Mode Levels 🟢
**Status:** Not Started
**Estimate:** 1 hour

Implement `-v`, `-vv`, `-vvv` verbosity:

| Level | Output |
|-------|--------|
| Default | Task names, status |
| `-v` | + Task results summary |
| `-vv` | + Command outputs |
| `-vvv` | + Connection details, timing |

**Files to modify:**
- `src/sansible/engine/runner.py`
- `src/sansible/san_cli.py`

---

## Module Additions

### Task 8: Add `file` Module 🟢
**Status:** Not Started
**Estimate:** 2 hours

Implement basic `file` module:
- `state: directory` — create directory
- `state: absent` — remove file/directory
- `state: touch` — create empty file
- `mode` — set permissions (Unix only)

**Files to create:**
- `src/sansible/modules/builtin_file.py`
- `tests/unit/test_module_file.py`

---

### Task 9: Add `template` Module 🟡
**Status:** Not Started
**Estimate:** 2-3 hours

Implement `template` module:
- Read source file
- Render with Jinja2
- Write to destination
- Support `mode`, `owner`, `group` (best-effort)

**Files to create:**
- `src/sansible/modules/builtin_template.py`
- `tests/unit/test_module_template.py`
- `tests/fixtures/templates/test.j2`

---

### Task 10: Add `lineinfile` Module 🔴
**Status:** Not Started
**Estimate:** 3-4 hours

Implement `lineinfile` module (common but complex):
- `line` — line to add
- `regexp` — pattern to match
- `state: present|absent`
- `insertbefore`, `insertafter`
- `create: yes|no`

**Files to create:**
- `src/sansible/modules/builtin_lineinfile.py`
- `tests/unit/test_module_lineinfile.py`

---

## Documentation Tasks

### Task 11: Usage Examples 🟢
**Status:** Not Started
**Estimate:** 1 hour

Add example playbooks demonstrating:
- Basic file copy
- Running commands
- Conditional execution
- Loop usage
- Multi-host deployment

**Files to create:**
- `examples/basic_copy.yml`
- `examples/conditional_tasks.yml`
- `examples/loop_example.yml`
- `examples/multi_host.yml`
- `examples/inventory_example.ini`

---

### Task 12: Troubleshooting Guide 🟢
**Status:** Not Started
**Estimate:** 1 hour

Add common problems and solutions:
- SSH connection refused
- WinRM authentication failed
- Module not found
- Template variable undefined
- Permission denied

**Files to create:**
- `docs/TROUBLESHOOTING.md`

---

## Infrastructure

### Task 13: GitHub Actions CI 🟡
**Status:** Not Started
**Estimate:** 2 hours

Create CI workflow:
- Run on push/PR
- Matrix: Python 3.9-3.13
- Run unit tests
- Run linting (ruff)
- Build wheel
- Check pure Python compliance

**Files to create:**
- `.github/workflows/ci.yml`

---

### Task 14: Pre-commit Hooks 🟢
**Status:** Not Started
**Estimate:** 30 min

Add pre-commit configuration:
- ruff linting
- ruff formatting
- mypy type checking
- Check YAML validity

**Files to create:**
- `.pre-commit-config.yaml`

---

## Technical Debt

### Task 15: Improve Error Messages 🟡
**Status:** Not Started
**Estimate:** 2 hours

Enhance error reporting:
- Include playbook line numbers in errors
- Show file path in parse errors
- Suggest fixes for common mistakes
- Color-coded error output

**Files to modify:**
- `src/sansible/engine/errors.py`
- `src/sansible/engine/playbook.py`
- `src/sansible/engine/runner.py`

---

### Task 16: Connection Pooling 🔴
**Status:** Not Started
**Estimate:** 4+ hours

Optimize connection handling:
- Reuse SSH connections across tasks
- Implement connection caching
- Lazy connection establishment
- Graceful connection cleanup

Currently connections are created per host but could be optimized.

---

## How to Pick a Task

1. **New to project?** Start with 🟢 Easy tasks
2. **Want impact?** Prioritize Tasks 1-6 (immediate priorities)
3. **Like testing?** Tasks 1, 3, 6 are test-focused
4. **Like modules?** Tasks 8-10 add new functionality
5. **Like docs?** Tasks 11-12 improve documentation

---

## Completion Checklist

When completing a task:
- [ ] Code follows existing patterns
- [ ] Unit tests added/updated
- [ ] Docstrings added
- [ ] Tested manually
- [ ] Update STATUS.md if needed
- [ ] Commit with descriptive message
