# Sansible Roadmap

> **Last Updated:** 2025-01-11
> **Current Version:** v0.1.0 (Alpha)

## Vision

Sansible aims to be a **minimal, pure-Python, Windows-native** Ansible-compatible runner. It's not a full Ansible replacement—it's a focused tool for running simple playbooks without the overhead of full Ansible on Windows.

---

## Release Milestones

### v0.1.0 — Proof of Concept ✅ COMPLETE
**Goal:** Run basic playbooks on localhost

- [x] CLI (`san run`, `sansible-playbook`)
- [x] INI + YAML inventory parsing
- [x] Playbook parser with FQCN support
- [x] Jinja2 templating (variables, filters, tests)
- [x] Conditional execution (`when`)
- [x] Loop support (`loop`, `with_items`)
- [x] Local connection (localhost)
- [x] Core modules: command, shell, raw, copy, debug, set_fact, fail, assert
- [x] Unit test suite (41+ tests)
- [x] Pure Python wheel (`py3-none-any`)

### v0.2.0 — Remote Connections 🔄 IN PROGRESS
**Goal:** Execute on remote Linux (SSH) and Windows (WinRM) targets

- [x] SSH connection implementation (`asyncssh`)
- [x] WinRM/PSRP connection implementation (`pypsrp`)
- [x] Windows modules: win_shell, win_command, win_copy
- [ ] Docker-based SSH integration tests
- [ ] Windows CI integration tests (GitHub Actions)
- [ ] Golden tests vs `ansible-playbook`

### v0.3.0 — Production Readinesscreate ai instrutcions end execute them based on current project :



Let's say I am on Windows and I want to run just simple playbooks, either through WinRM or run something on Windows target host or SSH on Linux target host. The playbooks should be compatible with the Ansible, but I don't even need the parallelism or anything else like that. I just need the way how to interact with the general Ansible playbooks and be able to have the smallest possible footprint in Python, which is able to translate it into functional working code using Ansible and Ansible Galaxy plugins and whatever else like that, and then it would be able to run it and execute it. It doesn't have to be full replacement of Ansible, but it needs to be sort of a replacement that I am able to use any playbooks which are not specifically dependent, but which are able to use just functions like SSH or WinRM and then execute the code. So that is my highest priority as the first making proof of concept replacement of Ansible by Sansible.
how many core modules are there foransible to work prortly nad how many are posix specific ? , otr even better how to make minisnasible . takes invnetory , lnpws basic thinkgs  like copy fils remote code execution ... in ansible way , so it can use existing playbooks with just lisstle work . nothing complicated just playboppook wrapper sort of for most ofthe used use acses ]

ChatGPT can make mistakes. Check important info. See Cookie Preferences.You’re asking for two things that fight each other:

“Very small footprint”

“Completely compatible with current Ansible codebase”

Full Ansible compatibility means re-implementing (or bundling) Ansible’s entire execution model: inventory semantics, variable precedence, templating filters/tests, plugins, strategies, callbacks, connection layers, module execution, collections, vault, etc. That’s… not “small.” It’s basically “Ansible, but again.”

So the sane path is:

Define a strict “supported subset” that covers your real use-cases (copy + remote exec over SSH/WinRM + inventory + parallelism).

Build Sansible as a small runner for that subset.

Prove correctness by golden tests: run the same playbooks with ansible-playbook and with san and compare outcomes.

Also: Ansible’s own docs explicitly warn the Python API isn’t something they consider supported/stable.
So Sansible should not depend on undocumented internals unless you accept churn.

Below is a copy/paste mega-prompt for an AI coding agent to implement this as a real repo with tests + docs.

# AI AGENT PROMPT — Build “Sansible” (minimal Ansible-compatible runner)

## Role
You are a senior Python engineer building a minimal “Ansible-like” runner called **Sansible**.
You will implement a **small-footprint** executable that can run **basic Ansible playbooks** against:
- Linux hosts over **SSH**
- Windows hosts over **WinRM/PSRP (PowerShell Remoting)**

