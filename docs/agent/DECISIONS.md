# Architecture Decision Records (ADRs)

This document captures key architectural decisions made during sansible development.

---

## ADR-001: Use subprocess for SSH Transport (Phase A)

**Date:** 2026-01-10  
**Status:** Accepted

### Context
SSH implementations typically require compiled cryptography libraries (paramiko needs cryptography, which has Rust/C extensions).

### Decision
Implement SSH transport using subprocess calls to the system's OpenSSH client (`ssh`, `sftp`, `scp`).

### Rationale
1. Windows 10+ includes OpenSSH client by default
2. Subprocess approach is pure Python (just calling executables)
3. Faster time-to-working-implementation
4. Feature-complete SSH without reimplementing crypto

### Consequences
- Positive: Pure Python wheel, works out of the box on modern Windows
- Positive: Full SSH feature support (ProxyJump, certificates, etc.)
- Negative: Requires SSH client installed on control node
- Negative: Slightly higher overhead than native library

### Future
Phase B may implement a minimal pure-Python SSH client for environments without system SSH.

---

## ADR-002: Platform Abstraction Layer

**Date:** 2026-01-10  
**Status:** Accepted

### Context
Ansible's codebase has POSIX assumptions scattered throughout. We need systematic portability.

### Decision
Create a `sansible.platform` package that abstracts all OS-specific operations:
- `paths.py` - Path handling
- `fs.py` - Filesystem operations
- `proc.py` - Process execution
- `concurrency.py` - Parallel execution
- `tty.py` - Terminal handling
- `users.py` - User/permission abstractions
- `locks.py` - File locking

### Rationale
1. Single place to handle Windows/Unix differences
2. Testable abstractions
3. Clear API for the rest of the codebase
4. No scattered `if platform.system() == "Windows"` checks

### Consequences
- Positive: Clean separation of concerns
- Positive: Easy to test platform-specific behavior
- Negative: Indirection overhead
- Negative: Must maintain abstraction as new needs arise

---

## ADR-003: Thread-based Concurrency (Default)

**Date:** 2026-01-10  
**Status:** Accepted

### Context
Ansible uses multiprocessing with `fork()` which doesn't work on Windows.

### Decision
Use `ThreadPoolExecutor` as the default concurrency mechanism.

### Rationale
1. Works identically on Windows and Unix
2. Lower overhead than multiprocessing
3. Sufficient for I/O-bound tasks (SSH/WinRM are network I/O)
4. Avoids `fork()` complications entirely

### Consequences
- Positive: Cross-platform without code changes
- Positive: No pickle/serialization requirements
- Negative: GIL limits CPU parallelism (acceptable for I/O-bound work)
- Negative: Can't use fork-specific features like copy-on-write memory

---

## ADR-004: Pure Python WinRM Implementation

**Date:** 2026-01-10  
**Status:** Accepted

### Context
The `pywinrm` library depends on `requests` and `requests-ntlm` which can pull in compiled dependencies.

### Decision
Implement WinRM protocol from scratch using:
- `urllib.request` / `http.client` for HTTP(S)
- Pure Python NTLM implementation
- WSMan SOAP envelopes built manually

### Rationale
1. Full control over dependencies
2. Can guarantee pure Python
3. WinRM/WSMan protocol is well-documented
4. Only need subset of features for Ansible use cases

### Consequences
- Positive: Guaranteed pure Python
- Positive: No dependency conflicts
- Negative: Significant implementation effort
- Negative: Must handle edge cases ourselves
- Negative: Kerberos may require alternative approach

---

## ADR-005: Separate Namespace from Upstream Ansible

**Date:** 2026-01-10  
**Status:** Accepted

### Context
Need to avoid conflicts with upstream `ansible` package.

### Decision
Use `sansible` as package name and `sansible` as Python module:
- CLI: `sansible`, `sansible-playbook`, `sansible-inventory`
- Module: `import sansible`

### Rationale
1. Can be installed alongside upstream Ansible
2. Clear distinction for users
3. Avoids import conflicts
4. Allows gradual migration

### Consequences
- Positive: No conflicts with existing Ansible installations
- Positive: Users can compare behavior
- Negative: Muscle memory for CLI commands
- Negative: Existing scripts need modification

---

## ADR-006: YAML Parser Selection

**Date:** 2026-01-10  
**Status:** Accepted

### Context
Need to parse YAML inventory and playbooks. PyYAML has optional C extension.

### Decision
Use PyYAML with pure Python fallback:
- PyYAML works without libyaml (C library)
- Just don't use `CLoader`/`CDumper`
- Always use `Loader`/`Dumper`

### Rationale
1. PyYAML's pure Python implementation is mature
2. Performance is acceptable for config files
3. Widely used, well-tested
4. No need to implement YAML parser ourselves

### Consequences
- Positive: Standard YAML support
- Positive: Minimal code to maintain
- Negative: Slightly slower than C version (acceptable)
- Negative: Must ensure we don't accidentally use C extensions

---

## Template for New ADRs

```markdown
## ADR-XXX: Title

**Date:** YYYY-MM-DD  
**Status:** Proposed | Accepted | Deprecated | Superseded

### Context
What is the issue or situation that motivates this decision?

### Decision
What is the decision that was made?

### Rationale
Why was this decision made?

### Consequences
What are the positive and negative results?
```
