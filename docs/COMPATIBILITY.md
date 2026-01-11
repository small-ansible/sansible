# Sansible Compatibility Matrix

This document defines the **tested and verified** features of Sansible v0.4.

> **Last Updated:** January 11, 2026  
> **Test Systems:** Linux RHEL 8.5 (SSH) | Windows Server 2019/2022 (WinRM)

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ L | Tested on Linux |
| ✅ W | Tested on Windows |
| ✅ L/W | Tested on both platforms |
| ⚠️ | Partial support / limitations |
| ❌ | Not supported |

---

## Modules

### Core Modules (Platform-independent)

| Module | Linux | Windows | Status | Notes |
|--------|:-----:|:-------:|--------|-------|
| `ping` | ✅ | - | Tested | Connection test |
| `debug` | ✅ | ✅ | Tested L/W | msg, var output |
| `set_fact` | ✅ | ✅ | Tested L/W | Variable setting |
| `assert` | ✅ | ✅ | Tested L/W | Condition assertion |
| `fail` | ✅ | ✅ | Tested L/W | Intentional failure |
| `pause` | ✅ | ✅ | Tested L/W | Execution pause |
| `meta` | ✅ | ✅ | Tested L/W | noop, refresh_inventory |
| `include_vars` | ✅ | ✅ | Tested L/W | Load YAML vars |
| `add_host` | ✅ | ✅ | Tested L/W | Dynamic inventory |
| `group_by` | ✅ | ✅ | Tested L/W | Dynamic grouping |

### Linux Modules

| Module | Linux | Status | Notes |
|--------|:-----:|--------|-------|
| `command` | ✅ | Tested | Execute commands |
| `shell` | ✅ | Tested | Shell expansion works |
| `raw` | ✅ | Tested | Raw command execution |
| `copy` | ✅ | Tested | content, src/dest |
| `file` | ✅ | Tested | directory, touch, absent |
| `stat` | ✅ | Tested | File info retrieval |
| `slurp` | ✅ | Tested | Read file (base64) |
| `fetch` | ✅ | Tested | Download from remote |
| `template` | ✅ | Tested | Jinja2 templating |
| `lineinfile` | ✅ | Tested | Line management |
| `blockinfile` | ✅ | Tested | Block management |
| `replace` | ✅ | Tested | Regex replacement |
| `find` | ✅ | Tested | File discovery |
| `tempfile` | ✅ | Tested | Create temp files |
| `setup` | ✅ | Tested | Fact gathering |
| `wait_for` | ✅ | Tested | Port/file waiting |
| `wait_for_connection` | ✅ | Tested | Connection waiting |
| `uri` | ✅ | Tested | HTTP requests |
| `get_url` | ✅ | Tested | Download from URL |
| `yum` | ✅ | Tested | RedHat package management |
| `dnf` | ✅ | Tested | Fedora package management |
| `apt` | - | Available | Debian package management |
| `pip` | ✅ | Tested | Python package management |
| `git` | ✅ | Tested | Git operations |
| `cron` | ✅ | Tested | Cron job management |
| `systemd` | ✅ | Tested | Systemd service management |
| `service` | ✅ | Tested | Service management |
| `hostname` | ✅ | Tested | Hostname management |
| `known_hosts` | ✅ | Tested | SSH known hosts |
| `unarchive` | ✅ | Tested | Archive extraction |
| `getent` | ✅ | Tested | Name service lookup |
| `reboot` | ✅ | Tested | System reboot (check mode) |
| `user` | ✅ | Tested | User management |
| `group` | ✅ | Tested | Group management |
| `script` | ✅ | Tested | Local script transfer & execution |

### Windows Modules

