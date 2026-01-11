# Sansible Compatibility

This document defines the **supported subset** of Ansible features in Sansible v0.4.

> **Last Updated:** Live-tested on RHEL 8.5 (SSH) and Windows Server 2019 (WinRM)

## Supported Features

### Inventory

| Feature | Status | Notes |
|---------|--------|-------|
| INI format | ✅ Tested | Standard Ansible INI format |
| YAML format | ✅ Tested | Standard Ansible YAML format |
| `[group]` sections | ✅ Tested | Host grouping |
| `[group:children]` | ✅ Tested | Group inheritance |
| `[group:vars]` | ✅ Tested | Group variables |
| Host patterns (ranges) | ✅ Tested | `web[01:10].example.com` |
| Inline host vars | ✅ Tested | `host ansible_host=x ansible_user=y` |
| `host_vars/` directory | ✅ Tested | Per-host variable files |
| `group_vars/` directory | ✅ Tested | Per-group variable files |
| `--limit` pattern | ✅ Tested | Basic patterns |
| Dynamic inventory | ✅ Supported | JSON format scripts |

### Playbooks

| Feature | Status | Notes |
|---------|--------|-------|
| Multiple plays | ✅ Tested | Sequential execution |
| `hosts` | ✅ Tested | Required per play |
| `vars` | ✅ Tested | Play-level variables |
| `vars_files` | ✅ Tested | YAML files only |
| `tasks` | ✅ Tested | Task list |
| `gather_facts: false` | ✅ Tested | Default is false |
| `gather_facts: true` | ✅ Tested | Gathers OS/hostname facts |
| `handlers` | ✅ Tested | Handler sections with notify |
| `roles` | ✅ Tested | tasks, defaults, vars, handlers |
| `pre_tasks/post_tasks` | ✅ Supported | Before/after main tasks |
| `strategy` | ⚠️ Linear only | Linear strategy implemented |

### Tasks

| Feature | Status | Notes |
|---------|--------|-------|
| `name` | ✅ Tested | Task description |
| Module invocation | ✅ Tested | See modules table |
| FQCN modules | ✅ Tested | `ansible.builtin.*`, `ansible.windows.*` |
| `args` / inline args | ✅ Tested | Dict or `key=value` format |
| `register` | ✅ Tested | Capture output |
| `when` | ✅ Tested | Boolean/Jinja expressions |
| `loop` / `with_items` | ✅ Tested | List iteration |
| `loop_control` | ⚠️ Partial | `loop_var` only |
| `ignore_errors` | ✅ Tested | Continue on failure |
| `changed_when` | ✅ Tested | Override changed status |
| `failed_when` | ✅ Tested | Override failed status |
| `notify` | ✅ Tested | Trigger handlers |
| `become` | ✅ Tested | sudo, su methods |
| `become_user` | ✅ Tested | Target user |
| `become_method` | ✅ Tested | sudo (default), su |
| `block/rescue/always` | ✅ Tested | Error handling blocks |
| `tags` | ✅ Tested | Task tagging |
| `delegate_to` | ✅ Tested | Tested with localhost |
| `include_tasks` | ✅ Supported | Task file inclusion |
| `import_tasks` | ✅ Supported | Static task inclusion |
| `include_role` | ✅ Supported | Dynamic role inclusion |
| `import_role` | ✅ Supported | Static role inclusion |
| `async/poll` | ❌ Not supported | Synchronous only |

### Modules

#### Linux Modules (45+)

