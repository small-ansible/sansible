# Dependency & Feature Inventory

This document tracks the dependency analysis and feature mapping for sansible.

## Upstream Reference

### Pinned Commits
| Repository | Commit Hash | Date | Notes |
|------------|-------------|------|-------|
| ansible/ansible | 28927a70b43a43ecd99d5926ef7860cd6a35d12e | 2026-01-10 | Cloned for analysis |

### Clone Commands
```bash
mkdir -p /home/adam/projects/sansible/upstream
cd /home/adam/projects/sansible/upstream
git clone --depth=1 https://github.com/ansible/ansible.git
cd ansible && git rev-parse HEAD
# Output: 28927a70b43a43ecd99d5926ef7860cd6a35d12e
```

---

## Runtime Dependencies

### sansible Direct Dependencies

| Package | Version | Pure Python | Purpose |
|---------|---------|-------------|---------|
| pyyaml | >=6.0 | Yes* | YAML parsing (inventory, playbooks) |

*Note: PyYAML has optional C extensions but works without them

### Dependency Audit Status

Run `python -m tools.dep_audit` to verify:
- [ ] All dependencies are pure Python
- [ ] No compiled extensions in dependency tree
- [ ] Wheel is tagged `py3-none-any`

---

## POSIX-Only Import Analysis

### Scan Results (from upstream ansible/lib/ansible)

**Total:** 574 files scanned, 117 POSIX-only findings in 36 files

| Module | Usages | Portable Alternative |
|--------|--------|---------------------|
| fcntl | ~15 | sansible.platform.locks (msvcrt on Windows) |
| pwd | ~10 | sansible.platform.users (env vars on Windows) |
| grp | ~5 | sansible.platform.users (stub on Windows) |
| resource | ~3 | Not needed for control node |
| readline | ~2 | Not needed (optional CLI feature) |
| syslog | ~1 | sansible.platform.logging (EventLog on Windows) |
| signal.SIGALRM | ~8 | Thread-based timeout instead |
| signal.alarm | ~6 | Thread-based timeout instead |
| socket.AF_UNIX | ~3 | Named pipes or TCP on Windows |
| os.getuid/geteuid | ~15 | sansible.platform.users (placeholder on Windows) |
| os.chown/lchown | ~10 | No-op on Windows (ACLs different model) |
| os.setsid | ~2 | Not needed (fork-based, we use threads) |

### Key Portability Issues Identified

1. **Locking (fcntl)**: Upstream uses fcntl for file locking. We use msvcrt on Windows.
2. **User/Group (pwd/grp)**: Upstream uses pwd/grp for permission handling. We stub on Windows.
3. **Signals (SIGALRM)**: Upstream uses alarm-based timeouts. We use thread-based timeouts.
4. **Unix Sockets (AF_UNIX)**: Connection multiplexing uses Unix sockets. Alternative needed.
5. **Process Isolation (setsid)**: Worker processes use setsid. We use threads instead.

---

## External Tool Dependencies

### SSH Transport
| Tool | Purpose | Windows Availability |
|------|---------|---------------------|
| ssh | Remote command execution | Windows 10+ built-in |
| sftp | File transfer | Windows 10+ built-in |
| scp | File transfer (fallback) | Windows 10+ built-in |

### Installation Check
```powershell
# Windows
Get-Command ssh, sftp, scp
```
```bash
# Linux
which ssh sftp scp
```

---

## Feature Mapping

### Control Node Components

| Upstream Location | Our Module | Portability Status |
|-------------------|------------|-------------------|
| `lib/ansible/cli/` | `sansible/cli/` | ✓ Portable |
| `lib/ansible/inventory/` | `sansible/inventory/` | Planned |
| `lib/ansible/playbook/` | `sansible/playbook/` | Planned |
| `lib/ansible/executor/` | `sansible/executor/` | Planned |
| `lib/ansible/plugins/connection/` | `sansible/transport/` | Planned |

### Transport Plugins

| Upstream | Our Implementation | Status |
|----------|-------------------|--------|
| `ssh.py` | `sansible/transport/ssh_subprocess.py` | Planned |
| `local.py` | `sansible/transport/local.py` | Planned |
| `winrm.py` | `sansible/transport/winrm.py` | Planned |

### Module Categories

| Category | Priority | Notes |
|----------|----------|-------|
| command/shell | P0 | Core functionality |
| copy/file | P0 | File operations |
| setup (facts) | P1 | Host information |
| template | P1 | Jinja2 templating |
| package managers | P2 | apt, yum, etc. |
| service | P2 | Service management |

---

## Pure Python Implementation Notes

### Cryptography
- SSH: Using subprocess to system ssh (no crypto needed in Python)
- WinRM/HTTPS: Using stdlib ssl module (pure Python interface)
- NTLM: Will port from permissive-licensed implementation

### File Operations
- All through `sansible.platform.fs` abstraction
- Atomic writes handled with tempfile + rename
- Permissions best-effort on Windows

### Process Management
- Subprocess via `sansible.platform.proc`
- No fork() usage (not available on Windows)
- Thread-based parallelism for host execution

---

## Scan Outputs

### POSIX Import Scan (Summary)
```
Files scanned: 574
Findings: 117
Files with findings: 36

Key modules: fcntl (15), pwd (10), grp (5), resource (3), signal.SIGALRM (8)
Key functions: os.getuid (15), os.chown (10), signal.alarm (6)
```

### Subprocess Scan (Summary)
```
Files scanned: 574
Subprocess calls found: 150

External tools: less (1), shred (1), ssh-agent (dynamic)
Most calls are for module execution (expected)
```

---

## Update Log

| Date | What Changed |
|------|--------------|
| 2026-01-10 | Initial inventory structure created |