The project must include:
- A working CLI (`san`)
- Core engine for playbooks + inventory + parallel execution
- Minimal module set (copy + remote command execution)
- Integration tests that compare Sansible behavior to real `ansible-playbook` (golden tests)
- Clear docs + “AI handoff” docs for future agents

IMPORTANT: Do not aim for full Ansible compatibility. Implement a **documented supported subset** that matches common/simple playbooks. If a playbook uses unsupported features, fail fast with a precise error.

## North Star
Goal: “Tiny Ansible footprint” that can run simple playbooks with minimal changes:
- Inventory-driven host selection
- Parallel execution across hosts (forks-like)
- Copy file(s) to target
- Execute commands/scripts remotely
- Windows via PowerShell (WinRM/PSRP)
- Linux via SSH
- Deterministic output and sensible exit codes

## Hard Constraints
- Keep runtime dependencies minimal.
- Separate dependencies by extras:
  - `sansible[ssh]` for SSH deps
  - `sansible[winrm]` for WinRM deps
  - `sansible[dev]` for tests, linting, ansible oracle, docker tooling
- Tests must be runnable locally and in CI.
- Provide excellent error messages and logs.
- Provide docs and AI handoff markdown files.

## Reality Check / Compatibility Contract
Create `docs/COMPATIBILITY.md` that explicitly lists what is supported.

### Supported subset v0.1 (must implement)
**Inventory**
- INI inventory file: hosts, groups, group children, vars sections.
- Host patterns: `all`, `group`, `host`, `group:children` (basic), `--limit`.
- `host_vars/` and `group_vars/` directories (YAML).

**Playbooks**
- One or more plays:
  - `hosts`
  - `vars` and `vars_files` (YAML only)
  - `tasks` (no handlers initially)
  - `gather_facts: false` default (facts not implemented)
- Task fields:
  - `name`
  - module invocation by key or FQCN:
    - `copy` or `ansible.builtin.copy`
    - `command` / `shell` / `raw`
    - Windows: `win_shell` / `win_command` / `win_copy`
  - `args` / inline params
  - `register`
  - `when` (basic boolean/jinja expression)
  - `loop` / `with_items` (list only)
- Variable templating:
  - Jinja2 rendering inside strings for task args, `when`, and `vars`.
  - Provide a minimal filter set: `default`, `lower`, `upper`, `replace`, `to_json`.

**Execution model**
- Strategy: “linear” like Ansible:
  - For each task, run it across all hosts in parallel (bounded by `--forks`)
  - Each host executes tasks sequentially
- Fail behavior:
  - If a host fails a task, mark host failed and skip remaining tasks on that host (configurable later).
- Output:
  - Human-readable console output similar-ish to Ansible (ok/changed/failed per host per task)
  - Optional JSON output `--json` with structured results.

**Connections**
- SSH:
  - Use `asyncssh` if possible (preferred for concurrency); fallback to `paramiko` if needed.
  - Support key auth, optional password auth, known_hosts handling (default accept-new).
- Windows:
  - Use `pypsrp` (PSRP over WinRM) for PowerShell execution and file transfer. (Ansible itself supports psrp/winrm and installs separate deps.) Document this.  
  - Implement `win_shell`/`win_command` by running PowerShell and capturing stdout/stderr/rc.
  - Implement `win_copy` by base64 chunk upload + PowerShell to reassemble on target (chunked, safe for large files).

## Non-goals (explicitly NOT implemented in v0.1)
- Ansible collections/galaxy dependency resolution
- Handlers, notify, async/poll
- Become/sudo/runas
- Complex var precedence identical to Ansible
- Facts gathering
- Templating parity with Ansible filters/tests (only minimal set)
- Jinja2 sandbox parity
- Network devices, privilege escalation, vault, callbacks/plugins

Fail fast with explicit errors when encountering these.

## Repo Layout (must create)