| Module | Status | Notes |
|--------|--------|-------|
| `ping` | ✅ Tested | Connection test |
| `command` | ✅ Tested | No shell processing |
| `shell` | ✅ Tested | Full shell support |
| `raw` | ✅ Tested | Direct execution |
| `copy` | ✅ Tested | File/content copy |
| `file` | ✅ Tested | Files/directories/links |
| `template` | ✅ Tested | Jinja2 template rendering |
| `stat` | ✅ Tested | File status info |
| `slurp` | ✅ Tested | Read file content (base64) |
| `fetch` | ✅ Tested | Download files |
| `find` | ✅ Tested | File discovery |
| `lineinfile` | ✅ Tested | Line management |
| `blockinfile` | ✅ Tested | Block management |
| `replace` | ✅ Tested | Regex replacement |
| `tempfile` | ✅ Tested | Create temp files |
| `wait_for` | ✅ Tested | Port/file waiting |
| `pause` | ✅ Tested | Execution pause |
| `setup` | ✅ Tested | Fact gathering |
| `debug` | ✅ Tested | Print messages/vars |
| `set_fact` | ✅ Tested | Set variables |
| `fail` | ✅ Tested | Fail with message |
| `assert` | ✅ Tested | Condition checking |
| `include_vars` | ✅ Tested | Load YAML vars |
| `meta` | ✅ Tested | noop, refresh_inventory |
| `service` | ✅ Tested | Service management (check mode) |
| `systemd` | ✅ Available | Systemd service management |
| `user` | ✅ Tested | User management (check mode) |
| `group` | ✅ Tested | Group management (check mode) |
| `get_url` | ✅ Available | Download from URL |
| `uri` | ✅ Available | HTTP requests |
| `apt` | ✅ Available | Debian package management |
| `yum` | ✅ Available | RedHat package management |
| `dnf` | ✅ Available | Fedora package management |
| `pip` | ✅ Available | Python package management |
| `git` | ✅ Available | Git operations |
| `cron` | ✅ Available | Cron job management |
| `hostname` | ✅ Available | Hostname management |
| `known_hosts` | ✅ Available | SSH known hosts |
| `unarchive` | ✅ Available | Archive extraction |
| `add_host` | ✅ Available | Dynamic inventory |
| `group_by` | ✅ Available | Dynamic grouping |
| `getent` | ✅ Available | Name service lookup |
| `reboot` | ✅ Available | System reboot |
| `script` | ⚠️ Partial | Requires local script file |
| `wait_for_connection` | ✅ Available | Connection waiting |

#### Windows Modules (18+)

| Module | Status | Notes |
|--------|--------|-------|
| `win_ping` | ✅ Tested | Connection test |
| `win_command` | ✅ Tested | Windows cmd.exe |
| `win_shell` | ✅ Tested | Windows PowerShell |
| `win_copy` | ✅ Tested | Windows file copy |
| `win_file` | ✅ Tested | Windows files/directories |
| `win_stat` | ✅ Tested | File status info |
| `win_slurp` | ✅ Tested | Read file content |
| `win_template` | ⚠️ Partial | Requires local template |
| `win_service` | ✅ Tested | Service management |
| `win_lineinfile` | ✅ Tested | Line management |
| `win_wait_for` | ✅ Tested | Port/file waiting |
| `win_reboot` | ✅ Tested | System reboot (check mode) |
| `win_user` | ✅ Available | User management |
| `win_group` | ✅ Available | Group management |
| `win_get_url` | ✅ Available | Download from URL |
| `win_acl` | ✅ Available | ACL management |
| `win_environment` | ✅ Available | Environment variables |
| `win_registry` | ✅ Available | Registry management |

### Galaxy FQCN Support

| Namespace | Status | Notes |
|-----------|--------|-------|
| `ansible.builtin.*` | ✅ Tested | Maps to native modules |
| `ansible.windows.*` | ✅ Tested | Maps to native win_* modules |
| `ansible.posix.*` | ✅ Supported | Remote execution on Linux |
| `community.general.*` | ✅ Supported | Remote execution on Linux |

See [GALAXY.md](GALAXY.md) for detailed Galaxy support documentation.

### Templating

