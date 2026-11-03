# Changelog

All notable changes to Sansible are documented here. Versions are `<ansible-core version>.<revision>`.

## [2.22.0.1] - 2026-11-03

Sansible is now a distribution of the real ansible-core that runs natively on Windows,
replacing the original from-scratch engine (preserved on the `legacy-0.4` branch; 0.4.1
remains installable from PyPI).

### Added
- ansible-core 2.22.0 (exact pin) with an import-time compatibility layer, loaded automatically
  by `sansible_autoload.pth`; the stock `ansible-*` commands work on Windows.
- Persistent spawn-based worker pool replacing fork-per-task workers (default on Windows,
  `SANSIBLE_WORKER=pool` elsewhere). Results identical to fork on ansible-core's own
  integration targets; Ctrl-C stops workers together with the processes their tasks started.
- `sansible.core.paramiko` connection plugin (adapted from ansible-core's removed paramiko
  plugin); Windows controllers use it for `ssh`.
- `sansible.core.winlocal` connection plugin: PowerShell-based local execution on Windows
  controllers (`local`, implicit `localhost`, `delegate_to: localhost`).
- `sansible doctor` command.
- CI on Linux, macOS and Windows (Python 3.13/3.14) with real SSH and PSRP targets and
  ansible-core integration targets; daily tracking of new ansible-core releases with automatic
  test-gated publishing.

### Changed
- License: GPL-3.0-or-later (was MIT).
- Requires Python 3.13+.

### Removed
- The original Sansible engine, modules and CLIs (see the `legacy-0.4` branch).

## [0.2.0] - 2025-01-11

### Added
- **Handlers support**: `handlers`, `notify`, and `listen` now work
- **Block support**: `block/rescue/always` for error handling
- **Privilege escalation**: `become`, `become_user`, `become_method`
- **Fact gathering**: `gather_facts: true` and `setup` module
- **Check mode**: `--check` flag for dry-run execution
- **Diff mode**: `--diff` flag to show file content differences
- **New modules**:
  - `stat` / `win_stat` - File status information
  - `lineinfile` / `win_lineinfile` - Line management in files
  - `wait_for` / `win_wait_for` - Wait for port/file conditions
  - `win_service` - Windows service management
  - `setup` - Fact gathering
  - `file` - File/directory/symlink management
  - `template` - Jinja2 template rendering
- Comprehensive example playbooks in `examples/playbooks/`
- 209 unit tests passing

### Changed
- Updated to Development Status :: 4 - Beta
- Improved documentation (README, COMPATIBILITY, STATUS)
- Better error messages for unsupported features

### Fixed
- Block parsing now supports nested blocks
- pre_tasks now correctly supports blocks

## [0.1.0] - 2025-01-10

### Added
- Initial release
- Core playbook execution engine
- INI and YAML inventory support
- `host_vars/` and `group_vars/` directory loading
- SSH connection via `asyncssh`
- WinRM connection via `pypsrp`
- Local connection for control node
- Core modules: `command`, `shell`, `raw`, `copy`, `debug`, `set_fact`, `fail`, `assert`
- Windows modules: `win_command`, `win_shell`, `win_copy`, `win_file`
- Jinja2 templating with common filters
- Parallel execution with `--forks`
- Conditionals (`when`), loops (`loop`, `with_items`)
- Registered variables, `changed_when`, `failed_when`
- Tags and `--limit` support
- JSON output mode (`--json`)
- Role support (tasks, defaults, vars)
- Golden tests comparing against `ansible-playbook`
- Docker-based SSH integration tests
- Pure Python wheel (`py3-none-any`)

[0.2.0]: https://github.com/sansible/sansible/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/sansible/sansible/releases/tag/v0.1.0