sansible/
pyproject.toml
README.md
LICENSE
src/sansible/
init.py
cli.py
engine/
init.py
inventory.py
playbook.py
templating.py
scheduler.py
results.py
errors.py
connections/
init.py
base.py
ssh_asyncssh.py
winrm_psrp.py
transfer.py
modules/
init.py
base.py
builtin_copy.py
builtin_command.py
builtin_shell.py
builtin_raw.py
win_copy.py
win_shell.py
win_command.py
tests/
unit/
integration/
fixtures/
inventory.ini
playbooks/
linux_smoke.yml
windows_smoke.yml
mixed_smoke.yml
docs/
ARCHITECTURE.md
COMPATIBILITY.md
TESTING.md
ROADMAP.md
AI_HANDOFF.md
AI_TASKS_NEXT.md
.github/workflows/ci.yml


## CLI Spec
Command:
- `san run -i INVENTORY playbook.yml [--limit ...] [--forks N] [--json] [--check] [--diff]`
Only implement `--check/--diff` as “recognized but not supported” (error) in v0.1, unless trivial.

Exit codes:
- 0: success for all hosts
- 2: one or more hosts failed
- 3: invalid input / parse errors
- 4: unsupported feature encountered

## Implementation Details

### Inventory Parser
- Parse INI inventory format:
  - `[group]`
  - `[group:children]`
  - `[group:vars]`
  - host lines: `host ansible_host=... ansible_user=... ansible_port=... ansible_connection=ssh|winrm`
- Store host vars and group vars.
- Merge with `group_vars/` and `host_vars/` YAML (optional but implement).

### Playbook Parser
- Use `yaml.safe_load_all`.
- Normalize module invocation:
  - `copy:` and `ansible.builtin.copy:` map to module id `copy`
- Parse task args:
  - Inline style: `copy: src=a dest=b`
  - Dict style: `copy: {src: a, dest: b}`
- Validate required args per module; error nicely.

### Templating
- Jinja2 Environment with strict undefined.
- Render strings recursively in dict/list structures.
- Minimal filters:
  - implement `to_json` using `json.dumps`
- Evaluate `when`:
  - render as Jinja expression returning truthy
  - allow simple forms: `var == "x"`, `var is defined` (implement `defined` as best-effort)

### Scheduler / Parallelism
- Use `asyncio`.
- For each task:
  - create per-host coroutine
  - run with semaphore sized `forks`
  - gather results
- Maintain per-host context:
  - vars
  - registered vars
  - connection object
  - failed flag

### Connection Abstractions
Define base class:
- `run(command: str, shell: bool, timeout: int|None) -> RunResult`
- `put(local_path, remote_path) -> None`
- `mkdir(remote_path) -> None` (best-effort)

SSH:
- run via remote shell or exec
- put via SFTP
Windows (pypsrp):
- run via PowerShell (for both command and shell tasks; “win_command” should avoid shell features but in practice run as PowerShell with stricter quoting)
- put via chunked base64:
  - read file bytes
  - split chunks (e.g., 700KB)
  - for each chunk: send PS that appends bytes to temp file
  - finalize move to dest
  - ensure directories exist

### Modules
Implement module interface:
- input: args dict + host context
- output: `{changed: bool, rc: int, stdout: str, stderr: str, ...}`

Modules to implement:
- `copy`:
  - args: `src`, `dest`
  - For SSH: upload file; changed true if remote differs (simple: compare size+mtime or hash if cheap)
  - For Windows: same concept
- `command`:
  - run without shell interpretation (best-effort)
- `shell`:
  - run via shell (`/bin/sh -lc` on linux; PowerShell on windows)
- `raw`:
  - run exactly as provided (no JSON, no templating except string render)
- Windows:
  - `win_shell`, `win_command`, `win_copy` map to WinRM connection equivalents

### Output
- Print task banner `TASK [name]`
- For each host:
  - `ok: [host]`, `changed: [host]`, `failed: [host] (rc=...)`
- Final recap:
  - `ok= changed= failed= skipped=` per host

Also provide `--json`:
- machine-readable results: per play -> per task -> per host.

## Testing Strategy (must implement)

### Unit tests
- inventory parsing
- playbook parsing and normalization
- templating + when evaluation
- scheduler semantics (forks limit)

### Integration tests (Linux)
Use Docker to run an SSH target container and run playbooks against it.
- Bring up container in test using `docker` python SDK or `pytest-docker` (choose simplest).
- Provide inventory pointing to container.
- Test playbook `linux_smoke.yml`:
  - copy a file
  - run `cat` to confirm content
  - run shell to create a file