| Module | Windows | Status | Notes |
|--------|:-------:|--------|-------|
| `win_ping` | ✅ | Tested | Returns pong |
| `win_command` | ✅ | Tested | Execute cmd commands |
| `win_shell` | ✅ | Tested | PowerShell execution |
| `win_copy` | ✅ | Tested | File copy with content |
| `win_file` | ✅ | Tested | directory, absent states |
| `win_stat` | ✅ | Tested | File info retrieval |
| `win_slurp` | ✅ | Tested | Read file content |
| `win_template` | ✅ | Tested | Jinja2 templating |
| `win_lineinfile` | ✅ | Tested | Line management |
| `win_service` | ✅ | Tested | Service management |
| `win_wait_for` | ✅ | Tested | Port/file waiting |
| `win_user` | ✅ | Tested | User management |
| `win_group` | ✅ | Tested | Group management |
| `win_reboot` | ✅ | Tested | System reboot (check mode) |
| `win_get_url` | ✅ | Tested | Download from URL |
| `win_hostname` | ✅ | Tested | Hostname management |

---

## Galaxy FQCN Support

| Namespace | Linux | Windows | Notes |
|-----------|:-----:|:-------:|-------|
| `ansible.builtin.*` | ✅ | ✅ | Maps to native modules |
| `ansible.windows.*` | - | ✅ | Maps to native win_* modules |
| `ansible.posix.*` | ✅ | - | Remote execution on Linux |
| `community.general.*` | ✅ | - | Remote execution on Linux |

---

## Playbook Features

| Feature | Linux | Windows | Status |
|---------|:-----:|:-------:|--------|
| Multiple plays | ✅ | ✅ | Tested L/W |
| `vars` | ✅ | ✅ | Tested L/W |
| `vars_files` | ✅ | ✅ | Tested L/W |
| `gather_facts` | ✅ | ✅ | Tested L/W |
| `when` conditionals | ✅ | ✅ | Tested L/W |
| `loop` / `with_items` | ✅ | ✅ | Tested L/W |
| `register` | ✅ | ✅ | Tested L/W |
| `changed_when` / `failed_when` | ✅ | ✅ | Tested L/W |
| `ignore_errors` | ✅ | ✅ | Tested L/W |
| `handlers` / `notify` | ✅ | ✅ | Tested L/W |
| `check_mode` (global) | ✅ | ✅ | Tested L/W |
| `check_mode` (task-level) | ✅ | ✅ | Tested L/W |
| `diff` mode | ✅ | ✅ | Tested L/W |
| `tags` / `skip-tags` | ✅ | ✅ | Tested L/W |
| `become` (sudo) | ✅ | - | Tested L |
| `delegate_to` | ✅ | ✅ | Tested L/W |
| `block/rescue/always` | ✅ | ✅ | Tested L/W |
| `include_tasks` / `import_tasks` | ✅ | ✅ | Tested L/W |
| `include_role` / `import_role` | ✅ | ✅ | Tested L/W |
| Roles | ✅ | ✅ | Tested L/W |
| Vault | ✅ | ✅ | Tested L/W |
| Dynamic inventory | ✅ | ✅ | JSON scripts |

---

## Jinja2 Filters

| Filter | Linux | Windows | Notes |
|--------|:-----:|:-------:|-------|
| `default` / `d` | ✅ | ✅ | Default values |
| `lower` / `upper` | ✅ | ✅ | Case conversion |
| `replace` | ✅ | ✅ | String replacement |
| `to_json` | ✅ | ✅ | JSON serialization |
| `to_yaml` | ✅ | ✅ | YAML serialization |
| `trim` | ✅ | ✅ | Whitespace trimming |
| `join` | ✅ | ✅ | List joining |
| `first` / `last` | ✅ | ✅ | List access |
| `length` | ✅ | ✅ | Collection size |
| `int` / `bool` / `string` | ✅ | ✅ | Type conversion |
| `basename` / `dirname` | ✅ | ✅ | Path manipulation |
| `regex_replace` | ✅ | ✅ | Regex substitution |
| `b64encode` / `b64decode` | ✅ | ✅ | Base64 encoding |
| `combine` | ✅ | ✅ | Dict merging |