| Feature | Status | Notes |
|---------|--------|-------|
| `{{ variable }}` | ✅ Tested | Variable interpolation |
| Jinja2 expressions | ✅ Tested | In strings |
| `default` / `d` filter | ✅ Tested | Default values |
| `lower` / `upper` | ✅ Tested | Case conversion |
| `replace` | ✅ Tested | String replacement |
| `to_json` | ✅ Tested | JSON serialization |
| `to_yaml` | ✅ Tested | YAML serialization |
| `trim` | ✅ Tested | Whitespace trimming |
| `join` | ✅ Tested | List joining |
| `first` / `last` | ✅ Tested | List access |
| `length` | ✅ Tested | Collection size |
| `int` / `bool` / `string` | ✅ Tested | Type conversion |
| `basename` / `dirname` | ✅ Tested | Path manipulation |
| `regex_replace` | ✅ Tested | Regex substitution |
| `b64encode` / `b64decode` | ✅ Tested | Base64 encoding |
| `is defined` test | ✅ Tested | Variable existence |
| `is undefined` test | ✅ Tested | Variable non-existence |
| `is string/number` | ✅ Tested | Type checking |
| Custom filters | ❌ Not supported | Built-in only |
| `lookup()` | ❌ Not supported | No lookups |

### Connections

| Type | Status | Dependency | Notes |
|------|--------|------------|-------|
| `local` | ✅ Tested | None | Control node execution |
| `ssh` | ✅ Tested | `asyncssh` | Linux/Unix hosts |
| `winrm` | ✅ Tested | `pypsrp` | Windows hosts |

### CLI Options

| Option | Status | Notes |
|--------|--------|-------|
| `-i, --inventory` | ✅ Tested | Inventory file/directory |
| `-l, --limit` | ✅ Tested | Host pattern limiting |
| `-t, --tags` | ✅ Tested | Run specific tags |
| `--skip-tags` | ✅ Tested | Skip specific tags |
| `-e, --extra-vars` | ✅ Tested | Extra variables |
| `-f, --forks` | ✅ Tested | Parallel execution |
| `-C, --check` | ✅ Tested | Dry-run mode |
| `--diff` | ✅ Tested | Show file differences |
| `--json` | ✅ Tested | JSON output format |
| `--vault-password-file` | ✅ Supported | Vault password |
| `--ask-vault-pass` | ✅ Supported | Prompt for vault |
| `-v/-vv/-vvv` | ✅ Tested | Verbosity levels |

### Vault

| Feature | Status | Notes |
|---------|--------|-------|
| `--vault-password-file` | ✅ Supported | File with password |
| `--ask-vault-pass` | ✅ Supported | Interactive prompt |
| AES256 encrypted files | ✅ Supported | Requires `cryptography` |

## Not Supported

The following features are **explicitly not supported** and will raise `UnsupportedFeatureError`:

- `async` / `poll` (asynchronous task execution)
- `lookup()` functions  
- Callbacks / Plugins
- Galaxy collections install (`ansible-galaxy`)
- Network device connections (netconf, etc.)
- Custom Jinja2 filters/tests
- Complex variable precedence (simplified merging)

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Host failure(s) occurred |
| 3 | Parse/syntax error |
| 4 | Unsupported feature used |

## Test Coverage

### Unit Tests: 269 Passed

All core functionality has unit test coverage:

- Playbook parsing and execution
- Module execution (mock connections)
- Templating and filters
- Inventory parsing
- Handlers and blocks
- Tags and limits
- Vault decryption
- Galaxy FQCN resolution

### Live System Tests

| Target | Platform | Status |
|--------|----------|--------|
| Linux SSH | RHEL 8.5 | ✅ All modules working |
| Windows WinRM | Server 2019 | ✅ All modules working |

Run tests:

```bash
# Unit tests
pytest tests/unit/ -v

# Golden tests (compare vs ansible-playbook)
pytest tests/golden/ -v

# Integration tests (requires Docker)
pytest tests/integration/ -v
```