- Assert:
  - Sansible returns success
  - Running the same playbook with real `ansible-playbook` also returns success (oracle).
  - Idempotency: run twice; second run has fewer/no “changed” (best-effort)

### Integration tests (Windows)
Provide two modes:
- CI on GitHub Actions windows runner:
  - Configure WinRM locally and target `localhost` with WinRM listener.
  - Run `windows_smoke.yml` with Sansible.
- Local dev:
  - Mark as `pytest -m windows` and skip if env vars not set.

### Golden tests vs Ansible
Add a test helper that:
- runs `ansible-playbook` with same inventory and playbook (only in dev/test environment)
- runs `san run ...`
- compares:
  - both exit success
  - basic side effects match (files exist, command output contains expected lines)

Document test setup in `docs/TESTING.md` and note that Ansible’s own testing tooling exists, but we’re using Ansible as an oracle rather than running Ansible’s CI suite. (Ansible unit tests use pytest; ansible-test exists but is geared to Ansible/collections.)  

## Packaging
- Use `pyproject.toml` with extras:
  - `ssh = ["asyncssh>=..."]`
  - `winrm = ["pypsrp>=..."]`
  - `dev = ["pytest", "pytest-xdist", "ruff", "mypy", "ansible-core", "docker", ...]`
- Provide a console entry point `san=sansible.cli:main`.

Optional: Provide PyInstaller recipe later; document in ROADMAP.

## Documentation (must write)
- `README.md`: what it is, what it is not, quick start
- `docs/ARCHITECTURE.md`: data flow, scheduler model, connections, module system
- `docs/COMPATIBILITY.md`: exact supported subset + examples + unsupported features behavior
- `docs/TESTING.md`: how to run unit/integration tests + docker notes + windows notes
- `docs/ROADMAP.md`: staged expansion (handlers, become, more modules)
- `docs/AI_HANDOFF.md`: “how to continue work” (key files, invariants, how to add modules/connections)
- `docs/AI_TASKS_NEXT.md`: curated backlog for future agents

## Deliverables Checklist
- [ ] Working `san run` CLI
- [ ] INI inventory support + vars merge
- [ ] Playbook parser + subset semantics
- [ ] Jinja2 templating + basic `when` + loops
- [ ] Async scheduler with forks limit
- [ ] SSH connection + copy/command/shell/raw
- [ ] WinRM/PSRP connection + win_shell/win_command/win_copy
- [ ] Console output + JSON output mode
- [ ] Unit tests + Linux docker integration tests
- [ ] Windows tests (CI-friendly)
- [ ] Golden tests running against `ansible-playbook` in dev
- [ ] Full docs set

## Finish Condition
Work until:
- `pytest` passes (unit + linux integration)
- Golden tests comparing Sansible vs Ansible pass for supported playbooks
- Docs are accurate and explicit
- `san` can run at least `linux_smoke.yml` end-to-end and (in windows mode) `windows_smoke.yml`

Now implement everything. No stubs. No “TODO” left in core paths. If something is out of scope, error clearly and document it.

A couple of blunt but useful notes

WinRM is always the pain point. Ansible itself treats WinRM/PSRP as “extra Python requirements,” not bundled. That’s normal.

Using Ansible as an oracle is the fastest way to prove your subset behaves correctly, without pretending you can run Ansible’s entire internal test suite (which is designed for Ansible’s own repo/collections). Ansible’s docs on testing/ansible-test exist, but they’re not a turnkey harness for “a separate Ansible-like runner.”

If later you decide you really want “full compatibility,” the honest solution is: ship ansible-core, and your “Neo” becomes a slim wrapper around it (plus packaging tricks like pipx, zipapp, PyInstaller). That’s bigger, but it’s real.

This prompt sets you up for a POC that actually ships, works, and has proofs—without accidentally signing up to recreate the entire Ansible universe in your basement.
**Goal:** Feature parity for common automation tasks

