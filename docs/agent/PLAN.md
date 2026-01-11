# Sansible Project Plan

## Vision

Create a Windows-native, pure-Python implementation of Ansible's core functionality that:
- Runs on Windows as a control node without WSL
- Ships as 100% pure Python wheels
- Maintains compatibility with Ansible playbook semantics

## Milestones

### M0 — Evidence & Inventory ⬅️ CURRENT
**Status:** In Progress  
**Goal:** Understand what we're working with

**Definition of Done:**
- [x] Upstream sources identified and pinned by commit hash
- [ ] Automated scans produce:
  - [ ] Dependency tree (runtime)
  - [ ] POSIX-only imports usage map
  - [ ] Transport usage map
- [ ] Concrete "port plan" written in INVENTORY.md

**Tasks:**
1. Clone upstream ansible-core as reference
2. Run `scan_imports.py` on upstream
3. Run `scan_subprocess.py` on upstream
4. Document findings

---

### M1 — Pure-Python Install + CLI Boots
**Status:** Not Started  
**Goal:** Basic installable package

**Definition of Done:**
- [ ] `pip install dist/*.whl` works on Linux and Windows (pure wheel)
- [ ] `sansible --version` prints correctly
- [ ] `sansible-inventory --help` works
- [ ] `python -m tools.dep_audit` passes

**Tasks:**
1. Finalize pyproject.toml
2. Implement version detection
3. Build and test wheel on both platforms
4. Set up CI pipeline

---

### M2 — Inventory + Localhost Execution
**Status:** Not Started  
**Goal:** Run playbooks locally

**Definition of Done:**
- [ ] Inventory parsing works for INI/YAML
- [ ] Running a "localhost" playbook works on Windows & Linux
- [ ] Basic modules work: command, shell, copy, file

**Tasks:**
1. Implement inventory parser (INI format)
2. Implement inventory parser (YAML format)
3. Implement task runner
4. Implement localhost connection
5. Implement command/shell modules
6. Add integration tests

---

### M3 — SSH Transport (Windows → Linux)
**Status:** Not Started  
**Goal:** Remote execution over SSH

**Definition of Done:**
- [ ] From Windows, can run a playbook against a Linux host over SSH
- [ ] Feature minimum: command execution + file transfer + stdout/stderr capture
- [ ] Uses Windows built-in OpenSSH client

**Tasks:**
1. Implement ssh_subprocess transport
2. Implement SFTP/SCP file transfer
3. Implement connection multiplexing
4. Handle SSH key authentication
5. Add integration tests

---

### M4 — WinRM Transport (Windows → Windows)
**Status:** Not Started  
**Goal:** Remote execution over WinRM

**Definition of Done:**
- [ ] Can run a playbook against a Windows host via WinRM
- [ ] Pure Python implementation (no pywinrm with compiled deps)
- [ ] Basic auth over HTTPS works

**Tasks:**
1. Implement WSMan SOAP protocol in pure Python
2. Implement HTTP transport using urllib
3. Implement Basic authentication
4. Implement NTLM authentication (if possible in pure Python)
5. Design Kerberos fallback strategy
6. Add integration tests

---

### M5 — Concurrency, Plugins, Polish
**Status:** Not Started  
**Goal:** Production-ready

**Definition of Done:**
- [ ] Multi-host runs with concurrency work on Windows
- [ ] Plugin loading works for common built-ins
- [ ] "Pure python" audit passes
- [ ] CI green on all platforms

**Tasks:**
1. Implement thread-pool based concurrency
2. Implement plugin discovery and loading
3. Implement fact gathering
4. Optimize performance
5. Documentation and examples
6. Release preparation

---

## Timeline Estimates

| Milestone | Estimated Effort | Dependencies |
|-----------|------------------|--------------|
| M0 | 1-2 days | None |
| M1 | 2-3 days | M0 |
| M2 | 1-2 weeks | M1 |
| M3 | 1-2 weeks | M2 |
| M4 | 2-3 weeks | M2 |
| M5 | 1-2 weeks | M3, M4 |

## Risk Factors

See [RISKS.md](RISKS.md) for detailed risk analysis.

Key risks:
1. Pure Python crypto primitives may be slow
2. WinRM NTLM/Kerberos without compiled libs is complex
3. Upstream Ansible changes faster than we can adapt
