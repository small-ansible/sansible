# Sansible Compatibility

This document defines the **exact supported subset** of Ansible features in Sansible v0.2.

## Supported Features

### Inventory

| Feature | Status | Notes |
|---------|--------|-------|
| INI format | ✅ Supported | Standard Ansible INI format |
| YAML format | ✅ Supported | Standard Ansible YAML format |
| `[group]` sections | ✅ Supported | Host grouping |
| `[group:children]` | ✅ Supported | Group inheritance |
| `[group:vars]` | ✅ Supported | Group variables |
| Host patterns (ranges) | ✅ Supported | `web[01:10].example.com` |
| Inline host vars | ✅ Supported | `host ansible_host=x ansible_user=y` |
| `host_vars/` directory | ✅ Supported | Per-host variable files |
| `group_vars/` directory | ✅ Supported | Per-group variable files |
| `--limit` pattern | ✅ Supported | Basic patterns only |
| Dynamic inventory | ❌ Not supported | Static inventory only |

### Playbooks

| Feature | Status | Notes |
|---------|--------|-------|
| Multiple plays | ✅ Supported | Sequential execution |
| `hosts` | ✅ Supported | Required per play |
| `vars` | ✅ Supported | Play-level variables |
| `vars_files` | ✅ Supported | YAML files only |
| `tasks` | ✅ Supported | Task list |
| `gather_facts: false` | ✅ Supported | Default is false |
| `gather_facts: true` | ✅ Supported | Gathers OS/hostname facts |
| `handlers` | ✅ Supported | Handler sections |
| `roles` | ✅ Supported | tasks, defaults, vars |
| `pre_tasks/post_tasks` | ✅ Supported | Before/after main tasks |
| `strategy` | ❌ Not supported | Linear strategy only |

### Tasks

| Feature | Status | Notes |
|---------|--------|-------|
| `name` | ✅ Supported | Task description |
| Module invocation | ✅ Supported | See modules table |
| FQCN modules | ✅ Supported | `ansible.builtin.*` |
| `args` / inline args | ✅ Supported | Dict or `key=value` format |
| `register` | ✅ Supported | Capture output |
| `when` | ✅ Supported | Boolean/Jinja expressions |
| `loop` / `with_items` | ✅ Supported | List iteration only |
| `loop_control` | ⚠️ Partial | `loop_var` only |
| `ignore_errors` | ✅ Supported | Continue on failure |
| `changed_when` | ✅ Supported | Override changed status |
| `failed_when` | ✅ Supported | Override failed status |
| `notify` | ✅ Supported | Trigger handlers |
| `become` | ✅ Supported | sudo, su methods |
| `become_user` | ✅ Supported | Target user |
| `become_method` | ✅ Supported | sudo (default), su |
| `block/rescue/always` | ✅ Supported | Error handling blocks |
| `tags` | ✅ Supported | Task tagging |
| `delegate_to` | ❌ Not supported | Direct execution only |
| `async/poll` | ❌ Not supported | Synchronous only |
| `include_tasks` | ❌ Not supported | Single file only |
| `import_tasks` | ❌ Not supported | Single file only |

### Modules

#### Linux Modules

| Module | Status | Notes |
|--------|--------|-------|
| `command` | ✅ Supported | No shell processing |
| `shell` | ✅ Supported | Full shell support |
| `raw` | ✅ Supported | Direct execution |
| `copy` | ✅ Supported | File/content copy |
| `file` | ✅ Supported | Files/directories/links |
| `template` | ✅ Supported | Jinja2 template rendering |
| `stat` | ✅ Supported | File status info |
| `lineinfile` | ✅ Supported | Line management |
| `wait_for` | ✅ Supported | Port/file waiting |
| `setup` | ✅ Supported | Fact gathering |
| `debug` | ✅ Supported | Print messages/vars |
| `set_fact` | ✅ Supported | Set variables |
| `fail` | ✅ Supported | Fail with message |
| `assert` | ✅ Supported | Condition checking |

#### Windows Modules

| Module | Status | Notes |
|--------|--------|-------|
| `win_command` | ✅ Supported | Windows cmd.exe |
| `win_shell` | ✅ Supported | Windows PowerShell |
| `win_copy` | ✅ Supported | Windows file copy |
| `win_file` | ✅ Supported | Windows files/directories |
| `win_service` | ✅ Supported | Service management |
| `win_stat` | ✅ Supported | File status info |
| `win_lineinfile` | ✅ Supported | Line management |
| `win_wait_for` | ✅ Supported | Port/file waiting |

### Templating

| Feature | Status | Notes |
|---------|--------|-------|
| `{{ variable }}` | ✅ Supported | Variable interpolation |
| Jinja2 expressions | ✅ Supported | In strings |
| `default` filter | ✅ Supported | Default values |
| `lower` / `upper` | ✅ Supported | Case conversion |
| `replace` | ✅ Supported | String replacement |
| `to_json` | ✅ Supported | JSON serialization |
| `to_yaml` | ✅ Supported | YAML serialization |
| `trim` | ✅ Supported | Whitespace trimming |
| `join` | ✅ Supported | List joining |
| `first` / `last` | ✅ Supported | List access |
| `basename` / `dirname` | ✅ Supported | Path manipulation |
| `regex_replace` | ✅ Supported | Regex substitution |
| `is defined` test | ✅ Supported | Variable existence |
| `is undefined` test | ✅ Supported | Variable non-existence |
| `is string/number` | ✅ Supported | Type checking |
| Custom filters | ❌ Not supported | Built-in only |
| `lookup()` | ❌ Not supported | No lookups |

### Connections

| Type | Status | Dependency | Notes |
|------|--------|------------|-------|
| `local` | ✅ Supported | None | Control node execution |
| `ssh` | ✅ Supported | `asyncssh` | Linux/Unix hosts |
| `winrm` | ✅ Supported | `pypsrp` | Windows hosts |

### CLI Options

| Option | Status | Notes |
|--------|--------|-------|
| `-i, --inventory` | ✅ Supported | Inventory file/directory |
| `-l, --limit` | ✅ Supported | Host pattern limiting |
| `-t, --tags` | ✅ Supported | Run specific tags |
| `--skip-tags` | ✅ Supported | Skip specific tags |
| `-e, --extra-vars` | ✅ Supported | Extra variables |
| `-f, --forks` | ✅ Supported | Parallel execution |
| `-C, --check` | ✅ Supported | Dry-run mode |
| `--diff` | ✅ Supported | Show file differences |
| `--json` | ✅ Supported | JSON output format |
| `-v/-vv/-vvv` | ✅ Supported | Verbosity levels |

## Not Supported

The following features are **explicitly not supported** and will raise `UnsupportedFeatureError`:

- Ansible Galaxy / Collections
- `include_tasks`, `import_tasks`
- `include_role`, `import_role`
- `delegate_to`
- `async` / `poll`
- Ansible Vault
- Callbacks / Plugins
- Dynamic inventory scripts
- Custom Jinja2 filters/tests
- `lookup()` functions
- Network device connections
- Complex variable precedence (simplified merging)

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Host failure(s) occurred |
| 3 | Parse/syntax error |
| 4 | Unsupported feature used |