- [ ] JSON output mode (`--json`)
- [ ] Check mode (`--check`)
- [ ] Diff mode (`--diff`)
- [ ] Improved error messages with line numbers
- [ ] Verbose mode levels (`-v`, `-vv`, `-vvv`)
- [ ] Configuration file support (`~/.sansible.cfg`)
- [ ] SSH agent forwarding
- [ ] SSH jump hosts (ProxyJump)

### v0.4.0 — Extended Modules
**Goal:** Add commonly needed modules

- [ ] `file` module (permissions, directories, symlinks)
- [ ] `template` module (Jinja2 templates with dest)
- [ ] `lineinfile` module
- [ ] `blockinfile` module
- [ ] `fetch` module
- [ ] `stat` module
- [ ] `wait_for` module
- [ ] `pause` module

### v0.5.0 — Handlers & Blocks
**Goal:** More Ansible semantics

- [ ] Handler system (`handlers:`, `notify`)
- [ ] Block/rescue/always
- [ ] `any_errors_fatal`
- [ ] `max_fail_percentage`

### v1.0.0 — Stable Release
**Goal:** Production-ready for documented subset

- [ ] Complete documentation
- [ ] API stability commitment
- [ ] Performance benchmarks
- [ ] Security audit
- [ ] PyInstaller single-binary option
- [ ] Homebrew/Chocolatey packages

---

## Non-Goals (Intentionally Out of Scope)

These features are **not planned** for Sansible:

1. **Full Ansible Compatibility** — Use `ansible-core` for complex workflows
2. **Collections/Galaxy** — No automatic module download
3. **Roles** — Convert to inline tasks
4. **Dynamic Inventory** — Static inventory only
5. **Vault** — External secret management recommended
6. **Callback Plugins** — Fixed output format
7. **Strategy Plugins** — Linear strategy only
8. **Connection Plugins (other)** — SSH and WinRM only
9. **Facts Gathering** — Use explicit data gathering
10. **Network Device Modules** — Not in scope

---

## Contributing Priorities

If you want to contribute, these are the most impactful areas:

### High Priority
1. **Integration Tests** — Docker SSH tests, Windows CI
2. **Golden Tests** — Ansible comparison framework
3. **Bug Fixes** — Edge cases in templating, inventory
4. **Documentation** — Examples, tutorials

### Medium Priority
1. **New Modules** — Following existing patterns
2. **Error Messages** — Better diagnostics
3. **Performance** — Connection pooling, caching

### Lower Priority
1. **New Features** — Check roadmap above
2. **Refactoring** — Only if it improves clarity

---

## Compatibility Strategy

### Ansible Version Tracking
- Sansible targets behavior compatible with Ansible 2.15+
- We test against `ansible-core` in golden tests
- Breaking changes in Ansible are evaluated case-by-case

### Python Version Support
- Minimum: Python 3.9
- Tested: Python 3.9, 3.10, 3.11, 3.12, 3.13
- No Python 2 support ever

### Platform Support
- Linux: Full support as control and target
- macOS: Full support as control and target
- Windows: Full support as control node, target via WinRM

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-01-10 | Use `asyncssh` over `paramiko` | Pure Python + async native |
| 2025-01-10 | Use `pypsrp` for WinRM | Modern PSRP protocol, cleaner API |
| 2025-01-10 | Default `gather_facts: false` | Facts not implemented |
| 2025-01-11 | Fail fast on unsupported features | Clear error > silent misbehavior |
| 2025-01-11 | Pure Python wheel only | Cross-platform requirement |

---

## FAQ

**Q: Why not just use Ansible?**
A: Ansible is excellent but requires WSL on Windows as a control node. Sansible runs natively on Windows with minimal dependencies.

**Q: Will Sansible support roles?**
A: No. Convert role tasks to inline in your playbooks. This keeps Sansible simple.

**Q: What about Ansible Galaxy collections?**
A: Not supported. If you need collection modules, use full Ansible.

**Q: How does Sansible handle unsupported features?**
A: It fails immediately with a clear error message pointing to the unsupported feature.

**Q: Can I use Sansible in production?**
A: For simple playbooks in the documented subset, yes. For complex automation, use Ansible.