### Jinja2 Lookups

Supported lookup plugins:

| Lookup | Supported | Notes |
|--------|:---------:|-------|
| `file` | ✅ | Read file content |
| `env` | ✅ | Read environment variable |
| `pipe` | ✅ | Execute command and return stdout |
| `fileglob` | ✅ | Glob pattern matches |
| `first_found` | ✅ | Return first existing file |
| `items` | ✅ | Return list of items |
| `dict` | ✅ | Convert dict to list of {key,value} |
| `password` | ✅ | Read password file (strips whitespace) |
| `lines` | ✅ | Read file lines |

### Jinja2 Tests

| Test | Linux | Windows | Notes |
|------|:-----:|:-------:|-------|
| `defined` / `undefined` | ✅ | ✅ | Variable existence |
| `string` / `number` | ✅ | ✅ | Type checking |
| `mapping` / `sequence` / `iterable` | ✅ | ✅ | Container type checking |
| `failed` / `success` / `succeeded` | ✅ | ✅ | Task result tests |
| `changed` / `skipped` | ✅ | ✅ | Task result tests |

---

## Connections

| Connection | Status | Notes |
|------------|--------|-------|
| `local` | ✅ Tested | Control node execution |
| `ssh` | ✅ Tested L | asyncssh, Linux/Unix hosts |
| `winrm` | ✅ Tested W | pypsrp, Windows hosts |

---

## CLI Options

| Option | Linux | Windows | Notes |
|--------|:-----:|:-------:|-------|
| `-i, --inventory` | ✅ | ✅ | Inventory file/directory |
| `-l, --limit` | ✅ | ✅ | Host pattern limiting |
| `-t, --tags` | ✅ | ✅ | Run specific tags |
| `--skip-tags` | ✅ | ✅ | Skip specific tags |
| `-e, --extra-vars` | ✅ | ✅ | Extra variables |
| `-f, --forks` | ✅ | ✅ | Parallel execution |
| `-C, --check` | ✅ | ✅ | Dry-run mode |
| `--diff` | ✅ | ✅ | Show file differences |
| `--json` | ✅ | ✅ | JSON output format |
| `--vault-password-file` | ✅ | ✅ | Vault password |
| `--ask-vault-pass` | ✅ | ✅ | Prompt for vault |
| `-v/-vv/-vvv` | ✅ | ✅ | Verbosity levels |

---

## Not Supported

| Feature | Reason |
|---------|--------|
| `async` / `poll` | Asynchronous task execution |
| `lookup()` functions | Now supported (file, env, pipe, fileglob, first_found, items, dict, password, lines) |
| Callbacks / Plugins | Architecture limitation |
| Galaxy install (`ansible-galaxy`) | Out of scope |
| Network device connections | netconf, etc. |
| Custom Jinja2 filters | Built-in only |

---

## Test Coverage

### Unit Tests: 307 Passed ✅

All core functionality has comprehensive unit test coverage.

### Live System Tests

| Target | Connection | Modules Tested | Status |
|--------|------------|----------------|--------|
| Linux RHEL 8.5 | SSH | 36+ | ✅ All passing |
| Windows Server 2019 | WinRM | 17+ | ✅ All passing |

### Key Fixes in v0.4.0

- Fixed `ignore_errors` not preventing host failure flag
- Added task-level `check_mode` support
- Fixed git module null stat handling
- Added `b64decode` and `b64encode` filters
- Added `combine` filter support
- Added `failed`/`success`/`changed`/`skipped` tests
- Added `playbook_dir` variable for template/script modules
- Added `args:` key support for modules (script, command, etc.)
- Added `script` module free-form parsing
- Fixed `win_template` variable resolution

---

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Host failure(s) occurred |
| 3 | Parse/syntax error |
| 4 | Unsupported feature used |
